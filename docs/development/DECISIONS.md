# Recording architecture decisions

This project records significant, non-obvious architectural decisions as
**Architecture Decision Records (ADRs)** under [`docs/adr/`](../adr/README.md).
This page explains *when* to write one and *how*.

## When an ADR is required

Write an ADR when a change involves a decision whose rationale is not obvious
from the code and would otherwise be lost. Typical triggers:

- Depending on a third-party library's internals or making an assumption about
  its behavior (e.g. the bump-my-version adapter).
- Introducing or changing a quality gate (coverage, typing, mutation, size,
  hygiene) or its threshold.
- A structural convention other contributors are expected to follow (e.g. how
  large modules are split).
- A non-local trade-off: choosing one approach over a reasonable alternative for
  reasons that future readers would otherwise have to reverse-engineer.

You do **not** need an ADR for routine bug fixes, dependency bumps, or changes
whose intent is clear from the diff and its tests.

## How to add one

1. Copy the structure of an existing record in [`docs/adr/`](../adr/README.md).
   We use a lightweight [MADR](https://adr.github.io/madr/) style: **Context**,
   **Decision**, **Consequences**, plus a `Status` line.
2. Number it sequentially (`000N-short-kebab-title.md`).
3. Add a row to the table in [`docs/adr/README.md`](../adr/README.md).
4. If the decision changes an earlier one, add a new ADR that supersedes it and
   set the old record's status to `Superseded by 000N` — ADRs are immutable once
   accepted; we add, we don't rewrite.

## Repo-owned vs. template-synced files

Some governance and config files (for example `CONTRIBUTING.md`, `ruff.toml`,
the `rhiza_*.yml` workflows, and `.pre-commit-config.yaml`) are **synced from
the [Rhiza template](https://github.com/Jebel-Quant/rhiza)** and are listed in
`.rhiza/template.lock`. Editing them here is reverted on the next sync — changes
to those belong upstream. Everything under `src/`, `tests/`, `docs/adr/`, this
`docs/development/DECISIONS.md`, `pyproject.toml`, and `mkdocs.yml` is repo-owned
and edited here directly.
