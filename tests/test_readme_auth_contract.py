"""README contract for the current browser and machine OIDC boundaries."""

from pathlib import Path


_README = Path(__file__).resolve().parents[1] / "README.md"


def test_readme_does_not_recommend_retired_public_client_password_grants() -> None:
    """Public-client ROPC stays retired in buyer/operator documentation."""
    readme = _README.read_text(encoding="utf-8")

    assert "remaining local ROPC consumer" not in readme
    assert "Public direct grants stay" not in readme
    assert "password-grant migration item" not in readme
    assert "public direct grants are disabled" in readme
    assert "Authorization Code + S256 PKCE" in readme
    assert "distinct confidential" in readme
