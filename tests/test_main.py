"""Tests for rhiza_tools.__main__.py module."""

import importlib.util
import runpy
import subprocess
import sys
from unittest.mock import patch


def test_main_entry_point():
    """Test that __main__.py can be executed as a module."""
    # Run the module with --help to verify it executes
    result = subprocess.run(
        [sys.executable, "-m", "rhiza_tools", "--help"],
        capture_output=True,
        text=True,
    )

    # Should exit successfully
    assert result.returncode == 0
    # Should show help text
    assert "Rhiza Tools" in result.stdout or "Usage" in result.stdout


def test_main_direct_execution():
    """Test that __main__.py can be executed directly as a script."""
    # Find the __main__.py file
    spec = importlib.util.find_spec("rhiza_tools.__main__")
    main_file = spec.origin

    # Run the file directly with --help
    result = subprocess.run(
        [sys.executable, main_file, "--help"],
        capture_output=True,
        text=True,
    )

    # Should exit successfully
    assert result.returncode == 0
    # Should show help text
    assert "Rhiza Tools" in result.stdout or "Usage" in result.stdout


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
        with patch("sys.argv", ["rhiza_tools", "--help"]):
            with patch("rhiza_tools.cli.app") as mock_app:
                try:
                    # Run the module as if it were __main__
                    runpy.run_module(main_module_name, run_name="__main__")
                except SystemExit:
                    # Expected when app() runs and exits
                    pass

                # The app should have been called
                assert mock_app.called
    finally:
        # Restore the module to sys.modules if it was there before
        if saved_module is not None:
            sys.modules[main_module_name] = saved_module
