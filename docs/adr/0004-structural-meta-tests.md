# 0004 — Enforce structure with meta-tests, not convention

- Status: Accepted
- Deciders: rhiza-tools maintainers

## Context

Two structural properties tend to erode quietly over a project's life:

- Command modules accrete code until they are hard to navigate.
- Test suites accumulate "coverage bucket" files whose only purpose is to
  execute lines for the coverage number, divorced from behavior.

Conventions and code review catch these inconsistently. We prefer guarantees
that fail a build.

## Decision

Encode the structural rules as ordinary tests that run with the suite:

- **`tests/test_module_size.py`** — every `src/rhiza_tools/commands/*.py` must
  stay at or below a line ceiling (currently 750; see
  [ADR-0005](0005-command-module-split.md)). Growth must be split into a new
  module rather than accreted.
- **`tests/test_suite_hygiene.py`** — there must be no `test_coverage*.py`
  catch-all bucket, and no test module may declare its purpose as achieving a
  coverage number. Coverage honesty is the job of mutation testing
  (see [ADR-0003](0003-quality-gates.md)), not of line-chasing files.

## Consequences

- The "keep modules small" and "tests assert behavior" rules are enforced, not
  hoped for; violations fail CI with an actionable message.
- The ceiling is a deliberate, reviewable number that moves only with an
  accompanying decision.
