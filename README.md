# template_llm_mini

A standard-library Python harness for a coding assistant: **define → optional input
analysis → build → optional output analysis → QC → test → memory → done**.
Python 3.11+ is sufficient; no model server, SDK, database, or third-party packages
are required. The assistant supplies model access, delegation, and compaction.

## Initialize and configure

Use [the initialization primer](prompts/template_prompt_initialization.md), replacing
its <placeholders>, or ask the assistant to read AGENTS.md and configure the harness.
Asking “What is the template prompt initialization?” displays it unchanged.

The assistant presents all [configuration questions](CONFIGURE.md), clarifies material
questions, and proposes a brief/configuration/change/validation plan for approval.
Copy templates/config.json to project-config.json and complete the agreed answers.
Before initial configuration, preflight is read-only:

```sh
python3 scripts/workflow.py validate-config --config project-config.json
python3 scripts/workflow.py configure --config project-config.json --approved
```

Configuration generates PROJECT.md, project-specific AGENTS.md, canonical
.workflow/config.json, task state, and indexes. Shared rules come from
[templates/agent_rules.md](templates/agent_rules.md), without embedding all config.
Approval flags record the coordinator's assertion of actual consent; they cannot
authenticate the user. This reusable working template remains unconfigured.

## Ground rules

All deterministic functionality uses Python; models supply judgment. Every feature
enhancement needs an approved plan after material questions are clarified. Only
clear fixes/maintenance adding no functionality may use the small-task exception.
Ask when uncertain. Keep logging, QC, tests, and feature memories in either case.

External evidence is read only from ./data. Downloads into it require explicit
approval; no downloader is provided. Project code/instructions and internal workflow
evidence remain accessible. Attribute factual claims to available files/locators,
origins, and lineage. State source unavailable or unknown instead of inventing
facts, citations, or results. Original drafts, code, and labeled synthetic content
need no invented external source; externally derived facts still need attribution.

Changes to architecture, conventions, roles, or workflow update the appropriate
instructions, documentation, interview/configuration, prompts, and tests. Keep
communication concise and checkpoint decisions, sources, unknowns, and next actions
before compaction. Full policy is in templates/agent_rules.md.

## Task flow

Only the coordinator runs workflow mutations; workers return reports and handoffs.
Serialize writes: there is no cross-process locking. Redact secrets before storage.

