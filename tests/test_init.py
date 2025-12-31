"""Tests for rhiza_tools.__init__.py module."""

import sys
from importlib.metadata import PackageNotFoundError
from unittest.mock import patch


def test_version_available():
    """Test that __version__ is set when package is installed."""
    import rhiza_tools

    # Should have a version attribute
    assert hasattr(rhiza_tools, "__version__")
    assert isinstance(rhiza_tools.__version__, str)
    # Version should be a valid format (not "unknown")
    assert rhiza_tools.__version__ != "unknown"
    # Basic sanity check that it looks like a version
    assert len(rhiza_tools.__version__) > 0


def test_version_package_not_found():
    """Test that __version__ is 'unknown' when PackageNotFoundError occurs."""
    # We need to mock importlib.metadata.version before importing rhiza_tools
    with patch("importlib.metadata.version", side_effect=PackageNotFoundError):
        # Remove the module from sys.modules to force a fresh import
        if "rhiza_tools" in sys.modules:
            del sys.modules["rhiza_tools"]

        # Import the module - this will trigger the exception handling
        import rhiza_tools

        # Should fall back to "unknown"
        assert rhiza_tools.__version__ == "unknown"

        # Clean up - reload with proper version for other tests
        del sys.modules["rhiza_tools"]
        import rhiza_tools
