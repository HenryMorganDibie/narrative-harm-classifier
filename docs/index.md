# Narrative Harm Classifier

Open-source narrative harm detection: a rule-based classification engine, escalation-chain tracking
across sources over time, and a templated benchmark suite — installable as a library, a CLI, an API,
or a container.

Detects dehumanizing, incitement, and narrative-distortion language against target groups (ethnic,
religious, gender, national-origin, political), and tracks whether a given source's rhetoric is
escalating up the harm ladder (othering → dehumanization → criminalization → violence calls) rather
than treating each text as an isolated event.

[Install & Quickstart :material-arrow-right:](quickstart.md){ .md-button .md-button--primary }
[View on GitHub :material-github:](https://github.com/HenryMorganDibie/narrative-harm-classifier){ .md-button }

## Who is this for?

Narrative Harm Classifier is designed for researchers, trust & safety teams, journalists, NGOs, and
developers who need transparent, explainable analysis of harmful narratives over time. It is intended
as a decision-support tool for human review, not as an automated enforcement or prediction system —
see [Why this exists](#why-this-exists) and the [FAQ](faq.md) for what that distinction means in
practice.

## Why this exists

Most content-moderation tooling scores a single piece of text and stops there: is *this sentence*
toxic, yes or no. But real-world incitement rarely looks like a single bad sentence — it looks like a
pattern that builds over time. Researchers who study genocide and mass-atrocity prevention (e.g.
Gregory Stanton's "10 Stages of Genocide," the escalation frameworks used by atrocity early-warning
groups) describe a recognizable progression: a group is first "othered," then dehumanized (compared
to animals, vermin, disease), then criminalized, and eventually rhetoric turns to explicit calls for
violence. By the time the violent language shows up, the earlier stages have usually been visible
for a while — the pattern is often more informative than any single post.

This project has two goals:

1. **Classify individual text** for dehumanizing, incitement, and narrative-distortion language
   against a target group — the same job most moderation tools do, done transparently (every
   decision comes with a plain-language rationale, not just a score).
2. **Track a source over time** — a social account, an outlet, a document stream — and surface
   whether its rhetoric is climbing that ladder, so a human reviewer can be pointed at "this account
   is escalating" instead of drowning in individually-unremarkable posts.

It is a **rule-based, transparent system**, not a trained ML model and not a claim to predict
violence. It's deliberately simple and inspectable — every classification and every escalation score
can be explained in plain English — which is a real trade-off against the higher raw accuracy a
large language model might offer. The [FAQ](faq.md) goes into this trade-off directly, and
[Status & Roadmap](status-roadmap.md) is explicit about what still doesn't work well.

## Where to go next

- New here? Start with [Install & Quickstart](quickstart.md).
- Want the mental model first? Read [Core Concepts](concepts.md).
- Curious about a specific feature? See [Escalation Tracking](features/escalation-tracking.md),
  [Benchmark Suite](features/benchmark.md), [Multilingual Support](features/multilingual.md),
  [Dog-whistle Lexicon](features/dogwhistles.md), [Counter-Narrative Guidance](features/counter-narrative.md),
  or [Provenance & Tamper-Evidence](features/provenance.md).
- Evaluating this for real use? Read [Limitations](limitations.md) first, then [Performance](performance.md).
- Want to contribute? See [Contributing](contributing.md).
