Initialize customization of the harness at <path_to_template_llm_mini>.

My project:
- Name: <project_name>
- Purpose: <problem_to_solve>
- Intended users: <intended_users>
- Initial scope: <features_or_deliverables>
- Exclusions: <out_of_scope_items>
- Technology preferences: <languages_frameworks_and_environment_or_no_preference>
- Data: <known_inputs_generated_outputs_and_sensitivity_or_none>
- Constraints: <technical_operational_budget_or_other_constraints_or_none>
- Success criteria: <observable_conditions_for_success>

Read AGENTS.md, README.md, CONFIGURE.md, and templates/config.json
before proceeding.

Begin with the complete configuration interview. Present every
customizable component, explain its purpose, recommend defaults,
and identify fixed implementation constraints. Use the information
above to prefill answers for confirmation. Ask about remaining
choices together where practical; do not silently accept defaults.

Cover project definition, technology, data handling, agent roles,
delegation capabilities, handoffs, task tracking, prompt logging,
feature memories, token management, validation, approval boundaries,
and delivery requirements. Include source-fingerprint coverage, validation
timeouts and diagnostic-summary policy, context character limits, and
checkpoint/resume behavior. Configure the optional analyzer for relevant
pre-build inputs and post-processing outputs, dataset formats/schema
expectations, inspection limits, and approved summary access. Distinguish Python-enforced settings from
assistant policies.

All deterministic components must use Python scripts. Models govern
only work requiring interpretation or judgment. Clarify ambiguous
classifications with me before implementing the affected component.

Preserve raw data as read-only originals. Exclude data contents from
Git by default and obtain explicit approval for small tracked fixtures.

Configure a build → independent QC → test workflow with structured,
automated handoffs where the coding assistant supports them.
Disclose capability limitations and obtain approval for any fallback.

Reduce token consumption through selective context loading, concise
handoffs, Python automation, and compaction after persisting progress.
Log major prompts, track tasks through completion, and save memories
after feature additions. Only the coordinator mutates workflow state;
workers return reports. Use focused context packets and checkpoint/resume
commands. Preserve template memories, and require evidence that matches
the selected source/configuration version before completing work.

After the interview, present the completed project brief,
configuration, proposed changes, and validation plan for my approval.
Do not configure the project, generate project-specific instructions,
or begin implementation until I explicitly approve that plan.

For subsequent work, apply this planning policy:

Every feature enhancement, including a small enhancement, requires an
explicitly approved scope/change/validation plan. Clarify material questions
before generating it. Substantial fixes also require approval. Only clear
fixes or maintenance that add no functionality may proceed without a
separate plan. Ask if classification is uncertain. Material scope changes
require renewed approval; agents cannot approve on my behalf. Read-only
work may proceed. No exception removes logging, QC, tests, or feature memory.

Use one optional analyzer for raw, processed, and generated data, before
building and after processing when relevant. Skip empty or unrelated data.
If my request implies data should exist but it is missing, or the data
fails structural checks or appears unrelated, explain the discrepancy
and ask me how to proceed before dependent work. Do not invent or silently
substitute data. The builder implements Python processing, the coordinator
executes it, and the analyzer interprets approved results. Record analysis
evidence against the selected data version and reassess changed datasets.

Use external evidence only from ./data. Obtain my explicit approval before
downloading any sources there. Preserve available file/locator, original
source, and lineage details; state source unavailable when missing. Original
drafts, code, and labeled synthetic content need no external attribution,
but externally derived facts inside generated content still do. Project
code, instructions, and workflow evidence remain accessible normally.

Never invent facts, sources, observations, or test results. If evidence cannot
answer a question, say unknown or cannot be determined. Distinguish inference
and uncertainty from established facts. When conventions or workflows change,
update the relevant agent instructions, README, configuration/interview,
role prompts, primer, and tests. Keep language concise and prune irrelevant
context while preserving decisions, source references, unknowns, and next actions.

During the initial interview, also clarify column quality rules, strict JSON,
selected-data/phase compatibility, and optional aggregate profiling. Keep profiling
disabled unless approved with approved-summaries access; no raw rows in summaries.
Use read-only configuration preflight. Future config updates must preview differences,
affected tasks, and data scope and obtain approval tied to that preview. Preserve
historical evidence and recorded parent versions; never silently drop vanished data.

Configure a running decision journal for significant decisions and feature
milestones, including rejected alternatives when they explain a tradeoff.
Use logging/journal.jsonl and its generated Markdown view. Record rationale,
outcome, task/project reference, and evidence links through Python commands.
Preserve earlier entries; append corrections or superseding decisions.
Retrieve only relevant entries to conserve context. Keep raw data, secrets,
and routine chatter out. Automatic milestones do not replace explicit decision
capture, feature memories, or human approval.

Keep decision-journal retrieval compact and character-bounded by default, with
full originals available explicitly. Generate query previews in Python on demand;
do not store extra summaries or use a model to produce them. If append commits
but view rendering fails, report the saved ID and rebuild the view rather than
retrying append. Escape Markdown display without altering canonical JSONL text.
