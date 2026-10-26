# Optional analyzer

State schema 3 adds per-phase analysis state, inspections/reports, selected dataset
hashes, and awaiting-data/analyzing statuses. auto uses relevant discovery/config
specs; expected records request-implied missing data; none requires a relevance
reason. Coordinator judgment sets task relevance, not Python text heuristics.

Pre analysis gates building; post analysis gates independent QC after the coordinator
runs processors. One analyzer handles raw/processed/generated data under configured
access. Builder implements deterministic processing; analyzer supplies interpretation.

Bounded read-only Python inspection supports UTF-8 CSV, JSON, JSONL, text, Markdown.
Metadata/hashes/counts enter artifacts, never raw rows. Bad/missing/unsupported data
asks a user question. Semantic concerns use needs-input with an explicit question;
unchanged data requires an actual recorded user response before reconsideration.
Unrelated tasks continue. A user-approved scope change may explicitly skip data.

Analysis and downstream evidence are bound to selected data versions; changes force
reassessment. Completed historical evidence is checked without reading later data.
Configuration defaults to metadata-only; semantic fit needs sufficient approved
summaries or user clarification. No automatic redaction or agent launching exists.
Tests cover optional activation, full pre/post flow, structural and semantic mismatch,
user resolution, changed data, context privacy, and the existing no-data workflow.
