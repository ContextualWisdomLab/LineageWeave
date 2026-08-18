from lineageweave.semantic_hints import format_semantic_hints


def test_semantic_hints_keep_explicit_project_pool_and_author_sources() -> None:
    hints = format_semantic_hints(
        author_name="Synthetic Author",
        author_affiliations=["Synthetic Corp"],
        order_pool_code="POOL-7",
        order_pool_name="Synthetic bids",
        project_field="PROJECT-42",
        customer_name="Synthetic Customer",
    )

    assert "project_field=PROJECT-42" in hints
    assert "source_field=source_post.secondary_grouping_key" in hints
    assert "order_pool=POOL-7: Synthetic bids" in hints
    assert "author_affiliations=Synthetic Corp" in hints
    assert "customer_hint_trust=normal" in hints


def test_unknown_customer_is_a_weak_hint_not_project_evidence() -> None:
    hints = format_semantic_hints(
        author_name=None,
        author_affiliations=[],
        order_pool_code=None,
        order_pool_name=None,
        project_field=None,
        customer_name="미등록고객",
    )

    assert "customer=미등록고객" in hints
    assert "customer_hint_trust=low" in hints
    assert "project_field=none" in hints
