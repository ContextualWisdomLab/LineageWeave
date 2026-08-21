from lineageweave.source_lineage_hints import source_lineage_hint_facts, source_lineage_hints


def test_source_combination_uses_zero_as_absent_item_sentinel() -> None:
    hints = source_lineage_hints(
        customer_code="C-1",
        order_pool_code="POOL-1",
        sales_order_code="SO-1",
        sales_order_item_number=0,
        stage_code="Z",
        detail_state_code="A",
        inspection_point_code="F",
    )

    assert hints["combination_code"] == "1110"
    assert hints["commercial_context_code"] == "sales_order_without_item_candidate"
    assert hints["present_fields"] == ["customer", "order_pool", "sales_order"]
    assert hints["lifecycle_vector"] == "Z/A/F/∅"


def test_source_combination_keeps_inference_separate_from_raw_facts() -> None:
    facts = source_lineage_hint_facts(
        customer_code=None,
        order_pool_code=None,
        sales_order_code=None,
        sales_order_item_number=None,
        stage_code="Z",
        detail_state_code="A",
        inspection_point_code="Z",
        deleted_flag=None,
    )

    assert "commercial_context=no_sales_identifier_candidate" in facts[0]
    assert "inference=inferred" in facts[0]
    assert "raw_codes_only" in facts[1]
