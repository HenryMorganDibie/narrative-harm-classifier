"""
classifier/tracking/tracker.py — Escalation-chain scoring.

Computes trend and risk level from simple, explainable arithmetic over a
rolling window of observations (first-half vs second-half average severity
delta), rather than a learned model — consistent with the rest of this
project's rationale-driven design.
"""

from narrative_harm_classifier.core.models import ClassifyRequest
from narrative_harm_classifier.classifier.rules.engine import ClassificationEngine
from narrative_harm_classifier.classifier.tracking.models import (
    Observation,
    SourceProfile,
    SeverityLevel,
    severity_for_mechanism,
    risk_level_for,
)
from narrative_harm_classifier.classifier.tracking.store import TrackingStore

# Minimum average-severity delta (second half vs first half) to call a trend
# escalating/de-escalating rather than stable. Chosen to require at least
# roughly one severity-level shift on average across the window.
TREND_THRESHOLD = 0.25

DEFAULT_WINDOW = 20


class EscalationTracker:
    def __init__(self, engine: ClassificationEngine, store: TrackingStore):
        self.engine = engine
        self.store = store

    def observe(self, source_id: str, request: ClassifyRequest) -> Observation:
        result = self.engine.classify(request)
        severity = severity_for_mechanism(result.harm_mechanism)

        obs = Observation(
            source_id=source_id,
            text_excerpt=result.text_excerpt,
            is_harmful=result.is_harmful,
            harm_category=result.harm_category,
            harm_mechanism=result.harm_mechanism,
            confidence=result.confidence,
            severity=severity,
        )
        return self.store.add_observation(obs)

    def profile(self, source_id: str, window: int = DEFAULT_WINDOW) -> SourceProfile:
        history = self.store.history(source_id, limit=window)

        if not history:
            return SourceProfile(
                source_id=source_id,
                observation_count=0,
                current_severity=SeverityLevel.NONE,
                rolling_avg_severity=0.0,
                trend="insufficient_data",
                risk_level="low",
                history=[],
            )

        severities = [int(o.severity) for o in history]
        current_severity = history[-1].severity
        rolling_avg = sum(severities) / len(severities)

        trend = self._compute_trend(severities)
        risk_level = risk_level_for(current_severity, trend)

        return SourceProfile(
            source_id=source_id,
            observation_count=len(history),
            current_severity=current_severity,
            rolling_avg_severity=round(rolling_avg, 3),
            trend=trend,
            risk_level=risk_level,
            history=history,
        )

    def list_profiles(self, window: int = DEFAULT_WINDOW) -> list[SourceProfile]:
        profiles = [self.profile(sid, window=window) for sid in self.store.list_source_ids()]
        profiles.sort(key=lambda p: (p.current_severity, p.rolling_avg_severity), reverse=True)
        return profiles

    @staticmethod
    def _compute_trend(severities: list[int]) -> str:
        if len(severities) < 2:
            return "insufficient_data"

        midpoint = len(severities) // 2
        first_half = severities[:midpoint] if midpoint > 0 else severities[:1]
        second_half = severities[midpoint:]

        first_avg = sum(first_half) / len(first_half)
        second_avg = sum(second_half) / len(second_half)
        delta = second_avg - first_avg

        if delta >= TREND_THRESHOLD:
            return "escalating"
        if delta <= -TREND_THRESHOLD:
            return "de-escalating"
        return "stable"
