"""Buyer-facing SKOS companion labels for corroborated organization names.

[ADR 0008](docs/adr/0008-organization-abbreviation-resolution.md) already
persists a search-corroborated ``skos:altLabel`` / ``skos:prefLabel`` pair
(Miles & Bechhofer, 2009) in ``organization_name_resolution``. Catalog
resolution still compares mentions to ``corporate_entity.entity_name``, so
a chip that only prints that name hides the short form the source used.

This module does not invent aliases. It returns the *other* label when the
displayed name uniquely matches one side of a corroborated pair, and stays
silent on a miss, a pending row, identical labels, or a tie.

Synthetic fixtures only: ``DC`` / ``Demo Corp``, ``AGP`` / ``Aurora Grid
Power``. Real organization names must not appear here.
"""

from __future__ import annotations

from collections.abc import Mapping, MutableMapping, Sequence
from dataclasses import dataclass
from typing import Any

from lineageweave.corporate_hierarchy_resolution import normalize_organization_name


@dataclass(frozen=True)
class OrganizationNameAlias:
    """One corroborated SKOS alt/pref pair.

    Attributes:
        alt_label: the abbreviated or slang form (``skos:altLabel``).
        pref_label: the preferred catalog form (``skos:prefLabel``).
    """

    alt_label: str
    pref_label: str


def companion_organization_alias(
    display_name: str,
    aliases: Sequence[OrganizationNameAlias],
) -> str | None:
    """Return the other corroborated label, or ``None``.

    A display name that matches neither side, matches both sides of one
    pair (identical labels), or matches two distinct companions is a
    miss. Callers must not invent a parenthetical in those cases.
    """
    normalized = normalize_organization_name(display_name)
    if not normalized:
        return None

    companions: list[str] = []
    seen: set[str] = set()
    for alias in aliases:
        alt = normalize_organization_name(alias.alt_label)
        pref = normalize_organization_name(alias.pref_label)
        if not alt or not pref or alt == pref:
            continue
        companion: str | None = None
        if normalized == pref:
            companion = alias.alt_label.strip()
        elif normalized == alt:
            companion = alias.pref_label.strip()
        if companion is None:
            continue
        key = normalize_organization_name(companion)
        if not key or key in seen:
            continue
        seen.add(key)
        companions.append(companion)
    if len(companions) != 1:
        return None
    return companions[0]


def organization_alias_caption(
    display_name: str,
    organization_alias: str | None,
) -> str:
    """Visible chip text: ``Demo Corp (DC)`` when an alias is present."""
    alias = (organization_alias or "").strip()
    if not alias:
        return display_name
    return f"{display_name} ({alias})"


def attach_organization_alias(
    record: MutableMapping[str, Any],
    aliases: Sequence[OrganizationNameAlias],
    *,
    name_key: str = "entity_name",
) -> None:
    """Write ``organization_alias`` onto one JSON record when unique."""
    name = record.get(name_key)
    if not isinstance(name, str):
        return
    companion = companion_organization_alias(name, aliases)
    if companion:
        record["organization_alias"] = companion


def attach_organization_aliases(
    records: Sequence[Mapping[str, Any]] | Sequence[MutableMapping[str, Any]],
    aliases: Sequence[OrganizationNameAlias],
    *,
    name_key: str = "entity_name",
    children_key: str = "children",
) -> None:
    """Write ``organization_alias`` onto a forest or a flat record list."""
    for record in records:
        if not isinstance(record, MutableMapping):
            continue
        attach_organization_alias(record, aliases, name_key=name_key)
        children = record.get(children_key)
        if isinstance(children, list):
            attach_organization_aliases(
                children,
                aliases,
                name_key=name_key,
                children_key=children_key,
            )
