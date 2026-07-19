"""
classifier/counter_narrative.py — General counter-narrative guidance per harm mechanism.

Deliberately general, templated guidance grounded in the public
"acknowledge -> redirect -> inform" counter-messaging framework (the
methodology behind projects like Moonshot CVE and the Redirect Method), not
auto-generated bespoke rebuttal text for the specific input. Generating
custom rebuttal text is a materially harder, riskier text-generation problem
(prone to tone-deaf or factually wrong output) and is out of scope here —
this gives a human moderator/responder a starting frame, not a script to
paste verbatim.
"""

from typing import Optional

_GUIDANCE: dict[str, str] = {
    "animalization": (
        "Dehumanizing comparisons (to animals, vermin, disease) are a documented precursor to "
        "real-world violence against targeted groups. Effective counter-messaging typically: "
        "(1) avoids repeating or amplifying the dehumanizing frame itself, (2) affirms the "
        "target group's humanity with specific, concrete facts rather than abstract appeals, "
        "(3) redirects toward the underlying grievance being exploited, if any."
    ),
    "demonization": (
        "Framing a group as evil or supernaturally malevolent shuts down empathy and factual "
        "engagement. Counter-messaging typically works better by naming the rhetorical move "
        "explicitly (\"this frames an entire group as inherently evil\") and redirecting to "
        "specific, falsifiable claims rather than arguing the moral framing directly."
    ),
    "objectification": (
        "Reducing a group to objects or property strips away agency and interiority. "
        "Counter-messaging typically centers first-person voices from the affected group and "
        "concrete examples of agency, rather than abstract arguments against the framing."
    ),
    "criminalization": (
        "Blanket criminal framing of a group is usually contradicted by the actual data. "
        "Effective counter-messaging leads with accurate, sourced statistics and specific "
        "counterexamples rather than general appeals not to stereotype."
    ),
    "direct_call_to_violence": (
        "Explicit calls to violence should typically be escalated for human review and, where "
        "applicable, reported to platform trust & safety or law enforcement channels rather than "
        "countered by automated messaging alone. If counter-messaging is used at all, prioritize "
        "de-escalation and directing at-risk viewers toward support resources over debating the "
        "claim itself."
    ),
    "false_attribution": (
        "Claims about a group's supposed hidden agenda are typically unfalsifiable by design. "
        "Counter-messaging tends to work better by asking what specific, checkable evidence is "
        "being offered (usually none) rather than trying to disprove an unfalsifiable claim "
        "directly."
    ),
}

_DEFAULT_GUIDANCE = (
    "Consider whether a direct rebuttal, a redirect to factual information, or escalation to "
    "human review is the most appropriate response before responding automatically."
)


def guidance_for(harm_mechanism: Optional[str]) -> Optional[str]:
    """Return general counter-narrative guidance for a harm mechanism, or None if harmless."""
    if not harm_mechanism:
        return None
    return _GUIDANCE.get(harm_mechanism, _DEFAULT_GUIDANCE)
