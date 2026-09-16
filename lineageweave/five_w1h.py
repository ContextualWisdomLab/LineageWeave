"""Evidence-only 5W1H slots for a source post.

This is a projection of persisted evidence, not a second summarizer. Empty
slots are intentional: an absent claim must not become an LLM guess.
"""

from __future__ import annotations

from typing import Any

from .ontology import ontology_annotations

FIVE_W1H_SLOTS = ("who", "what", "when", "where", "why", "how")
_SLOT_LOOKUP_CODES = {
    "who": ("prov_person", "prov_organization", "prov_team"),
    "what": ("node_post",),
    "when": (),
    "where": ("prov_organization",),
    "why": (),
    "how": (),
}


def _build_evidence_slot_value(
    evidence_text_value: Any,
    evidence_source_code: str,
    ontology_codes: tuple[str, ...] = (),
) -> dict[str, Any] | None:
    if not isinstance(evidence_text_value, str) or not evidence_text_value.strip():
        return None
    ontology_annotation_map: dict[str, Any] = {}
    for ontology_code in ontology_codes:
        ontology_annotation_map.update(ontology_annotations(ontology_code))
    return {
        "text": evidence_text_value.strip(),
        "source": evidence_source_code,
        "ontology_codes": list(ontology_codes),
        "ontology_annotations": ontology_annotation_map,
    }


def _deduplicate_slot_values(
    slot_values: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    seen_value_keys: set[tuple[str, str]] = set()
    unique_slot_values: list[dict[str, Any]] = []
    for evidence_slot_value in slot_values:
        evidence_value_key = (
            evidence_slot_value["text"],
            evidence_slot_value["source"],
        )
        if evidence_value_key not in seen_value_keys:
            seen_value_keys.add(evidence_value_key)
            unique_slot_values.append(evidence_slot_value)
    return unique_slot_values


def assemble_five_w1h_slots(
    *,
    post_summary_roles: list[dict[str, Any]],
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
    five_w1h_slots: dict[str, list[dict[str, Any]]] = {
        slot_code: [] for slot_code in FIVE_W1H_SLOTS
    }

    for post_summary_role in post_summary_roles:
        actor_type_code = post_summary_role.get("actor_type_code")
        if actor_type_code not in _SLOT_LOOKUP_CODES["who"]:
            continue
        evidence_slot_value = _build_evidence_slot_value(
            post_summary_role.get("actor_name"),
            "post_summary_role",
            (actor_type_code,),
        )
        if evidence_slot_value:
            five_w1h_slots["who"].append(evidence_slot_value)
        affiliation_slot_value = _build_evidence_slot_value(
            post_summary_role.get("affiliated_organization_name"),
            "post_summary_role.affiliated_organization_name",
            ("prov_organization",),
        )
        if affiliation_slot_value:
            five_w1h_slots["where"].append(affiliation_slot_value)

    for key_event_text in key_events:
        evidence_slot_value = _build_evidence_slot_value(
            key_event_text,
            "post_summary_event",
            _SLOT_LOOKUP_CODES["what"],
        )
        if evidence_slot_value:
            five_w1h_slots["what"].append(evidence_slot_value)

    for evidence_claim in evidence_claims or []:
        slot_code = evidence_claim.get("slot_code")
        if slot_code not in {"when", "where", "why", "how"}:
            continue
        evidence_slot_value = _build_evidence_slot_value(
            evidence_claim.get("value_text"),
            "post_summary_five_w1h",
        )
        if evidence_slot_value:
            evidence_slot_value["evidence_text"] = evidence_claim.get(
                "evidence_text", ""
            )
            five_w1h_slots[slot_code].append(evidence_slot_value)
    if not five_w1h_slots["what"]:
        for lineage_node_label in lineage_node_labels or []:
            evidence_slot_value = _build_evidence_slot_value(
                lineage_node_label,
                "post_lineage_edge",
                _SLOT_LOOKUP_CODES["what"],
            )
            if evidence_slot_value:
                five_w1h_slots["what"].append(evidence_slot_value)

    for counterparty_name in counterparties or []:
        evidence_slot_value = _build_evidence_slot_value(
            counterparty_name,
            "post_counterparty_entity",
            ("prov_organization",),
        )
        if evidence_slot_value:
            five_w1h_slots["where"].append(evidence_slot_value)

    return {
        slot_code: _deduplicate_slot_values(slot_values)
        for slot_code, slot_values in five_w1h_slots.items()
    }


def slots_payload(
    five_w1h_slots: dict[str, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    """Return a stable API shape; the UI translates slot labels and actions."""
    return [
        {
            "slot_code": slot_code,
            "values": five_w1h_slots.get(slot_code, []),
            "empty_next_action_code": "inspect_source_body_or_related_posts",
        }
        for slot_code in FIVE_W1H_SLOTS
    ]


__all__ = ["FIVE_W1H_SLOTS", "assemble_five_w1h_slots", "slots_payload"]
