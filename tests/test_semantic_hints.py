from lineageweave.semantic_hints import format_semantic_hints


def test_semantic_hints_keep_explicit_project_pool_and_author_sources() -> None:
    hints = format_semantic_hints(
        author_name="Synthetic Author",
        author_account_id="synthetic-author-account",
        author_affiliations=["Synthetic Corp"],
        order_pool_code="POOL-7",
        order_pool_name="Synthetic bids",
        project_field="PROJECT-42",
        customer_name="Synthetic Customer",
        source_author_code="source-author",
        source_company_code="SOURCE-COMPANY",
        source_business_unit_code="SOURCE-BU",
        source_customer_code="SOURCE-CUSTOMER",
        source_project_code="SOURCE-PROJECT",
    )

    assert "project_field=PROJECT-42" in hints
    assert "source_field=source_post.secondary_grouping_key" in hints
    assert "order_pool=POOL-7: Synthetic bids" in hints
    assert "author_affiliations=Synthetic Corp" in hints
    assert "author_account_id=synthetic-author-account" in hints
    assert "author_side_hint=our_side_context_only" in hints
    assert "customer_hint_trust=normal" in hints
    assert "source_author_code=source-author" in hints
    assert "source_company_code=SOURCE-COMPANY" in hints
    assert "source_customer_code=SOURCE-CUSTOMER" in hints
    assert "source_project_code=SOURCE-PROJECT" in hints


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


def test_source_context_keeps_authorization_identity_as_non_binding_keyman_context() -> None:
    hints = format_semantic_hints(
        author_name="Demo Analyst",
        author_account_id="demo-account",
        author_affiliations=["Demo Corp"],
        order_pool_code="DEMO-PU",
        order_pool_name="Demo scope",
        project_field=None,
        customer_name="Demo Corp",
        source_author_code="SOURCE-AUTHOR",
        source_company_code="SOURCE-COMPANY",
        source_context_present=True,
    )

    assert "author_account_id=demo-account" in hints
    assert "author_account_name=none" in hints
    assert "author_affiliations=Demo Corp" in hints
    assert "customer=none" in hints
    assert "author_side_hint=our_side_context_only" in hints
    assert "Demo Corp" in hints
