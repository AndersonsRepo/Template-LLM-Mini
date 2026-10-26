# Decision journal

journal.jsonl is the chronological canonical record; journal.md is generated.
Only Python workflow commands append records. Do not edit/rewrite earlier entries.
This directory is not a Python package and does not replace standard-library logging.

Record significant decisions and feature milestones. Include rejected alternatives
only when they explain a tradeoff. Keep entries concise, with rationale, outcome,
and links to existing prompts, evidence, or memories rather than copied bodies.
No secrets, raw data, routine tool chatter, or internal deliberation transcripts.

Use templates/decision.json and workflow.py decide. A project decision may be
recorded before configuration; --task T001 requires an existing configured task.
Status records proposed/accepted/rejected, not independently verified user consent.
An accepted new decision can --supersedes J000001; original bytes remain intact.

workflow.py journal defaults to compact output, at most 20 entries, and 6000
characters including JSON formatting and the final newline. --max-chars adjusts
the budget (1000..1000000). Compact decision/rationale/outcome previews are at most
160 characters each, with clipped fields marked. Alternatives and evidence are
excluded explicitly; --id J000001 --full retrieves original fields.

Filter --task T001 (or project), --type decision|milestone, or --id J000001. --all
removes the count limit, not compact mode or the character cap. --full includes
complete records, still bounded; if a record cannot fit, it is omitted whole.
Counts report every omitted record. Increase --max-chars or narrow the filter.
Summaries are deterministic projections generated on demand, never persisted and
never produced by a model. Only content actually supplied to a model consumes
its context; keeping original records on disk does not itself consume tokens.

--render rebuilds the Markdown view without changing JSONL records. Display fields
are escaped for Markdown/HTML and multiline text is flattened; evidence link
paths are encoded. Original values and line breaks remain intact in JSONL.

Initial configuration, task creation/completion, and applied config updates produce
automatic milestones. Agents must still identify and record meaningful decisions;
Python cannot determine whether every significant decision has been captured.

Keep records in Git. No automatic retention/deletion is performed. Append-only is
a command policy, not tamper-proof storage. Existing evidence is not backfilled or
reinterpreted as historical approval. Config/state/journal writes are not one
transaction. If append succeeds but rendering fails, the command still succeeds,
prints the saved ID, and warns that the view needs rebuilding. Do not repeat the
append; run journal --render. Python append returns id/record_saved/view_rendered
and recovery details on view failure. A canonical write failure still raises an
error; it is not reported as a committed record. Partial/corrupt canonical records require explicit recovery before append.
