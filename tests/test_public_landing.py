"""Tests for the authoritative LineageWeave GitHub Pages landing source."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "publish_ontology_site.py"


def _load_publisher():
    spec = importlib.util.spec_from_file_location("publish_ontology_site_landing", SCRIPT)
    if spec is None or spec.loader is None:
        raise AssertionError("ontology publisher could not be loaded")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_publication_copies_the_authoritative_landing_with_durable_navigation(
    tmp_path: Path,
) -> None:
    publisher = _load_publisher()
    output = tmp_path / "site"

    publisher.publish_site(ROOT, output)

    source = (ROOT / publisher.LANDING_RELATIVE_PATH).read_text(encoding="utf-8")
    published = (output / "index.html").read_text(encoding="utf-8")
    assert published == source
    for target in (
        'href="ontology/"',
        'href="https://github.com/ContextualWisdomLab/LineageWeave"',
        'href="https://github.com/ContextualWisdomLab/LineageWeave/blob/main/README.md"',
        'href="https://github.com/ContextualWisdomLab/LineageWeave/blob/main/ARCHITECTURE.md"',
        'href="https://github.com/ContextualWisdomLab/LineageWeave/releases"',
        'href="https://deepwiki.com/ContextualWisdomLab/LineageWeave"',
    ):
        assert target in published


def test_publication_fails_closed_without_the_authoritative_landing(
    tmp_path: Path,
    monkeypatch,
) -> None:
    publisher = _load_publisher()
    output = tmp_path / "site"
    monkeypatch.setattr(publisher, "LANDING_RELATIVE_PATH", Path("docs/missing-index.html"))

    with pytest.raises(FileNotFoundError, match="public landing source"):
        publisher.publish_site(ROOT, output)

    assert not output.exists()
