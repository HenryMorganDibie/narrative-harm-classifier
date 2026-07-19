"""
classifier/rules/engine.py — Multi-dimensional, multi-language classification engine.

Implements D2.4a specification: operationalizes relationships between
targets, identities, harm mechanisms, and decision thresholds.

Architecture:
  1. Signal detection  — pattern matching (per-language) + dog-whistle lexicon
                          + Azure NLP entity/sentiment signals
  2. Suppression       — negation / counter-speech / benign-context heuristics
  3. Signal scoring    — weighted aggregation per taxonomy row
  4. Multi-signal resolution — ambiguity rules from taxonomy config
  5. Decision          — threshold gating with rationale + provenance hash
"""

import re
import logging
from pathlib import Path
from typing import Optional

from narrative_harm_classifier.core.models import (
    ClassifyRequest,
    ClassificationResult,
    SignalMatch,
    HarmCategory,
    TargetType,
    IdentityAxis,
)
from narrative_harm_classifier.classifier.taxonomy.loader import TaxonomyConfig, TaxonomyRow, CategorySpec
from narrative_harm_classifier.classifier.rules.azure_nlp import AzureNLPClient, AzureNLPResult
from narrative_harm_classifier.classifier.rules.patterns_loader import (
    LanguagePatterns,
    load_language_patterns,
    DEFAULT_LANGUAGE,
)
from narrative_harm_classifier.classifier.rules.dogwhistles import DogwhistleLexicon, DogwhistleEntry
from narrative_harm_classifier.classifier.counter_narrative import guidance_for
from narrative_harm_classifier.classifier.provenance import content_hash

logger = logging.getLogger(__name__)

DEFAULT_PATTERNS_DIR = str(Path(__file__).parent.parent.parent / "data" / "patterns")

# Negation cues are checked in a window immediately before a matched harm
# pattern ("these people are NOT vermin"), rather than across the whole
# text, so an unrelated un-negated claim later in the same text isn't
# suppressed by a negation word that has nothing to do with it.
_NEGATION_WINDOW_CHARS = 60


# ---------------------------------------------------------------------------
# Signal detection
# ---------------------------------------------------------------------------

def _detect_identity_anchor(text: str, patterns: LanguagePatterns) -> Optional[str]:
    """Return the identity axis if a group mention is found in the text."""
    text_lower = text.lower()
    deobf_lower = patterns.deobfuscate(text_lower)
    for axis, compiled_patterns in patterns.identity_anchors.items():
        for compiled in compiled_patterns:
            if compiled.search(text_lower) or compiled.search(deobf_lower):
                return axis
    return None


def _detect_harm_signals(
    text: str, row: TaxonomyRow, patterns: LanguagePatterns
) -> tuple[bool, Optional[str], Optional[re.Match], str]:
    """
    Check text against harm patterns for a given taxonomy row, against both
    the literal text and a deobfuscated ("v3rmin" -> "vermin") version.

    Returns (matched, matched_pattern, match_object, matched_text_lower) — the
    match object and the text version it was found in are returned so callers
    can run negation-window / counter-speech checks against the same text
    the match actually came from.
    """
    text_lower = text.lower()
    deobf_lower = patterns.deobfuscate(text_lower)
    compiled_patterns = patterns.harm_patterns.get(row.harm_mechanism, [])
    for compiled in compiled_patterns:
        match = compiled.search(text_lower)
        if match:
            return True, compiled.pattern, match, text_lower
        match = compiled.search(deobf_lower)
        if match:
            return True, compiled.pattern, match, deobf_lower
    return False, None, None, text_lower


def _azure_negative_amplifier(azure_result: Optional[AzureNLPResult]) -> float:
    """
    Use Azure sentiment negativity as a signal amplifier (0.0 → 1.0).
    High negative sentiment boosts confidence; neutral is neutral.
    Falls back to 1.0 (no penalty) when Azure is unavailable.
    """
    if azure_result is None or azure_result.is_fallback:
        return 1.0  # no penalty when Azure not configured
    # Map: 0.0 negative → 0.2, 1.0 negative → 1.0
    return 0.2 + (azure_result.sentiment_score_negative * 0.8)


