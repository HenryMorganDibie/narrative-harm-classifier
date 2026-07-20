# Counter-Narrative Guidance

When a classification is harmful, `counter_narrative_guidance` on the response gives general,
templated guidance for that specific harm mechanism, grounded in the public "acknowledge → redirect →
inform" counter-messaging framework used by projects like Moonshot CVE and the Redirect Method — for
example, criminalization-framed content gets guidance to lead with accurate statistics rather than
general appeals not to stereotype, while `direct_call_to_violence` gets guidance favoring escalation
to human review over automated counter-messaging.

This is deliberately **not** auto-generated bespoke rebuttal text for the specific input — generating
custom rebuttal text is a materially harder, riskier text-generation problem (prone to tone-deaf or
factually wrong output). What's here is a starting frame for a human moderator or responder, not a
script to paste verbatim. See `narrative_harm_classifier/classifier/counter_narrative.py` for the
full mapping.
