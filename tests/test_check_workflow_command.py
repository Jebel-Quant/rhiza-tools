"""Tests for check_workflow command."""

from pathlib import Path

import pytest
import yaml

from rhiza_tools.commands.check_workflow import check_file, check_workflow_command


class TestCheckFile:
    """Tests for check_file function."""

    def test_correct_prefix_returns_true(self, tmp_path: Path) -> None:
        """File with correct (RHIZA) prefix returns True."""
        workflow = tmp_path / "workflow.yml"
        workflow.write_text('name: "(RHIZA) My Workflow"\non: push\n')

        assert check_file(str(workflow)) is True

    def test_missing_prefix_updates_file(self, tmp_path: Path) -> None:
        """File without (RHIZA) prefix is updated and returns False."""
        workflow = tmp_path / "workflow.yml"
        workflow.write_text("name: My Workflow\non: push\n")

        result = check_file(str(workflow))

        assert result is False
        content = workflow.read_text()
        assert "(RHIZA) My Workflow" in content

    def test_missing_name_field_returns_false(self, tmp_path: Path) -> None:
        """File without name field returns False."""
        workflow = tmp_path / "workflow.yml"
        workflow.write_text("on: push\njobs:\n  test:\n    runs-on: ubuntu-latest\n")

        result = check_file(str(workflow))

        assert result is False

    def test_invalid_yaml_returns_false(self, tmp_path: Path) -> None:
        """Invalid YAML returns False."""
        workflow = tmp_path / "workflow.yml"
        workflow.write_text("name: test\n  invalid: yaml: syntax:\n")

        result = check_file(str(workflow))

        assert result is False

    def test_empty_file_returns_true(self, tmp_path: Path) -> None:
        """Empty YAML file returns True (nothing to check)."""
        workflow = tmp_path / "workflow.yml"
        workflow.write_text("")

        assert check_file(str(workflow)) is True

    def test_preserves_other_content(self, tmp_path: Path) -> None:
        """Updating name prefix preserves other file content."""
        original = """name: CI Pipeline
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
"""
        workflow = tmp_path / "workflow.yml"
        workflow.write_text(original)

        result = check_file(str(workflow))
        assert result is False

        content = workflow.read_text()
        # Check name was updated
        assert "(RHIZA) CI Pipeline" in content
        # Check other content preserved
        assert "branches: [main]" in content
        assert "runs-on: ubuntu-latest" in content
        assert "actions/checkout@v4" in content

    def test_quoted_name_with_prefix(self, tmp_path: Path) -> None:
        """File with quoted name containing prefix returns True."""
        workflow = tmp_path / "workflow.yml"
        workflow.write_text('name: "(RHIZA) Test"\non: push\n')

        assert check_file(str(workflow)) is True

    def test_unquoted_name_with_prefix(self, tmp_path: Path) -> None:
        """File with unquoted name containing prefix returns True."""
        workflow = tmp_path / "workflow.yml"
        workflow.write_text("name: (RHIZA) Test\non: push\n")

        assert check_file(str(workflow)) is True

    def test_name_with_special_characters(self, tmp_path: Path) -> None:
        """Name with special characters is handled correctly."""
        workflow = tmp_path / "workflow.yml"
        workflow.write_text("name: Build & Deploy\non: push\n")

        result = check_file(str(workflow))
        assert result is False

        content = workflow.read_text()
        assert "(RHIZA) Build & Deploy" in content

    def test_non_string_name_field_returns_false(self, tmp_path: Path) -> None:
        """File with non-string name field returns False."""
        workflow = tmp_path / "workflow.yml"
        # YAML boolean value (unquoted 'on' parses as True in YAML 1.1)
        workflow.write_text("name: 123\non: push\n")

        result = check_file(str(workflow))

        assert result is False

    def test_name_with_quotes_escaped_correctly(self, tmp_path: Path) -> None:
        """Name containing quotes is escaped correctly in output."""
        workflow = tmp_path / "workflow.yml"
        workflow.write_text('name: Test "quoted" name\non: push\n')

        result = check_file(str(workflow))
        assert result is False

        content = workflow.read_text()
        # The new name should be properly escaped and valid YAML
        assert "(RHIZA)" in content
        # Verify it's valid YAML
        parsed = yaml.safe_load(content)
        assert parsed["name"] == '(RHIZA) Test "quoted" name'

    def test_name_with_backslashes_escaped_correctly(self, tmp_path: Path) -> None:
        """Name containing backslashes is escaped correctly in output."""
        workflow = tmp_path / "workflow.yml"
        workflow.write_text(r'name: Test\path\name' + '\non: push\n')

        result = check_file(str(workflow))
        assert result is False

        content = workflow.read_text()
        # Verify it's valid YAML
        parsed = yaml.safe_load(content)
        assert parsed["name"] == r'(RHIZA) Test\path\name'


class TestCheckWorkflowCommand:
    """Tests for check_workflow_command function."""

    def test_no_files_exits_with_error(self) -> None:
        """Command with no files exits with error."""
        import typer

        with pytest.raises(typer.Exit) as exc_info:
            check_workflow_command([])
        assert exc_info.value.exit_code == 1

    def test_nonexistent_file_exits_with_error(self, tmp_path: Path) -> None:
        """Command with nonexistent file exits with error."""
        import typer

        nonexistent = tmp_path / "nonexistent.yml"
        with pytest.raises(typer.Exit) as exc_info:
            check_workflow_command([str(nonexistent)])
        assert exc_info.value.exit_code == 1

    def test_correct_file_succeeds(self, tmp_path: Path) -> None:
        """Command with correct file succeeds."""
        workflow = tmp_path / "workflow.yml"
        workflow.write_text('name: "(RHIZA) Test"\non: push\n')

        # Should not raise
        check_workflow_command([str(workflow)])

    def test_incorrect_file_exits_with_error(self, tmp_path: Path) -> None:
        """Command with incorrect file exits with error after updating."""
        import typer

        workflow = tmp_path / "workflow.yml"
        workflow.write_text("name: Test\non: push\n")

        with pytest.raises(typer.Exit) as exc_info:
            check_workflow_command([str(workflow)])
        assert exc_info.value.exit_code == 1

        # Check that file was updated
        content = workflow.read_text()
        assert "(RHIZA) Test" in content

    def test_multiple_files(self, tmp_path: Path) -> None:
        """Command can check multiple files."""
        workflow1 = tmp_path / "workflow1.yml"
        workflow1.write_text('name: "(RHIZA) Test1"\non: push\n')

        workflow2 = tmp_path / "workflow2.yml"
        workflow2.write_text('name: "(RHIZA) Test2"\non: push\n')

        # Should not raise
        check_workflow_command([str(workflow1), str(workflow2)])

    def test_mixed_files_exits_with_error(self, tmp_path: Path) -> None:
        """Command with mix of correct and incorrect files exits with error."""
        import typer

        workflow1 = tmp_path / "workflow1.yml"
        workflow1.write_text('name: "(RHIZA) Test1"\non: push\n')

        workflow2 = tmp_path / "workflow2.yml"
        workflow2.write_text("name: Test2\non: push\n")

        with pytest.raises(typer.Exit) as exc_info:
            check_workflow_command([str(workflow1), str(workflow2)])
        assert exc_info.value.exit_code == 1

        # Check that incorrect file was updated
        content = workflow2.read_text()
        assert "(RHIZA) Test2" in content
