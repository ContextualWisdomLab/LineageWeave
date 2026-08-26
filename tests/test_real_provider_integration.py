"""Real-provider integration tests: prove the pluggable embedding and LLM
adjudication clients actually work end-to-end against a live provider, not
just that their interfaces are satisfiable by a stub.

Every test here is skipped unless its own credential env vars are set, so
CI on a clone with no credentials configured stays green -- these are
opt-in, not part of the default test run. Only synthetic fixture-style
text is ever sent to a real provider; no real record content lives in this
repository (see AGENTS.md).
"""

from __future__ import annotations

import os

import pytest

from lineageweave.adjudication_client import ContextualOrchestratorAdjudicationClient
from lineageweave.embedding_client import ContextualOrchestratorEmbeddingClient
from lineageweave.fixtures import ambiguous_keyman_post
from lineageweave.image_content import orchestrator_vision_client
from lineageweave.keyman_extraction import (
    COUNTERPARTY,
    OUR_SIDE,
    ContextualOrchestratorKeymanExtractionClient,
)

_EMBEDDING_MODEL = os.environ.get("LINEAGEWEAVE_TEST_EMBEDDING_MODEL", "text-embedding-3-large")

_ORCHESTRATOR_BASE_URL = os.environ.get("LINEAGEWEAVE_TEST_ORCHESTRATOR_BASE_URL")
_ORCHESTRATOR_API_KEY = os.environ.get("LINEAGEWEAVE_TEST_ORCHESTRATOR_API_KEY")

_VISION_MODEL = os.environ.get("LINEAGEWEAVE_TEST_VISION_MODEL", "gpt-4.1-mini")


@pytest.mark.skipif(
    not (_ORCHESTRATOR_BASE_URL and _ORCHESTRATOR_API_KEY),
    reason="set LINEAGEWEAVE_TEST_ORCHESTRATOR_BASE_URL and LINEAGEWEAVE_TEST_ORCHESTRATOR_API_KEY to run",
)
def test_contextual_orchestrator_embedding_client_returns_real_vectors() -> None:
    """A real embedding call returns a complete provider-owned vector."""
    client = ContextualOrchestratorEmbeddingClient(
        base_url=_ORCHESTRATOR_BASE_URL, api_key=_ORCHESTRATOR_API_KEY, model=_EMBEDDING_MODEL
    )

    a = client.embed("Quarterly budget review meeting notes")
    assert len(a) > 8


@pytest.mark.skipif(
    not (_ORCHESTRATOR_BASE_URL and _ORCHESTRATOR_API_KEY),
    reason="set LINEAGEWEAVE_TEST_ORCHESTRATOR_BASE_URL and LINEAGEWEAVE_TEST_ORCHESTRATOR_API_KEY to run",
)
def test_vision_client_performs_real_ocr_on_a_generated_image() -> None:
    """Generate a real PNG with real rendered text (Pillow, not a fixture
    file) and prove the vision client actually reads it back -- real OCR,
    not a mocked response.
    """
    from io import BytesIO

    from PIL import Image, ImageDraw

    image = Image.new("RGB", (400, 100), color="white")
    draw = ImageDraw.Draw(image)
    draw.text((10, 40), "INVOICE 48213", fill="black")
    buffer = BytesIO()
    image.save(buffer, format="PNG")

    client = orchestrator_vision_client(_ORCHESTRATOR_BASE_URL, _ORCHESTRATOR_API_KEY, _VISION_MODEL)
    assert client.available
    description = client.describe(buffer.getvalue(), "image/png")

    assert "48213" in description.extracted_text
    assert description.caption
    assert len(description.tags) > 0


@pytest.mark.skipif(
    not (_ORCHESTRATOR_BASE_URL and _ORCHESTRATOR_API_KEY),
    reason=(
        "set LINEAGEWEAVE_TEST_ORCHESTRATOR_BASE_URL and "
        "LINEAGEWEAVE_TEST_ORCHESTRATOR_API_KEY to run against a live "
        "contextual-orchestrator instance (e.g. `python -m "
        "contextual_orchestrator.server` pointed at a real agent pool)"
    ),
)
def test_contextual_orchestrator_adjudication_client_returns_a_real_confidence() -> None:
    client = ContextualOrchestratorAdjudicationClient(
        base_url=_ORCHESTRATOR_BASE_URL, api_key=_ORCHESTRATOR_API_KEY
    )

    confidence = client.judge(
        "Quarterly budget review meeting notes",
        "Budget review follow-up: revised quarterly numbers",
    )

    assert 0.0 <= confidence <= 1.0


@pytest.mark.skipif(
    not (_ORCHESTRATOR_BASE_URL and _ORCHESTRATOR_API_KEY),
    reason=(
        "set LINEAGEWEAVE_TEST_ORCHESTRATOR_BASE_URL and "
        "LINEAGEWEAVE_TEST_ORCHESTRATOR_API_KEY to run against a live "
        "contextual-orchestrator instance"
    ),
)
def test_contextual_orchestrator_extracts_two_sided_keymen_from_ambiguous_prose() -> None:
    """A real orchestrator call against a genuinely LLM-ambiguous synthetic
    post: one dual-hatted counterparty, two of our people, and an
    organization that sent nobody. The assertion is on structure (both
    sides present, N affiliations on the counterparty, no invented
    Westfield person) rather than exact string spelling.
    """
    title, body = ambiguous_keyman_post()
    client = ContextualOrchestratorKeymanExtractionClient(
        base_url=_ORCHESTRATOR_BASE_URL, api_key=_ORCHESTRATOR_API_KEY
    )
    mentions = client.extract(title, body)

    names = " ".join(mention.person_name.lower() for mention in mentions)
    assert "priya" in names
    assert "jordan" in names or "sam" in names
    assert "westfield" not in names

    sides = {mention.person_side_code for mention in mentions}
    assert OUR_SIDE in sides
    assert COUNTERPARTY in sides

    priya = next(mention for mention in mentions if "priya" in mention.person_name.lower())
    assert priya.person_side_code == COUNTERPARTY
    affiliation_blob = " ".join(priya.affiliated_organization_names).lower()
    assert "northridge" in affiliation_blob
    assert len(priya.affiliated_organization_names) >= 2
