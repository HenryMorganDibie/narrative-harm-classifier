"""
classifier/rules/engine.py — Multi-dimensional classification engine.

Implements D2.4a specification: operationalizes relationships between
targets, identities, harm mechanisms, and decision thresholds.

Architecture:
  1. Signal detection  — pattern matching + Azure NLP entity/sentiment signals
  2. Signal scoring    — weighted aggregation per taxonomy row
  3. Multi-signal resolution — ambiguity rules from taxonomy config
  4. Decision          — threshold gating with rationale generation
"""

import re
import logging
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

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Signal detection helpers
# ---------------------------------------------------------------------------

# Group identity anchors — used to detect whether a target group is present
IDENTITY_ANCHORS: dict[str, list[str]] = {
    "religion": [
        r"\b(christian|muslim|jewish|hindu|buddhist|sikh|atheist|catholic|protestant)\b",
        r"\b(islam|christianity|judaism|hinduism|buddhism)\b",
    ],
    "race_ethnicity": [
        r"\b(black|white|asian|hispanic|latino|arab|indigenous|native)\b",
        r"\b(african|european|chinese|mexican|korean|japanese)\b",
    ],
    "gender": [
        r"\b(women|men|female|male|nonbinary|transgender|trans)\b",
        r"\b(girls|boys|ladies|gentlemen)\b",
    ],
    "national_origin": [
        r"\b(immigrant|immigrants|refugee|refugees|foreigner|foreigners|migrant|migrants|alien|aliens)\b",
        r"\b(american|mexican|chinese|russian|iranian|north korean)\b",
    ],
    "political_affiliation": [
        r"\b(democrat|republican|liberal|conservative|socialist|communist|fascist)s?\b",
        r"\b(left.?wing|right.?wing|antifa|maga)\b",
    ],
}

# Harm mechanism signal patterns per D2.4a taxonomy
HARM_PATTERNS: dict[str, list[str]] = {
    "animalization": [
        r"\b(vermin|cockroach|rat|pest|animal|beast|savage|subhuman|ape|monkey)\b",
        r"\b(infest|swarm|plague|infestation)\b",
        r"less than human",
        r"not (even )?human",
        r"multiply(ing)? out of control",
        r"take over everything",
    ],
    "demonization": [
        r"\b(demonic|satanic|evil|devil|diabolical|sinister|vile|wicked)\b",
        r"\b(spawn of|servants? of (evil|satan|the devil))\b",
        r"pure evil",
        r"dark forces working against",
    ],
    "objectification": [
        r"\b(object|property|possession|belong to|owned by)\b",
        r"\b(exist(s)? (only |just )?(to|for) (serve|pleasure|use))\b",
        r"just (?:an? )?(?:object|thing|tool)",
        r"no value beyond what (they|it) (can |could )?provide",
    ],
    "criminalization": [
        r"\b(all .{0,20} (are |'re )?(criminal|criminal|rapist|murderer|thief|terrorist))\b",
        r"\b(bring(ing)? crime|bringing drugs|criminals and rapists)\b",
        r"\b(deport (them|all))\b",
        r"responsible for (most|all) (of )?the problems",
    ],
    "direct_call_to_violence": [
        r"\b(attack|kill|destroy|eliminate|exterminate|wipe out|get rid of)\b.{0,30}\b(them|those|these|the \w+s?)\b",
        r"\b(time to (fight|attack|eliminate))\b",
        r"\b(must (die|be (killed|eliminated|destroyed)))\b",
        r"something needs to happen to",
    ],
    "false_attribution": [
        r"\ball\s.{0,20}\s*(want to|secretly|are (all|really)?)",
        r"\b(they (all|always|never) )\b.{0,30}\b(want|plan|scheme|conspire)\b",
        r"\b(their (real|secret|true) (agenda|goal|plan))\b",
        r"goals they (won't|will not|wont) publicly admit",
    ],
}

# Common character substitutions used to evade literal keyword matching
# ("v3rmin" -> "vermin"). Applied as an additional detection pass alongside
# the original text, not a replacement for it.
_LEET_MAP = str.maketrans({"0": "o", "1": "i", "3": "e", "4": "a", "5": "s", "7": "t", "@": "a", "$": "s"})


def _deobfuscate(text_lower: str) -> str:
    return text_lower.translate(_LEET_MAP)


# Negation cues checked in a window immediately before a matched harm pattern
# ("these people are NOT vermin"). A local window (rather than whole-text)
# keeps this from suppressing an unrelated, un-negated claim later in the
# same text.
_NEGATION_CUES = re.compile(
    r"\b(not|never|no longer|false that|isn't|aren't|wasn't|weren't|"
    r"doesn't|don't|didn't|won't|wouldn't|cannot|can't)\b"
)
_NEGATION_WINDOW_CHARS = 60


def _is_negated(matched_text_lower: str, match_start: int) -> bool:
    window = matched_text_lower[max(0, match_start - _NEGATION_WINDOW_CHARS) : match_start]
    return bool(_NEGATION_CUES.search(window))


# Counter-speech: harmful rhetoric quoted in order to condemn it
# ("Calling X vermin is dangerous and dehumanizing"). Requires BOTH a
# reporting/attribution cue AND a condemnation cue somewhere in the text —
# either alone is too weak a signal and risks suppressing genuine harm.
_REPORTING_CUES = re.compile(
    r"\b(some (commentators|say)|calling|treating|politicians who say|"
    r"rhetoric claiming|conspiracy theories claiming|claims? that|people who say)\b"
)
_CONDEMNATION_CUES = re.compile(
    r"\b(dangerous|bigoted|nonsense|moral catastrophe|spreading (dangerous )?lies|"
    r"led to (real-world )?violence|caused real harm|monstrous|fuels? violence|"
    r"dehumanizing|harmful stereotype|is wrong|is false)\b"
)


