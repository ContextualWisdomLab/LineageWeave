"""5W1H slots and grounded lineage Q&A from the semantic layer.

Buyer 사건 lineage shows Who / What / When / Where / Why / How as
slots on the summary. Values come only from authorized, already-extracted
lineage and source facts bound through the published ontology
(``docs/ontology/lineageweave-kg.ttl``, ADR 0004). A missing slot stays
empty. This module never invents a theta, a leftover distance, or
guessed prose.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from datetime import datetime
from typing import Literal

from .ontology import iri_for_lookup_code

SlotCode = Literal["who", "what", "when", "where", "why", "how"]

FIVE_W1H_SLOTS: tuple[SlotCode, ...] = ("who", "what", "when", "where", "why", "how")

SLOT_LABELS: dict[SlotCode, str] = {
    "who": "누가",
    "what": "무엇을",
    "when": "언제",
    "where": "어디서",
    "why": "왜",
    "how": "어떻게",
}

# Lookup codes whose ontology terms may fill a slot. An undeclared code
# is dropped (iri_for_lookup_code is None) -- never a fabricated class.
SLOT_LOOKUP_CODES: dict[SlotCode, tuple[str, ...]] = {
    "who": ("prov_person", "prov_organization", "prov_team", "node_person"),
    "what": ("node_post",),
    "when": (),
    "where": ("node_corporate_entity",),
    "why": (),
    "how": (),
}

_TRAILING_PUNCT = re.compile(r"[?.!\s]+$")

QuestionKind = SlotCode | Literal["what_happened"]


def empty_slot_next_action(*slot_codes: SlotCode) -> str:
    """Fail-closed empty copy that names the next human action."""
    labels = "/".join(SLOT_LABELS[code] for code in slot_codes)
    return f"이 사건의 {labels}가 아직 없습니다"


def ungrounded_question_next_action() -> str:
    return "이 사건 lineage에서 근거할 수 있는 질문이 아직 없습니다"


def slot_ontology_iris(slot: SlotCode) -> tuple[str, ...]:
    """Ontology IRIs that may fill this slot, or empty when unbound."""
    iris: list[str] = []
    for code in SLOT_LOOKUP_CODES[slot]:
        iri = iri_for_lookup_code(code)
        if iri:
            iris.append(iri)
    return tuple(iris)


def _unique_text(values: Sequence[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        text = value.strip()
        if not text or text in seen:
            continue
        seen.add(text)
        out.append(text)
    return tuple(out)


def _date_label(value: datetime | str | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date().isoformat()
    text = str(value).strip()
    if not text:
        return None
    return text[:10]


def assemble_five_w1h_slots(
    *,
    roles: Sequence[dict[str, object]],
    key_events: Sequence[str],
    created_at: datetime | str | None,
    lineage_occurred_at: Sequence[datetime | str] = (),
    affiliated_names: Sequence[str] = (),
    counterparty_names: Sequence[str] = (),
    lineage_node_labels: Sequence[str] = (),
) -> dict[SlotCode, tuple[str, ...]]:
    """Fill slots from authorized facts only.

    Who is R&R actors (Person / Organization / Team). What is stored
    key events, else authorized lineage node titles. When is the post
    write clock and lineage occurred_at. Where is affiliated or
    counterparty organization names. Why and How stay empty until a
    grounded source fact exists -- never a guessed motive or method.
    """
    who = _unique_text(
        str(role.get("actor_name") or "")
        for role in roles
        if isinstance(role, dict)
    )
    what = _unique_text(key_events)
    if not what:
        what = _unique_text(lineage_node_labels)
    when = _unique_text(
        [label for label in (_date_label(created_at),) if label]
        + [label for value in lineage_occurred_at if (label := _date_label(value))]
    )
    where = _unique_text(
        [
            str(role.get("affiliated_organization_name") or "")
            for role in roles
            if isinstance(role, dict)
        ]
        + list(affiliated_names)
        + list(counterparty_names)
    )
    return {
        "who": who,
        "what": what,
        "when": when,
        "where": where,
        "why": (),
        "how": (),
    }


def classify_lineage_question(question: str) -> QuestionKind | None:
    """Map a buyer question to a 5W1H slot or the what-happened walk.

    Unrecognized questions return None -- the caller fail-closes instead
    of guessing prose.
    """
    folded = _TRAILING_PUNCT.sub("", " ".join(question.strip().lower().split()))
    if not folded:
        return None
    if any(token in folded for token in ("누가", "누구", "who is involved", "who's involved", "who ")):
        return "who"
    if any(token in folded for token in ("왜", "why ")):
        return "why"
    if any(token in folded for token in ("어떻게", "how ")):
        return "how"
    if any(token in folded for token in ("언제", "when ")):
        return "when"
    if any(token in folded for token in ("어디서", "어디", "where ")):
        return "where"
    if any(
        token in folded
        for token in ("무엇을", "무슨 일", "what happened", "what is", "무슨")
    ):
        if "happened" in folded or "무슨 일" in folded or "between" in folded:
            return "what_happened"
        return "what"
    if folded in {"what happened between these events", "what happened"}:
        return "what_happened"
    return None


def chronology_from_slots(slots: dict[SlotCode, tuple[str, ...]]) -> list[dict[str, str]]:
    """Authorized When clocks only. Never invents a missing date."""
    return [{"occurred_at": clock, "label": clock} for clock in slots.get("when", ())]


def answer_lineage_question(
    question: str,
    slots: dict[SlotCode, tuple[str, ...]],
) -> dict[str, object]:
    """Answer from assembled slots only. Never invent a sentence."""
    kind = classify_lineage_question(question)
    chronology = chronology_from_slots(slots)
    who = list(slots.get("who", ()))
    what_happened = list(slots.get("what", ()))
    if kind is None:
        return {
            "question": question.strip(),
            "slot_code": None,
            "values": [],
            "grounded": False,
            "empty_next_action": ungrounded_question_next_action(),
            "who": who,
            "what_happened": what_happened,
            "chronology": chronology,
        }
    slot: SlotCode = "what" if kind == "what_happened" else kind
    values = list(slots.get(slot, ()))
    if values:
        return {
            "question": question.strip(),
            "slot_code": slot,
            "values": values,
            "grounded": True,
            "empty_next_action": None,
            "who": who,
            "what_happened": what_happened,
            "chronology": chronology,
        }
    return {
        "question": question.strip(),
        "slot_code": slot,
        "values": [],
        "grounded": False,
        "empty_next_action": empty_slot_next_action(slot),
        "who": who,
        "what_happened": what_happened,
        "chronology": chronology,
    }


def slots_payload(slots: dict[SlotCode, tuple[str, ...]]) -> list[dict[str, object]]:
    """Buyer-facing slot list with fail-closed empty next actions."""
    rows: list[dict[str, object]] = []
    for code in FIVE_W1H_SLOTS:
        values = list(slots[code])
        rows.append(
            {
                "slot_code": code,
                "slot_label": SLOT_LABELS[code],
                "values": values,
                "ontology_iris": list(slot_ontology_iris(code)),
                "empty_next_action": None if values else empty_slot_next_action(code),
            }
        )
    return rows