# ---------------------------------------------------------------------------
# Suppression pipeline — negation / counter-speech / benign-context
# ---------------------------------------------------------------------------
# Each rule answers "should this matched signal be discarded?" A match is
# suppressed if ANY rule fires. Extracted into a uniform list (rather than
# three separate inline `if` statements) so a new heuristic — or a new
# language's cues — plugs in without restructuring classify() again.

def _rule_negation(matched_text: str, match_obj: Optional[re.Match], patterns: LanguagePatterns) -> bool:
    if patterns.negation_cues is None or match_obj is None:
        return False
    window = matched_text[max(0, match_obj.start() - _NEGATION_WINDOW_CHARS) : match_obj.start()]
    return bool(patterns.negation_cues.search(window))


def _rule_counter_speech(matched_text: str, match_obj: Optional[re.Match], patterns: LanguagePatterns) -> bool:
    if patterns.reporting_cues is None or patterns.condemnation_cues is None:
        return False
    return bool(patterns.reporting_cues.search(matched_text)) and bool(
        patterns.condemnation_cues.search(matched_text)
    )


def _rule_benign_context(matched_text: str, match_obj: Optional[re.Match], patterns: LanguagePatterns) -> bool:
    if patterns.benign_context_cues is None:
        return False
    return bool(patterns.benign_context_cues.search(matched_text))


_SUPPRESSION_RULES = (_rule_counter_speech, _rule_negation, _rule_benign_context)


def _is_suppressed(matched_text: str, match_obj: Optional[re.Match], patterns: LanguagePatterns) -> bool:
    return any(rule(matched_text, match_obj, patterns) for rule in _SUPPRESSION_RULES)


# identity_axis -> TargetType, shared by taxonomy rows and dog-whistle entries
_AXIS_TO_TARGET_TYPE = {
    "race_ethnicity": TargetType.ETHNIC_GROUP,
    "religion": TargetType.RELIGIOUS_GROUP,
    "gender": TargetType.GENDER_GROUP,
    "national_origin": TargetType.NATIONAL_ORIGIN_GROUP,
    "political_affiliation": TargetType.POLITICAL_GROUP,
}


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

