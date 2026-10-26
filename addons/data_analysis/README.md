# Data-analysis add-on

Optional. Enable it when tasks consume or produce datasets that need inspection:
set `addons.data_analysis: true` and copy `addons/data_analysis/config.json` into the
project config as `analysis`. When disabled, tasks are created with no data mode and
the data commands (`data-check`, `analysis-report`, `data-resolve`, `profile`) are
rejected. Projects that will never need it list `data_analysis` in `prune`.

Contents: `data_analysis.py` (inspection), `fetching.py` (approved fetch/parse runs),
`profiling.py` (aggregates), `rules.md` (appended to the project AGENTS.md), and
`templates/` (source, dataset, column rules, provenance, analysis report). Its roles
live with all the others in `agents/analyzer.md` and `agents/fetcher.md`
(`requires: data_analysis`).

## Fetching from approved sources

Register each source in `analysis.sources` (templates/source.json). Approving the
configuration, at `configure` or through `update-config`, is the explicit approval to
download from that source; anything else still asks every time.

| Field | Meaning |
|---|---|
| `name` | Identifier used by `fetch --source` |
| `origin`, `locator` | Where the data comes from and which part (recorded as provenance) |
| `command` | `["python3", "scripts/fetch/x.py", ...args]`: writes files under `$FETCH_TARGET` |
| `target` | Folder under `data/raw/`; each fetch lands in a new `<target>/<UTC stamp>/` |
| `parser`, `parsed_target` | Optional Python parser reading `$FETCH_DIR` and writing to `$PARSE_TARGET`, published under `data/processed/` (`[]` and `""` to skip) |
| `timeout_seconds` | 1..3600 per step |

The fetcher role writes the scripts inside its task's paths. The claim holder then runs:

```sh
python3 scripts/workflow.py fetch T001 --source sales_api
python3 scripts/workflow.py data-check T001 --phase pre
```

Both steps run in a staging area. Nothing is published unless every step exits 0
and produces files, and existing originals are never overwritten. Script output is
discarded, so credentials and values are never stored; scripts read credentials from
environment variables. Each fetch records a `fetches` artifact (paths and hashes)
and updates `.workflow/fetch-manifest.json`. Inspection reads that manifest, so raw
files carry the source origin/locator and parsed files carry lineage back to them.
Declared `analysis.provenance` entries take precedence.

Use the CONFIGURE.md interview to approve datasets, phases, access policy, column
expectations, size limits, profiling, and handling of unavailable evidence. The
analyzer interprets data under approved access; deterministic processing and
statistics are Python work.

## Dataset selection

Inputs must exist before a `pre` inspection can pass. If a task produces its own
inputs (for example synthetic fixtures), stage them in an approved setup step before
the task starts, or declare them as `phase: post` datasets. Declare processed and
generated outputs you want inspected as `post` too; otherwise post analysis is
skipped.

Use `add ... --data expected` if the request implies inputs should exist. `auto`
uses relevant configured/discovered data; `none --data-reason '...'` records that
a task is unrelated. Missing expected data pauses dependent work and asks the
user. Empty discovery before a task has used data can skip without a model call.
Losing a previously inspected input requires clarification; it cannot silently
turn into a skipped phase. Record an explicit scope change via data-resolve.

Use repeated `--dataset data/raw/file.csv` to narrow selection; equivalent ./data/
spellings are normalized before matching configured requirements. Selected data
must overlap requested `--analysis-phase pre`/`post` phases; conflicts are errors,
not silently empty selections. With no specs, pre covers raw/ and other input
folders, while post covers processed/generated. Use specs for different timing.

Supported inspection formats (the dataset `format` key) are `csv`, `json`, `jsonl`,
`txt`, and `md` (Markdown), all UTF-8. Other
formats need approved Python extraction into data/. Inspectors never execute input.
Strict JSON rejects duplicate keys and nonfinite constants; schema ambiguity must
be resolved before analysis. Input files are never rewritten.

Dataset specs follow templates/dataset.json here. Optional column_rules follow
templates/column_rules.json: type, nullable, unique, minimum, and maximum. Rules
validate values in Python rather than asking a model to count or check constraints.
Type options are string, integer, number, boolean, and date. Check implementation
semantics for CSV/text coercion when selecting rules; unknown schema expectations
must be clarified up front. Empty rules preserve the basic required-column check.

## Analyzer flow

Before building, start pauses for relevant input analysis. Once the coordinator
has executed the builder's Python processor, reviewer handoff pauses for relevant
output analysis. Give the analyzer its current packet, not the whole data folder:

```sh
python3 scripts/workflow.py context T001 --role analyzer
python3 scripts/workflow.py analysis-report T001 --phase pre --verdict pass --file analysis.md
```

Use templates/analysis.md (in this folder) and record the correct phase. Repeat the requested
handoff after a passing report. Metadata alone does not establish semantic fit;
state unknown or ask for approved summaries when evidence is insufficient.

For semantic mismatch or missing evidence:

```sh
python3 scripts/workflow.py analysis-report T001 --phase pre --verdict needs-input --file analysis.md --question 'Is this the intended dataset?'
python3 scripts/workflow.py data-check T001 --phase pre
python3 scripts/workflow.py data-resolve T001 --file user-response.md --approved
```

Relay the question and wait for a real response. Corrected files can be reinspected;
an unchanged semantic question needs a recorded response. A user-approved scope
change may use data-resolve --data none. Never fabricate or substitute inputs.
Other tasks can continue while this one waits. `check` and context flag stale
pending inspections so a model does not waste a call on known outdated evidence.

## Optional profiling

Profiling is disabled by default. Enable analysis.profiling.enabled only under an
approved configuration with analysis.data_access=approved-summaries. It is a local
Python aggregate hook, not a new model or external service:

```sh
python3 scripts/workflow.py profile T001 --phase pre
python3 scripts/workflow.py context T001 --role analyzer
```

It works during intake/pending analysis, so there is no need to pass an uninformed
analyzer report merely to begin implementing a custom processor. It records bounded
statistics, duplicate/missing counts, observed types, uniqueness counts, and finite
numeric summaries, linked to input hashes/provenance. It emits no sample rows or
category values. Numeric aggregates may still reveal sensitive information; approval
must cover the selected fields and statistics. There is no privacy guarantee or
automatic redactor. Bound output with max_columns/max_chars; omissions are explicit.
Changed inputs invalidate summaries. Metadata-only mode must not expose previously
recorded summary contents, even if profiling used to be enabled.

## Provenance and versions

All external evidence is read from data/; downloading into it needs explicit approval.
Use data/raw/ for read-only originals, processed/ for transformations, and generated/
for synthetic/model datasets. Git ignores contents except explicit approved fixtures.
Code, instructions, and internal workflow evidence remain readable normally.

Record known source, locator, and derived_from entries using templates/provenance.json (in this folder).
An empty analysis.provenance list explicitly yields source unavailable. Only declared
original generated material is exempt; externally derived facts retain attribution
regardless of output folder. Origin declarations are not independently verified.

Inspection manifests preserve selected file versions and observed upstream parent
versions. Active parent drift changes evidence freshness even when a derived file
has not changed. Historical manifests remain as recorded. A current parent hash
is an observation, not proof that the producer used that version. Record production
inputs with your Python processor when that stronger guarantee is required. Missing,
unreadable, or oversized parents must have explicit version-status limitations.

Keep factual findings attributable to local files and available locators/origins.
Say source unavailable for missing provenance and unknown when evidence cannot
answer. Python checks structures and versions; the reviewer assesses factual support.
