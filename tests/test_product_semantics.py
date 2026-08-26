"""Tests for evidence-bound product semantic extraction."""

from lineageweave.product_semantics import (
    ContextualOrchestratorProductExtractionClient,
    ProductEvidenceSource,
    ProductMention,
    ProductRelationTarget,
    normalize_product_alias,
    parse_product_mentions,
    product_analysis_input_sha256,
    resolve_product_mention,
)
import pytest


def test_parse_product_mentions_binds_exact_source_span() -> None:
    source = ProductEvidenceSource("post-a", "Synthetic Model Q supports the test.")
    parsed = parse_product_mentions(
        '{"mentions":[{"product_name":"Synthetic Model Q","evidence_post_id":"post-a",'
        '"evidence_text":"Synthetic Model Q"}],"relations":[]}',
        (source,),
    )
    assert parsed is not None
    assert parsed.mentions == (
        ProductMention(
            "Synthetic Model Q", "Synthetic Model Q", "post-a", source.input_sha256
        ),
    )
    assert len(product_analysis_input_sha256((source,))) == 64


def test_parse_product_mentions_rejects_uncited_and_duplicate_output() -> None:
    source = ProductEvidenceSource("post-a", "Synthetic Model Q")
    assert parse_product_mentions(
        '{"mentions":[{"product_name":"Other","evidence_post_id":"post-a",'
        '"evidence_text":"Other"}],"relations":[]}',
        (source,),
    ) is None
    item = (
        '{"product_name":"Synthetic Model Q","evidence_post_id":"post-a",'
        '"evidence_text":"Synthetic Model Q"}'
    )
    assert parse_product_mentions(f'{{"mentions":[{item},{item}],"relations":[]}}', (source,)) is None


def test_parse_product_mentions_rejects_invalid_shapes() -> None:
    source = ProductEvidenceSource("post-a", "Synthetic Model Q")
    assert parse_product_mentions("not-json", (source,)) is None
    assert parse_product_mentions("{}", (source,)) is None
    assert parse_product_mentions("[1]", (source,)) is None
    assert parse_product_mentions(
        '{"mentions":[{"product_name":"","evidence_post_id":"post-a","evidence_text":"x"}],"relations":[]}',
        (source,),
    ) is None


def test_parse_product_relations_accepts_only_authorized_closed_targets() -> None:
    source = ProductEvidenceSource("post-a", "Synthetic Model Q supports Project A.")
    target = ProductRelationTarget(
        "project:project-a", "project", "Project A", ("post-a", "project-a")
    )
    content = (
        '{"mentions":[{"product_name":"Synthetic Model Q","evidence_post_id":"post-a",'
        '"evidence_text":"Synthetic Model Q"}],"relations":[{"mention_ordinal":0,'
        '"target_id":"project:project-a","relation_type_code":"used_by_project",'
        '"evidence_post_id":"post-a","evidence_text":"Synthetic Model Q supports Project A"}]}'
    )
    parsed = parse_product_mentions(content, (source,), (target,))
    assert parsed is not None
    assert parsed.relations[0].target_locator == ("post-a", "project-a")
    assert parse_product_mentions(content.replace("project:project-a", "project:hidden"), (source,), (target,)) is None
    assert parse_product_mentions(content.replace("used_by_project", "concerns_product"), (source,), (target,)) is None


def test_catalog_resolution_is_unique_missing_or_tie() -> None:
    mention = ProductMention(" Product  Q ", "Product Q", "post-a", "a" * 64)
    assert normalize_product_alias("  PRODUCT  Ｑ ") == "product q"
    unique = resolve_product_mention(mention, ("catalog-a", "catalog-a"))
    missing = resolve_product_mention(mention, ())
    tie = resolve_product_mention(mention, ("catalog-a", "catalog-b"))
    unavailable = resolve_product_mention(mention, None)
    assert (unique.resolution_status_code, unique.product_catalog_id) == (
        "unique",
        "catalog-a",
    )
    assert (missing.resolution_status_code, missing.product_catalog_id) == (
        "missing",
        None,
    )
    assert (tie.resolution_status_code, tie.product_catalog_id) == ("tie", None)
    assert (unavailable.resolution_status_code, unavailable.product_catalog_id) == (
        "unavailable",
        None,
    )


def test_orchestrator_product_client_uses_auto_and_timeout(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_post(url, payload, *, headers, timeout):
        captured.update(url=url, payload=payload, headers=headers, timeout=timeout)
        return {
            "choices": [
                {
                    "message": {
                        "content": '{"mentions":[{"product_name":"Synthetic Model Q",'
                        '"evidence_post_id":"post-a","evidence_text":"Synthetic Model Q"}],"relations":[]}'
                    }
                }
            ]
        }

    monkeypatch.setattr("lineageweave.product_semantics.post_json", fake_post)
    source = ProductEvidenceSource("post-a", "Synthetic Model Q")
    result = ContextualOrchestratorProductExtractionClient(
        "https://orchestrator.invalid/", "secret", timeout=12.5
    ).extract((source,), session_id="post-session-a")
    assert result.mentions[0].evidence_post_id == "post-a"
    assert captured["url"] == "https://orchestrator.invalid/v1/chat/completions"
    assert captured["payload"]["model"] == "orchestrator/auto"
    assert captured["payload"]["response_format"] == {"type": "json_object"}
    assert captured["payload"]["session_id"] == "post-session-a"
    assert captured["headers"] == {
        "authorization": "Bearer secret",
        "x-request-timeout-ms": "12500",
    }


def test_orchestrator_product_client_rejects_invalid_evidence(monkeypatch) -> None:
    monkeypatch.setattr(
        "lineageweave.product_semantics.post_json",
        lambda *args, **kwargs: {"choices": [{"message": {"content": "{}"}}]},
    )
    with pytest.raises(RuntimeError, match="invalid product evidence"):
        ContextualOrchestratorProductExtractionClient("https://x", "secret").extract(
            (ProductEvidenceSource("post-a", "Synthetic Model Q"),)
        )


def test_orchestrator_product_client_normalizes_malformed_envelope(monkeypatch) -> None:
    """Malformed provider content is a bounded product-validation failure."""
    monkeypatch.setattr(
        "lineageweave.product_semantics.post_json",
        lambda *args, **kwargs: {"choices": [{"message": {"content": None}}]},
    )
    with pytest.raises(RuntimeError, match="invalid product evidence"):
        ContextualOrchestratorProductExtractionClient("https://x", "secret").extract(
            (ProductEvidenceSource("post-a", "Synthetic Model Q"),)
        )
