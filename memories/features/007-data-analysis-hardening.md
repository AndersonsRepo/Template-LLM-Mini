# Data-analysis hardening

Canonical data paths are matched to configured requirements before inspection;
explicit task selections must overlap their phases. Configuration validation uses
the project root, not caller CWD. Strict JSON rejects duplicate keys/nonfinite
constants. Optional column rules check type, nullability, uniqueness, numeric
bounds, and ISO dates without rewriting data. CSV coercion is check-only.

Previously inspected data disappearing now asks the user rather than skipping.
Pending data drift is reported before model work. Context retains phase/question/
references and prioritizes evidence over generic settings, with compact explicit
omissions. Read role_instruction_ref when its body is omitted.

Profiling is standard-library Python, disabled by default; enabled profiles require
approved-summaries. Bounded aggregates contain counts/types/numeric approximations,
never row samples or categorical values. Aggregates are not automatic anonymization.
Current data hashes bind summaries, and metadata-only mode does not inject stored
summaries into model context. Observed parent versions change selected derived
inspection hashes; saved historical manifests remain unchanged. Current parent
hashes do not prove original production inputs.

Config version 1 adds profile defaults. validate-config is read-only. update-config
previews config/guidance differences and affected tasks; approval uses a hash tied
to candidate, current config/state, rules, and guidance. Revisions preserve old/new
config, prior state, and guidance. Active evidence is invalidated, completed history
and unanswered questions survive. Explicit dataset scope edits reset active scope;
unrelated edits retain inspected-input expectations. Multi-file writes are not a
database transaction; prepared revision records support recovery.

README is concise; detailed recipes are in docs/data-analysis.md. The reusable
template remains unconfigured and requires no model calls or external data for tests.
