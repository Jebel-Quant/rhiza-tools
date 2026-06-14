"""Property-based tests for the pure version-math in ``bump_versioning``.

``bump_versioning`` is the deliberately side-effect-free version-arithmetic
layer of the bump command (PEP 440 / semver normalization, prerelease
calculation, bump-type resolution, version-argument parsing). Issue #262 adds
``hypothesis`` coverage so these functions are checked against generated inputs —
invariants that hold for *every* version, not just the hand-picked examples in
``test_bump_command.py``.

Each property asserts a structural guarantee (validity, ordering, idempotence)
rather than a single expected value, so regressions in the math surface even for
versions no example test happens to use.
"""

from __future__ import annotations

import semver
from hypothesis import given
from hypothesis import strategies as st

from rhiza_tools.commands.bump_versioning import (
    _denormalize_pep440_to_semver,
    _parse_version_argument,
    _validate_explicit_version,
    get_bumped_version_from_type,
    get_next_prerelease,
)

# Version components kept in a sane range: large enough to exercise multi-digit
# parsing, small enough to keep generated cases cheap.
_COMPONENT = st.integers(min_value=0, max_value=10_000)

# Build a clean (no prerelease / build) semver Version from three components.
_versions = st.builds(semver.Version, major=_COMPONENT, minor=_COMPONENT, patch=_COMPONENT)

# PEP 440 prerelease letters and their semver expansion (mirrors the release_map
# in ``_denormalize_pep440_to_semver``).
_PEP440_LETTERS = {"a": "alpha", "alpha": "alpha", "b": "beta", "beta": "beta", "rc": "rc", "dev": "dev"}

_PRERELEASE_TOKENS = st.sampled_from(["alpha", "beta", "rc", "dev"])


# --------------------------------------------------------------------------- #
# get_bumped_version_from_type
# --------------------------------------------------------------------------- #
@given(_versions)
def test_major_bump_increments_major_and_zeros_rest(version: semver.Version) -> None:
    """A ``major`` bump increments major and zeros minor/patch, staying valid semver."""
    result = semver.Version.parse(get_bumped_version_from_type(version, "major"))
    assert result.major == version.major + 1
    assert result.minor == 0
    assert result.patch == 0


@given(_versions)
def test_minor_bump_increments_minor_and_zeros_patch(version: semver.Version) -> None:
    """A ``minor`` bump increments minor, zeros patch, and leaves major untouched."""
    result = semver.Version.parse(get_bumped_version_from_type(version, "minor"))
    assert result.major == version.major
    assert result.minor == version.minor + 1
    assert result.patch == 0


@given(_versions)
def test_patch_bump_increments_only_patch(version: semver.Version) -> None:
    """A ``patch`` bump increments patch and leaves major/minor untouched."""
    result = semver.Version.parse(get_bumped_version_from_type(version, "patch"))
    assert result.major == version.major
    assert result.minor == version.minor
    assert result.patch == version.patch + 1


@given(_versions, st.sampled_from(["patch", "minor", "major", "prerelease", "build"]))
def test_known_bump_types_yield_valid_semver(version: semver.Version, bump_type: str) -> None:
    """Every supported bump keyword produces a parseable semantic version."""
    result = get_bumped_version_from_type(version, bump_type)
    assert result != ""
    semver.Version.parse(result)  # raises if invalid


@given(
    _versions,
    st.text().filter(
        lambda s: s not in {"patch", "minor", "major", "prerelease", "build", "alpha", "beta", "rc", "dev"}
    ),
)
def test_unknown_bump_type_returns_empty_string(version: semver.Version, bump_type: str) -> None:
    """An unrecognized bump type yields the empty-string sentinel, never a guess."""
    assert get_bumped_version_from_type(version, bump_type) == ""


# --------------------------------------------------------------------------- #
# get_next_prerelease
# --------------------------------------------------------------------------- #
@given(_versions, _PRERELEASE_TOKENS)
def test_next_prerelease_is_greater_and_tagged(version: semver.Version, token: str) -> None:
    """From a release version, the next prerelease is strictly greater and carries the token."""
    result = get_next_prerelease(version, token)
    assert result > version
    assert result.prerelease is not None
    assert result.prerelease.startswith(token)


@given(_versions, _PRERELEASE_TOKENS)
def test_same_token_prerelease_bumps_monotonically(version: semver.Version, token: str) -> None:
    """Re-applying the same token to an existing prerelease advances it monotonically."""
    first = get_next_prerelease(version, token)
    second = get_next_prerelease(first, token)
    assert second > first
    assert second.prerelease.startswith(token)


# --------------------------------------------------------------------------- #
# _denormalize_pep440_to_semver
# --------------------------------------------------------------------------- #
@given(_COMPONENT, _COMPONENT, _COMPONENT, st.sampled_from(list(_PEP440_LETTERS)), _COMPONENT)
def test_pep440_prerelease_denormalizes_to_valid_semver(
    major: int, minor: int, patch: int, letter: str, pre_n: int
) -> None:
    """A PEP 440 prerelease (e.g. ``1.2.3a4``) becomes the matching semver form and parses."""
    pep440 = f"{major}.{minor}.{patch}{letter}{pre_n}"
    result = _denormalize_pep440_to_semver(pep440)
    assert result == f"{major}.{minor}.{patch}-{_PEP440_LETTERS[letter]}.{pre_n}"
    semver.Version.parse(result)  # raises if invalid


@given(_COMPONENT, _COMPONENT, _COMPONENT)
def test_plain_semver_is_unchanged(major: int, minor: int, patch: int) -> None:
    """A release-only version (no PEP 440 prerelease) passes through untouched."""
    plain = f"{major}.{minor}.{patch}"
    assert _denormalize_pep440_to_semver(plain) == plain


@given(_COMPONENT, _COMPONENT, _COMPONENT, st.sampled_from(list(_PEP440_LETTERS)), _COMPONENT)
def test_denormalize_is_idempotent(major: int, minor: int, patch: int, letter: str, pre_n: int) -> None:
    """Denormalizing an already-denormalized value is a no-op (stable under repetition)."""
    once = _denormalize_pep440_to_semver(f"{major}.{minor}.{patch}{letter}{pre_n}")
    assert _denormalize_pep440_to_semver(once) == once


# --------------------------------------------------------------------------- #
# _validate_explicit_version / _parse_version_argument
# --------------------------------------------------------------------------- #
@given(_versions, st.booleans())
def test_validate_explicit_version_strips_v_and_roundtrips(version: semver.Version, with_prefix: bool) -> None:
    """A valid version (optionally ``v``-prefixed) is cleaned to its canonical semver string."""
    raw = f"v{version}" if with_prefix else str(version)
    cleaned = _validate_explicit_version(raw)
    assert not cleaned.startswith("v")
    assert semver.Version.parse(cleaned) == version


@given(_versions)
def test_parse_explicit_version_argument_returns_same_version(version: semver.Version) -> None:
    """An explicit version argument is returned verbatim (independent of the current version)."""
    result = _parse_version_argument(str(version), "0.0.0")
    assert semver.Version.parse(result) == version


@given(_versions)
def test_parse_patch_keyword_increments_current(version: semver.Version) -> None:
    """The ``patch`` keyword resolves against the *current* version, bumping its patch."""
    result = _parse_version_argument("patch", str(version))
    assert semver.Version.parse(result) == version.bump_patch()
