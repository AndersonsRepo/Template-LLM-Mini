# Configuration interview

Present ALL topics below at the beginning, explain choices and fixed constraints,
and prefill known answers for confirmation. Offer recommended defaults for batch
acceptance. Resolve missing, conflicting, or ambiguous choices before implementation.
Follow templates/agent_rules.md for approval and Python/model boundaries.

Record answers in a copy of templates/config.json. Every field is required (analysis.datasets and data.provenance may be []); use
`none` or `not applicable` explicitly for inapplicable text. Show the completed
brief, configuration, proposed changes, and validation plan for explicit approval
before `configure --config project-config.json --approved`.

| Topic | Ask | Default / implementation |
|---|---|---|
| Project | Name, purpose, users, scope, exclusions, observable acceptance? | One focused deliverable |
| Technology | Languages, frameworks, dependencies, environment? | Python for ALL deterministic components; native tools may be invoked |
| Data | Usage during setup or later, sources, sensitivity, size, retention, outputs, Git exceptions? | Read-only raw/; transformations processed/; synthetic/model generated/; contents ignored |
| Evidence quality | Confirm external-data staging, download approvals, source/locator availability, lineage, and unknown handling? | ./data only; explicit download approval; source unavailable/unknown rather than invented content |
| Roles | Builder, reviewer, tester, conditional analyzer, optional specialists? | Three required roles plus automatic analyzer when data is relevant |
| Analysis | Expected datasets, phase, formats, columns, minimum records, meaning, size/file limits, access? | analysis phases pre/post; auto discovery or explicit datasets; metadata-only; max_file_bytes=5000000; max_files=100 |
| Data quality | Column types, nullable/unique rules, numeric bounds, strict JSON, and date expectations? | Optional column_rules={}; reject ambiguous/nonfinite JSON; see templates/column_rules.json |
| Profiling | Approve aggregate summaries for selected data, limits, and sensitivity? | Disabled; enable only with approved-summaries; max_columns=20, max_chars=6000; no rows/category values |
| Configuration updates | Version, dry-run checks, approval preview and active task reset? | config_version=1; validate-config is read-only; update-config needs approval and matching preview hash |
| Delegation | Capabilities, concurrency, independent review or approved fallback? | Independent QC; concurrency 1; coordinator alone writes state |
| Handoffs | Routing, context requirements, repair allowance? | Fixed structured fields; handoffs/; two repair cycles |
| Tasks | Granularity, dependencies, evidence, done criteria? | One reviewable feature; built-in states; evidence freshness |
| Prompts | Major-prompt definition, retention, exclusions? | Requests, scope changes, exact assignments; reference evidence without copying it |
| Decision journal | Which choices count as significant; retention, evidence links, retrieval budget, and sensitive exclusions? | logging/journal.jsonl plus generated Markdown; significant choices/milestones; relevant alternatives; compact latest 20/6000 characters; full records on request; retain in Git; no raw data/secrets |
| Memory | Durable decisions, feature updates, relevant retrieval? | Preserve template index and project feature memories |
| Tokens/context | Desired context size, compaction triggers, output expectations, usage availability? | context.max_chars=12000; focused packets and structured checkpoints |
| Validation coverage | Which source directories, tests, manifests, and files affect behavior? | validation.source_paths defaults cover harness; add application paths; reviewer references extend coverage |
| Validation execution | Commands, timeout, diagnostics, summary limits, manual checks? | Argument arrays; timeout_seconds=60; diagnostics=off; summary_max_chars=2000 |
| Approvals | Clarify material questions before plans; confirm approval for ALL feature enhancements, substantial fixes, download actions, and progress expectations? | Small-task exception applies only to clear fixes/maintenance adding no functionality; ask when uncertain; setup always needs approval |
| Delivery | Documentation, deployment, supported environments, definition of done? | Evidence, review, executed tests, memory |
| Execution boundary | Any ambiguous deterministic/judgment components? | Clarify before implementing; record boundary_decisions |

Confirm raw/Git policies. Never modify/delete originals during processing; authorize
retention deletion separately. Document exact approved small fixtures or `none`.
These fields do not implement OS protection or edit .gitignore.

