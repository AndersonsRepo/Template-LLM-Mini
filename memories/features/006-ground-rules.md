# Evidence and project ground rules

Mandatory policy lives in templates/agent_rules.md; bootstrap references it and
configuration copies it into generated AGENTS.md. All feature enhancements now
need approved plans, including small enhancements. Clarify material questions
before generating plans. Only narrow fixes/maintenance with no new functionality
retain the exception. Older flexible-plan notes describe superseded history.

External evidence must be staged in ./data. Downloads need explicit approval;
no downloading code is included. Code/instructions/internal workflow evidence are
still accessible. Unknown or cannot be determined is correct when evidence is
insufficient. Never invent sources, facts, observations, or validation results.

Optional data.provenance entries (templates/provenance.json) record path, kind,
source, locator, and parent data references. Python checks paths, types, duplicates,
lineage cycles, and generated exceptions with parents. Inspections preserve known
origins/lineage and explicitly mark missing origins source unavailable. Original
generated content needs no source only when declared; generated folders alone do
not establish exemption. Attribution declarations are not independently verified.
Provenance changes alter inspected data hashes and require reassessment.

Changes to conventions/architecture/workflow must update appropriate instructions,
README, configuration/interview, roles, primer, and tests. Keep language concise;
checkpoint evidence references, decisions, unknowns, approvals, and next actions
before compaction. Configured projects need a reviewed config migration for the
new data.provenance list; preserve existing task history. Template is unconfigured.
