# Approved: configuration-trial fixes

Status: **approved 2026-10-26** (user: "Run all four phases"; all phases on branch
`trial-fixes`, one report at the end). A matching
`memories/011-configuration-trial-fixes.md` is added when the work is done.

## Source

On 2026-10-26 the template was configured into a real project
(`~/eCRF_specifications_test`: data add-on on, Claude only, independent review). One
task went through the whole workflow to done. The run worked, but it surfaced the
problems below. Each item lists what happened in the trial, the change, and the files
it touches. Line numbers refer to `7549f8c`.

## Ground rules for this work

- Work on branch `trial-fixes` with one commit per phase. `main` stays at `7549f8c`
  until the user approves a merge.
- The template's own rule applies: a change to conventions or workflow updates the
  shared rules, README, CONFIGURE.md, role definitions, primer, and tests together.
- Standard library only. No new prunable components unless listed here.
- Every behavior change gets a test in the existing `tests/test_*.py` files. The
  full suite must pass at the end of each phase.

---

## Phase 1: Documentation and messages (low risk, no state changes)

### 1.1 Config examples and precise errors (trial item 1)
In the trial, three `validate-config` runs failed, all because of guessed field
shapes: the format of `commands`, provenance needing an exact path plus `kind`, and
`md` versus "Markdown".
- `templates/config.json`: set `validation.commands` to a working default,
  `[["python3", "-m", "unittest", "discover", "-s", "tests", "-v"]]`.
- `addons/data_analysis/data_analysis.py:123`: replace "Unsupported phase/format"
  with an error that names the bad value and lists the allowed values (`FORMATS`, `PHASES`).
- `data_analysis.py:43-44`: the provenance error lists the required keys and says
  "one entry per exact file path; globs are not supported".
- `scripts/workflow.py:205`: the commands error shows the expected shape
  (`[["python3", "-m", "unittest", ...]]`).
- `addons/data_analysis/README.md`: list the exact format keys
  (`csv json jsonl txt md`) in place of "Markdown".

### 1.2 Clearer task-flow messages (small points)
- `workflow.py:449`: after a pending analysis, say that a passing
  `analysis-report` resumes the build automatically, so `start` should not be re-run.
- `analysis_report` (pass path): print `T001 resumed: building (claim: <agent>)`.
- `workflow.py:926`: when `start` is called on a task that is not planned, give a
  status-specific hint, e.g. "T001 is already building; use `context`".
- `workflow.py:395`: the handoff reference error says that `files` and `memories`
  must be existing file paths, and gives the latest memory artifact path as an example.

### 1.3 Interview approval semantics (trial: "Approved" with three questions open)
- `CONFIGURE.md` and `templates/agent_rules.md`: the approval summary must end with
  an **"Assumed unless you object"** list that names every open item and the default
  that will be used. A bare approval then has a defined meaning.
- `configure`: the milestone journal entry records the assumed defaults when the
  coordinator passes `--assumed FILE`. This flag is optional, so no config schema
  change is needed.

### 1.4 Inputs created by the task itself, and declared outputs (trial items 3 and 9)
- `addons/data_analysis/README.md` and `CONFIGURE.md` data topic: when a task
  produces its own inputs, either stage them in a setup step first or declare them
  as `phase: post`, not `pre`. Add an interview question: "Which processed or
  generated outputs should be declared as post datasets?"
- `CONFIGURE.md` validation topic: say that a builder's processor runs write to
  `data/` outside task paths. This is expected and gitignored.

### 1.5 Where hooks load (trial item 4, documentation part)
- README "Hooks" and `CLAUDE.md`: Claude Code loads the project hooks only when the
  session starts in the project root. In a session rooted elsewhere, call
  `workflow.py guard ...` by hand and export `WORKFLOW_AGENT`.

---

## Phase 2: Setup mechanics

### 2.1 Approved fixtures are trackable (trial: needed `git add -f`)
- `configure` and an approved `update-config` maintain a marked block at the end of
  `.gitignore`:
  ```
  # >>> workflow: approved_fixtures (generated; edit via update-config)
  !/data/raw/STUDY/protocol.md
  # <<< workflow
  ```
- `scripts/guard.py` `protected()`: hand edits inside the marked block are denied.
  The rest of `.gitignore` stays editable.
- Tests: after configure, `git check-ignore` shows the fixtures as not ignored.
  Removing a fixture through `update-config` removes its line.

### 2.2 `validate-config` reports every structural error
- `workflow.py:168-181`: `structure()` collects all key and type errors with their
  field paths and raises them together. Semantic checks keep stopping at the first
  failure, but every message gains its `config.` path prefix.
- Test: a config with three structural errors reports all three.

### 2.3 `workflow.py doctor` (trial items 4 and 5)
A read-only command that prints `ok` or `warn` per line and exits 2 if any warning:
- `core.hooksPath` is `githooks`, and the hook file is executable;
- the git identity is set (repo or global);
- `WORKFLOW_AGENT` is set (otherwise "identity defaults to local");
- `$CLAUDE_PROJECT_DIR` is the project root, when present (the hooks are live);
- the `origin` remote does not point at a template_llm_mini checkout;
- every approved fixture exists and is not ignored;
- `README.md` is still the template README (see 4.2).

