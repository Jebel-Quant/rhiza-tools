"""Tests for the bump command using a sandboxed git environment."""

import pytest
from unittest.mock import patch, MagicMock
from typer.testing import CliRunner
from rhiza_tools.cli import app
import tomlkit
from loguru import logger

runner = CliRunner()

@pytest.fixture
def capture_logs():
    logs = []
    # Add a sink that appends the message to the logs list
    handler_id = logger.add(lambda msg: logs.append(msg), format="{message}")
    yield logs
    logger.remove(handler_id)

@pytest.fixture
def mock_questionary():
    with patch("rhiza_tools.commands.bump.questionary") as mock:
        yield mock

def test_bump_patch_interactive(git_repo, mock_questionary, capture_logs):
    """Test interactive patch bump."""
    # Setup mock return value for questionary
    mock_questionary.select.return_value.ask.return_value = "Patch (0.1.0 -> 0.1.1)"

    # Run command in the git repo directory
    with patch("rhiza_tools.commands.bump.Path.cwd", return_value=git_repo):
        # We need to change the current working directory for the test
        # because the command looks for pyproject.toml in cwd
        import os
        cwd = os.getcwd()
        os.chdir(git_repo)
        try:
            result = runner.invoke(app, ["bump"])
        finally:
            os.chdir(cwd)

    assert result.exit_code == 0
    
    # Check logs
    output = "".join(capture_logs)
    assert "Current version: 0.1.0" in output
    assert "Bumping version using: patch" in output
    assert "New version will be: 0.1.1" in output
    assert "Version bumped: 0.1.0 -> 0.1.1" in output

    # Verify pyproject.toml updated
    with open(git_repo / "pyproject.toml") as f:
        content = f.read()
        assert 'version = "0.1.1"' in content

def test_bump_minor_interactive(git_repo, mock_questionary, capture_logs):
    """Test interactive minor bump."""
    mock_questionary.select.return_value.ask.return_value = "Minor (0.1.0 -> 0.2.0)"

    import os
    cwd = os.getcwd()
    os.chdir(git_repo)
    try:
        result = runner.invoke(app, ["bump"])
    finally:
        os.chdir(cwd)

    assert result.exit_code == 0
    output = "".join(capture_logs)
    assert "New version will be: 0.2.0" in output
    
    with open(git_repo / "pyproject.toml") as f:
        content = f.read()
        assert 'version = "0.2.0"' in content

def test_bump_major_interactive(git_repo, mock_questionary, capture_logs):
    """Test interactive major bump."""
    mock_questionary.select.return_value.ask.return_value = "Major (0.1.0 -> 1.0.0)"

    import os
    cwd = os.getcwd()
    os.chdir(git_repo)
    try:
        result = runner.invoke(app, ["bump"])
    finally:
        os.chdir(cwd)

    assert result.exit_code == 0
    output = "".join(capture_logs)
    assert "New version will be: 1.0.0" in output
    
    with open(git_repo / "pyproject.toml") as f:
        content = f.read()
        assert 'version = "1.0.0"' in content

def test_bump_dry_run(git_repo, mock_questionary, capture_logs):
    """Test dry run does not update file."""
    mock_questionary.select.return_value.ask.return_value = "Patch (0.1.0 -> 0.1.1)"

    import os
    cwd = os.getcwd()
    os.chdir(git_repo)
    try:
        result = runner.invoke(app, ["bump", "--dry-run"])
    finally:
        os.chdir(cwd)

    assert result.exit_code == 0
    output = "".join(capture_logs)
    assert "Dry run enabled" in output
    
    # Verify pyproject.toml NOT updated
    with open(git_repo / "pyproject.toml") as f:
        content = f.read()
        assert 'version = "0.1.0"' in content

def test_bump_explicit_version(git_repo, capture_logs):
    """Test bumping to an explicit version."""
    import os
    cwd = os.getcwd()
    os.chdir(git_repo)
    try:
        result = runner.invoke(app, ["bump", "1.2.3"])
    finally:
        os.chdir(cwd)

    assert result.exit_code == 0
    output = "".join(capture_logs)
    assert "New version will be: 1.2.3" in output
    
    with open(git_repo / "pyproject.toml") as f:
        content = f.read()
        assert 'version = "1.2.3"' in content

def test_bump_invalid_version_file(git_repo, capture_logs):
    """Test error when pyproject.toml has invalid version."""
    # Corrupt the version in pyproject.toml
    with open(git_repo / "pyproject.toml", "r") as f:
        data = tomlkit.parse(f.read())
    data["project"]["version"] = "invalid"
    with open(git_repo / "pyproject.toml", "w") as f:
        f.write(tomlkit.dumps(data))

    import os
    cwd = os.getcwd()
    os.chdir(git_repo)
    try:
        result = runner.invoke(app, ["bump"])
    finally:
        os.chdir(cwd)

    assert result.exit_code == 1
    output = "".join(capture_logs)
    assert "Invalid semantic version" in output

def test_bump_no_pyproject(tmp_path, capture_logs):
    """Test error when pyproject.toml is missing."""
    import os
    cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        result = runner.invoke(app, ["bump"])
    finally:
        os.chdir(cwd)

    assert result.exit_code == 1
    output = "".join(capture_logs)
    assert "pyproject.toml not found" in output
