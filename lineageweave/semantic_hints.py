"""Structured source-field hints for semantic extraction prompts.

These values are priors with explicit source labels, never extracted facts.
The customer sentinel values are deliberately weak because they do not
identify a real customer or project.
"""

from __future__ import annotations

from collections.abc import Iterable

_WEAK_CUSTOMER_VALUES = frozenset(
    {"기타", "미등록", "미등록고객", "unknown", "unregistered", "other"}
)


def _value(value: str | None) -> str:
    return value.strip() if isinstance(value, str) and value.strip() else "none"


def format_semantic_hints(
    *,
    author_name: str | None,
    author_affiliations: Iterable[str],
    order_pool_code: str | None,
    order_pool_name: str | None,
    project_field: str | None,
    customer_name: str | None,
    author_account_id: str | None = None,
    author_account_name: str | None = None,
    source_author_code: str | None = None,
    source_author_name: str | None = None,
    source_company_code: str | None = None,
    source_company_name: str | None = None,
    source_business_unit_code: str | None = None,
    source_process_unit_name: str | None = None,
    source_sales_pool_code: str | None = None,
    source_sales_pool_name: str | None = None,
    source_customer_code: str | None = None,
    source_customer_name: str | None = None,
    source_project_code: str | None = None,
    source_project_name: str | None = None,
    source_context_present: bool = False,
) -> str:
    """Render source-field hints without upgrading them into assertions."""
    source_context = source_context_present or any(
        value is not None
        for value in (
            source_author_code,
            source_author_name,
            source_company_code,
            source_company_name,
            source_business_unit_code,
            source_process_unit_name,
            source_sales_pool_code,
            source_sales_pool_name,
            source_customer_code,
            source_customer_name,
            source_project_code,
            source_project_name,
        )
    )
    customer = _value(None if source_context else customer_name)
    customer_trust = "low" if customer.casefold() in _WEAK_CUSTOMER_VALUES else "normal"
    affiliations = sorted(
        {
            _value(value)
            for value in author_affiliations
            if _value(value) != "none"
        }
    )
    account_id = author_account_id
    if source_context:
        author_side_hint = (
            "our_side_context_only"
            if account_id or affiliations
            else "unresolved_source_author"
        )
    else:
        author_side_hint = "our_side_candidate"
    effective_source_author_name = source_author_name
    if effective_source_author_name and effective_source_author_name == source_author_code:
        effective_source_author_name = None
    effective_author_name = effective_source_author_name if source_context else author_name
    effective_account_name = author_account_name
    order_pool = ": ".join(
        value for value in (_value(order_pool_code), _value(order_pool_name)) if value != "none"
    ) or "none"
    order_pool_source = (
        "source_post.source_sales_pool_code"
        if source_sales_pool_code is not None
        else "source_post.source_sales_pool_name"
        if source_sales_pool_name is not None
        else "none"
    )
    source_customer_name_value = _value(source_customer_name)
    source_customer_name_trust = (
        "none"
        if source_customer_name_value == "none"
        else "low"
        if source_customer_name_value.casefold() in _WEAK_CUSTOMER_VALUES
        else "normal"
    )
    return "; ".join(
        (
            f"author_account_id={_value(account_id)} [source_field=source_post.author_account_id]",
            f"author_account_name={_value(effective_account_name)} [source_field=user_account.display_name]",
            f"author={_value(effective_author_name)} [source_field=source_post.author_code]",
            "author_affiliations="
            f"{', '.join(affiliations) or 'none'} [source_field=account_affiliation.corporate_entity_id]",
            f"author_side_hint={author_side_hint} [source_rule=source_post.author_code]",
            f"order_pool={order_pool} [source_field={order_pool_source}]",
            f"project_field={_value(project_field)} [source_field=source_post.secondary_grouping_key]",
            f"customer={customer} [source_field=source_post.corporate_entity_id]",
            f"customer_hint_trust={customer_trust}",
            f"source_author_code={_value(source_author_code)} [source_field=source_post.source_author_code]",
            f"source_author_name={_value(effective_source_author_name)} [source_field=source_post.source_author_name]",
            f"source_company_code={_value(source_company_code)} [source_field=source_post.source_company_code]",
            f"source_company_name={_value(source_company_name)} [source_field=source_post.source_company_name]",
            f"source_business_unit_code={_value(source_business_unit_code)} [source_field=source_post.source_process_unit_code]",
            f"source_process_unit_name={_value(source_process_unit_name)} [source_field=source_post.source_process_unit_name]",
            f"source_sales_pool_code={_value(source_sales_pool_code)} [source_field=source_post.source_sales_pool_code]",
            f"source_sales_pool_name={_value(source_sales_pool_name)} [source_field=source_post.source_sales_pool_name]",
            f"source_customer_code={_value(source_customer_code)} [source_field=source_post.source_customer_code]",
            f"source_customer_name={source_customer_name_value} [source_field=source_post.source_customer_name]",
            f"source_customer_name_hint_trust={source_customer_name_trust}",
            f"source_project_code={_value(source_project_code)} [source_field=source_post.source_project_code]",
            f"source_project_name={_value(source_project_name)} [source_field=source_post.source_project_name]",
        )
    )
