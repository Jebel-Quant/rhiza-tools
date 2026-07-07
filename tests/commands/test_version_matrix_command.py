"""Comprehensive unit tests for version matrix command."""

import json

import pytest
import typer

from rhiza_tools.commands.version_matrix import (
    PyProjectError,
    VersionSpecifierError,
    _check_operator,
    get_supported_versions,
    parse_version,
    satisfies,
    version_matrix_command,
)


class TestParseVersion:
    """Tests for the parse_version function."""

    def test_simple_two_part_version(self):
        """Test parsing a simple two-part version."""
        assert parse_version("3.11") == (3, 11)

    def test_three_part_version(self):
        """Test parsing a three-part version."""
        assert parse_version("3.11.0") == (3, 11, 0)

    def test_version_with_suffix(self):
        """Test parsing version with non-numeric suffix (e.g., rc1)."""
        # The function extracts only the numeric prefix
        assert parse_version("3.11.0rc1") == (3, 11, 0)

    def test_version_with_multiple_suffixes(self):
        """Test parsing version with suffixes in multiple parts."""
        assert parse_version("3.11rc1.0beta2") == (3, 11, 0)

    def test_invalid_version_component_no_digits(self):
        """Test that version component without digits raises error."""
        with pytest.raises(VersionSpecifierError) as exc_info:
            parse_version("3.alpha")
        assert "Invalid version component" in str(exc_info.value)
        assert "'alpha'" in str(exc_info.value)

    def test_invalid_version_component_special_chars(self):
        """Test that version component with only special chars raises error."""
        with pytest.raises(VersionSpecifierError) as exc_info:
            parse_version("3.-11")
        assert "Invalid version component" in str(exc_info.value)


class TestCheckOperator:
    """Tests for the _check_operator function."""

    def test_greater_than_or_equal_true(self):
        """Test >= operator returns True when condition is met."""
        assert _check_operator((3, 11), ">=", (3, 10)) is True
        assert _check_operator((3, 11), ">=", (3, 11)) is True

    def test_greater_than_or_equal_false(self):
        """Test >= operator returns False when condition is not met."""
        assert _check_operator((3, 9), ">=", (3, 10)) is False

    def test_less_than_or_equal_true(self):
        """Test <= operator returns True when condition is met."""
        assert _check_operator((3, 10), "<=", (3, 11)) is True
        assert _check_operator((3, 11), "<=", (3, 11)) is True

    def test_less_than_or_equal_false(self):
        """Test <= operator returns False when condition is not met."""
        assert _check_operator((3, 12), "<=", (3, 11)) is False

    def test_greater_than_true(self):
        """Test > operator returns True when condition is met."""
        assert _check_operator((3, 12), ">", (3, 11)) is True

    def test_greater_than_false(self):
        """Test > operator returns False when condition is not met."""
        assert _check_operator((3, 11), ">", (3, 11)) is False

    def test_less_than_true(self):
        """Test < operator returns True when condition is met."""
        assert _check_operator((3, 10), "<", (3, 11)) is True

    def test_less_than_false(self):
        """Test < operator returns False when condition is not met."""
        assert _check_operator((3, 11), "<", (3, 11)) is False

    def test_equal_true(self):
        """Test == operator returns True when condition is met."""
        assert _check_operator((3, 11), "==", (3, 11)) is True

    def test_equal_false(self):
        """Test == operator returns False when condition is not met."""
        assert _check_operator((3, 11), "==", (3, 12)) is False

    def test_not_equal_true(self):
        """Test != operator returns True when condition is met."""
        assert _check_operator((3, 11), "!=", (3, 12)) is True

    def test_not_equal_false(self):
        """Test != operator returns False when condition is not met."""
        assert _check_operator((3, 11), "!=", (3, 11)) is False

    def test_unknown_operator(self):
        """Test that unknown operator raises error."""
        with pytest.raises(VersionSpecifierError) as exc_info:
            _check_operator((3, 11), "~=", (3, 10))
        assert "Unknown operator" in str(exc_info.value)


