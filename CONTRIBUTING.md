# Contributing

Thanks for your interest in contributing to `rhiza-tools`.

## Development setup

This project uses [`uv`](https://docs.astral.sh/uv/) for environment management.

1. Clone the repository.
2. From the repository root, run:

```bash
make install
```

If setup or tooling fails, run `make doctor` for prerequisite checks and guidance.

## Quality gates

Before opening a pull request, run the same core checks that gate CI:

- `make fmt`
- `make test`
- `make typecheck`
- `make security`

You can also run `make all` to execute the local CI target set in one command.

## Pull requests

- Open pull requests against the default branch.
- Include tests and documentation updates when your change needs them.
- For non-trivial features or behavior changes, start with a GitHub issue so the
  approach can be discussed before implementation.
- Expect normal review iteration before merge.

## Commit conventions

We use [Conventional Commits](https://www.conventionalcommits.org/). Use:

```text
<type>(<scope>): <short summary>
```

Typical commit types include `feat`, `fix`, `docs`, `refactor`, `test`, `ci`,
`chore`, `perf`, and `security`.

## More contributor guidance

- [Architecture decisions](docs/development/DECISIONS.md)
- [Testing guide](docs/development/TESTS.md)
- [Release guide](docs/RELEASING.md)
