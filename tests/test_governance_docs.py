"""Tests for repository-level governance documents."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_governance_docs_exist_at_repository_root():
    """The contributing guide and code of conduct should live at the repo root."""
    assert (ROOT / "CONTRIBUTING.md").exists()
    assert (ROOT / "CODE_OF_CONDUCT.md").exists()


def test_readme_links_to_governance_docs():
    """README should link to the root governance documents for contributors."""
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "(CONTRIBUTING.md)" in readme
    assert "(CODE_OF_CONDUCT.md)" in readme


def test_code_of_conduct_includes_enforcement_contact():
    """The code of conduct should use Contributor Covenant text with a contact."""
    code_of_conduct = (ROOT / "CODE_OF_CONDUCT.md").read_text(encoding="utf-8")
    assert "Contributor Covenant" in code_of_conduct
    assert "thomas.s@yukkalab.com" in code_of_conduct
