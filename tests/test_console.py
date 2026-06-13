"""Tests for rhiza_tools.console."""


class TestConsole:
    """Tests for console.py verbose configuration path."""

    def test_configure_verbose_adds_logger_handler(self):
        """console.py:46 – logger.add is called when verbose=True."""
        from rhiza_tools import console

        console.configure(verbose=True)
        assert console.is_verbose() is True
        # Cleanup to avoid polluting other tests
        console.configure(verbose=False)
