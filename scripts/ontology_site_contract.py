"""Shared contracts for safe public ontology-site identifiers."""

from urllib.parse import quote


def public_fragment(fragment: str) -> str:
    """Encode one local identifier for use in a URL fragment reference."""
    return quote(fragment, safe="-._~")
