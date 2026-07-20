# FAQ

**Is this a genocide/violence prediction tool?**
No. It classifies text against a harm taxonomy and tracks whether a source's rhetoric is trending
toward more severe categories over time. It does not predict real-world violence, and the severity
ladder it uses is a simplified, project-specific model *inspired by* general escalation research —
not a validated academic or forecasting instrument. Treat its output as a prioritization signal for
human review, not a verdict.

**How is this different from Perspective API / other toxicity classifiers?**
Most toxicity APIs score a single message for general toxicity. This is narrower and more specific
(it requires a named target group and a specific harm mechanism, not general rudeness), fully
transparent (every decision has a plain-language rationale and a versioned taxonomy behind it, no
black-box model), and adds a temporal dimension (escalation tracking across a source) that most
single-message APIs don't attempt.

**Why rules/regex instead of a machine-learning or LLM-based classifier?**
Transparency and reproducibility were prioritized over raw accuracy: every decision can be traced to
a specific matched pattern and taxonomy row, and results are stable across time given the same
taxonomy version. Negation, counter-speech, and obfuscated spelling are handled through explainable
heuristics (a negation-cue window, a reporting+condemnation cue pair, a character-substitution map —
see [Contributing](contributing.md#how-the-engine-handles-negation-counter-speech-and-obfuscation))
rather than genuine language understanding, so they generalize only as far as those heuristics reach.
An LLM-assisted or hybrid engine is on the [roadmap](status-roadmap.md) for the cases that fall
outside them, and contributions in that direction are welcome.

**Can I use my own taxonomy or add new harm mechanisms?**
Yes — the taxonomy is just a YAML file (`TAXONOMY_CONFIG_PATH` to override it), and the pattern list
per mechanism per language lives in `data/patterns/<lang>.yaml`. See [Contributing](contributing.md).

**Does it work in languages other than English?**
Yes, for 7 additional languages — Spanish, French, Russian, and Arabic at the same detection rigor as
English; Igbo, Yoruba, and Hausa as smaller, explicitly `experimental` seed vocabularies (see
[Multilingual Support](features/multilingual.md)). Any other language falls back to English rather
than silently misclassifying. None of the eight — including the "verified" tier — have had
native-speaker domain-expert review yet.

**What's a "dog-whistle" and why does the engine check for them separately?**
A coded term with a specific, documented bigoted meaning that looks innocuous without that context
(e.g. "globalist" as an antisemitic conspiracy trope). It's not checked "separately" in the sense of a
second decision path — it contributes a signal through the exact same scoring pipeline as a taxonomy
row, still gated by the same identity-anchor requirement. See
[Dog-whistle Lexicon](features/dogwhistles.md).

**Does the counter-narrative guidance write a rebuttal for me?**
No — it's general, templated guidance for the matched harm mechanism (e.g. "lead with accurate
statistics" for criminalization-framed content), not a custom-generated rebuttal for your specific
input. Auto-generating bespoke rebuttal text is a harder, riskier problem (tone-deaf or factually
wrong output) that's out of scope here. See [Counter-Narrative Guidance](features/counter-narrative.md).

**What does the provenance hash actually protect against?**
It makes tampering with a stored observation *detectable* (recomputing the chain shows exactly which
record no longer matches), not *impossible* — someone with direct database write access could still
recompute the whole chain to hide an edit. It's a tamper-evidence mechanism, not encryption or access
control; pair it with real database security for anything that matters. See
[Provenance & Tamper-Evidence](features/provenance.md).

**Is the severity ladder / escalation model scientifically validated?**
No, and the docs and code comments say so deliberately. It's a simplified, explainable ordering
inspired by general narrative-escalation research (see [Why this exists](index.md#why-this-exists)),
built so a human can audit *why* a trend was flagged — not a peer-reviewed forecasting model.
