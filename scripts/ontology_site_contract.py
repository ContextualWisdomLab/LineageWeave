"""Shared contracts for safe public ontology-site identifiers."""

from urllib.parse import quote


def public_fragment(fragment: str) -> str:
    """Encode one local fragment identically for HTML IDs and hrefs."""
    return quote(fragment, safe="-._~")
