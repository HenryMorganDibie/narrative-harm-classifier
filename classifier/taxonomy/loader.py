"""
classifier/taxonomy/loader.py — Versioned taxonomy config loader.

Loads taxonomy_v1.yaml (or any versioned config) and provides structured access
to taxonomy rows, thresholds, and ambiguity resolution rules.
Supports M1 baseline reproducibility via version pinning.
"""

import yaml
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field
from functools import lru_cache


@dataclass
class TaxonomyRow:
    row_id: str
    target_type: str
    harm_mechanism: str
    identity_axis: str
    signal_weight: float
    decision_threshold: float
    positive_examples: list[str] = field(default_factory=list)
    negative_examples: list[str] = field(default_factory=list)


@dataclass
class CategorySpec:
    id: str
    name: str
    description: str
    priority: int
    precision_min: float
    recall_min: float
    fpr_max: float
    rows: list[TaxonomyRow] = field(default_factory=list)


@dataclass
class AmbiguityRules:
    multi_signal_conflict: str
    threshold_tie: str
    context_window_tokens: int
    require_target_present: bool
    min_signal_count: int


@dataclass
class TaxonomyConfig:
    version: str
    effective_date: str
    baseline_tag: str
    priority_category: str
    categories: list[CategorySpec]
    ambiguity_rules: AmbiguityRules

    def get_category(self, name: str) -> Optional[CategorySpec]:
        return next((c for c in self.categories if c.name == name), None)

    def get_row(self, row_id: str) -> Optional[TaxonomyRow]:
        for cat in self.categories:
            for row in cat.rows:
                if row.row_id == row_id:
                    return row
        return None

    def all_rows(self) -> list[tuple[str, TaxonomyRow]]:
        """Returns (category_name, row) pairs for all taxonomy rows."""
        result = []
        for cat in self.categories:
            for row in cat.rows:
                result.append((cat.name, row))
        return result


@lru_cache(maxsize=8)
def load_taxonomy(config_path: str) -> TaxonomyConfig:
    """Load and parse taxonomy YAML. Cached per path for performance."""
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Taxonomy config not found: {config_path}")

    with open(path) as f:
        raw = yaml.safe_load(f)

    categories = []
    for cat_raw in raw.get("categories", []):
        rows = []
        for row_raw in cat_raw.get("taxonomy_rows", []):
            rows.append(TaxonomyRow(
                row_id=row_raw["row_id"],
                target_type=row_raw["target_type"],
                harm_mechanism=row_raw["harm_mechanism"],
                identity_axis=row_raw["identity_axis"],
                signal_weight=row_raw["signal_weight"],
                decision_threshold=row_raw["decision_threshold"],
                positive_examples=row_raw.get("examples", {}).get("positive", []),
                negative_examples=row_raw.get("examples", {}).get("negative", []),
            ))

        thresholds = cat_raw.get("thresholds", {})
        categories.append(CategorySpec(
            id=cat_raw["id"],
            name=cat_raw["name"],
            description=cat_raw["description"],
            priority=cat_raw["priority"],
            precision_min=thresholds.get("precision_min", 0.70),
            recall_min=thresholds.get("recall_min", 0.65),
            fpr_max=thresholds.get("fpr_max", 0.20),
            rows=rows,
        ))

    ar = raw.get("ambiguity_rules", {})
    ambiguity_rules = AmbiguityRules(
        multi_signal_conflict=ar.get("multi_signal_conflict", "highest_weight_wins"),
        threshold_tie=ar.get("threshold_tie", "conservative"),
        context_window_tokens=ar.get("context_window_tokens", 256),
        require_target_present=ar.get("require_target_present", True),
        min_signal_count=ar.get("min_signal_count", 1),
    )

    return TaxonomyConfig(
        version=raw["version"],
        effective_date=raw["effective_date"],
        baseline_tag=raw["baseline_tag"],
        priority_category=raw["priority_category"],
        categories=categories,
        ambiguity_rules=ambiguity_rules,
    )