class ClassificationEngine:
    """
    Multi-signal, multi-language classification engine implementing the
    D2.4a spec plus an optional dog-whistle lexicon.

    Signal resolution order:
      1. Load the request's language vocabulary (falls back to English)
      2. Identity anchor check (require_target_present rule)
      3. Per-row harm pattern matching + dog-whistle lexicon matching
      4. Suppression (negation / counter-speech / benign-context)
      5. Azure NLP sentiment amplification
      6. Weighted score aggregation
      7. Ambiguity resolution (highest_weight_wins / conservative tie-break)
      8. Threshold decision + provenance hash + counter-narrative guidance
    """

    def __init__(
        self,
        taxonomy: TaxonomyConfig,
        azure_client: Optional[AzureNLPClient] = None,
        patterns_dir: Optional[str] = None,
        dogwhistles: Optional[DogwhistleLexicon] = None,
    ):
        self.taxonomy = taxonomy
        self.azure = azure_client or AzureNLPClient()  # fallback mode if no creds
        self.patterns_dir = patterns_dir or DEFAULT_PATTERNS_DIR
        self.dogwhistles = dogwhistles
        # harm_mechanism -> category name, derived once from the taxonomy,
        # so dog-whistle matches (which name a harm_mechanism directly, not
        # a category) can be scored through the same pipeline as taxonomy rows.
        self._mechanism_to_category = {row.harm_mechanism: category for category, row in taxonomy.all_rows()}

    def _load_patterns(self, requested_language: str) -> tuple[LanguagePatterns, Optional[str]]:
        try:
            return load_language_patterns(self.patterns_dir, requested_language), None
        except FileNotFoundError:
            fallback = load_language_patterns(self.patterns_dir, DEFAULT_LANGUAGE)
            return fallback, f"Language '{requested_language}' not available — fell back to '{DEFAULT_LANGUAGE}'."

    def classify(self, request: ClassifyRequest) -> ClassificationResult:
        text = request.text
        full_text = f"{request.context or ''} {text}".strip()
        patterns, language_fallback_note = self._load_patterns(request.language or DEFAULT_LANGUAGE)
        hash_value = content_hash(text, request.context, self.taxonomy.version)

        # Step 1: Run Azure NLP (non-blocking — fallback if unavailable)
        azure_result = self.azure.analyze(full_text)

        # Step 2: Check for identity anchor (target group presence)
        identity_axis_detected = _detect_identity_anchor(full_text, patterns)

        rules = self.taxonomy.ambiguity_rules
        if rules.require_target_present and not identity_axis_detected:
            rationale = "No target group identity detected — require_target_present=True"
            if language_fallback_note:
                rationale += f" {language_fallback_note}"
            return self._no_harm_result(request, rationale, patterns, hash_value)

        # Step 3: Score each taxonomy row + dog-whistle lexicon entries.
        # Each signal carries its own decision_threshold directly (rather
        # than being re-derived later via a row_id lookup) so a dog-whistle
        # match — which has no corresponding taxonomy row — can't fall
        # through to an unrelated config value as a threshold.
        # Each entry: (score, SignalMatch, CategorySpec, dogwhistle_term_or_None, decision_threshold)
        signal_matches: list[tuple[float, SignalMatch, CategorySpec, Optional[str], float]] = []
        azure_amp = _azure_negative_amplifier(azure_result)

        for category, row in self.taxonomy.all_rows():
            harm_matched, pattern, match_obj, matched_text = _detect_harm_signals(full_text, row, patterns)
            if not harm_matched:
                continue
            if _is_suppressed(matched_text, match_obj, patterns):
                continue

            cat_spec = self.taxonomy.get_category(category)
            score = row.signal_weight * azure_amp
            match = SignalMatch(
                row_id=row.row_id,
                harm_mechanism=row.harm_mechanism,
                target_type=TargetType(row.target_type) if row.target_type in TargetType._value2member_map_ else TargetType.UNKNOWN,
                identity_axis=IdentityAxis(row.identity_axis) if row.identity_axis in IdentityAxis._value2member_map_ else IdentityAxis.UNKNOWN,
                signal_weight=row.signal_weight,
                matched_pattern=pattern,
                azure_sentiment_score=azure_result.sentiment_score_negative if not azure_result.is_fallback else None,
                azure_entity_detected=None,
            )
            signal_matches.append((score, match, cat_spec, None, row.decision_threshold))

        if self.dogwhistles is not None:
            for entry in self.dogwhistles.detect(full_text):
                category = self._mechanism_to_category.get(entry.harm_mechanism)
                cat_spec = self.taxonomy.get_category(category) if category else None
                if cat_spec is None:
                    continue  # dog-whistle maps to a mechanism this taxonomy doesn't define
                score = entry.signal_weight * azure_amp
                match = SignalMatch(
                    row_id=f"DOGWHISTLE:{entry.term}",
                    harm_mechanism=entry.harm_mechanism,
                    target_type=_AXIS_TO_TARGET_TYPE.get(entry.identity_axis, TargetType.UNKNOWN),
                    identity_axis=IdentityAxis(entry.identity_axis) if entry.identity_axis in IdentityAxis._value2member_map_ else IdentityAxis.UNKNOWN,
                    signal_weight=entry.signal_weight,
                    matched_pattern=entry.term,
                    azure_sentiment_score=azure_result.sentiment_score_negative if not azure_result.is_fallback else None,
                    azure_entity_detected=None,
                )
                signal_matches.append((score, match, cat_spec, entry.term, entry.decision_threshold))

        # Step 4: Check min_signal_count
        if len(signal_matches) < rules.min_signal_count:
            rationale = f"Signal count {len(signal_matches)} below minimum {rules.min_signal_count}"
            return self._no_harm_result(request, rationale, patterns, hash_value)

        # Step 5: Ambiguity resolution — highest_weight_wins
        if rules.multi_signal_conflict == "highest_weight_wins":
            signal_matches.sort(key=lambda x: x[0], reverse=True)

        best_score, best_match, best_cat, best_dogwhistle_term, threshold = signal_matches[0]

        # Step 6: Threshold decision
        # Conservative tie-break
        if best_score == threshold and rules.threshold_tie == "conservative":
            is_harmful = True
        else:
            is_harmful = best_score >= threshold

        all_matches = [m for _, m, _, _, _ in signal_matches]

        rationale = self._build_rationale(
            is_harmful, best_score, threshold, best_match, azure_result, identity_axis_detected
        )
        if language_fallback_note:
            rationale += f" {language_fallback_note}"

        category_map = {
            "dehumanization": HarmCategory.DEHUMANIZATION,
            "incitement": HarmCategory.INCITEMENT,
            "narrative_distortion": HarmCategory.NARRATIVE_DISTORTION,
        }

        return ClassificationResult(
            request_id=request.request_id,
            text_excerpt=text[:200],
            is_harmful=is_harmful,
            harm_category=category_map.get(best_cat.name, HarmCategory.NONE) if is_harmful else HarmCategory.NONE,
            confidence=round(min(best_score, 1.0), 4),
            target_type=best_match.target_type if is_harmful else None,
            identity_axis=best_match.identity_axis if is_harmful else None,
            harm_mechanism=best_match.harm_mechanism if is_harmful else None,
            signals_matched=all_matches,
            decision_rationale=rationale,
            taxonomy_version=self.taxonomy.version,
            language=patterns.language,
            language_confidence=patterns.confidence,
            dogwhistle_matched=best_dogwhistle_term if is_harmful else None,
            counter_narrative_guidance=guidance_for(best_match.harm_mechanism) if is_harmful else None,
            content_hash=hash_value,
        )

    def _no_harm_result(
        self, request: ClassifyRequest, rationale: str, patterns: LanguagePatterns, hash_value: str
    ) -> ClassificationResult:
        return ClassificationResult(
            request_id=request.request_id,
            text_excerpt=request.text[:200],
            is_harmful=False,
            harm_category=HarmCategory.NONE,
            confidence=0.0,
            signals_matched=[],
            decision_rationale=rationale,
            taxonomy_version=self.taxonomy.version,
            language=patterns.language,
            language_confidence=patterns.confidence,
            content_hash=hash_value,
        )

    def _build_rationale(
        self,
        is_harmful: bool,
        score: float,
        threshold: float,
        match: SignalMatch,
        azure: AzureNLPResult,
        identity_axis: Optional[str],
    ) -> str:
        parts = []
        if is_harmful:
            # Use the axis actually detected in the text rather than the
            # matched row's static tag when both are available — the two
            # can differ (a row tagged race_ethnicity can still fire on text
            # whose only identity anchor is national_origin), and reporting
            # both a static "targeting X" and a detected "Identity axis: Y"
            # in the same rationale read as self-contradictory.
            axis_for_rationale = identity_axis or match.identity_axis.value
            parts.append(f"HARM DETECTED: {match.harm_mechanism} targeting {axis_for_rationale}.")
            parts.append(f"Confidence {score:.3f} ≥ threshold {threshold:.3f}.")
            parts.append(f"Matched row {match.row_id}.")
        else:
            parts.append(f"NO HARM: score {score:.3f} below threshold {threshold:.3f}.")

        if not azure.is_fallback:
            parts.append(f"Azure sentiment: {azure.sentiment} (neg={azure.sentiment_score_negative:.2f}).")
        else:
            parts.append("Azure NLP: fallback mode (no credentials).")

        if identity_axis:
            parts.append(f"Identity axis detected: {identity_axis}.")

        return " ".join(parts)
