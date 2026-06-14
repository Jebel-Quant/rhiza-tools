# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com),
and entries are generated from [Conventional Commits](https://www.conventionalcommits.org).

## [0.7.3] - 2026-06-14

### Other Changes
- Strip SLSA provenance from dist/ before PyPI publish (#267)

## [0.7.2] - 2026-06-14

### Other Changes
- Bump version 0.7.1 → 0.7.2

## [0.7.1] - 2026-06-14

### Maintenance
- Bound dependency upper limits; add deptry to local quality sweep (#257)
- Address quality findings #259–#262 (#265)
- Complete deptry package_module_name_map (#266)

### Other Changes
- Cliff and rhiza_release (#258)
- Bump version 0.7.0 → 0.7.1

## [0.7.0] - 2026-06-14

### New Features
- *(release)* Always bump on release; remove --with-bump (#248)

### Maintenance
- Grant repository-admin bypass on main-branch-protection ruleset
- Add Claude Code project config (#255)
- 100% coverage + enforce type annotations (closes #251, #252) (#256)

### Other Changes
- Bump version 0.6.0 → 0.7.0

## [0.6.0] - 2026-06-13

### New Features
- *(bump)* Fold a regenerated CHANGELOG.md into the bump commit (#205)

### Bug Fixes
- *(ci)* Pin scorecard/codeql actions to commit SHAs, not tag objects (#243)

### Maintenance
- Chore(deps-dev)(deps-dev): bump the python-dependencies group with 3 updates (#204)
- Chore(deps)(deps): bump the github-actions group with 9 updates (#203)
- Relocate coverage-chasing tests; add mutation job + suite-hygiene gate (#206) (#214)
- *(bump)* Split into versioning/engine modules; add complexity & size gates (#207, #208) (#215)
- *(commands)* Split bump/release/rollback; ratchet module-size gate 750→500 (#241)
- Codify main branch protection as a repository ruleset (#238) (#247)

### Other Changes
- Docs gate, strict ty, 100% coverage (#209, #210) (#213)
- Add OpenSSF Scorecard workflow + CODEOWNERS; bump sync ref to v0.18.10 (#211) (#216)
- Add explicit private vulnerability reporting links (#230)
- Reach 10/10: repo-owned quality issues (#218, #222, #223, #224, #226) (#231)
- Add root contributing and code of conduct docs (#240)
- SHA-pin Scorecard workflow third-party actions (#242)
- Avoid Bandit B404 in update README help test (#239)
- Add ClusterFuzzLite integration for version matrix parsing (#228)
- Remove Any escape hatches in config/bump (#232) (#245)
- SHA-pin third-party actions in rhiza_fuzzing.yml (#234) (#246)
- Enable ERA/T10/PIE/PL/BLE ruff rules; narrow broad excepts (#233, #235) (#244)
- Bump version 0.5.2 → 0.6.0

## [0.5.2] - 2026-06-08

### Maintenance
- Chore(deps)(deps): bump the github-actions group with 9 updates (#200)
- Chore(deps)(deps): bump the python-dependencies group with 2 updates (#199)

### Other Changes
- Remove mypy configuration from pyproject.toml (#201)
- Bump version 0.5.1 → 0.5.2

## [0.5.1] - 2026-05-31

### Bug Fixes
- Bump rhiza_benchmark.yml reference to v0.18.4 (#196)
- Raise typer floor to 0.16.0 for PEP 604 + click 8.3 compatibility (#198)
- Stop bump/release from publishing an older version (#1126) (#197)

### Maintenance
- Chore(deps-dev)(deps-dev): bump numpy in the python-dependencies group (#186)
- Sync with rhiza template v0.10.9 (#188)
- Update rhiza to v0.15.2 (#191)
- Update rhiza to v0.17.0 (#193)

### Other Changes
- Update template.yml
- Rhiza v0.18.4 (#195)
- Bump version 0.5.0 → 0.5.1

## [0.5.0] - 2026-05-18

### Dependencies
- *(deps)* Lock file maintenance (#176)
- *(deps)* Lock file maintenance (#181)

### Maintenance
- Chore(deps-dev)(deps-dev): bump marimo in the python-dependencies group (#183)
- Chore(deps)(deps): bump the python-dependencies group with 3 updates (#184)
- Chore(deps)(deps): bump github/codeql-action in the github-actions group (#182)

### Other Changes
- Fix broken coverage badge in README (#178)
- Update template.yml
- Delete renovate.json
- Gate `fig.show()` behind `--show` flag (default: off) (#180)
- Update template.yml with new references and templates (#185)
- Bump version 0.4.5 → 0.5.0

## [0.4.5] - 2026-04-25

### Dependencies
- *(deps)* Lock file maintenance (#166)
- *(deps)* Lock file maintenance (#170)
- *(deps)* Update pre-commit hook astral-sh/ruff-pre-commit to v0.15.12 (#175)

### Maintenance
- Chore(deps)(deps): bump the github-actions group with 2 updates (#173)
- Chore(deps-dev)(deps-dev): bump marimo in the python-dependencies group (#174)
- Sync with rhiza template v0.10.1 (#172)
- Sync with rhiza template v0.10.3

### Other Changes
- Rhiza (#167)
- Add root-level mkdocs.yml inheriting from docs/mkdocs-base.yml (#169)
- Update ref version to v0.10.3
- Remove div from md file
- Remove API Reference section from mkdocs.yml
- Bump version 0.4.4 → 0.4.5

## [0.4.4] - 2026-04-12

### Dependencies
- *(deps)* Lock file maintenance (#163)

### Maintenance
- Chore(deps)(deps): bump docker/login-action in the github-actions group (#164)

### Other Changes
- Update rhiza_sync.yml to trigger on renovate and rhiza branches
- Update template.yml to reference version v0.9.2 (#165)
- Fix book target failing when mkdocs.yml is under docs/
- Bump version 0.4.3 → 0.4.4

## [0.4.3] - 2026-04-02

### Maintenance
- Chore(deps)(deps): bump github/codeql-action in the github-actions group (#161)
- Chore(deps-dev)(deps-dev): bump numpy in the python-dependencies group (#160)

### Other Changes
- Update template.yml with new ref and templates (#162)
- Bump version 0.4.2 → 0.4.3

## [0.4.2] - 2026-03-24

### New Features
- Pass --config through release to bump command (#159)

### Maintenance
- Chore(deps)(deps): bump the python-dependencies group with 2 updates (#157)

### Other Changes
- Update template.yml to reference version v0.8.16 (#155)
- Bump version 0.4.1 → 0.4.2

## [0.4.1] - 2026-03-19

### Maintenance
- Chore(deps-dev)(deps-dev): bump marimo in the python-dependencies group (#146)

### Other Changes
- Update template.yml to reference v0.8.13 (#148)
- Remove benchmarks
- Update template.yml to reference version v0.8.14 (#150)
- Fix coverage badge link in README.md (#153)
- Fix coverage badge link in README.md (#154)
- Bump version 0.4.0 → 0.4.1

## [0.4.0] - 2026-03-13

### Dependencies
- *(deps)* Update astral-sh/setup-uv action to v7.3.1 (#138)

### Maintenance
- Update via rhiza (#141)
- Chore(deps)(deps): bump the python-dependencies group across 1 directory with 3 updates (#142)
- Chore(deps)(deps): bump github/codeql-action in the github-actions group (#139)

### Other Changes
- Update repository reference from v0.8.3 to v0.8.5 (#137)
- Add `--config` / `-c` flag to `bump` to support custom `.cfg.toml` location (#144)
- Bump version 0.3.6 → 0.4.0

## [0.3.6] - 2026-02-24

### Bug Fixes
- Create test_coverage_gaps.py with language argument for resolve function tests (#133)
- Document security exceptions in tests/conftest.py

### Dependencies
- *(deps)* Update github/codeql-action action to v4.32.4 (#128)
- *(deps)* Update pre-commit hook astral-sh/ruff-pre-commit to v0.15.2 (#129)
- *(deps)* Lock file maintenance (#130)
- *(deps)* Lock file maintenance (#135)
- *(deps)* Update dependency jebel-quant/rhiza to v0.8.3 (#134)

### Maintenance
- Add tests to achieve 100% coverage (#136)

### Other Changes
- Refactor complex test helpers to reduce cyclomatic complexity (#127)
- Sync with rhiza 0.8.3
- Bump version 0.3.5-beta.2 → 0.3.6

## [0.3.5-beta.2] - 2026-02-20

### New Features
- Multi-language support for release command (#125)

### Dependencies
- *(deps)* Update pre-commit hook python-jsonschema/check-jsonschema to v0.36.2 (#122)
- *(deps)* Update actions/download-artifact action to v7 (#123)
- *(deps)* Update dependency astral-sh/uv to v0.10.4 (#120)
- *(deps)* Update pre-commit hook astral-sh/uv-pre-commit to v0.10.4 (#121)

### Other Changes
- Bump version 0.3.5-beta.1 → 0.3.5-beta.2

## [0.3.5-beta.1] - 2026-02-17

### Other Changes
- Fix rollback: lookup commit before tag deletion (#116)
- Fix PEP 440 normalization in release workflow version verification (#117)
- Fix serialize patterns for prerelease version formatting (#119)
- Bump version 0.3.4 → 0.3.5-beta.1

## [0.3.4] - 2026-02-17

### Dependencies
- *(deps)* Lock file maintenance (#105)
- *(deps)* Update pre-commit hook python-jsonschema/check-jsonschema to v0.36.2 (#108)
- *(deps)* Update actions/download-artifact action to v7 (#109)

### Maintenance
- Chore(deps)(deps): bump typer in the python-dependencies group (#110)
- Update via rhiza (#114)

### Other Changes
- Update template.yml (#107)
- Update reference version to v0.8.0
- Fix version format mismatch between pyproject.toml and git tags (#112)
- Bump version 0.3.3 → 0.3.4

## [0.3.3] - 2026-02-15

### Other Changes
- Bump version 0.3.2 → 0.3.3

## [0.3.2] - 2026-02-15

### Bug Fixes
- *(deps)* Update dependency bump-my-version to v1.2.7 (#101)

### Dependencies
- *(deps)* Update pre-commit hook rhysd/actionlint to v1.7.11 (#100)

### Maintenance
- Refactor (#97)

### Other Changes
- Add Go and multi-language support to bump command with model-based architecture (#99)
- Make sync (#102)
- Bump version 0.3.1 → 0.3.2
- Make sync

## [0.3.1] - 2026-02-14

### Bug Fixes
- Fix release and bump flow for push to remote (#96)

### Other Changes
- Release tag pushed before bump
- Bump version 0.3.0 → 0.3.1

## [0.3.0] - 2026-02-14

### New Features
- Check for errors first (#93)
- Rollback (#94)

### Bug Fixes
- Fix release flow e2e (#91)

### Dependencies
- *(deps)* Lock file maintenance (#77)
- *(deps)* Lock file maintenance (#79)
- *(deps)* Update dependency astral-sh/uv to v0.10.1 (#80)
- *(deps)* Update pre-commit hook jebel-quant/rhiza-hooks to v0.2.1 (#82)
- *(deps)* Update pre-commit hook astral-sh/uv-pre-commit to v0.10.2 (#81)

### Maintenance
- Sync with rhiza (#78)

### Other Changes
- Utilize bump-my-version configuration for complete release workflow (#84)
- Enhance bump and release commands with interactive flows, remote push support, and comprehensive testing guide (#86)
- Make sync + docs (#87)
- Update template.yml
- Sync
- Fix bugs release (#90)
- Bump version 0.2.3 → 0.3.0
- Revert "Chore: bump version 0.2.3 → 0.3.0"
- Update .cfg.toml
- Update docs (#92)
- Prettier output (#95)
- Bump version 0.2.3 → 0.3.0

## [0.2.3] - 2026-02-08

### Other Changes
- Add analyze-benchmarks command for pytest-benchmark visualization (#76)
- Bump version 0.2.2 → 0.2.3

## [0.2.2] - 2026-02-08

### Other Changes
- Update README.md
- Add version-matrix command for Python version detection (#75)
- Bump version 0.2.1 → 0.2.2

## [0.2.1] - 2026-02-07

### Bug Fixes
- Resolve mypy type checking errors
- Update mypy type ignore comments to match current errors
- Complete marimushka target implementation in book.mk

### Dependencies
- *(deps)* Update python docker tag to v3.14 (#55)
- *(deps)* Update ghcr.io/astral-sh/uv docker tag to v0.9.26 (#56)
- *(deps)* Update dependency astral-sh/uv to v0.9.26 (#57)
- *(deps)* Update ghcr.io/astral-sh/uv docker tag to v0.9.27 (#64)
- *(deps)* Update dependency astral-sh/uv to v0.9.27 (#63)
- *(deps)* Update github/codeql-action action to v4.32.2 (#72)
- *(deps)* Update dependency astral-sh/uv to v0.10.0 (#74)
- *(deps)* Update astral-sh/setup-uv action to v7.3.0 (#73)
- *(deps)* Update ghcr.io/astral-sh/uv docker tag to v0.9.30 (#71)

### Maintenance
- Chore(deps)(deps): bump the python-dependencies group with 2 updates (#60)
- Import rhiza templates (#61)
- Update via rhiza (#62)
- Sync with rhiza (#67)
- Chore(deps)(deps): bump github/codeql-action in the github-actions group (#68)
- Chore(deps-dev)(deps-dev): bump the python-dependencies group with 2 updates (#69)

### Other Changes
- Manual sync (#58)
- Add exclusions for book/marimo and book/jupyter
- Remove marimo.mk
- Fmt
- Sync
- Sync (#70)
- Sync
- Bump version 0.2.0 → 0.2.1

## [0.2.0] - 2026-01-12

### Other Changes
- Delete .rhiza.env (#48)
- Add --version flag to rhiza-tools CLI (#50)
- Bump version 0.1.4 → 0.2.0

## [0.1.4] - 2026-01-12

### Maintenance
- Update via rhiza (#21)
- Rhiza manage sync (#23)
- Import rhiza templates (#26)
- Update via rhiza (#42)

### Other Changes
- Import rhiza templates
- Add explicit package-to-module mappings for deptry (#39)
- Convert update-readme-help.sh to Python command (#29)
- Coverage (#40)
- [WIP] Add tests to achieve 100% coverage (#45)
- Introduce detailed Google-style docstrings including examples in src (#47)
- Bump version 0.1.2 → 0.1.3
- Bump version 0.1.3 → 0.1.4

## [0.1.2] - 2026-01-03

### Other Changes
- 18 move to dependency groups (#19)
- Bump backend (#20)

## [0.1.1] - 2026-01-01

### Maintenance
- Update via rhiza (#1)

### Other Changes
- Rhiza migrate
- Add badges
- Include python-dotenv as dev dependency
- Rhiza.env file
- Bump command (#2)
- Update README.md
- Merge pull request #7 from Jebel-Quant/6-codefactor-rating-into-readme
- Merge branch 'main' into 3-bring-in-python-dotenv
- Merge pull request #4 from Jebel-Quant/3-bring-in-python-dotenv
- Rhiza
- Merge pull request #9 from Jebel-Quant/8-sync
- Initial plan
- Refactor complex bump_command method into smaller, focused functions
- Address code review feedback: add constant for bump types, improve error handling, add rc test
- Add RC option to interactive bump type selection menu
- Refactor _determine_bump_type_from_choice to use dictionary-based lookup
- Merge pull request #11 from Jebel-Quant/copilot/refactor-complex-method
- Fix Downloads badge link in README.md
- Initial plan
- Initial plan for coverage percentage badge
- Add dynamic coverage percentage badge
- Add tests for coverage badge generation
- Improve error handling in coverage badge script
- Make book.sh script more robust by setting SCRIPTS_FOLDER fallback
- Improve code quality based on review feedback
- Fix shellcheck warning SC2181 - check exit code directly
- Pass COVERAGE_JSON directly to Python without fallback
- Merge pull request #15 from Jebel-Quant/copilot/add-coverage-percentage-badge
- Initial plan
- Add tests to achieve 100% test coverage
- Address code review feedback - improve test robustness
- Move imports to top of file for PEP 8 compliance
- Improve comment clarity in version verification test
- Run make fmt to fix linting issues
- Merge pull request #13 from Jebel-Quant/copilot/increase-test-coverage-100
- Spelling mistake in pytest
- Fix pytest spawn error in `make test` with configurable venv path (#17)

## [0.1.0] - 2025-12-24

### Maintenance
- Import rhiza templates

### Other Changes
- Initial commit
- Make install
- Update template
- Skeleton for rhiza-tools
- Readme
- Make fmt
- Remove old file

<!-- generated by git-cliff -->
