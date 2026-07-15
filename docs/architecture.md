# Architecture

This page is the map for **where code goes** in `rhiza_tools`. The rationale
behind the layout lives in the Architecture Decision Records — see
[ADR-0005](adr/0005-command-module-split.md) (splitting command modules by
responsibility). This page is the living reference; the ADRs are the history.

## Layers

```
cli.py                          Typer surface — argument parsing, --help text, option wiring
  └─ commands/<command>.py      single-file commands that never grew satellites
  └─ commands/<command>/__init__.py  orchestration — the workflow for one command
       └─ <sibling>.py          an extracted responsibility (parsing, reporting, …)
```

A command that has only one responsibility stays a single module
(`commands/<command>.py`); one that grows past the
[500-line gate](adr/0004-structural-meta-tests.md) (`tests/test_module_size.py`)
becomes a **subpackage** (`commands/<command>/`) whose `__init__.py` holds the
orchestration and whose siblings own the extracted responsibilities.

Dependencies point downward only: the orchestration `__init__.py` calls into its
sibling modules; the siblings do not import the package back.

## The command-subpackage convention

Inside a `commands/<command>/` subpackage the file name tells you what lives
there: `__init__.py` is the Typer-facing command orchestration (the entry point
invoked from `cli.py`), and each sibling owns one extracted responsibility. The
`suppression/` command is the current example:

| Module | Responsibility |
| ------ | -------------- |
| `suppression/__init__.py` | Command orchestration — `suppression_audit_command`, invoked from `cli.py` |
| `suppression/parse.py` | Scan the codebase and parse inline-suppression comments |
| `suppression/report.py` | Render the per-file report, histogram, and density grade |

Commands that never outgrew a single file stay flat: `version_matrix.py`,
`analyze_benchmarks.py`, `pip_audit.py`.

Extracted helpers are **re-exported** from the orchestration `__init__.py`, so
callers and tests keep importing `commands.<command>.<helper>` even after a
move. When a moved function resolves a dependency in its **new** module's
namespace, the test patch target moves with it.

## Where does my code go?

Work top-down through the first match:

1. **A new user-facing command?** Add a `@app.command` in `cli.py` (parsing +
   `--help`) and a `commands/<command>.py` orchestration module for the workflow.
   Promote it to a `commands/<command>/` subpackage only once it outgrows one
   file.
2. **A distinct responsibility within a command** (parsing, reporting, I/O)? →
   a sibling module inside that command's subpackage.

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
