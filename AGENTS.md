# Configure this template first

Read templates/agent_rules.md for mandatory approval, Python/model, coordinator,
data, attribution, answer-quality, documentation, concise-context, and workflow rules. Those rules apply before and after customization.

For an initialization prompt request, show prompts/template_prompt_initialization.md
in full, preserving <placeholders>; do not execute it merely to display it.

To configure, read CONFIGURE.md and templates/config.json. Present every interview
topic at the beginning, with recommended defaults. Clarify material questions before generating any feature-enhancement plan.
Resolve missing or ambiguous answers. Present the project brief, configuration, proposed changes, and validation
plan for explicit approval before `configure --approved`. Generate project-specific
AGENTS.md only after approval. Read README.md for command details as needed.

Use validate-config for read-only preflight; for existing projects use the reviewed
update-config preview/apply process rather than overwriting configuration. See
docs/data-analysis.md only when working on data-analysis specifics.

Read logging/README.md when recording or retrieving significant project decisions.
Use Python journal commands; do not hand-edit the canonical journal or copy whole
prompts into it. Project decisions may be logged before configuration.

Prefer compact, character-bounded journal queries; --full is explicit. If a record
is saved but the Markdown view fails, rebuild the view instead of repeating append.
