from __future__ import annotations

from typing import Any

import pytest

from backend.app import main, report_ingestion
from backend.app.auth import CurrentAccount


class _Acquire:
    """Async context manager returning one inert connection token."""

    async def __aenter__(self) -> object:
        """Return the connection token used only by monkeypatched repository calls."""
        return object()

    async def __aexit__(self, _exc_type: object, _exc: object, _tb: object) -> None:
        """Leave the fake acquisition context without suppressing failures."""
        return None


class _Pool:
    """Minimal pool shape for report authorization application-boundary tests."""

    def acquire(self) -> _Acquire:
        """Return an inert asynchronous connection acquisition."""
        return _Acquire()


class _ComparisonConnection:
    """Repository double that exposes process scope only when the SQL selects it."""

    async def fetch(self, query: str, *_args: object) -> list[dict[str, Any]]:
        """Return the minimum stored report population required by comparison loading."""
        normalized = " ".join(query.split())
        if "from report_period_score" in normalized:
            return [
                {
                    "grouping_kind": "corporate_entity",
                    "grouping_key": "tenant-a",
                    "mean_theta": 2.0,
                    "post_count": 1,
                    "link_method": "reference",
                }
            ]
        if "from report_member_score" in normalized:
            return [
                {
                    "grouping_kind": "corporate_entity",
                    "grouping_key": "tenant-a",
                    "visibility_code": "public",
                    "corporate_entity_id": "tenant-a",
                    "process_unit_id": "unit-a",
                    "has_real_source_context": True,
                }
            ]
        if "from report_leftover_pair" in normalized:
            row: dict[str, Any] = {
                "grouping_kind": "corporate_entity",
                "grouping_key": "tenant-a",
                "pair_kind": "closest",
                "post_id": "private-pair",
                "criterion_code": "criterion-a",
                "leftover_distance": 0.1,
                "leftover_residual": 0.2,
                "leftover_map_reconstruction": 0.3,
                "post_title": "Hidden process-unit evidence",
                "visibility_code": "private",
                "corporate_entity_id": "tenant-a",
                "has_real_source_context": True,
            }
            if "p.process_unit_id" in normalized:
                row["process_unit_id"] = "unit-b"
            return [row]
        raise AssertionError(f"unexpected comparison query: {normalized}")

    async def fetchrow(self, query: str, *_args: object) -> dict[str, str] | None:
        """Resolve the one corporate-entity grouping label used by the fixture."""
        normalized = " ".join(query.split())
        if "from corporate_entity" in normalized:
            return {"entity_name": "Tenant A"}
        raise AssertionError(f"unexpected comparison label query: {normalized}")


def _account() -> CurrentAccount:
    """Build one reader admitted only to tenant A and process unit A."""
    return CurrentAccount(
        user_account_id="00000000-0000-0000-0000-000000000001",
        external_subject_id="report-scope-test",
        display_name="Report Scope Test",
        preferred_locale="en",
        corporate_entity_ids=frozenset({"tenant-a"}),
        process_unit_ids=frozenset({"unit-a"}),
        permission_codes=frozenset({"post_read"}),
    )


def _member(
    post_id: str,
    *,
    visibility_code: str,
    corporate_entity_id: str,
    process_unit_id: str,
) -> dict[str, Any]:
    """Build the visibility metadata consumed by the report application boundary."""
    return {
        "post_id": post_id,
        "post_title": post_id,
        "visibility_code": visibility_code,
        "corporate_entity_id": corporate_entity_id,
        "process_unit_id": process_unit_id,
        "has_real_source_context": True,
    }


async def _no_real_source_context(_conn: object, _entity_ids: list[str]) -> bool:
    """Keep synthetic-demo filtering out of the mixed-visibility regression."""
    return False


@pytest.mark.anyio
async def test_period_report_list_hides_aggregate_when_any_member_is_invisible(monkeypatch) -> None:
    """A summary aggregate must not expose statistics for a partly visible population."""
    rows = [
        {
            "grouping_key": "group-a",
            "mean_theta": 3.5,
            "members": [
                _member(
                    "public",
                    visibility_code="public",
                    corporate_entity_id="tenant-b",
                    process_unit_id="unit-b",
                ),
                _member(
                    "private",
                    visibility_code="private",
                    corporate_entity_id="tenant-b",
                    process_unit_id="unit-b",
                ),
            ],
        }
    ]

    async def fetch_rows(_conn: object, _grouping_kind: str) -> list[dict[str, Any]]:
        """Return one aggregate whose stored population is only partly visible."""
        return rows

    monkeypatch.setattr(main, "list_period_report_summaries", fetch_rows)
    monkeypatch.setattr(main, "has_real_source_context", _no_real_source_context)

    payload = await main.list_period_reports(next(iter(main.GROUPING_KINDS)), _account(), _Pool())

    assert payload["periods"] == []


@pytest.mark.anyio
async def test_period_report_detail_hides_aggregate_when_any_member_is_invisible(monkeypatch) -> None:
    """Detailed psychometric outputs must fail closed for a mixed-visibility population."""
    rows = [
        {
            "grouping_key": "group-a",
            "mean_theta": 3.5,
            "calibration_score": 0.8,
            "leftover_map_axes": [{"axis_index": 1, "explained_share": 0.7}],
            "leftover_pairs": [],
            "members": [
                _member(
                    "public",
                    visibility_code="public",
                    corporate_entity_id="tenant-b",
                    process_unit_id="unit-b",
                ),
                _member(
                    "private",
                    visibility_code="private",
                    corporate_entity_id="tenant-b",
                    process_unit_id="unit-b",
                ),
            ],
        }
    ]

    async def fetch_rows(
        _conn: object, _grouping_kind: str, _period_code: str
    ) -> list[dict[str, Any]]:
        """Return one persisted report with a hidden contributor."""
        return rows

    monkeypatch.setattr(main, "fetch_period_reports", fetch_rows)
    monkeypatch.setattr(main, "has_real_source_context", _no_real_source_context)
    monkeypatch.setattr(main, "parse_period_code", lambda _period_code: None)

    payload = await main.read_period_reports(
        next(iter(main.GROUPING_KINDS)), "2026-W36", _account(), _Pool()
    )

    assert payload["reports"] == []


