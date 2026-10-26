# Multi-agent coordination, hooks, roles, and add-on split

Behavior: every workflow mutation runs under `.workflow/lock`. Tasks declare `--path`
globs; `start`/`claim` take a lease for the agent named by `WORKFLOW_AGENT`. Other
agents cannot mutate a claimed task or claim overlapping paths (conservative prefix
overlap); one agent may overlap its own tasks. `max_concurrency` counts agents.
`cross-agent` review mode needs a different reviewing agent. Agent identity is
recorded on artifacts and journal entries (`agent` field; legacy records accepted).
`tasks.md` is a board table.

`scripts/guard.py` serves Claude PreToolUse/SessionStart hooks, `githooks/pre-commit`,
and manual `guard edit|bash|commit|session` calls. It denies hand edits to
workflow-owned files and raw originals, source edits without the agent's own live
claim, and hook bypasses. It asks before downloads, new raw files, and secret-like
content; at commit time it blocks journal rewrites, data/.env files, and secrets.
Hook errors fail closed.

Roles live in `agents/<role>.md` with frontmatter (runtime, model_hint, writes,
tools, independent_of); `sync-agents` generates `.claude/agents/`. Config version 2
adds `addons`, `coordination`, `data.approved_fixtures`, and custom roles; the data
analyzer, inspection, profiling, and provenance moved to `addons/data_analysis/`.

Limitations: Bash checks are pattern-based and do not claim-check source edits;
Codex hook support was not verified, so Codex relies on the locked CLI, the
pre-commit hook, and explicit guard calls. Version 1 configs need a rebuilt candidate.

Follow-up (same day): the data add-on gained a fetcher role and `fetch TASK --source`.
Sources are registered in `analysis.sources` (approval = config approval); Python
fetch/parse scripts write to staging, then results publish to new timestamped
folders under data/raw/ and data/processed/ only if every step succeeds. A fetch
manifest feeds provenance and lineage into inspection.

Follow-up: all role definitions live in agents/; add-on roles declare
`requires: data_analysis` and load only when that add-on is enabled. Config gained
`prune` (data_analysis, template_history, initialization_primer,
configuration_interview, claude_integration); configure or an approved update-config
deletes those components, and the interview recommends pruning everything unused.
