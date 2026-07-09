"""Interactive-prompt styling and non-interactive detection.

This module owns the presentation concerns shared by the interactive command
flows (bump, release, rollback):

    - COOL_STYLE: Shared questionary styling for interactive prompts.
    - NON_INTERACTIVE_ERRORS: Exceptions signalling a missing TTY, so callers can
      degrade gracefully in CI.
"""

import questionary as qs

# The win32 import only succeeds on Windows, so exactly one platform exercises
# each side of this branch; the fallback can never be covered on Windows.
try:
    from prompt_toolkit.output.win32 import (  # type: ignore[attr-defined]
        NoConsoleScreenBufferError as _WinConsoleError,
    )
except (ImportError, AssertionError):  # pragma: no cover

    class _WinConsoleError(Exception):  # type: ignore[no-redef]
        """Sentinel: never raised outside of Windows environments."""


# Tuple of exceptions indicating a non-interactive environment (no TTY).
# Use this in except clauses instead of bare ``EOFError`` so that Windows CI
# (which raises ``NoConsoleScreenBufferError`` instead of ``EOFError``) is
# handled consistently.
NON_INTERACTIVE_ERRORS: tuple[type[BaseException], ...] = (EOFError, _WinConsoleError)

COOL_STYLE = qs.Style(
    [
        ("separator", "fg:#cc5454"),
        ("qmark", "fg:#2FA4A9 bold"),
        ("question", ""),
        ("selected", "fg:#2FA4A9 bold"),
        ("pointer", "fg:#2FA4A9 bold"),
        ("highlighted", "fg:#2FA4A9 bold"),
        ("answer", "fg:#2FA4A9 bold"),
        ("text", "fg:#ffffff"),
        ("disabled", "fg:#858585 italic"),
    ]
)
