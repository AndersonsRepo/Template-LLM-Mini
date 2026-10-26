# template_llm_mini

A lightweight, standard-library Python harness for coding assistants (Claude Code,
Codex, or both side by side): **define → build → independent QC → test → memory →
done**, with a shared task board, path-scoped claims, and hooks that enforce the
rules that should never depend on a model remembering them.

Python 3.11+ is enough. No model server, SDK, database, or third-party packages.
The assistant supplies model access, delegation, and compaction.

## Layout

| Path | Purpose |
|---|---|
| `AGENTS.md` / `CLAUDE.md` | Agent entry point (Codex reads AGENTS.md; CLAUDE.md imports it) |
| `templates/agent_rules.md` | Shared rules; becomes the project AGENTS.md on configure |
| `agents/<role>.md` | All role definitions (add-on roles are marked `requires:`) |
| `scripts/workflow.py` | Task lifecycle, claims, evidence, journal (all state writes) |
| `scripts/guard.py` | Mechanical rule checks used by every hook |
| `.claude/settings.json` | Claude Code hooks and `WORKFLOW_AGENT=claude` |
| `githooks/pre-commit` | Tool-agnostic commit checks |
| `addons/data_analysis/` | Optional fetcher and analyzer roles, approved-source fetching, inspection, profiling |
| `logging/` | Decision journal (`journal.jsonl` canonical, `journal.md` generated) |
| `docs/template-history/` | How the template itself was built; delete in your project if unwanted |

## Configure

Paste [the initialization primer](prompts/template_prompt_initialization.md) with
its placeholders filled in, or ask the assistant to read AGENTS.md and configure the
harness. It runs the [interview](CONFIGURE.md), then asks for approval:

```sh
git init                      # if needed; configure installs the commit hook
cp templates/config.json project-config.json   # fill in the agreed answers
python3 scripts/workflow.py validate-config --config project-config.json
python3 scripts/workflow.py configure --config project-config.json --approved
```

