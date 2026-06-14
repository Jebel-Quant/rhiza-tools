## Makefile (repo-owned)
# Keep this file small. It can be edited without breaking template sync.

DEFAULT_AI_MODEL=claude-sonnet-4.6
LOGO_FILE=.rhiza/assets/rhiza-logo.svg
GH_AW_ENGINE ?= copilot  # Default AI engine for gh-aw workflows (copilot, claude, or codex)

# Override template default: fix quoting bug and typo (mkdocstring -> mkdocstrings)
MKDOCS_EXTRA_PACKAGES = --with-editable . --with 'mkdocstrings[python]'

# NOTE: we intentionally do NOT raise COVERAGE_FAIL_UNDER here. The Rhiza
# template owns the default (90) and has a contract test
# (.rhiza/tests/api/test_make_variable_overrides.py::test_default_threshold_is_90)
# that fails if the repo Makefile changes it. Raising the *enforced* gate to 100
# must happen upstream in jebel-quant/rhiza; actual src/ coverage is kept at 100%.

# Always include the Rhiza API (template-managed)
include .rhiza/rhiza.mk

# Optional: developer-local extensions (not committed)
-include local.mk
