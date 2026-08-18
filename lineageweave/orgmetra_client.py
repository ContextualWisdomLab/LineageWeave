"""Orgmetra consumption port for tenant org grain (team / PU / corporate).

Buyer chrome asks Orgmetra which organization units exist. This module
does not store an org-chart, infer affiliation, or invent a team / PU /
corporate tree. Unconfigured or failed transport is fail-closed
(``available = False``), the same missing-vs-negative discipline as
other Null clients. Keyverse remains the IdP; this port is not an IdP.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Literal, Protocol
from urllib.parse import quote
from urllib.request import Request, urlopen

OrgmetraGrain = Literal["team", "process_unit", "corporate"]

ORGMETRA_GRAINS: tuple[OrgmetraGrain, ...] = ("team", "process_unit", "corporate")

ORGMETRA_UNAVAILABLE_NEXT_ACTION = "이 범위의 조직 단위를 아직 받을 수 없습니다"


@dataclass(frozen=True)
class OrgmetraUnit:
    """One organization unit Orgmetra already knows."""

    grain_code: OrgmetraGrain
    unit_id: str
    unit_label: str


class OrgmetraClient(Protocol):
    """Tenant org-grain reader. Implementations must not invent units."""

    available: bool

    def list_units(self, grain: OrgmetraGrain) -> tuple[OrgmetraUnit, ...]:
        """Authorized units for ``grain``, or empty when unavailable."""


class NullOrgmetraClient:
    """Default: Orgmetra is not wired. Never invents a unit."""

    available = False

    def list_units(self, grain: OrgmetraGrain) -> tuple[OrgmetraUnit, ...]:
        del grain
        return ()


class HttpOrgmetraClient:
    """GET ``{base}/units?grain=`` -- consumption only, not an IdP."""

    available = True

    def __init__(self, base_url: str, timeout_seconds: float = 5.0) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds

    def list_units(self, grain: OrgmetraGrain) -> tuple[OrgmetraUnit, ...]:
        if grain not in ORGMETRA_GRAINS:
            return ()
        url = f"{self._base_url}/units?grain={quote(grain)}"
        request = Request(url, method="GET")
        try:
            with urlopen(request, timeout=self._timeout_seconds) as response:
                if response.status != 200:
                    return ()
                payload = _read_units_payload(response.read(), grain)
        except (OSError, ValueError):
            return ()
        return payload


def _read_units_payload(raw: bytes, grain: OrgmetraGrain) -> tuple[OrgmetraUnit, ...]:
    body = json.loads(raw.decode("utf-8"))
    rows = body.get("units") if isinstance(body, dict) else None
    if not isinstance(rows, list):
        return ()
    units: list[OrgmetraUnit] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        unit_id = str(row.get("unit_id") or "").strip()
        unit_label = str(row.get("unit_label") or "").strip()
        grain_code = str(row.get("grain_code") or grain).strip()
        if not unit_id or not unit_label or grain_code not in ORGMETRA_GRAINS:
            continue
        units.append(
            OrgmetraUnit(
                grain_code=grain_code if grain_code in ORGMETRA_GRAINS else grain,
                unit_id=unit_id,
                unit_label=unit_label,
            )
        )
    return tuple(units)


def build_orgmetra_client(base_url: str) -> OrgmetraClient:
    """Null when unset. HTTP only when a base URL is configured."""
    cleaned = base_url.strip()
    if not cleaned:
        return NullOrgmetraClient()
    return HttpOrgmetraClient(cleaned)