List unused template components in `prune` (see CONFIGURE.md, "Template
cleanup"); configure deletes them so the project carries only what it uses.

Configuring writes PROJECT.md, the project AGENTS.md, `.workflow/config.json`,
the task board, and `.claude/agents/*.md` generated from the role definitions, and
sets `core.hooksPath=githooks`. The approval flag records the coordinator's
assertion of consent; it cannot authenticate the user.

## Agents side by side

Each agent sets an identity: Claude Code gets `WORKFLOW_AGENT=claude` from
`.claude/settings.json`. For Codex, export `WORKFLOW_AGENT=codex` in its
environment (or pass `--agent codex`). Unset means `local`.

```sh
python3 scripts/workflow.py add --title 'API endpoint' --criterion 'GET /items works' \
    --path 'src/api/**' --path 'tests/test_api.py' --prompt request.md
python3 scripts/workflow.py start T001        # claims T001 for this agent (lease)
python3 scripts/workflow.py status            # board as JSON; tasks.md is the same board
python3 scripts/workflow.py claim T002 --ttl 60
python3 scripts/workflow.py heartbeat T001    # extend the lease
python3 scripts/workflow.py scope T001 --path 'src/api/**' --path 'src/models.py'
python3 scripts/workflow.py release T002
```

- Every mutation takes a file lock (`.workflow/lock`), so concurrent agents cannot
  corrupt state. Waiting is capped by `WORKFLOW_LOCK_TIMEOUT` (default 300 s).
- A claim stops other agents from changing that task or claiming a task whose
  paths overlap it. Overlap is conservative: `src/**` overlaps `src/api/x.py`.
- `delegation.max_concurrency` caps how many agents hold claims at once.
- Expired leases can be taken over; `done` releases the claim.
- `review_mode: cross-agent` requires a different agent to record the review.
- Agent identity is stored on handoffs, reviews, tests, and journal entries.
- When agents share one checkout, use a branch or `git worktree` per claimed task.

## Task flow

```sh
python3 scripts/workflow.py context T001 --role builder
python3 scripts/workflow.py handoff T001 --to reviewer --file handoff.json
python3 scripts/workflow.py review T001 --verdict pass --file review.md
python3 scripts/workflow.py handoff T001 --to tester --file handoff.json
python3 scripts/workflow.py test T001
python3 scripts/workflow.py memory T001 --file feature-memory.md
python3 scripts/workflow.py handoff T001 --to coordinator --file handoff.json
python3 scripts/workflow.py done T001
python3 scripts/workflow.py check
```

Use templates/handoff.json and templates/memory.md. A failed review or test
invalidates earlier passes and returns the task to building; exceeding
`handoffs.max_repairs` blocks it for user direction. `block`/`unblock`, `rebuild`,
`log` (scope changes), and `--depends` cover the rest. Completed tasks are
immutable; changes need a follow-up task.

Review and tests are bound to a fingerprint of `validation.source_paths` plus the
handoff's files, so later edits invalidate them. Include application source, tests,
and dependency manifests in `source_paths`. Hashes detect drift, not truth.

Validation commands are argument arrays run without a shell from the project root,
with `timeout_seconds` (1–3600). Output is discarded unless `diagnostics=summary`,
which accepts only a bounded JSON `{"summary": "..."}` from an approved wrapper.
Exit code 2 means failed checks or a pending gate; 1 means a workflow error.

## Roles

`config.roles` lists the roles (builder, reviewer, and tester are required; add
your own). Every role, including add-on roles, has `agents/<role>.md`. A role with
`requires: data_analysis` (analyzer, fetcher) loads automatically when that add-on
is enabled and is ignored otherwise; do not list it in `config.roles`.

```yaml
---
name: reviewer
description: Independently reviews a task's diff; read-only.
runtime: any            # any | claude | codex
model_hint: strong      # inherit | fast | balanced | strong
writes: []              # globs, or [task] for the claimed task's paths
tools: [read]           # read | edit | shell | web
independent_of: builder
requires: none          # or an add-on name, e.g. data_analysis
---
Short role-specific prompt.
```

`context --role` includes the policy. `sync-agents` regenerates the Claude
subagents in `.claude/agents/` (skipping `runtime: codex`). Codex is assigned a role
by pointing it at `agents/<role>.md`. The guard enforces `writes` when it knows the
role: from the Claude hook's `agent_type`, from `--role`, or from `WORKFLOW_ROLE`.

## Hooks

| Rule | Where it is enforced |
|---|---|
| Workflow-owned files are never hand-edited | Claude `PreToolUse` (Edit/Write/Bash) |
| `data/raw/` originals are read-only; new raw files need approval | Claude `PreToolUse` |
| Source edits need your own live claim covering the path | Claude `PreToolUse` (edit tools) |
| Downloads (`curl`, `wget`, WebFetch, WebSearch) need approval | `PreToolUse` ask + permissions |
| Secret-like content needs approval or redaction | `PreToolUse` ask; pre-commit block |
| No commit-hook bypass | `PreToolUse` (Bash) |
| Journal only grows; no data contents or `.env` in Git | `githooks/pre-commit` |
| Board, claims, and resume packet after compaction | Claude `SessionStart` |

Other tools can call the same checks: `workflow.py guard edit --path P`,
`guard bash --command C`, `guard session`, or `guard hook` with Claude-style JSON
on stdin (exit 2 means deny or ask). If your Codex version supports hooks, point
them at these commands; otherwise the pre-commit hook and the locked CLI still
apply. Shell checks are best-effort pattern matching, not a sandbox. Bash source
edits are not claim-checked.

## Configuration updates

```sh
python3 scripts/workflow.py update-config --config candidate.json
python3 scripts/workflow.py update-config --config candidate.json --approved --preview-hash <hash>
```

The preview shows changed fields, guidance diffs, affected tasks, and conflicts.
The hash binds the candidate, current config/state, and guidance, so a stale preview
must be redone. Revisions in `.workflow/config-revisions/` keep the old and new
configuration and prior state. Applying invalidates active evidence and keeps
completed history. Config version 2 is not compatible with version 1 projects;
migrate those by building a fresh candidate from templates/config.json.

## Decision journal

```sh
python3 scripts/workflow.py decide --task T001 --file decision.json
python3 scripts/workflow.py journal --task T001
python3 scripts/workflow.py journal --id J000004 --full
python3 scripts/workflow.py decide --file revised.json --supersedes J000004
```

Configuration, task creation and completion, and config updates add milestones
automatically; agents record significant decisions explicitly. Queries are compact
by default (latest 20, 6000 characters). See [logging/README.md](logging/README.md).

## Data

`data/raw/` holds read-only originals, `processed/` transformations, and
`generated/` synthetic data. Git ignores contents except `.gitkeep` and
`data.approved_fixtures`. The optional analyzer, the fetcher (pulls from approved
sources into versioned `data/raw/` folders and parses them into `data/processed/`),
dataset contracts, provenance, and profiling live in [addons/data_analysis](addons/data_analysis/README.md);
enable them with `addons.data_analysis: true` plus an `analysis` section copied
from `addons/data_analysis/config.json`.

## State and evidence

`.workflow/state.json` is authoritative; `tasks.md` and `memories/index.md` are
generated. Keep state, artifacts, and config revisions together in Git. Multi-file
updates are not one transaction.

## Validate

```sh
python3 -m unittest discover -s tests -v
```

Tests use isolated temporary copies and make no provider calls.

## License

[MIT No Attribution](LICENSE) (MIT-0): use, copy, and modify freely, with no notice
required. Projects created from the template may choose their own license.