def _is_counter_speech(matched_text_lower: str) -> bool:
    return bool(_REPORTING_CUES.search(matched_text_lower)) and bool(
        _CONDEMNATION_CUES.search(matched_text_lower)
    )


# Benign-context cues: a target group and a harm-pattern word can co-occur
# without the text being about harming that group ("Asian scientists study
# vermin traps"). This is a coarse allowlist, not a semantic parser — it
# covers documented hard-negative categories rather than claiming general
# sarcasm/context understanding.
_BENIGN_CONTEXT_CUES = re.compile(
    r"\b(pest control|insects?|wildlife|documentary|horror (movie|film)|"
    r"film critic|video game|self-defense class|academic|theory|statistics|"
    r"policy (debate|issue)|opposition part(y|ies))\b"
)


def _is_benign_context(matched_text_lower: str) -> bool:
    return bool(_BENIGN_CONTEXT_CUES.search(matched_text_lower))


def _detect_identity_anchor(text: str) -> Optional[str]:
    """Return the identity axis if a group mention is found in the text."""
    text_lower = text.lower()
    deobf_lower = _deobfuscate(text_lower)
    for axis, patterns in IDENTITY_ANCHORS.items():
        for pattern in patterns:
            if re.search(pattern, text_lower) or re.search(pattern, deobf_lower):
                return axis
    return None


def _detect_harm_signals(
    text: str, row: TaxonomyRow
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
    deobf_lower = _deobfuscate(text_lower)
    patterns = HARM_PATTERNS.get(row.harm_mechanism, [])
    for pattern in patterns:
        match = re.search(pattern, text_lower)
        if match:
            return True, pattern, match, text_lower
        match = re.search(pattern, deobf_lower)
        if match:
            return True, pattern, match, deobf_lower
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
# Engine
# ---------------------------------------------------------------------------

class ClassificationEngine:
    """
    Multi-signal classification engine implementing D2.4a spec.

    Signal resolution order:
      1. Identity anchor check (require_target_present rule)
      2. Per-row harm pattern matching
      3. Azure NLP sentiment amplification
      4. Weighted score aggregation
      5. Ambiguity resolution (highest_weight_wins / conservative tie-break)
      6. Threshold decision
    """

    def __init__(self, taxonomy: TaxonomyConfig, azure_client: Optional[AzureNLPClient] = None):
        self.taxonomy = taxonomy
        self.azure = azure_client or AzureNLPClient()  # fallback mode if no creds

    def classify(self, request: ClassifyRequest) -> ClassificationResult:
        text = request.text
        full_text = f"{request.context or ''} {text}".strip()

        # Step 1: Run Azure NLP (non-blocking — fallback if unavailable)
        azure_result = self.azure.analyze(full_text)

        # Step 2: Check for identity anchor (target group presence)
        identity_axis_detected = _detect_identity_anchor(full_text)

        rules = self.taxonomy.ambiguity_rules
        if rules.require_target_present and not identity_axis_detected:
            return self._no_harm_result(
                request, "No target group identity detected — require_target_present=True"
            )

        # Step 3: Score each taxonomy row
        signal_matches: list[tuple[float, SignalMatch, CategorySpec]] = []

        for category, row in self.taxonomy.all_rows():
            harm_matched, pattern, match_obj, matched_text = _detect_harm_signals(full_text, row)
            if not harm_matched:
                continue

            # Suppress signals that are negated, quoted-to-condemn (counter-speech),
            # or co-occurring with a benign-context cue rather than genuinely
            # targeting the identified group.
            if _is_counter_speech(matched_text):
                continue
            if match_obj and _is_negated(matched_text, match_obj.start()):
                continue
            if _is_benign_context(matched_text):
                continue

            cat_spec = self.taxonomy.get_category(category)

            # Weighted score: base signal weight × Azure amplifier
            azure_amp = _azure_negative_amplifier(azure_result)
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
            signal_matches.append((score, match, cat_spec))

        # Step 4: Check min_signal_count
        if len(signal_matches) < rules.min_signal_count:
            return self._no_harm_result(
                request, f"Signal count {len(signal_matches)} below minimum {rules.min_signal_count}"
            )

        # Step 5: Ambiguity resolution — highest_weight_wins
        if rules.multi_signal_conflict == "highest_weight_wins":
            signal_matches.sort(key=lambda x: x[0], reverse=True)

        best_score, best_match, best_cat = signal_matches[0]

        # Step 6: Threshold decision
        row_spec = self.taxonomy.get_row(best_match.row_id)
        threshold = row_spec.decision_threshold if row_spec else self.taxonomy.ambiguity_rules.context_window_tokens

        # Conservative tie-break
        if best_score == threshold and rules.threshold_tie == "conservative":
            is_harmful = True
        else:
            is_harmful = best_score >= threshold

        all_matches = [m for _, m, _ in signal_matches]

        rationale = self._build_rationale(
            is_harmful, best_score, threshold, best_match, azure_result, identity_axis_detected
        )

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
        )

    def _no_harm_result(self, request: ClassifyRequest, rationale: str) -> ClassificationResult:
        return ClassificationResult(
            request_id=request.request_id,
            text_excerpt=request.text[:200],
            is_harmful=False,
            harm_category=HarmCategory.NONE,
            confidence=0.0,
            signals_matched=[],
            decision_rationale=rationale,
            taxonomy_version=self.taxonomy.version,
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
            parts.append(f"HARM DETECTED: {match.harm_mechanism} targeting {match.identity_axis.value}.")
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