```sh
python3 scripts/workflow.py add --title 'Example feature' --criterion 'Observable behavior' --prompt request.md
python3 scripts/workflow.py start T001
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

Use templates/handoff.json, analysis.md, and memory.md; refresh handoff content for
each recipient. Source files in handoffs must exist and remain source-only; dataset
references travel in inspection evidence. Passing input analysis resumes building;
output analysis follows Python processing and precedes independent QC. Analysis
may pause these commands—see [data-analysis guidance](docs/data-analysis.md).

Use review --verdict fail for findings. Rejection/failure invalidates passes and
returns work to building; exceeding max_repairs blocks it for user direction.
`block TASK --file reason.md` / `unblock TASK` handle other blockers. `log TASK
--file request.md` records scope changes; `add ... --depends T001` declares dependencies.
Completed tasks are historical; changes use follow-ups. Independent QC is default;
unavailable delegation requires an approved independent-session or same-agent fallback.
Never describe role switching as independent. Python logs/delivers artifacts; the
assistant actually routes assignments.

## Focused context and evidence

```sh
python3 scripts/workflow.py status
python3 scripts/workflow.py status --all
python3 scripts/workflow.py show T001
python3 scripts/workflow.py checkpoint T001 --file handoff.json
python3 scripts/workflow.py resume T001 --role analyzer
```

Context packets prioritize current role evidence over generic settings. They retain
phase/question/reference and stale warnings, and list whole sections omitted under
context.max_chars. Read role_instruction_ref if its full text was omitted. Core
criteria are not silently truncated; narrow the task or increase --max-chars if
necessary. Character limits are not token accounting. No measured saving is claimed.

Checkpoints do not advance stages. Reinspect stale analyzer evidence before any
model call. Source/configuration fingerprints bind review/tests to relevant files;
set validation.source_paths to include application source, tests, and dependency
manifests. Reviewer file references extend coverage. Selected data and observed
lineage versions have separate manifests. Completed history checks saved evidence,
not later source changes. Hashes detect drift, not truth or independent review.

Validation commands are argument arrays run without a shell from the project root.
Configure timeout_seconds (1–3600). Nonzero exits, timeouts, launch failures, or
selected-input changes fail validation. Exit 2 indicates failed checks or a pending
analysis/input gate; ordinary workflow errors exit 1. Child-process supervision is
not provided. Diagnostics default off; opt-in summary mode expects approved Python
wrappers emitting bounded JSON {"summary":"..."}. No automatic redaction exists.

## Approved configuration updates

Preflight validates configuration without changing files. For an existing project:

```sh
python3 scripts/workflow.py update-config --config candidate.json
python3 scripts/workflow.py update-config --config candidate.json --approved --preview-hash <preview_hash>
```

Review the displayed changes, affected tasks, data-scope changes, and conflicts;
obtain approval before apply. The hash binds candidate, current config/state, and
shared rules; a stale preview must be refreshed and approved again. Revisions in
.workflow/config-revisions/ preserve old/new configuration and prior state. Apply
regenerates project instructions/brief and invalidates active evidence while keeping
completed history. Changing dataset scope explicitly resets active analysis scope;
unrelated config edits retain previously inspected input expectations.

Config version 1 adds profiling defaults. For older schema-3 projects, build a
complete candidate from templates/config.json and copy agreed values; update-config
can preview against old stored config without overwriting history. Older state
schemas need a separate reviewed migration. Multi-file updates are not a database
transaction; a prepared revision preserves recovery information if writing fails.

## Data and persistence

Use data/raw/ for read-only originals, processed/ for transformations, generated/
for synthetic/model data. Do not overwrite/delete originals during processing.
Git ignores contents except approved fixtures and placeholders. No OS read-only
protection or automatic retention deletion is included. Record origins in
data.provenance using templates/provenance.json; default unknowns remain explicit.
Details on strict JSON, column rules, profiling, and lineage are in docs/data-analysis.md.

.workflow/state.json is authoritative; tasks.md and memories/index.md are generated.
Keep state, artifacts, and config revisions together. Preserve template history via
memories/template-index.md; add project memories after features. Do not routinely
load full history into agent context.

## Running decision journal

Significant choices now have one chronological journal under logging/, alongside
existing prompt logs, task evidence, and feature memories. journal.jsonl is canonical;
journal.md is generated. Record the decision, rationale, relevant alternatives,
outcome, status, and existing evidence references using templates/decision.json:

```sh
python3 scripts/workflow.py decide --task T001 --file decision.json
python3 scripts/workflow.py journal --task T001
python3 scripts/workflow.py journal --type decision --limit 10
python3 scripts/workflow.py decide --task T002 --file revised-decision.json --supersedes J000004
python3 scripts/workflow.py journal --id J000004 --full
python3 scripts/workflow.py journal --render
```

Omit --task for project-level decisions, including before configuration. The CLI
checks that specified tasks exist. IDs include both decisions and milestones;
supersedes must identify a decision. Accepted superseding entries leave old bytes
intact; filtered results still identify cross-task supersession. Default retrieval
is compact, latest 20, within 6000 characters; --max-chars adjusts the cap. Compact
previews are deterministic and created only for the query, not stored or generated
by a model. --full retrieves original fields. --all removes only the count limit;
omitted/clipped content is explicit. Reference journal IDs from memories rather
than duplicating contents. Full records that exceed the cap are omitted whole.

Configuration approval, task creation/completion, and applied config updates append
automatic milestones. Preview/read commands do not append records. Agents must
submit significant decisions explicitly: the script cannot prove completeness or
verify actual human consent. Secrets/raw data and routine tool chatter are excluded
by policy, not automatic redaction. Journal changes do not invalidate source checks.
If Markdown rendering fails after a successful append, the saved ID is returned
with a warning; do not repeat the append. Use journal --render to repair the view.
Markdown display escaping preserves original JSONL text. Keep the journal in Git;
it is append-only through commands, not tamper-proof storage.
See [logging/README.md](logging/README.md) for recovery and retention details.

## Validate

```sh
python3 -m unittest discover -s tests -v
```

Tests use allowlisted temporary copies rather than application data, environments,
or live state and run before/after customization. Select a license before external
distribution. No provider calls or external data are needed for validation.
