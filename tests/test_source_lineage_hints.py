from lineageweave.source_lineage_hints import source_lineage_hint_facts, source_lineage_hints


def test_source_lineage_hints_preserve_zero_as_absent_item_sentinel() -> None:
    hints = source_lineage_hints(
        customer_code="C-1",
        order_pool_code="PU-1",
        sales_order_code="SO-1",
        sales_order_item_number=0,
        stage_code="STAGE-1",
        detail_state_code="D",
        inspection_point_code="IP-1",
        deleted_flag="N",
    )

    assert hints["combination_code"] == "1110"
    assert hints["commercial_context_code"] == "sales_order_without_item_candidate"
    assert hints["inference_status_code"] == "inferred"
    assert hints["present_fields"] == ["customer", "order_pool", "sales_order"]
    assert hints["missing_fields"] == ["sales_order_item"]
    assert hints["lifecycle_vector"] == "STAGE-1/D/IP-1/N"
    assert hints["deleted_marker_present"] is True


def test_source_lineage_hints_distinguish_customer_only_and_empty_source() -> None:
    customer_only = source_lineage_hints(customer_code=" C-1 ")
    empty = source_lineage_hints(
        customer_code=" ",
        order_pool_code=None,
        sales_order_code="",
        sales_order_item_number=None,
    )

    assert customer_only["combination_code"] == "1000"
    assert customer_only["commercial_context_code"] == "customer_only_candidate"
    assert empty["combination_code"] == "0000"
    assert empty["commercial_context_code"] == "no_sales_identifier_candidate"
    assert empty["present_fields"] == []
    assert empty["missing_fields"] == [
        "customer",
        "order_pool",
        "sales_order",
        "sales_order_item",
    ]


def test_source_lineage_hint_facts_are_bounded_and_provenance_bearing() -> None:
    facts = source_lineage_hint_facts(
        customer_code="C-1",
        order_pool_code="PU-1",
        sales_order_code="SO-1",
        sales_order_item_number=2,
        stage_code="S1",
        detail_state_code="A",
        inspection_point_code="I1",
        deleted_flag="N",
    )

    assert len(facts) == 2
    assert facts[0] == (
        "commercial_context=sales_order_item_context "
        "[combination=1111; inference=inferred; "
        "provenance=source_post.field_presence]"
    )
    assert facts[1] == (
        "source_lifecycle_vector=S1/A/I1/N "
        "[raw_codes_only; provenance=source_post.lifecycle_fields]"
    )
