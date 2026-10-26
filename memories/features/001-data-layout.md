# Data layout and policy

Use data/raw/ for originals, data/processed/ for transformations, and data/generated/
for synthetic/model datasets. Raw originals are read-only by agent instruction;
processing must not overwrite/delete them. Retention deletion requires authorization.

The interview and required configuration fields cover usage, sources, sensitivity,
expected size, retention, generated outputs, and approved Git exceptions. Answers
flow into generated AGENTS.md. Default raw/Git policy strings are validated.

.gitignore excludes nested contents while preserving .gitkeep placeholders.
Small fixture exceptions need explicit approval and a reviewed ignore change, or
placement under tests/fixtures/. Configuration does not change ignore rules itself.
Behavioral tests verify required data answers, preserved policies, generated
instructions, and actual Git ignore behavior in an isolated repository.

No OS permission enforcement, automatic deletion, or data ingestion is provided.