`configure` runs `doctor` at the end and prints its output. The `SessionStart`
hook appends any warnings.

### 2.4 Warn on the default identity
- `coordination.py:24`: mutating commands print one stderr warning when the
  identity falls back to `local` in a configured project.

### 2.5 New project from the template (trial item 5)
- `workflow.py new DEST [--from PATH]`, run from the template:
  `git clone --no-hardlinks`, rename `origin` to `template` (kept for pulling later
  fixes, never pushed to), copy the repo-local `user.name`/`user.email` if set, and
  print the next steps (`cd DEST`, start Claude Code there, run the interview).
  Refuse if DEST exists.
- README "Configure" opens with this command. The manual `git init` path stays documented.

---

## Phase 3: Workflow ergonomics (less ceremony)

T001 in the trial took about 15 commands and 8 scratch files. The target is about
half as many files with no lost evidence.

### 3.1 Handoffs pre-filled from the previous one
- `handoff TASK --to X` with no `--file` copies the previous handoff and accepts
  `--set field=value` overrides. With no previous handoff, `--file` stays required.
- When the target is the coordinator, `memories` includes the task's latest memory
  artifact automatically.
- The recorded handoff stays complete. Only the input becomes shorter.

### 3.2 Inline request text
- `add --prompt-text "..."` as an alternative to `--prompt FILE`.

### 3.3 Passing with deferred findings (trial item 7)
- `add ... --follows T001` records a `follows` link and a journal entry
  ("follow-up to T001's review").
- `done T001` lists any open follow-ups. `status` and `tasks.md` show the link.
- The task state gains an optional `follows` field; older state without it still loads.

### 3.4 Review identity is recorded honestly (trial item 2)
Python cannot authenticate who reviewed. The fix is to make the claim explicit and
tie it to the reviewed version:
- `review --reviewer NAME` is required in `independent` and `cross-agent` modes. It
  is stored separately from the recording agent (`agent`). In `independent` mode it
  must differ from `built_by`, and from the builder role name when the same agent
  holds both roles.
- `context --role reviewer` includes `review_ref = snapshot hash[:12]`. The
  reviewer's report must contain that token, and `review` rejects a report without
  the current token. This shows the report was written against the current version,
  not who wrote it.
- README and `agents/reviewer.md`: say plainly that `--reviewer` is an assertion,
  like `--approved`.

---

## Phase 4: Structure

### 4.1 Separate the harness's tests from project tests (trial item 8)
- Move the harness tests (`tests/harness.py`, `test_workflow`, `test_coordination`,
  `test_journal`, and the data add-on tests) to `harness_tests/`, with `tests/`
  left empty except `.gitkeep`.
- Update `PRUNABLE['data_analysis']`, the README "Validate" section, and `harness.py`'s
  `ROOT` handling.
- Default `validation.commands` runs `-s tests` only, so project checks stay fast.
  `workflow.py self-test` runs the harness tests.

### 4.2 Project README after configure
- Move the command reference from `README.md` into `docs/workflow.md`, which is core
  and not prunable. AGENTS.md and the rules point to it.
- `configure` writes a short project `README.md` from the brief (name, purpose, how
  to run checks, link to `docs/workflow.md`). The template README remains in the
  template repo.

---

## Decisions (user answers, 2026-10-26)

1. **README split (4.2):** yes. Move the command reference to `docs/workflow.md`
   and have `configure` generate the project README.
2. **Harness test location (4.1):** `scripts/tests/`, not `harness_tests/`. Read
   every `harness_tests/` reference in 4.1 as `scripts/tests/`. Projects do **not**
   run `self-test` by default; it is run when harness files change.
3. **`new` keeps the template as a remote (2.5):** yes, named `template`.
4. **Review token (3.4):** yes, it is required.

## Validation plan

1. Each phase: `python3 -m unittest discover -s tests -v` (in Phase 4,
   `harness_tests`) passes, with new tests for every behavior above.
2. After Phase 3, re-run the trial end to end in a scratch directory:
   - `workflow.py new` → configure with the eCRF trial config (fixed for 1.1).
   - Run T001's flow with the same ingestion code.
   - Pass conditions:
     - `validate-config` passes or lists all errors in one run;
     - no `git add -f` is needed;
     - `doctor` is clean when run from the project root;
     - the task needs no more than 5 scratch files;
     - an `independent` review without `--reviewer` or with a stale token is rejected.
3. Live check (not scriptable here): start a Claude Code session in the scratch
   project and confirm the `SessionStart` and `PreToolUse` hooks fire, and whether
   the hook input includes `agent_type`. This is the open item from prompt 010.
4. Record the history in `docs/template-history/memories/011-configuration-trial-fixes.md`
   and add an entry to the template-history index.

## Out of scope

- Codex hook support (still untestable here: `codex` is not on PATH).
- Changes to `~/eCRF_specifications_test`. Its T002 stays as registered.
- Config version 3 or state migration. The only new field is the optional `follows`,
  which loads with a default.
