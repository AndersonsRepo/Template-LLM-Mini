# Approved data layout update

The owner requested a data directory plus initial-interview and configuration
coverage for raw inputs and generated data. The owner approved raw/, processed/,
and generated/ subfolders; excluding contents from Git while retaining structure;
explicit approval for small tracked fixtures; and treating raw inputs as read-only
originals. The implementation plan was explicitly approved before edits.

Scope: folders, Git rules, interview, configuration and validation, generated
instructions, README, and focused behavioral tests. No OS permissions or automatic
retention deletion are introduced. Deterministic data processing remains Python.
