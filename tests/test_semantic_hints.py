from lineageweave.semantic_hints import customer_hint_trust, format_semantic_hints


def test_customer_hint_trust_marks_generic_values_weak() -> None:
    for value in ("기타", "기타고객", "기타 고객", "미등록", "미등록고객", "미등록 고객"):
        assert customer_hint_trust(value) == "low"
    assert customer_hint_trust("Named customer", "other") == "low"
    assert customer_hint_trust("Named customer") == "normal"


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
        source_company_catalog_name="Catalog Company",
        source_process_unit_catalog_name="Catalog PU",
        source_customer_catalog_name="Catalog Customer",
        source_project_code="SOURCE-PROJECT",
        source_company_name="Named company",
        source_process_unit_name="Named PU",
        source_voc_type_code="vocc",
        source_stage_code="medium",
        source_detail_state_code="inspection-report",
    )

    assert "project_field=PROJECT-42" in hints
    assert "source_field=source_post.secondary_grouping_key" in hints
    assert "order_pool=POOL-7: Synthetic bids" in hints
    # Real source-system fields are present, so this is implicitly a
    # bulk-imported record -- the placeholder account's affiliation is
    # untrustworthy here (see test_source_context_drops_account_affiliation
    # _as_untrustworthy_org_identity for why).
    assert "author_affiliations=none" in hints
    assert "author_account_id=synthetic-author-account" in hints
    assert "author_side_hint=our_side_context_only" in hints
    assert "customer_hint_trust=normal" in hints
    assert "source_author_code=source-author" in hints
    assert "source_company_code=SOURCE-COMPANY" in hints
    assert "source_customer_code=SOURCE-CUSTOMER" in hints
    assert "source_project_code=SOURCE-PROJECT" in hints
    assert "source_company_name=Named company [source_field=source_post.source_company_name]" in hints
    assert "source_process_unit_name=Named PU [source_field=source_post.source_process_unit_name]" in hints
    assert "source_voc_type_code=vocc [source_field=source_post.voc_type_code]" in hints
    assert "source_stage_code=medium [source_field=source_post.source_stage_code]" in hints
    assert "source_detail_state_code=inspection-report [source_field=source_post.source_detail_state_code]" in hints
    assert "source_company_catalog_name=Catalog Company [source_lookup=corporate_entity.corporate_entity_code]" in hints
    assert "source_process_unit_catalog_name=Catalog PU [source_lookup=process_unit.process_unit_code]" in hints
    assert "source_customer_catalog_name=Catalog Customer [source_lookup=corporate_entity.corporate_entity_code]" in hints


def test_catalog_lookup_hint_reports_a_code_without_inventing_a_name() -> None:
    hints = format_semantic_hints(
        author_name=None,
        author_affiliations=(),
        order_pool_code=None,
        order_pool_name=None,
        project_field=None,
        customer_name=None,
        source_company_code="UNRESOLVED-COMPANY",
    )

    assert "source_company_catalog_name=none [source_lookup=corporate_entity.corporate_entity_code]" in hints


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


def test_source_context_drops_account_affiliation_as_untrustworthy_org_identity() -> None:
    """A bulk-imported real record shares one platform placeholder account
    across every record, so its `account_affiliation` names the
    placeholder's own org, never the real author `source_author_code`/
    `source_company_code` actually names. Live bug (2026-08-19): asserting
    the placeholder's org as "our side" context fed a wrong company name
    into a real Keyman-extraction prompt and inverted the
    our_side/counterparty classification. `customer_name` already gets
    this same treatment for the identical reason; extend it here too.
    """
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
    assert "author_affiliations=none" in hints
    assert "customer=none" in hints
    assert "author_side_hint=our_side_context_only" in hints
    assert "Synthetic Corp" not in hints


def test_without_source_context_account_affiliation_is_kept_as_keyman_hint() -> None:
    """A genuine, non-bulk-imported post (no independent source-system
    record) has no placeholder-account ambiguity -- the account's real
    affiliation is legitimate non-binding Keyman context here.
    """
    hints = format_semantic_hints(
        author_name="Synthetic Analyst",
        author_account_id="demo-account",
        author_account_name="Synthetic Analyst",
        author_affiliations=["Synthetic Corp"],
        order_pool_code=None,
        order_pool_name=None,
        project_field=None,
        customer_name=None,
    )

    assert "author_affiliations=Synthetic Corp" in hints
    assert "author_side_hint=our_side_candidate" in hints


def test_classification_only_hints_do_not_suppress_identity_context() -> None:
    """Classification evidence is not a substitute source identity boundary."""
    hints = format_semantic_hints(
        author_name="Synthetic Analyst",
        author_account_id="demo-account",
        author_account_name="Synthetic Analyst",
        author_affiliations=["Synthetic Corp"],
        order_pool_code=None,
        order_pool_name=None,
        project_field=None,
        customer_name="Synthetic Customer",
        source_voc_type_code="vop",
        source_stage_code="synthetic-stage",
        source_detail_state_code="synthetic-detail",
    )

    assert "author_affiliations=Synthetic Corp" in hints
    assert "customer=Synthetic Customer" in hints
    assert "author_side_hint=our_side_candidate" in hints
    assert "source_voc_type_code=vop" in hints
