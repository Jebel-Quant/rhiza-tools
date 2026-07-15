"""Tests for rhiza_tools.__main__.py module."""

import contextlib
import importlib.util
import runpy
import sys
from unittest.mock import patch


def test_main_entry_point():
    """Test that the CLI entry point works (equivalent to python -m rhiza_tools --help).

    Uses typer.testing.CliRunner instead of spawning a subprocess, which avoids
    DLL-loading failures on Windows Python 3.14 when sys.executable points to a
    uv-managed venv whose Python DLLs are not on the child-process search path.
    """
    from typer.testing import CliRunner

    from rhiza_tools.cli import app

    runner = CliRunner()
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Rhiza Tools" in result.output or "Usage" in result.output


def test_main_direct_execution():
    """Test that __main__.py can be executed directly as a script.

    Uses runpy.run_path instead of spawning a subprocess, which avoids
    DLL-loading failures on Windows Python 3.14 when sys.executable points to a
    uv-managed venv whose Python DLLs are not on the child-process search path.
    """
    spec = importlib.util.find_spec("rhiza_tools.__main__")
    main_file = spec.origin

    exit_code = None
    with patch("sys.argv", ["rhiza_tools", "--help"]):
        try:
            runpy.run_path(main_file, run_name="__main__")
        except SystemExit as e:
            exit_code = e.code

    assert exit_code == 0


def test_main_if_name_main_block():
    """Test the if __name__ == '__main__' block in __main__.py is covered."""
    # Use runpy to execute the module as __main__
    # This properly triggers the if __name__ == "__main__" block

    # Remove rhiza_tools.__main__ from sys.modules to avoid the warning
    # about finding the module before execution
    main_module_name = "rhiza_tools.__main__"
    saved_module = sys.modules.pop(main_module_name, None)

    try:
        # Mock sys.argv and the app to prevent actual execution
        with (
            patch("sys.argv", ["rhiza_tools", "--help"]),
            patch("rhiza_tools.cli.app") as mock_app,
            contextlib.suppress(SystemExit),
        ):
            # Run the module as if it were __main__
            runpy.run_module(main_module_name, run_name="__main__")

            # The app should have been called
            assert mock_app.called
    finally:
        # Restore the module to sys.modules if it was there before
        if saved_module is not None:
            sys.modules[main_module_name] = saved_module
