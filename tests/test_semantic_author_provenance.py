from lineageweave.semantic_hints import format_semantic_hints


def test_author_identity_is_a_prior_with_explicit_side_provenance() -> None:
    hints = format_semantic_hints(
        author_name="Synthetic Author",
        author_account_id="account-1",
        author_affiliations=["Synthetic Corp"],
        order_pool_code=None,
        order_pool_name=None,
        project_field=None,
        customer_name="기타",
    )

    assert "author_account_id=account-1 [source_field=source_post.author_account_id]" in hints
    assert "author_side_hint=our_side_candidate" in hints
    assert "customer_hint_trust=low" in hints
