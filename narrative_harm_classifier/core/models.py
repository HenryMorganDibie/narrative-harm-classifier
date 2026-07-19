"""
core/models.py — Pydantic schemas for request/response and internal classification objects.
"""

from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum
from datetime import datetime


class HarmCategory(str, Enum):
    DEHUMANIZATION = "dehumanization"
    INCITEMENT = "incitement"
    NARRATIVE_DISTORTION = "narrative_distortion"
    NONE = "none"


class TargetType(str, Enum):
    ETHNIC_GROUP = "ethnic_group"
    RELIGIOUS_GROUP = "religious_group"
    GENDER_GROUP = "gender_group"
    NATIONAL_ORIGIN_GROUP = "national_origin_group"
    POLITICAL_GROUP = "political_group"
    UNKNOWN = "unknown"


class IdentityAxis(str, Enum):
    RACE_ETHNICITY = "race_ethnicity"
    RELIGION = "religion"
    GENDER = "gender"
    NATIONAL_ORIGIN = "national_origin"
    POLITICAL_AFFILIATION = "political_affiliation"
    UNKNOWN = "unknown"


# --- Request ---

class ClassifyRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=10000, description="Text to classify")
    context: Optional[str] = Field(None, description="Optional surrounding context")
    request_id: Optional[str] = Field(None, description="Client-supplied idempotency key")
    language: str = Field(
        "en",
        description=(
            "ISO 639-1 language code of the text (explicit, not auto-detected). "
            "Falls back to English with a rationale note if the code isn't available."
        ),
    )


class BatchClassifyRequest(BaseModel):
    items: list[ClassifyRequest] = Field(..., min_length=1, max_length=100)


# --- Internal signal ---

class SignalMatch(BaseModel):
    row_id: str
    harm_mechanism: str
    target_type: TargetType
    identity_axis: IdentityAxis
    signal_weight: float
    matched_pattern: Optional[str] = None
    azure_sentiment_score: Optional[float] = None
    azure_entity_detected: Optional[str] = None


# --- Response ---

class ClassificationResult(BaseModel):
    request_id: Optional[str] = None
    text_excerpt: str = Field(..., description="First 200 chars of input text")
    is_harmful: bool
    harm_category: HarmCategory
    confidence: float = Field(..., ge=0.0, le=1.0)
    target_type: Optional[TargetType] = None
    identity_axis: Optional[IdentityAxis] = None
    harm_mechanism: Optional[str] = None
    signals_matched: list[SignalMatch] = []
    decision_rationale: str
    taxonomy_version: str
    language: str = Field("en", description="Language the text was classified as (echoes the request)")
    language_confidence: str = Field(
        "verified",
        description="'verified' (well-resourced language) or 'experimental' (seed vocabulary, not native-speaker-reviewed)",
    )
    dogwhistle_matched: Optional[str] = Field(
        None, description="Coded-language term that contributed a signal, if any"
    )
    counter_narrative_guidance: Optional[str] = Field(
        None, description="General counter-messaging guidance for the matched harm mechanism, when harmful"
    )
    content_hash: str = Field(
        ..., description="SHA-256 of (text, context, taxonomy_version) — deterministic, for provenance"
    )
    classified_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        use_enum_values = True


class BatchClassificationResult(BaseModel):
    results: list[ClassificationResult]
    total: int
    harmful_count: int
    taxonomy_version: str
    processed_at: datetime = Field(default_factory=datetime.utcnow)


# --- Validation / metrics ---

class ValidationSample(BaseModel):
    text: str
    expected_is_harmful: bool
    expected_category: Optional[HarmCategory] = None


class ValidationReport(BaseModel):
    category: str
    taxonomy_version: str
    sample_count: int
    true_positives: int
    false_positives: int
    true_negatives: int
    false_negatives: int
    precision: float
    recall: float
    fpr: float  # false positive rate
    f1: float
    meets_precision_threshold: bool
    meets_recall_threshold: bool
    meets_fpr_threshold: bool
    passes: bool
    validated_at: datetime = Field(default_factory=datetime.utcnow)
