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
from lineageweave.embedding_client import (
    OpenAiCompatibleEmbeddingClient,
    chunked_max_similarity,
    cosine_similarity,
)
from lineageweave.fixtures import ambiguous_keyman_post
from lineageweave.image_content import OpenAiCompatibleVisionClient
from lineageweave.keyman_extraction import (
    COUNTERPARTY,
    OUR_SIDE,
    ContextualOrchestratorKeymanExtractionClient,
)

_EMBEDDING_BASE_URL = os.environ.get("LINEAGEWEAVE_TEST_EMBEDDING_BASE_URL")
_EMBEDDING_API_KEY = os.environ.get("LINEAGEWEAVE_TEST_EMBEDDING_API_KEY")
_EMBEDDING_MODEL = os.environ.get("LINEAGEWEAVE_TEST_EMBEDDING_MODEL", "text-embedding-3-large")

_ORCHESTRATOR_BASE_URL = os.environ.get("LINEAGEWEAVE_TEST_ORCHESTRATOR_BASE_URL")
_ORCHESTRATOR_API_KEY = os.environ.get("LINEAGEWEAVE_TEST_ORCHESTRATOR_API_KEY")

_VISION_BASE_URL = os.environ.get("LINEAGEWEAVE_TEST_VISION_BASE_URL")
_VISION_API_KEY = os.environ.get("LINEAGEWEAVE_TEST_VISION_API_KEY")
_VISION_MODEL = os.environ.get("LINEAGEWEAVE_TEST_VISION_MODEL", "gpt-4.1-mini")


@pytest.mark.skipif(
    not (_EMBEDDING_BASE_URL and _EMBEDDING_API_KEY),
    reason="set LINEAGEWEAVE_TEST_EMBEDDING_BASE_URL and LINEAGEWEAVE_TEST_EMBEDDING_API_KEY to run",
)
def test_openai_compatible_embedding_client_scores_similar_text_higher() -> None:
    """A real embedding call, with a real, meaningful assertion: two labels
    about the same synthetic topic must cosine-score higher than two about
    unrelated synthetic topics -- not just "the call didn't crash".
    """
    client = OpenAiCompatibleEmbeddingClient(
        base_url=_EMBEDDING_BASE_URL, api_key=_EMBEDDING_API_KEY, model=_EMBEDDING_MODEL
    )

    a = client.embed("Quarterly budget review meeting notes")
    b = client.embed("Budget review follow-up: revised quarterly numbers")
    c = client.embed("Office parking lot repaving schedule")

    related_score = cosine_similarity(a, b)
    unrelated_score = cosine_similarity(a, c)

    assert 0.0 <= related_score <= 1.0
    assert 0.0 <= unrelated_score <= 1.0
    assert related_score > unrelated_score


@pytest.mark.skipif(
    not (_EMBEDDING_BASE_URL and _EMBEDDING_API_KEY),
    reason="set LINEAGEWEAVE_TEST_EMBEDDING_BASE_URL and LINEAGEWEAVE_TEST_EMBEDDING_API_KEY to run",
)
def test_chunked_embedding_finds_a_relevant_unit_buried_in_a_longer_document() -> None:
    """The real case chunking exists for: a short relevant passage sitting
    inside a much longer, mostly-irrelevant document. Whole-document
    embedding dilutes the relevant passage with everything around it;
    chunked max-pooled similarity should not.
    """
    client = OpenAiCompatibleEmbeddingClient(
        base_url=_EMBEDDING_BASE_URL, api_key=_EMBEDDING_API_KEY, model=_EMBEDDING_MODEL
    )

    query = "Quarterly budget review meeting notes"
    long_document = (
        "Office parking lot repaving schedule for the north campus.\n\n"
        "New badge access policy for the west entrance starting next month.\n\n"
        "Budget review follow-up: revised quarterly numbers and next steps.\n\n"
        "Cafeteria menu rotation for the coming season.\n\n"
        "Reminder about the annual fire drill scheduled for next week."
    )

    chunked_score, best_a, best_b = chunked_max_similarity(client, query, long_document)
    whole_document_score = cosine_similarity(client.embed(query), client.embed(long_document))

    assert "Budget review" in best_b.text
    assert chunked_score > whole_document_score


@pytest.mark.skipif(
    not (_VISION_BASE_URL and _VISION_API_KEY),
    reason="set LINEAGEWEAVE_TEST_VISION_BASE_URL and LINEAGEWEAVE_TEST_VISION_API_KEY to run",
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

    client = OpenAiCompatibleVisionClient(
        base_url=_VISION_BASE_URL, api_key=_VISION_API_KEY, model=_VISION_MODEL
    )
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
