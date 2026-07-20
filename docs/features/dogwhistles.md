# Dog-whistle Lexicon

A small, explicitly-sourced seed list (~12 entries, `narrative_harm_classifier/data/dogwhistles.yaml`)
of coded terms with a documented bigoted meaning that reads as innocuous without that context —
"globalist" and "cultural Marxism" as antisemitic conspiracy tropes, "great replacement" and "white
genocide" as white-nationalist demographic conspiracy theories, "13/50" as a racist crime-statistic
trope, "1488" and "14 words" as neo-Nazi numeric/slogan codes, and similar. Each entry cites where
it's publicly documented (ADL's Hate Symbols Database, SPLC, or academic literature on coded hate
speech) rather than being asserted without a source.

A dog-whistle match is scored through the **same pipeline** as a taxonomy row — not a separate
decision path — and still requires an identity anchor to be present in the text
(`require_target_present` applies identically). Ambiguous terms with legitimate non-bigoted uses
(e.g. "globalist" can just mean "pro-globalization") get a lower `signal_weight`; unambiguous,
purpose-built coded terms get a higher one. When a dog-whistle contributes the winning signal,
`dogwhistle_matched` on the response names the term.

This is currently English-only and, like everything in [Limitations](../limitations.md), a floor
rather than a ceiling: coded language changes faster than any static list, so this needs ongoing
curation, not a one-time build. See [Contributing](../contributing.md) for how to propose a new entry
(a public source is required).
