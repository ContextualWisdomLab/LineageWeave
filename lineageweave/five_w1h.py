"""Evidence-only 5W1H slots for a source post.

This is a projection of persisted evidence, not a second summarizer. Empty
slots are intentional: an absent claim must not become an LLM guess.
"""

from __future__ import annotations

from typing import Any

from .ontology import ontology_annotations

FIVE_W1H_SLOTS = ("who", "what", "when", "where", "why", "how")
_SLOT_LOOKUP_CODES = {
    "who": ("prov_person", "prov_organization", "prov_team", "prov_software_agent"),
    "what": ("node_post",),
    "when": (),
    "where": ("prov_organization",),
    "why": (),
    "how": (),
}


def _value(text: Any, source: str, codes: tuple[str, ...] = ()) -> dict[str, Any] | None:
    if not isinstance(text, str) or not text.strip():
        return None
    annotations: dict[str, Any] = {}
    for code in codes:
        annotations.update(ontology_annotations(code))
    return {
        "text": text.strip(),
        "source": source,
        "ontology_codes": list(codes),
        "ontology_annotations": annotations,
    }


def _unique(values: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[str, str]] = set()
    result: list[dict[str, Any]] = []
    for value in values:
        key = (value["text"], value["source"])
        if key not in seen:
            seen.add(key)
            result.append(value)
    return result


def assemble_five_w1h_slots(
    *,
    roles: list[dict[str, Any]],
    key_events: list[str],
    counterparties: list[str] | None = None,
    lineage_node_labels: list[str] | None = None,
    evidence_claims: list[dict[str, Any]] | None = None,
) -> dict[str, list[dict[str, Any]]]:
    """Assemble only persisted, authorized evidence into six slots.

    There is no ``created_at`` fallback on purpose: the source post's
    creation timestamp is ``prov:generatedAtTime`` for the *record*, not
    evidence of when the narrated event took place. When/where/why/how are
    populated only by an explicitly extracted claim with source evidence.
    """
    slots: dict[str, list[dict[str, Any]]] = {slot: [] for slot in FIVE_W1H_SLOTS}

    for role in roles:
        actor_type = role.get("actor_type_code")
        if actor_type not in _SLOT_LOOKUP_CODES["who"]:
            continue
        item = _value(role.get("actor_name"), "post_summary_role", (actor_type,))
        if item:
            slots["who"].append(item)
        affiliation = _value(
            role.get("affiliated_organization_name"),
            "post_summary_role.affiliated_organization_name",
            ("prov_organization",),
        )
        if affiliation:
            slots["where"].append(affiliation)

    for event in key_events:
        item = _value(event, "post_summary_event", _SLOT_LOOKUP_CODES["what"])
        if item:
            slots["what"].append(item)

    for claim in evidence_claims or []:
        slot = claim.get("slot_code")
        if slot not in {"when", "where", "why", "how"}:
            continue
        item = _value(
            claim.get("value_text"),
            "post_summary_five_w1h",
        )
        if item:
            item["evidence_text"] = claim.get("evidence_text", "")
            if slot == "when":
                item["resolved_date_text"] = claim.get("resolved_date_text")
            slots[slot].append(item)
    if not slots["what"]:
        for title in lineage_node_labels or []:
            item = _value(title, "post_lineage_edge", _SLOT_LOOKUP_CODES["what"])
            if item:
                slots["what"].append(item)

    for name in counterparties or []:
        item = _value(name, "post_counterparty_entity", ("prov_organization",))
        if item:
            slots["where"].append(item)

    return {slot: _unique(values) for slot, values in slots.items()}


def slots_payload(slots: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    """Return a stable API shape; the UI translates slot labels and actions."""
    return [
        {
            "slot_code": slot,
            "values": slots.get(slot, []),
            "empty_next_action_code": "inspect_source_body_or_related_posts",
        }
        for slot in FIVE_W1H_SLOTS
    ]


__all__ = ["FIVE_W1H_SLOTS", "assemble_five_w1h_slots", "slots_payload"]