@pytest.mark.anyio
async def test_period_report_comparison_hides_aggregate_when_any_member_is_invisible(
    monkeypatch,
) -> None:
    """Cross-group comparison must not reveal full-population statistics via one member."""
    rows = [
        {
            "grouping_kind": "corporate_entity",
            "grouping_key": "group-a",
            "mean_theta": 3.5,
            "leftover_pairs": [],
            "members": [
                _member(
                    "public",
                    visibility_code="public",
                    corporate_entity_id="tenant-b",
                    process_unit_id="unit-b",
                ),
                _member(
                    "private",
                    visibility_code="private",
                    corporate_entity_id="tenant-b",
                    process_unit_id="unit-b",
                ),
            ],
        }
    ]

    async def fetch_rows(_conn: object, _period_code: str) -> list[dict[str, Any]]:
        """Return one comparison row with a hidden contributor."""
        return rows

    monkeypatch.setattr(main, "fetch_period_comparison", fetch_rows)
    monkeypatch.setattr(main, "has_real_source_context", _no_real_source_context)
    monkeypatch.setattr(main, "parse_period_code", lambda _period_code: None)

    payload = await main.compare_period_groupings("2026-W36", _account(), _Pool())

    assert payload["groupings"] == []


@pytest.mark.anyio
async def test_period_report_comparison_preserves_leftover_process_scope(monkeypatch) -> None:
    """Comparison loading must carry process-unit identity into leftover evidence ABAC."""
    connection = _ComparisonConnection()

    async def fetch_rows(_conn: object, period_code: str) -> list[dict[str, Any]]:
        """Exercise the production comparison repository instead of a shaped payload."""
        return await report_ingestion.fetch_period_comparison(connection, period_code)

    monkeypatch.setattr(main, "fetch_period_comparison", fetch_rows)
    monkeypatch.setattr(main, "has_real_source_context", _no_real_source_context)
    monkeypatch.setattr(main, "parse_period_code", lambda _period_code: None)

    payload = await main.compare_period_groupings("2026-W36", _account(), _Pool())

    assert payload["groupings"] == []


@pytest.mark.anyio
async def test_period_report_detail_hides_aggregate_when_leftover_pair_is_not_visible(
    monkeypatch,
) -> None:
    """Persisted leftover-map aggregates must fail closed if pair evidence is hidden."""
    public = _member(
        "public",
        visibility_code="public",
        corporate_entity_id="tenant-b",
        process_unit_id="unit-b",
    )
    hidden_pair = _member(
        "private-pair",
        visibility_code="private",
        corporate_entity_id="tenant-b",
        process_unit_id="unit-b",
    )
    rows = [
        {
            "grouping_key": "group-a",
            "mean_theta": 3.5,
            "leftover_map_axes": [{"axis_index": 1, "explained_share": 0.7}],
            "leftover_pairs": [hidden_pair],
            "members": [public],
        }
    ]

    async def fetch_rows(
        _conn: object, _grouping_kind: str, _period_code: str
    ) -> list[dict[str, Any]]:
        """Return a report whose member is visible but leftover evidence is not."""
        return rows

    monkeypatch.setattr(main, "fetch_period_reports", fetch_rows)
    monkeypatch.setattr(main, "has_real_source_context", _no_real_source_context)
    monkeypatch.setattr(main, "parse_period_code", lambda _period_code: None)

    payload = await main.read_period_reports(
        next(iter(main.GROUPING_KINDS)), "2026-W36", _account(), _Pool()
    )

    assert payload["reports"] == []


@pytest.mark.anyio
async def test_period_report_detail_preserves_aggregate_for_fully_visible_population(
    monkeypatch,
) -> None:
    """Fail-closed filtering must retain a complete visible aggregate."""
    rows = [
        {
            "grouping_key": "group-a",
            "mean_theta": 3.5,
            "leftover_map_axes": [{"axis_index": 1, "explained_share": 0.7}],
            "leftover_pairs": [],
            "members": [
                _member(
                    "public-a",
                    visibility_code="public",
                    corporate_entity_id="tenant-b",
                    process_unit_id="unit-b",
                ),
                _member(
                    "public-b",
                    visibility_code="public",
                    corporate_entity_id="tenant-c",
                    process_unit_id="unit-c",
                ),
            ],
        }
    ]

    async def fetch_rows(
        _conn: object, _grouping_kind: str, _period_code: str
    ) -> list[dict[str, Any]]:
        """Return a report whose entire persisted evidence population is visible."""
        return rows

    monkeypatch.setattr(main, "fetch_period_reports", fetch_rows)
    monkeypatch.setattr(main, "has_real_source_context", _no_real_source_context)
    monkeypatch.setattr(main, "parse_period_code", lambda _period_code: None)

    payload = await main.read_period_reports(
        next(iter(main.GROUPING_KINDS)), "2026-W36", _account(), _Pool()
    )

    assert len(payload["reports"]) == 1
    assert payload["reports"][0]["mean_theta"] == 3.5
    assert payload["reports"][0]["post_count"] == 2