Distinguish Python-enforced settings (types, role names, source selection, artifact
checks, data inspection/phase gates, context size, timeout, diagnostics, repair transitions) from assistant
policies (approval, actual concurrency, independent delegation, compaction,
sensitivity, retention, semantic criteria, and Python-only application work).
The script cannot authenticate human approval, launch agents, or compact context.
Paths, states, roles, and handoff fields are fixed; changing them needs reviewed code.

Source fingerprints skip data, workflow artifacts, environments, caches, and build
outputs. Selected data has a separate version fingerprint for analysis and downstream
evidence. Discuss task relevance, expected data, and semantic suitability explicitly. Choose all relevant source
roots so added/deleted files are detected. Sources outside selection are not covered.
For diagnostic summaries, approve a Python wrapper that emits sanitized summary JSON;
raw stdout/stderr is never automatically retained. No automatic redaction is promised.

If independent agents are unavailable, request an independent review session or
explicit approval for a same-agent fallback. Keep builder, QC, and testing even
when a small task does not need a separate approval plan.

For analysis.datasets, use templates/dataset.json: required/optional input or output,
path under data/, phase, supported format, required columns, min_records, and purpose.
With no specs, raw/ and other data locations are pre inputs; processed/generated are
post outputs. Use explicit specs for other timing or --dataset task selections.
Only UTF-8 CSV/JSON/JSONL/text/Markdown are inspected natively; approve Python extraction
for other formats. Ask about sensitivity before authorizing selected summaries.

At intake the coordinator records auto/expected/none task relevance. A request that
implies missing data must use expected; this inference is model judgment, not a
Python keyword rule. Missing/unsuitable data or semantic mismatch requires a user
question and pauses dependent work. Never fabricate or silently substitute data.
Both pre/post analysis run when relevant. No data means no analyzer model call.
Builder writes processors, coordinator executes, analyzer interprets; QC/test remain.

The shared rules are mandatory ground rules, not defaults to silently weaken.
External evidence must be staged under ./data; obtain explicit approval before
any downloads. Project code/instructions and workflow records remain accessible.
Record known origins/locators/lineage using data.provenance entries from
templates/provenance.json (or [] if unknown). Missing details must say source
unavailable. Original generated content needs no invented source; externally
derived facts still need attribution. Unknown is correct when evidence cannot
answer the question. Do not promise that metadata checks guarantee factual truth.

Confirm that architecture/convention/workflow changes update the appropriate
instructions, README, interview/configuration, role prompts, primer, and tests.
Keep communication concise and preserve decisions, sources, and unknowns while
pruning context. All material questions must be clarified before generating a
feature plan; every feature enhancement needs explicit approval, regardless of size.

Normalize dataset paths before matching rules; explicit selections must overlap
requested phases. Already inspected data cannot disappear into a skipped phase:
ask for restoration or an approved scope change. Reinspect pending stale evidence
before model work. Current phase, question, inspection, and role references take
priority over generic settings in compact context.

For optional profiling, approve the selected datasets and statistics explicitly.
Aggregates can still reveal sensitive facts. It works before the analyzer's initial
verdict, so there is no need to approve an uninformed analysis to build a profiler.
Column type rules do not rewrite input values; CSV integer/number/boolean checks
use controlled coercion, date requires YYYY-MM-DD, and unique ignores nullable blanks.

Discuss versioned lineage: recorded parent hashes describe observed local parents,
not proof of the producer's original inputs. Historical manifests remain intact.
For updates, validate and preview candidate config, inspect changed fields and task
impact, then obtain approval before --approved --preview-hash. Dataset scope changes
reset active scope explicitly; unrelated edits preserve previously inspected inputs.

The journal's location and core record schema are fixed; no additional config keys
are required. Record agreed scope/retention in the memory policy field. Preserve
existing entries; initial configure does not reset a prior project journal. Python
automatically records initial configuration, task creation/completion, and applied
config updates. Models/coordinator identify significant decisions; these cannot
be inferred reliably from lifecycle events. Prefer journal filters to full-history
context. Logging paths are excluded from source fingerprints, not from Git.

Journal retrieval compaction is an on-demand Python projection, not extra stored
summary content or a model call. Confirm the count/character expectations; CLI
--limit/--max-chars override defaults without new config keys. --all removes count
limits only, and --full is explicit for original fields. Saved-record/view-failure
responses must repair the view instead of appending duplicates. Markdown escaping
changes display only; JSONL preserves original text.
