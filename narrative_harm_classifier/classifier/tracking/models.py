"""
classifier/tracking/models.py — Escalation-chain data model.

Tracks a *source* (an account, outlet, or document stream identified by an
arbitrary caller-supplied source_id) across multiple classified observations,
and scores whether its rhetoric is climbing a harm-escalation ladder rather
than treating each text as an isolated event.

The severity ladder below is a simplified, project-specific model inspired by
general narrative-escalation research (e.g. othering -> dehumanization ->
criminalization -> violence calls). It is not a validated academic scale —
it exists to give a consistent, explainable ordering across taxonomy rows so
trend direction can be computed deterministically.
"""

from datetime import datetime
from enum import IntEnum
from typing import Optional

from pydantic import BaseModel, Field


class SeverityLevel(IntEnum):
    NONE = 0
    NARRATIVE_DISTORTION = 1
    DEMONIZATION_OBJECTIFICATION = 2
    ANIMALIZATION_CRIMINALIZATION = 3
    DIRECT_VIOLENCE_CALL = 4


# harm_mechanism -> severity, per the ladder above
HARM_MECHANISM_SEVERITY: dict[str, SeverityLevel] = {
    "false_attribution": SeverityLevel.NARRATIVE_DISTORTION,
    "demonization": SeverityLevel.DEMONIZATION_OBJECTIFICATION,
    "objectification": SeverityLevel.DEMONIZATION_OBJECTIFICATION,
    "animalization": SeverityLevel.ANIMALIZATION_CRIMINALIZATION,
    "criminalization": SeverityLevel.ANIMALIZATION_CRIMINALIZATION,
    "direct_call_to_violence": SeverityLevel.DIRECT_VIOLENCE_CALL,
}


def severity_for_mechanism(harm_mechanism: Optional[str]) -> SeverityLevel:
    if not harm_mechanism:
        return SeverityLevel.NONE
    return HARM_MECHANISM_SEVERITY.get(harm_mechanism, SeverityLevel.NONE)


class Observation(BaseModel):
    id: Optional[int] = None
    source_id: str
    text_excerpt: str
    is_harmful: bool
    harm_category: str
    harm_mechanism: Optional[str] = None
    confidence: float
    severity: SeverityLevel
    observed_at: datetime = Field(default_factory=datetime.utcnow)


class SourceProfile(BaseModel):
    source_id: str
    observation_count: int
    current_severity: SeverityLevel
    rolling_avg_severity: float
    trend: str  # "escalating" | "stable" | "de-escalating" | "insufficient_data"
    risk_level: str  # "low" | "watch" | "elevated" | "critical"
    history: list[Observation] = []


RISK_LEVELS = ("low", "watch", "elevated", "critical")


def risk_level_for(current_severity: SeverityLevel, trend: str) -> str:
    """
    Deterministic risk mapping: base risk from current severity, bumped up one
    level when the trend is escalating. Kept simple and explainable rather than
    a learned model, consistent with the rest of this project's rationale-driven
    design.
    """
    if current_severity == SeverityLevel.NONE:
        base = 0
    elif current_severity == SeverityLevel.NARRATIVE_DISTORTION:
        base = 1
    elif current_severity == SeverityLevel.DEMONIZATION_OBJECTIFICATION:
        base = 2
    else:  # ANIMALIZATION_CRIMINALIZATION or DIRECT_VIOLENCE_CALL
        base = 3

    if trend == "escalating" and base < 3:
        base += 1

    return RISK_LEVELS[base]