class TestSatisfies:
    """Tests for the satisfies function."""

    def test_single_specifier_greater_than_or_equal_true(self):
        """Test single >= specifier that matches."""
        assert satisfies("3.11", ">=3.11") is True
        assert satisfies("3.12", ">=3.11") is True

    def test_single_specifier_greater_than_or_equal_false(self):
        """Test single >= specifier that doesn't match."""
        assert satisfies("3.10", ">=3.11") is False

    def test_multiple_specifiers_all_match(self):
        """Test multiple comma-separated specifiers that all match."""
        assert satisfies("3.12", ">=3.11,<3.14") is True

    def test_multiple_specifiers_one_fails(self):
        """Test multiple specifiers where one fails."""
        assert satisfies("3.14", ">=3.11,<3.14") is False

    def test_specifier_with_spaces(self):
        """Test specifiers with extra whitespace."""
        assert satisfies("3.12", ">= 3.11 , < 3.14") is True

    def test_implicit_equality_specifier(self):
        """Test specifier without operator (assumes ==)."""
        assert satisfies("3.11", "3.11") is True
        assert satisfies("3.12", "3.11") is False

    def test_all_operators_in_combination(self):
        """Test complex combination of operators."""
        # Version 3.12 should satisfy: >=3.11, <=3.13, >3.10, <3.14, !=3.11
        assert satisfies("3.12", ">=3.11,<=3.13,>3.10,<3.14,!=3.11") is True

    def test_invalid_specifier_format(self):
        """Test that invalid specifier format raises error."""
        with pytest.raises(VersionSpecifierError) as exc_info:
            satisfies("3.11", "~=3.10")
        assert "Invalid specifier" in str(exc_info.value)

    def test_less_than_operator(self):
        """Test < operator in specifier."""
        assert satisfies("3.11", "<3.12") is True
        assert satisfies("3.13", "<3.12") is False

    def test_greater_than_operator(self):
        """Test > operator in specifier."""
        assert satisfies("3.13", ">3.12") is True
        assert satisfies("3.11", ">3.12") is False

    def test_not_equal_operator(self):
        """Test != operator in specifier."""
        assert satisfies("3.13", "!=3.12") is True
        assert satisfies("3.12", "!=3.12") is False

    def test_equal_operator_explicit(self):
        """Test == operator in specifier."""
        assert satisfies("3.12", "==3.12") is True
        assert satisfies("3.11", "==3.12") is False


class TestGetSupportedVersions:
    """Tests for the get_supported_versions function."""

    def test_successful_version_detection(self, tmp_path):
        """Test successful detection of supported versions."""
        # Create pyproject.toml
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("""
[project]
name = "test-project"
requires-python = ">=3.11"
""")

        candidates = ["3.10", "3.11", "3.12", "3.13"]
        result = get_supported_versions(pyproject, candidates)

        assert result == ["3.11", "3.12", "3.13"]

    def test_version_with_upper_bound(self, tmp_path):
        """Test version detection with upper bound."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("""
[project]
name = "test-project"
requires-python = ">=3.11,<3.13"
""")

        candidates = ["3.10", "3.11", "3.12", "3.13"]
        result = get_supported_versions(pyproject, candidates)

        assert result == ["3.11", "3.12"]

    def test_exact_version_match(self, tmp_path):
        """Test exact version matching."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("""
[project]
name = "test-project"
requires-python = "==3.11"
""")

        candidates = ["3.10", "3.11", "3.12"]
        result = get_supported_versions(pyproject, candidates)

        assert result == ["3.11"]

    def test_missing_pyproject_file(self, tmp_path):
        """Test error when pyproject.toml doesn't exist."""
        pyproject = tmp_path / "nonexistent.toml"
        candidates = ["3.11", "3.12"]

        with pytest.raises(PyProjectError) as exc_info:
            get_supported_versions(pyproject, candidates)

        assert "not found" in str(exc_info.value)

    def test_missing_requires_python(self, tmp_path):
        """Test error when requires-python field is missing."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("""
