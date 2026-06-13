# Architecture Decision Records

This directory records the **non-obvious** architectural decisions behind
`rhiza-tools` — the ones whose rationale is not self-evident from the code and
would otherwise live only in commit messages or a maintainer's head.

We use a lightweight [MADR](https://adr.github.io/madr/)-style format. Each
record is immutable once accepted: to change a decision, add a new ADR that
supersedes the old one (and update the old one's status), rather than editing
history.

See [the decision process](../development/DECISIONS.md) for when an ADR is
required and how to add one.

## Index

| ADR | Title | Status |
| --- | ----- | ------ |
| [0001](0001-bump-my-version-adapter.md) | Isolate bump-my-version behind an adapter | Accepted |
| [0002](0002-changelog-in-bump-commit.md) | Fold the regenerated CHANGELOG into the bump commit | Accepted |
| [0003](0003-quality-gates.md) | 100% coverage + strict `ty` + mutation testing | Accepted |
| [0004](0004-structural-meta-tests.md) | Enforce structure with meta-tests, not convention | Accepted |
| [0005](0005-command-module-split.md) | Split large command modules by responsibility | Accepted |
