# Approved journal refinements

The owner approved all three refinements after reviewing a brief implementation
plan: compact character-bounded retrieval generated only on demand, accurate
saved-record handling when Markdown rendering fails, and safe Markdown rendering
that preserves original canonical JSONL text.

Scope includes explicit full-record retrieval, omitted/clipped markers, recovery
instructions with the saved ID, updated agent/interview/README/primer guidance,
and focused plus regression tests. No dependencies, persisted summaries, model
calls, or changes to earlier canonical records are introduced.
