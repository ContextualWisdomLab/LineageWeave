"""Ontology-grounded 게시판 search. Never a keyword-only title scan.

A buyer query binds to a published ontology term (ADR 0004) or an
authorized catalog name (Keyman / organization / team). Unbound queries
fail-closed. This module does not ILIKE ``post_title`` and does not
invent a theta.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from typing import Literal

from .five_w1h import FIVE_W1H_SLOTS, SLOT_LABELS, SlotCode
from .ontology import ontology_term_index

BoardBindKind = Literal[
    "person",
    "organization",
    "team",
    "relationship",
    "node_class",
    "slot",
]

SEARCH_EMPTY_NEXT_ACTION = "이 검색을 근거할 수 있는 사건이 아직 없습니다"

_TRAILING_PUNCT = re.compile(r"[?.!\s]+$")

_RELATIONSHIP_ALIASES: dict[str, str] = {
    "voc": "rel_voc",
    "voice of customer": "rel_voc",
    "주간 voc": "rel_voc",
    "vom": "rel_vom",
    "voice of market": "rel_vom",
}

_NODE_ALIASES: dict[str, str] = {
    "post": "node_post",
    "사건": "node_post",
    "게시": "node_post",
    "person": "node_person",
    "keyman": "node_person",
    "keymen": "node_person",
}


def _fold(text: str) -> str:
    return _TRAILING_PUNCT.sub("", " ".join(text.strip().lower().split()))


def classify_board_query(
    query: str,
    *,
    person_names: Sequence[str] = (),
    organization_names: Sequence[str] = (),
    team_names: Sequence[str] = (),
) -> dict[str, object] | None:
    """Bind ``query`` to one ontology or catalog term, or None."""
    folded = _fold(query)
    if not folded:
        return None
    for name in person_names:
        if folded == _fold(name):
            return {
                "kind": "person",
                "lookup_code": "node_person",
                "matched_label": name.strip(),
                "catalog_name": name.strip(),
            }
    for name in organization_names:
        if folded == _fold(name):
            return {
                "kind": "organization",
                "lookup_code": "node_corporate_entity",
                "matched_label": name.strip(),
                "catalog_name": name.strip(),
            }
    for name in team_names:
        if folded == _fold(name):
            return {
                "kind": "team",
                "lookup_code": "node_team",
                "matched_label": name.strip(),
                "catalog_name": name.strip(),
            }
    if folded in _RELATIONSHIP_ALIASES:
        code = _RELATIONSHIP_ALIASES[folded]
        return {"kind": "relationship", "lookup_code": code, "matched_label": folded, "catalog_name": None}
    if folded in _NODE_ALIASES:
        code = _NODE_ALIASES[folded]
        return {"kind": "node_class", "lookup_code": code, "matched_label": folded, "catalog_name": None}
    for slot in FIVE_W1H_SLOTS:
        if folded == _fold(SLOT_LABELS[slot]) or folded == slot:
            return {"kind": "slot", "lookup_code": slot, "matched_label": SLOT_LABELS[slot], "catalog_name": None}
    for term in ontology_term_index():
        label = _fold(term["label"])
        code = _fold(term["lookup_code"])
        if folded == label or folded == code:
            lookup = term["lookup_code"]
            kind: BoardBindKind
            if lookup.startswith("rel_"):
                kind = "relationship"
            elif lookup in {"node_post", "node_person", "node_corporate_entity", "node_team"}:
                kind = "node_class"
            else:
                continue
            return {
                "kind": kind,
                "lookup_code": lookup,
                "matched_label": term["label"] or lookup,
                "catalog_name": None,
                "ontology_iri": term["iri"],
            }
    return None


def post_matches_bind(
    bind: dict[str, object],
    *,
    voc_type_code: str,
    person_names: Sequence[str],
    organization_names: Sequence[str],
    team_names: Sequence[str],
    relationship_codes: Sequence[str],
    has_keyman: bool,
    slot_codes_with_values: Sequence[SlotCode] = (),
) -> bool:
    """Whether one authorized post satisfies the bound term."""
    kind = bind.get("kind")
    lookup = str(bind.get("lookup_code") or "")
    catalog = str(bind.get("catalog_name") or "")
    if kind == "person":
        return any(_fold(name) == _fold(catalog) for name in person_names)
    if kind == "organization":
        return any(_fold(name) == _fold(catalog) for name in organization_names)
    if kind == "team":
        return any(_fold(name) == _fold(catalog) for name in team_names)
    if kind == "relationship":
        if lookup == "rel_voc" and voc_type_code == "voc":
            return True
        return lookup in relationship_codes
    if kind == "node_class":
        if lookup == "node_post":
            return True
        if lookup == "node_person":
            return has_keyman or bool(person_names)
        if lookup == "node_corporate_entity":
            return bool(organization_names)
        if lookup == "node_team":
            return bool(team_names)
        return False
    if kind == "slot":
        if lookup == "who":
            return has_keyman or bool(person_names)
        return lookup in slot_codes_with_values
    return False
