# Reliability and compact context

Source/config fingerprints bind review, executed tests, memory, and final handoff
to the current task cycle. Selected directories detect added/deleted files;
reviewer source references extend coverage. Dataset/workflow/cache paths are
excluded. Drift invalidates active passes at gated mutations. Completed history
checks saved evidence without comparing to later project changes.

Artifacts have recorded SHA-256 digests. done/check share evidence checks; hashes
are drift detection rather than signatures. State schema is version 2; old adopted
state requires a separately reviewed migration.

status/show/context provide focused reads. Context limits omit entire optional
sections explicitly, without truncating criteria. checkpoint saves progress
without moving stages; resume flags source/cycle/stage drift. Assignment logs
store instructions and references rather than duplicate handoff bodies.

Agent policies are maintained in templates/agent_rules.md; generated AGENTS.md
uses those rules without embedding configuration. The coordinator alone mutates
state. Template history comes from memories/template-index.md and survives saves.
Diagnostics default off. Approved wrappers may emit bounded sanitized JSON
summaries; no automatic redaction is provided. Configurable timeouts accept
1..3600 seconds. All automation uses the Python standard library.

Behavioral tests cover source changes, missing/altered/stale evidence, completed
history, data exclusions, checkpoints, context limits, diagnostics, and adoption
from an already configured project. Test copies exclude application state/data
and environments. No model usage or percentage token savings are measured.
