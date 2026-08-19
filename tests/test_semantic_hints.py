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
        source_company_name="Named company",
        source_process_unit_name="Named PU",
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
    assert "source_company_name=Named company [source_field=source_post.source_company_name]" in hints
    assert "source_process_unit_name=Named PU [source_field=source_post.source_process_unit_name]" in hints


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


def test_source_pool_and_project_code_keep_distinct_provenance() -> None:
    hints = format_semantic_hints(
        author_name=None,
        author_affiliations=[],
        order_pool_code="SOURCE-POOL",
        order_pool_name=None,
        project_field="SECONDARY-PROJECT",
        customer_name="Demo Corp",
        source_sales_pool_code="SOURCE-POOL",
        source_project_code="SOURCE-PROJECT",
        source_context_present=True,
    )

    assert "order_pool=SOURCE-POOL [source_field=source_post.source_sales_pool_code]" in hints
    assert "project_field=SECONDARY-PROJECT [source_field=source_post.secondary_grouping_key]" in hints
    assert "source_project_code=SOURCE-PROJECT [source_field=source_post.source_project_code]" in hints


def test_explicit_source_names_are_hints_with_name_provenance_and_customer_trust() -> None:
    hints = format_semantic_hints(
        author_name=None,
        author_affiliations=[],
        order_pool_code=None,
        order_pool_name="Named sales pool",
        project_field=None,
        customer_name=None,
        source_sales_pool_name="Named sales pool",
        source_customer_name="미등록고객",
        source_project_name="Named project",
        source_context_present=True,
    )

    assert "order_pool=Named sales pool [source_field=source_post.source_sales_pool_name]" in hints
    assert "source_customer_name=미등록고객 [source_field=source_post.source_customer_name]" in hints
    assert "source_customer_name_hint_trust=low" in hints
    assert "source_project_name=Named project [source_field=source_post.source_project_name]" in hints


def test_source_context_keeps_authorization_identity_as_non_binding_keyman_context() -> None:
    hints = format_semantic_hints(
        author_name="Synthetic Analyst",
        author_account_id="demo-account",
        author_account_name="Synthetic Analyst",
        author_affiliations=["Synthetic Corp"],
        order_pool_code="DEMO-PU",
        order_pool_name="Demo scope",
        project_field=None,
        customer_name="Demo Corp",
        source_author_code="SOURCE-AUTHOR",
        source_company_code="SOURCE-COMPANY",
        source_context_present=True,
    )

    assert "author_account_id=demo-account" in hints
    assert "author_account_name=Synthetic Analyst" in hints
    assert "author_affiliations=Synthetic Corp" in hints
    assert "customer=none" in hints
    assert "author_side_hint=our_side_context_only" in hints
    assert "Synthetic Corp" in hints
