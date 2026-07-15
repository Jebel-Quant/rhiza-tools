# Architecture

This page is the map for **where code goes** in `rhiza_tools`. The rationale
behind the layout lives in the Architecture Decision Records — in particular
[ADR-0005](adr/0005-command-module-split.md) (splitting command modules by
responsibility). This page is the living reference; the ADRs are the history.

> **Note:** The release-orchestration commands (`bump`, `release`, `rollback`)
> have been retired from `rhiza-tools` — releasing now happens via the
> rhiza-claude `/release` command. Some ADRs still describe those commands as
> historical context; `rhiza-tools` now ships only headless CI/CD tools.

## Layers

```
cli.py                          Typer surface — argument parsing, --help text, option wiring
  └─ commands/<command>/__init__.py  orchestration — the workflow for one command
       ├─ parse.py              pure parsing / analysis (no side effects)
       └─ report.py             formatting and output rendering
  └─ commands/<command>.py      single-file commands that never grew satellites
```

A command that has only one responsibility stays a single module
(`commands/<command>.py`); one that grows past the
[500-line gate](adr/0004-structural-meta-tests.md) (`tests/test_module_size.py`)
becomes a **subpackage** (`commands/<command>/`) whose `__init__.py` holds the
orchestration and whose siblings own the extracted responsibilities (for example
`commands/suppression/` splits into `parse.py` and `report.py`).

Dependencies point downward only: the orchestration `__init__.py` calls into its
sibling modules; the siblings do not import the package back.

## The command-subpackage convention

Inside a `commands/<command>/` subpackage, the file name tells you what lives
there:

| Module | Responsibility | Examples |
| ------ | -------------- | -------- |
| `__init__.py` | Typer-facing command orchestration — the entry point invoked from `cli.py` | `suppression/__init__.py` |
| `parse.py` | Pure parsing / analysis; no I/O side effects | `suppression/parse.py` |
| `report.py` | Formatting and output rendering | `suppression/report.py` |

Commands that never outgrew a single file stay flat: `version_matrix.py`,
`generate_badge.py`, `update_readme.py`, `analyze_benchmarks.py`, `pip_audit.py`.

Extracted helpers are **re-exported** from the orchestration `__init__.py`, so
callers and tests keep importing `commands.<command>.<helper>` even after a move.
When a moved function resolves a dependency in its **new** module's namespace,
the test patch target moves with it.

## Where does my code go?

Work top-down through the first match:

1. **A new user-facing command?** Add a `@app.command` in `cli.py` (parsing +
   `--help`) and a `commands/<command>.py` orchestration module for the workflow.
   Promote it to a `commands/<command>/` subpackage only once it outgrows one
   file.
2. **Pure parsing / analysis** (no side effects)? → `<command>/parse.py`.
3. **Formatting or output rendering?** → `<command>/report.py`.

Keep modules at or below the 500-line ceiling; when one approaches it, extract
the next responsibility into a sibling module within the subpackage and
re-export it from `__init__.py`.

## Tests mirror the package

`tests/` mirrors this layout: per-command tests live under
`tests/commands/<command>/` (e.g. `tests/commands/suppression/`), single-file
command tests sit directly in `tests/commands/`, and cross-cutting suites (CLI
wiring, structural meta-tests) stay at the `tests/` root. Test module basenames
are kept unique across the tree because pytest runs in `prepend` import mode
without `__init__.py` package markers.
