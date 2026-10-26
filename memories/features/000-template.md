# Template implementation

The template uses a standard-library Python CLI, a configuration interview,
generated project instructions, structured handoffs, and Markdown evidence.
The coding assistant supplies model access and delegation. Python does not
launch subagents or control assistant context compaction.

Task state is stored in .workflow/state.json after configuration. tasks.md and
the feature-memory index are generated views. One coordinator must serialize
writes. Checks verify structure and evidence presence; models assess substance.
Review/test failure invalidates prior passes. Repair limits block further work.

Configuration remains pending for the adopting project. The bootstrap record
is historical context, not a completed application feature or live task.
Behavioral verification uses isolated temporary copies and no model calls.
