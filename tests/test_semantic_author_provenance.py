import asyncio

from backend.app.main import _load_post_semantic_hints
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


def test_lifecycle_only_fields_do_not_hide_independent_identity_hints() -> None:
    """Lifecycle state is not source identity and must not suppress Keyman clues."""
    fields = {
        "author_account_id": "account-1",
        "author_name": "Synthetic Writer",
        "author_affiliation_name": "Synthetic Organization",
        "customer_name": "Named Customer",
    }
    for field_name in (
        "source_author_code",
        "source_author_name",
        "source_company_code",
        "source_company_name",
        "source_company_catalog_name",
        "source_process_unit_code",
        "source_process_unit_name",
        "source_process_unit_catalog_name",
        "source_sales_pool_code",
        "source_sales_pool_name",
        "source_order_pool_code",
        "source_sales_order_code",
        "source_sales_order_item_number",
        "source_inspection_point_code",
        "source_stage_code",
        "source_detail_state_code",
        "source_deleted_flag",
        "source_customer_code",
        "source_customer_name",
        "source_customer_catalog_name",
        "source_project_code",
        "source_project_name",
        "project_field",
    ):
        fields.setdefault(field_name, None)
    fields.update(
        source_stage_code="STAGE-1",
        source_detail_state_code="D",
        source_deleted_flag="N",
    )

    class Connection:
        async def fetch(self, _query: str, _post_id: str):
            return [fields]

    hints = asyncio.run(_load_post_semantic_hints(Connection(), "post-1"))

    assert "customer=Named Customer" in hints
    assert "author_affiliations=Synthetic Organization" in hints
