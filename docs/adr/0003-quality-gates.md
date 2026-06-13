# 0003 — 100% coverage + strict `ty` + mutation testing

- Status: Accepted
- Deciders: rhiza-tools maintainers

## Context

`rhiza-tools` performs irreversible git operations (tagging, pushing, reverting)
on behalf of users. A latent bug can corrupt a release. The codebase is small
enough that a high bar is affordable, and we want regressions caught
mechanically rather than by reviewer vigilance.

## Decision

Three independent gates run in CI, each catching a different failure class:

1. **100% line coverage** (`--cov-fail-under=100`). Every line must be executed
   by a test. This is a floor, not a goal — see gate 3 for why coverage alone is
   insufficient.
2. **Strict type checking** with `ty`, configured with
   `error-on-warning = true` in `pyproject.toml`, so *warnings* fail the build,
   not just hard errors. This keeps the type surface honest; the bump adapter
   uses concrete upstream types rather than `Any` for the same reason
   (see [ADR-0001](0001-bump-my-version-adapter.md)).
3. **Mutation testing** (`mutmut`, the `mutation` make target / workflow).
   Coverage proves lines *run*; mutation proves the tests would *fail* if the
   code were wrong. This is what makes the 100% coverage number meaningful
   rather than a line-execution ritual.

100%-docstring coverage (`interrogate --fail-under 100`) is enforced alongside
these for the public surface.

## Consequences

- New code must arrive with tests that both cover and *constrain* it.
- Coverage is never chased for its own sake; tests assert behavior. This is
  itself enforced — see [ADR-0004](0004-structural-meta-tests.md).
- The bar is sustainable specifically because the package is small and focused.
