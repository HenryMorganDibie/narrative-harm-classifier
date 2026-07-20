# Core Concepts

A short glossary — useful if you're reading this after hearing a talk about the project rather than
coming in as an engineer.

- **Target group / identity axis** — who the text is about: an ethnic, religious, gender,
  national-origin, or political group. The engine only ever flags harm *against* a named group — text
  with no identifiable target group is never flagged (`require_target_present` in the taxonomy).
- **Harm mechanism** — *how* the text is harmful. Six are currently implemented:
  `animalization`, `demonization`, `objectification`, `criminalization`, `direct_call_to_violence`,
  and `false_attribution`. These map to three broader categories: `dehumanization`, `incitement`,
  and `narrative_distortion`.
- **Taxonomy** — the versioned YAML file (`taxonomy_v1.yaml`) that defines every harm mechanism, its
  detection weight, and its decision threshold. Every classification result is stamped with the
  taxonomy version it was produced under, so results stay reproducible even as the taxonomy evolves.
- **Severity ladder** — a simplified ordering of harm mechanisms from least to most severe
  (`none → narrative_distortion → demonization/objectification → animalization/criminalization →
  direct_call_to_violence`), used only for escalation tracking. It is a project-specific model
  inspired by general atrocity-escalation literature, **not** a validated academic scale — see
  [Escalation-Chain Tracking](features/escalation-tracking.md).
- **Source** — an arbitrary identifier you choose (an account handle, a URL, a document ID) that
  ties a sequence of classified texts together so escalation can be tracked across them.
- **Benchmark test type** — a label on each benchmark case describing *what capability it tests*
  (does the engine handle negation? counter-speech? disguised spelling?), so a single aggregate
  accuracy number can't hide a specific, important blind spot. See
  [Benchmark Suite](features/benchmark.md).
- **Language confidence** — every classification is tagged `verified` (English, Spanish, French,
  Russian, Arabic — well-resourced languages with the same detection rigor) or `experimental` (Igbo,
  Yoruba, Hausa — a seed vocabulary, not native-speaker-reviewed). See
  [Multilingual Support](features/multilingual.md).
- **Dog-whistle** — a coded term with a specific, documented bigoted meaning ("globalist" as an
  antisemitic conspiracy trope) that reads as innocuous to anyone unfamiliar with it. Detected as an
  additional signal source alongside the taxonomy, not a separate system. See
  [Dog-whistle Lexicon](features/dogwhistles.md).
- **Content hash / record hash** — a SHA-256 fingerprint of what was classified (`content_hash`) and,
  for tracked sources, a hash chain over the observation history (`record_hash`) that makes tampering
  with a historical record detectable. See
  [Provenance & Tamper-Evidence](features/provenance.md).
