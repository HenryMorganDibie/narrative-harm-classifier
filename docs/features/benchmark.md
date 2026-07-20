# Benchmark Suite

The original validation set was 18 hand-picked examples, and it reported precision 1.0 / recall
0.875 — numbers that sound clean mostly because the test set was small and easy.
`narrative_harm_classifier/data/benchmark_templates.yaml` instead generates a much larger, systematic
test suite (~190 cases) modeled on the [HateCheck](https://arxiv.org/abs/2012.15606) methodology:
templates are tagged with a `test_type` and slot-filled across five identity groups, so a regression
in one specific capability is visible even when the aggregate looks fine, and the same rhetorical
pattern is tested identically across groups (cross-group consistency — does the engine behave the
same regardless of *which* group is named).

| test_type | what it checks |
|---|---|
| `explicit_positive` | clear, unambiguous harmful language |
| `implicit_positive` | harmful meaning without trigger words (recall probe) |
| `negation` | the harmful claim is negated — should NOT be flagged |
| `counter_speech` | harmful rhetoric quoted to condemn it — should NOT be flagged |
| `obfuscated_spelling` | trigger words altered to evade literal matching |
| `benign_trigger_word` | standalone hard negatives (trigger words in benign context, some with a group present) |

Run it with `nhc benchmark run` or `POST /benchmark/run`.

```text
Taxonomy version: 1.0.0
Total cases:      192

TEST TYPE             N     PRECISION  RECALL   FPR     F1
overall               192   1.0        1.0      0.0     1.0
benign_trigger_word   12    0.0        0.0      0.0     0.0
counter_speech        30    0.0        0.0      0.0     0.0
explicit_positive     60    1.0        1.0      0.0     1.0
implicit_positive     30    1.0        1.0      0.0     1.0
negation              30    0.0        0.0      0.0     0.0
obfuscated_spelling   30    1.0        1.0      0.0     1.0

Cross-group consistency: 36/36 templates consistent across groups
```

!!! note
    `negation`, `counter_speech`, and `benign_trigger_word` are entirely hard negatives — no positives
    exist in those buckets, so precision/recall are mathematically undefined and reported as `0.0` by
    convention. **FPR is the number that matters for those rows, and it's `0.0`**: zero false positives.

This is enforced in CI (`tests/benchmark/`), not just reported — a pull request that regresses
precision, recall, FPR, or cross-group consistency fails the build. The engine handles negation (via
a negation-cue window before a match), counter-speech (via a reporting-cue + condemnation-cue
heuristic), obfuscated/leetspeak spelling (via character-substitution normalization), and a set of
implicit phrasings (via additional patterns) — see
[Contributing](../contributing.md#how-the-engine-handles-negation-counter-speech-and-obfuscation) for
exactly how each heuristic works and its limits.

!!! warning "Read that honestly, not as 'solved'"
    A clean pass on this 192-case suite means the engine handles *this* benchmark's negation,
    counter-speech, and obfuscation patterns correctly — it does not mean adversarial evasion is a
    solved problem in general. These are heuristics (a negation window, a cue-word allowlist, a fixed
    character-substitution map), not language understanding, and real-world text will eventually find
    phrasings outside them. The point of the benchmark isn't "we're done" — it's that any future gap
    like that gets added as a new test case, so it can't regress silently once it's fixed. That's also
    why [escalation tracking](escalation-tracking.md) exists alongside single-text classification: a
    trend across many observations is more robust than any one classification being right.

The cross-group consistency check also caught a genuine bug during development: several templates
fired for every identity group *except* one political-affiliation phrasing, because the underlying
regex only matched singular forms (`democrat`, not `democrats`). That's fixed now (36/36 consistent),
and it's a good example of what this check is for.
