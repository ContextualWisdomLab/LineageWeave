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
) -> str:
    """Render source-field hints without upgrading them into assertions."""
    customer = _value(customer_name)
    customer_trust = "low" if customer.casefold() in _WEAK_CUSTOMER_VALUES else "normal"
    affiliations = sorted({_value(value) for value in author_affiliations if _value(value) != "none"})
    order_pool = ": ".join(
        value for value in (_value(order_pool_code), _value(order_pool_name)) if value != "none"
    ) or "none"
    return "; ".join(
        (
            f"author={_value(author_name)} [source_field=source_post.author_account_id]",
            "author_affiliations="
            f"{', '.join(affiliations) or 'none'} [source_field=account_affiliation.corporate_entity_id]",
            f"order_pool={order_pool} [source_field=source_post.process_unit_id]",
            f"project_field={_value(project_field)} [source_field=source_post.secondary_grouping_key]",
            f"customer={customer} [source_field=source_post.corporate_entity_id]",
            f"customer_hint_trust={customer_trust}",
        )
    )
