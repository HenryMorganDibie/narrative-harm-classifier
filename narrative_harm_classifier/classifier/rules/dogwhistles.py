"""
classifier/rules/dogwhistles.py — Curated coded-language ("dog-whistle") lexicon.

A dog-whistle match is treated as an additional signal source in the same
scoring pipeline as a taxonomy row — see engine.py — not a separate decision
path. It still requires an identity anchor to be present in the text (the
same require_target_present gate applies), which limits false-positive risk
on the more ambiguous terms in the seed list.

See data/dogwhistles.yaml for the actual entries and their public sourcing.
"""

import re
from dataclasses import dataclass
from functools import lru_cache

from narrative_harm_classifier.core.yaml_loader import load_yaml_file

# identity_axis -> TargetType value, mirrors the mapping taxonomy rows use.
AXIS_TO_TARGET_TYPE = {
    "race_ethnicity": "ethnic_group",
    "religion": "religious_group",
    "gender": "gender_group",
    "national_origin": "national_origin_group",
    "political_affiliation": "political_group",
}


@dataclass(frozen=True)
class DogwhistleEntry:
    term: str
    harm_mechanism: str
    identity_axis: str
    signal_weight: float
    decision_threshold: float
    source_note: str

    @property
    def target_type(self) -> str:
        return AXIS_TO_TARGET_TYPE.get(self.identity_axis, "unknown")


class DogwhistleLexicon:
    def __init__(self, entries: list[DogwhistleEntry]):
        self.entries = entries
        self._pattern_to_entry: list[tuple[re.Pattern, DogwhistleEntry]] = [
            (re.compile(r"\b" + re.escape(e.term) + r"\b", re.IGNORECASE), e) for e in entries
        ]

    def detect(self, text: str) -> list[DogwhistleEntry]:
        return [entry for pattern, entry in self._pattern_to_entry if pattern.search(text)]


@lru_cache(maxsize=4)
def load_dogwhistles(path: str) -> DogwhistleLexicon:
    raw = load_yaml_file(path)
    entries = [
        DogwhistleEntry(
            term=e["term"],
            harm_mechanism=e["harm_mechanism"],
            identity_axis=e["identity_axis"],
            signal_weight=e["signal_weight"],
            decision_threshold=e.get("decision_threshold", e["signal_weight"]),
            source_note=e["source_note"].strip(),
        )
        for e in raw.get("entries", [])
    ]
    return DogwhistleLexicon(entries)
