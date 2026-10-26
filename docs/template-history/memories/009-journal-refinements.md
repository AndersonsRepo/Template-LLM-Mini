# Journal refinements

Queries default to compact projections, latest 20 entries, and a 6000-character
cap including JSON formatting/newline. --full requests original fields; --all
removes count limits only. --max-chars is 1000..1000000. Compact decision/rationale/
outcome previews are at most 160 characters, with truncated_fields markers.
Alternatives/evidence exclusion is explicit. Whole records are omitted as needed
under the cap; full original fields are never silently truncated. No summaries
are persisted and no model calls are involved.

Python append now returns id/record_saved/view_rendered; view failures add error
class and recovery instructions after the canonical record has committed. CLI
decide still prints the ID, exits successfully for saved records, and warns on
stderr to rebuild with journal --render instead of repeating append. Automatic
milestones use the same reporting. Canonical write errors remain real failures.
This does not provide general retry idempotency or cross-process transactionality.

Markdown escapes literal HTML/Markdown, flattens multiline display fields, and
percent-encodes evidence-link paths. JSONL preserves original strings and line
breaks. Earlier records are unchanged. Shared rules, bootstrap AGENTS, interview,
README, primer, and roles explain compact retrieval and recovery. Tests cover
character bounds, explicit full retrieval, no persisted query summaries, original
text, injected formatting, actual write failure versus view failure, and CLI status.