[project]
name = "test-project"
""")

        candidates = ["3.11", "3.12"]

        with pytest.raises(PyProjectError) as exc_info:
            get_supported_versions(pyproject, candidates)

        assert "missing 'project.requires-python'" in str(exc_info.value)

    def test_no_candidates_match(self, tmp_path):
        """Test error when no candidates match the specifier."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("""
[project]
name = "test-project"
requires-python = ">=3.15"
""")

        candidates = ["3.11", "3.12", "3.13", "3.14"]

        with pytest.raises(PyProjectError) as exc_info:
            get_supported_versions(pyproject, candidates)

        assert "no supported Python versions match" in str(exc_info.value)
        assert ">=3.15" in str(exc_info.value)

    def test_missing_project_section(self, tmp_path):
        """Test error when project section is missing entirely."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("""
[build-system]
requires = ["hatchling"]
""")

        candidates = ["3.11", "3.12"]

        with pytest.raises(PyProjectError) as exc_info:
            get_supported_versions(pyproject, candidates)

        assert "missing 'project.requires-python'" in str(exc_info.value)


class TestVersionMatrixCommand:
    """Tests for the version_matrix_command function."""

    def test_successful_execution_with_defaults(self, tmp_path, monkeypatch, capsys):
        """Test successful execution with default arguments."""
        # Create pyproject.toml in current directory
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("""
[project]
name = "test-project"
requires-python = ">=3.11,<3.14"
""")

        # Change to temp directory so default path works
        monkeypatch.chdir(tmp_path)

        # Execute with defaults
        version_matrix_command()

        # Check output
        captured = capsys.readouterr()
        result = json.loads(captured.out.strip())
        assert result == ["3.11", "3.12", "3.13"]

    def test_execution_with_custom_pyproject_path(self, tmp_path, capsys):
        """Test execution with custom pyproject.toml path."""
        pyproject = tmp_path / "custom" / "pyproject.toml"
        pyproject.parent.mkdir()
        pyproject.write_text("""
[project]
name = "test-project"
requires-python = ">=3.12"
""")

        version_matrix_command(pyproject_path=pyproject)

        captured = capsys.readouterr()
        result = json.loads(captured.out.strip())
        assert "3.12" in result
        assert "3.13" in result
        assert "3.11" not in result

    def test_execution_with_custom_candidates(self, tmp_path, monkeypatch, capsys):
        """Test execution with custom candidate versions."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("""
[project]
name = "test-project"
requires-python = ">=3.10,<3.12"
""")

        monkeypatch.chdir(tmp_path)

        # Use custom candidates including 3.10
        version_matrix_command(candidates=["3.9", "3.10", "3.11", "3.12"])

        captured = capsys.readouterr()
        result = json.loads(captured.out.strip())
        assert result == ["3.10", "3.11"]

    def test_execution_with_missing_file_exits(self, tmp_path, monkeypatch, capsys):
        """Test that command exits with error when pyproject.toml is missing."""
        monkeypatch.chdir(tmp_path)

        # Should exit with error
        with pytest.raises(typer.Exit) as exc_info:
            version_matrix_command()

        assert exc_info.value.exit_code == 1

        # Check error message
        captured = capsys.readouterr()
        assert "not found" in captured.err

    def test_execution_with_invalid_specifier(self, tmp_path, monkeypatch, capsys):
        """Test that command exits with error for invalid specifier."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("""
[project]
name = "test-project"
requires-python = "~=3.11"
""")

        monkeypatch.chdir(tmp_path)

        with pytest.raises(typer.Exit) as exc_info:
            version_matrix_command()

        assert exc_info.value.exit_code == 1

        captured = capsys.readouterr()
        assert "Invalid specifier" in captured.err

    def test_execution_with_no_matching_versions(self, tmp_path, monkeypatch, capsys):
        """Test that command exits with error when no versions match."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("""
[project]
name = "test-project"
requires-python = ">=4.0"
""")

        monkeypatch.chdir(tmp_path)

        with pytest.raises(typer.Exit) as exc_info:
            version_matrix_command()

        assert exc_info.value.exit_code == 1

        captured = capsys.readouterr()
        assert "no supported Python versions match" in captured.err
