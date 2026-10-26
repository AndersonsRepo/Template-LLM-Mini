## Data-analysis add-on

Use the analyzer before building and after processing when task data is relevant.
At intake choose `--data expected` when the request implies inputs should exist,
`auto` for conditional discovery, or `none --data-reason` with a reason. Python
detects files and structure; it cannot infer what the request means.

Missing expected data, a structural failure, or an apparent semantic mismatch
requires a user question before dependent work; other tasks may continue. Never
fabricate or silently substitute data. Record `data-resolve --approved` only after
a real user response.

The builder writes deterministic processors, the coordinator runs them, and the
analyzer interprets results under the approved access policy (`metadata-only`
never authorizes raw records). Changed selected data needs reassessment and fresh
review/testing. Empty or unrelated data never justifies an analyzer model call.
Keep raw record values out of persistent artifacts.

Fetch only from sources registered in `analysis.sources`. The fetcher writes
Python fetch/parse scripts that write only to their staging variables, and the
claim holder publishes with `fetch TASK --source NAME`. Propose new sources through
`update-config`; never download ad hoc or write into data/raw/ directly.

Profiling needs `analysis.profiling.enabled=true` with `approved-summaries` access;
run `profile TASK --phase PHASE` before input analysis when aggregates are needed.
Aggregates may still reveal sensitive facts. Column contracts and parent hashes are
deterministic checks, not proof of factual truth. If `analysis_stale` is true, run
`data-check` before model work. See addons/data_analysis/README.md for details.
