"""Contract test pinning the bump-my-version interface rhiza-tools depends on.

The bump engine (``rhiza_tools.commands.bump_engine``) appends git-cliff commands
to a bump-my-version configuration's ``pre_commit_hooks`` list before running a
real bump. That depends on upstream bump-my-version exposing a ``Config`` model
with a list-typed ``pre_commit_hooks`` field. If a future upstream release renames
or retypes that field, this test fails loudly here rather than at release time
when a version bump would silently lose its changelog/lockfile staging.

The check is intentionally cheap: it inspects the Pydantic model fields only and
never runs a full bump.
"""

from __future__ import annotations

from bumpversion.config.models import Config


def test_config_exposes_pre_commit_hooks_field():
    """``Config`` must still declare the ``pre_commit_hooks`` field."""
    assert "pre_commit_hooks" in Config.model_fields


def test_pre_commit_hooks_is_list_typed():
    """``pre_commit_hooks`` must be a list type whose default factory yields a list."""
    field = Config.model_fields["pre_commit_hooks"]

    # The field annotation must be a list type (e.g. list[str] / typing.List[str]).
    annotation_repr = repr(field.annotation)
    assert "list" in annotation_repr.lower(), annotation_repr

    # And its default must materialise as a list, since the engine does
    # ``list(config.pre_commit_hooks) + [...]``.
    assert field.default_factory is not None
    default_value = field.default_factory()  # type: ignore[call-arg]
    assert isinstance(default_value, list)
