"""Deterministic, source-grounded commercial-context hints.

The source fields are observations. The combination label is an inference
from field presence and must remain visibly weaker than an extracted fact.
"""

from __future__ import annotations

from typing import Any


def _present_text(value: Any) -> bool:
    return value is not None and bool(str(value).strip())


def _present_item(value: Any) -> bool:
    if value is None or (isinstance(value, str) and not value.strip()):
        return False
    try:
        return int(value) > 0
    except (TypeError, ValueError):
        return False


def _display(value: Any) -> str:
    return str(value).strip() if _present_text(value) else "∅"


def source_lineage_hints(
    *,
    customer_code: Any = None,
    order_pool_code: Any = None,
    sales_order_code: Any = None,
    sales_order_item_number: Any = None,
    stage_code: Any = None,
    detail_state_code: Any = None,
    inspection_point_code: Any = None,
    deleted_flag: Any = None,
) -> dict[str, Any]:
    """Return presence, combination, and raw lifecycle-vector evidence."""
    presence = {
        "customer": _present_text(customer_code),
        "order_pool": _present_text(order_pool_code),
        "sales_order": _present_text(sales_order_code),
        "sales_order_item": _present_item(sales_order_item_number),
    }
    combination_code = "".join("1" if present else "0" for present in presence.values())
    context_codes = {
        "0000": "no_sales_identifier_candidate",
        "1000": "customer_only_candidate",
        "1100": "customer_order_pool_candidate",
        "1111": "sales_order_item_context",
        "0111": "sales_order_item_without_customer",
        "0100": "order_pool_only_candidate",
        "1110": "sales_order_without_item_candidate",
        "1010": "customer_sales_order_without_item_candidate",
    }
    context_code = context_codes.get(combination_code, "mixed_source_identifier_context")
    lifecycle_vector = "/".join(
        (
            _display(stage_code),
            _display(detail_state_code),
            _display(inspection_point_code),
            _display(deleted_flag),
        )
    )
    return {
        "combination_code": combination_code,
        "commercial_context_code": context_code,
        "inference_status_code": "inferred",
        "present_fields": [name for name, present in presence.items() if present],
        "missing_fields": [name for name, present in presence.items() if not present],
        "lifecycle_vector": lifecycle_vector,
        "deleted_marker_present": _present_text(deleted_flag),
    }


def source_lineage_hint_facts(**values: Any) -> tuple[str, ...]:
    """Format bounded source evidence for an orchestrator prompt or chat."""
    hints = source_lineage_hints(**values)
    return (
        "commercial_context="
        f"{hints['commercial_context_code']} "
        f"[combination={hints['combination_code']}; inference=inferred; "
        "provenance=source_post.field_presence]",
        f"source_lifecycle_vector={hints['lifecycle_vector']} "
        "[raw_codes_only; provenance=source_post.lifecycle_fields]",
    )


__all__ = ["source_lineage_hint_facts", "source_lineage_hints"]
