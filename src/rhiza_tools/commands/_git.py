"""Git plumbing shared across rhiza-tools commands.

This module owns the git-facing helpers used by the bump and release flows:

    - run_git_command: Execute git commands with standard error handling.
    - check_tag_exists: Report whether a tag exists locally and/or remotely.
    - get_current_git_branch: Safely determine the current git branch.
    - get_latest_remote_version: Highest semver tag published on the remote.
"""

import subprocess  # nosec B404 - subprocess needed for git operations

import semver

from rhiza_tools import console


def run_git_command(command: list[str], check: bool = True) -> subprocess.CompletedProcess[str]:
    """Run a git command and return the result.

    Args:
        command: The git command to run as a list of arguments.
        check: If True, raise an exception on non-zero exit code.

    Returns:
        CompletedProcess instance with stdout, stderr, and returncode.

    Raises:
        subprocess.CalledProcessError: If check=True and command fails.

    Example:
        >>> result = run_git_command(["git", "status", "--porcelain"])  # doctest: +SKIP
        >>> print(result.stdout)  # doctest: +SKIP
    """
    result = subprocess.run(command, capture_output=True, text=True, check=False)  # nosec B603 - git commands are trusted  # noqa: S603
    if check and result.returncode != 0:
        console.error(f"Git command failed: {' '.join(command)}")
        console.error(f"Error: {result.stderr}")
        raise subprocess.CalledProcessError(result.returncode, command, result.stdout, result.stderr)
    return result


def check_tag_exists(tag: str) -> tuple[bool, bool]:
    """Check if a tag exists locally and/or remotely.

    Args:
        tag: The tag name to check.

    Returns:
        Tuple of (exists_locally, exists_remotely).

    Example:
        >>> local, remote = check_tag_exists("v1.0.0")  # doctest: +SKIP
        >>> if remote:  # doctest: +SKIP
        ...     print("Tag already released")  # doctest: +SKIP
    """
    # Check local
    result = run_git_command(["git", "rev-parse", tag], check=False)
    exists_locally = result.returncode == 0

    # Check remote
    result = run_git_command(["git", "ls-remote", "--exit-code", "--tags", "origin", f"refs/tags/{tag}"], check=False)
    exists_remotely = result.returncode == 0

    return exists_locally, exists_remotely


def get_current_git_branch() -> str:
    """Get the current git branch name.

    This is the safe variant that returns ``"unknown"`` on failure,
    suitable for display purposes. For strict validation use
    :func:`run_git_command` directly.

    Returns:
        Current branch name or "unknown" if unable to determine.
    """
    result = run_git_command(["git", "rev-parse", "--abbrev-ref", "HEAD"], check=False)
    return result.stdout.strip() if result.returncode == 0 else "unknown"


def get_latest_remote_version(remote: str = "origin") -> semver.Version | None:
    """Return the highest semantic-version tag published on *remote*.

    This reads ``v*``-style tags directly from the remote with ``git ls-remote``
    (no local fetch, no working-tree changes) and returns the greatest valid
    semver among them. It is the source of truth for "what is the latest
    released version" and exists to stop the release tooling from trusting a
    potentially stale local ``pyproject.toml`` (see issue #1126).

    Tags that are not valid semantic versions are ignored. The function never
    raises for the common failure modes (no remote configured, no tags, network
    unavailable); it returns ``None`` so callers can degrade gracefully.

    Args:
        remote: The git remote to query. Defaults to ``"origin"``.

    Returns:
        The highest :class:`semver.Version` found on the remote, or ``None`` if
        the remote cannot be reached or has no valid version tags.

    Example:
        >>> latest = get_latest_remote_version()  # doctest: +SKIP
        >>> print(latest)  # doctest: +SKIP
        0.4.0
    """
    result = run_git_command(["git", "ls-remote", "--tags", remote], check=False)
    if result.returncode != 0 or not result.stdout.strip():
        return None

    versions: list[semver.Version] = []
    for line in result.stdout.splitlines():
        # Each line is "<sha>\trefs/tags/<tag>"; annotated tags also appear
        # peeled as "refs/tags/<tag>^{}" which we normalise away.
        ref = line.split("\t")[-1].strip()
        if not ref.startswith("refs/tags/"):
            continue
        tag = ref[len("refs/tags/") :].removesuffix("^{}")
        if tag.startswith("v"):
            tag = tag[1:]
        try:
            versions.append(semver.Version.parse(tag))
        except ValueError:
            # Non-semver tags (e.g. "latest", date stamps) are not releases.
            continue

    return max(versions) if versions else None
