# Running decision journal

scripts/decision_journal.py manages logging/journal.jsonl (canonical append-only)
and logging/journal.md (generated view). decide accepts templates/decision.json,
optional --task, and --supersedes. Project decisions can precede configuration;
task references require an existing task. Proposed/accepted/rejected are recorded
declarations, not independently verified approval.

journal defaults to latest 20, supports task/type/ID filters and --all, and can
--render a missing view. Superseding decisions preserve original bytes; cross-task
queries retain superseded_by references. Commands validate journal shape and reject
corruption/partial trailing records before append. Evidence must exist when linked;
historical missing references may remain after archival. Store no raw data/secrets.

Initial configure, task creation/completion, and applied config changes append
milestones. Previews and read queries do not. Records link immutable task evidence
where available. Coordinator submits significant decisions; workers flag them.
Templates/interview/README/primer explain scope, retention, limitations, and avoiding
duplicate history. Journal content is excluded from source fingerprints.

No config keys or state-schema changes are required. No automatic deletion or
backfill occurs. Append-only is a command policy, not tamper-proof storage, and
state/journal/view writes are not a single transaction. Git preserves recovery
history. Tests cover append/supersession, filters, missing/corrupt files, render
recovery, automatic milestones, and unchanged validation after logging.
