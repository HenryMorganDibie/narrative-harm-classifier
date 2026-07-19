"""
classifier/rules/patterns_loader.py — Per-language detection vocabulary.

Loads data/patterns/<lang>.yaml files into a LanguagePatterns object with
precompiled regexes (explicit precompilation rather than relying on Python's
internal re.compile cache — deliberate now that pattern volume grows with
each added language and the dog-whistle lexicon).

Every file declares a `confidence` of "verified" or "experimental" — see
README's Limitations section for what that distinction means in practice.
Not every language has negation/counter-speech/benign-context cues defined;
missing ones are treated as "no suppression available in this language yet"
rather than silently reused from English.
"""

import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Optional

from narrative_harm_classifier.core.yaml_loader import load_yaml_file

DEFAULT_LANGUAGE = "en"


def _compile_all(patterns: list[str]) -> list[re.Pattern]:
    return [re.compile(p, re.IGNORECASE) for p in patterns]


def _compile_dict(d: dict[str, list[str]]) -> dict[str, list[re.Pattern]]:
    return {key: _compile_all(patterns) for key, patterns in d.items()}


def _combine_and_compile(cue_list: Optional[list[str]]) -> Optional[re.Pattern]:
    """Join a YAML list of literal cue phrases into a single compiled alternation."""
    if not cue_list:
        return None
    alternation = "|".join(re.escape(cue) for cue in cue_list)
    return re.compile(rf"\b({alternation})\b", re.IGNORECASE)


@dataclass
class LanguagePatterns:
    language: str
    confidence: str  # "verified" | "experimental"
    identity_anchors: dict[str, list[re.Pattern]] = field(default_factory=dict)
    harm_patterns: dict[str, list[re.Pattern]] = field(default_factory=dict)
    negation_cues: Optional[re.Pattern] = None
    reporting_cues: Optional[re.Pattern] = None
    condemnation_cues: Optional[re.Pattern] = None
    benign_context_cues: Optional[re.Pattern] = None
    obfuscation_map: dict[str, str] = field(default_factory=dict)

    def deobfuscate(self, text_lower: str) -> str:
        if not self.obfuscation_map:
            return text_lower
        return text_lower.translate(str.maketrans(self.obfuscation_map))


@lru_cache(maxsize=32)
def load_language_patterns(patterns_dir: str, language: str) -> LanguagePatterns:
    """
    Load and precompile a language's detection vocabulary.

    Raises FileNotFoundError if the language isn't available — callers should
    catch this and fall back to DEFAULT_LANGUAGE rather than let a typo
    silently produce empty (always-no-harm) patterns.
    """
    path = Path(patterns_dir) / f"{language}.yaml"
    raw = load_yaml_file(path)

    return LanguagePatterns(
        language=raw["language"],
        confidence=raw["confidence"],
        identity_anchors=_compile_dict(raw.get("identity_anchors", {})),
        harm_patterns=_compile_dict(raw.get("harm_patterns", {})),
        negation_cues=_combine_and_compile(raw.get("negation_cues")),
        reporting_cues=_combine_and_compile(raw.get("reporting_cues")),
        condemnation_cues=_combine_and_compile(raw.get("condemnation_cues")),
        benign_context_cues=_combine_and_compile(raw.get("benign_context_cues")),
        obfuscation_map=raw.get("obfuscation_map") or {},
    )


def available_languages(patterns_dir: str) -> list[str]:
    return sorted(p.stem for p in Path(patterns_dir).glob("*.yaml"))
