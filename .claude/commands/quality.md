---
description: Run lint, type, and test checks and summarize what to fix
---

Assess the quality of this repo. Run these in order — cheapest checks first so
fast failures surface before the slow test suite — and collect results:

1. `make fmt` — pre-commit hooks + linting (ruff).
2. `make typecheck` — `ty` type checking.
3. `make test` — full test suite.

Then report:

- A pass/fail summary per step.
- Failures grouped by file, with the specific rule/error and line.
- A prioritized list of what to fix first (blocking errors before style nits).

Then analyse the repo and give marks on a scale of 1 to 10 for all relevant
subcategories. Pick the subcategories that fit what you actually observe — e.g.
linting/style, type safety, test pass rate, test coverage & depth, code
structure & readability, documentation, dependency & security hygiene, CI/tooling
health. For each: the score, a one-line justification grounded in evidence from
the checks above (and a quick look at the code where needed), and what would
raise it. Close with an overall score and the single highest-leverage
improvement.

**Scope the scorecard to locally-owned items — not what the mother repo (Rhiza)
owns.** This project syncs its dev infrastructure from `jebel-quant/rhiza` (see
`CLAUDE.md` for the authoritative split; the machine-generated list is the
`files:` block of `.rhiza/template.lock`). Score only the things this repo
actually controls — `src/rhiza_tools/`, `tests/`, `pyproject.toml`, `README.md`,
project-specific docs, `.rhiza/template.yml`, and locally-hardened config like
`ruff.toml`. Do **not** let Rhiza-managed files (the `.github/workflows/*`,
`Makefile`, `.pre-commit-config.yaml`, `pytest.ini`, the `ty`/typecheck target,
mutation/fuzzing/scorecard CI, etc.) drive the marks — a gap there is fixed
upstream in Rhiza, not here. If a relevant signal is Rhiza-owned, note it as
"upstream/out-of-scope" rather than scoring it against this repo.

Then, from the scorecard above, identify **actionable issues to improve the
score** — one per subcategory scoring below 10 (skip any that are maxed). For
each, give: a concrete title, the subcategory and current→target score it moves,
the specific file(s)/lines or config to change, and a crisp acceptance criterion
("done when…"). Keep them in-scope (locally-owned, per the scoping rule above) —
flag anything Rhiza-owned as upstream rather than listing it as a local action.
Order them by leverage (biggest score gain for least effort first). This is a
list of recommendations only — do not create GitHub issues or change code unless
I explicitly ask.

If everything passes, say so plainly — but still produce the 1–10 subcategory
marks. Do not fix anything unless I ask — this command only assesses.

If I passed an argument ($ARGUMENTS), scope the assessment to that path or topic
instead of the whole repo.
