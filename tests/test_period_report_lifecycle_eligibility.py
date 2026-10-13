"""Synthetic repository/consumer regressions for current report-source eligibility.

The connection seam records real repository SQL and models outer-join row
retention; no service, calibration, or native psychometric fit is performed.
"""

from __future__ import annotations

from datetime import datetime, timezone
import sqlite3
from typing import Any

import pytest

from backend.app import main, report_ingestion
from backend.app.post_eligibility import SOURCE_CONTEXT_COLUMNS, SOURCE_POST_ELIGIBILITY_SQL
from tests.test_period_report_whole_population_authorization import (
    _Pool,
    _account,
    _no_real_source_context,
)


class _PopulationConnection:
    """Supply synthetic persisted rows only at the database transport boundary."""

    def __init__(self) -> None:
        self.queries: list[str] = []
        self.missing_source: str | None = None
        self.revoked_source: str | None = None
        self.revocation: str | None = None

    def _canonical_outcome(self, post_id: str) -> bool:
        """Execute the canonical SQL expression, not a reimplementation of its policy.

        SQLite evaluates this portable boolean fragment with a btrim compatibility
        function only. This is not PostgreSQL driver/schema integration evidence.
        """
        with sqlite3.connect(":memory:") as db:
            db.create_function("btrim", 1, lambda value: None if value is None else value.strip())
            columns = ("post_id", "source_draft_code", "source_deleted_flag", *SOURCE_CONTEXT_COLUMNS)
            db.execute("create table source_post (" + ", ".join(f"{column} text" for column in columns) + ")")
            db.execute("insert into source_post (post_id) values (?)", (post_id,))
            if self.revocation != "global_synthetic":
                db.execute("update source_post set source_author_code = ?", ("synthetic-author",))
            if post_id == self.revoked_source:
                if self.revocation == "draft":
                    db.execute("update source_post set source_draft_code = ?", (" DRAFT ",))
                elif self.revocation == "deleted":
                    db.execute("update source_post set source_deleted_flag = ?", (" DELETED ",))
                elif self.revocation == "global_synthetic":
                    # A real-context row outside the reader scope activates the GLOBAL
                    # exclusion: it must not depend on the API's scoped demo query.
                    db.execute("insert into source_post (post_id, source_author_code) values (?, ?)",
                               ("outside-reader-scope", "synthetic-real-context"))
            expression = SOURCE_POST_ELIGIBILITY_SQL.format(alias="p")
            result = db.execute(f"select ({expression}) from source_post p where p.post_id = ?", (post_id,)).fetchone()
            assert result is not None
            return result[0] == 1

    async def fetch(self, query: str, *_args: object) -> list[dict[str, Any]]:
        """Record production SQL and emulate selected eligibility/outer joins."""
        sql = " ".join(query.split())
        self.queries.append(sql)
        if " union all " in sql:
            first, second = sql.split(" union all ", 1)
            recorded = list(self.queries)
            members = await self.fetch(first)
            pairs = await self.fetch(second)
            self.queries = recorded
            for row in members:
                row["contributor_kind"] = "member"
            for row in pairs:
                row["contributor_kind"] = "leftover"
            return members + pairs
        if "from report_period_score" in sql:
            return [{
                "grouping_kind": "corporate_entity", "grouping_key": "tenant-a",
                "period_code": "2026-W36", "rubric_version": "synthetic-rubric",
                "selected_model": "stored-model", "mean_theta": 2.75,
                "mean_theta_sd": 0.4, "post_count": 2, "item_count": 3,
                "fit_loglik": -7.0, "fit_converged": True, "calibration_score": 0.8,
                "computed_at": datetime(2026, 9, 1, tzinfo=timezone.utc),
                "link_method": "reference", "anchor_period_code": None,
                "delta_mean_theta": None,
            }]
        if "from report_member_score" in sql or "from report_leftover_pair" in sql:
            is_pair = "from report_leftover_pair" in sql
            rows = [self._source_row("stored-pair" if is_pair else "stored-member")]
            if not is_pair:
                rows.append(self._source_row("contracted-member"))
            canonical = " ".join(SOURCE_POST_ELIGIBILITY_SQL.format(alias="p").split())
            # Missing SQL eligibility is intentionally not synthesized by this seam.
            projected = canonical in sql.split("from report_", 1)[0]
            if projected and "as source_eligible" in sql:
                for row in rows:
                    row["source_eligible"] = self._canonical_outcome(row["post_id"])
            missing = next((row for row in rows if row["post_id"] == self.missing_source), None)
            if missing is not None:
                if "left join source_post p" not in sql:
                    rows.remove(missing)
                else:
                    for field in ("post_title", "visibility_code", "corporate_entity_id", "process_unit_id"):
                        missing[field] = None
                    if projected:
                        missing["source_eligible"] = False
            return rows
        if any(f"from {table}" in sql for table in (
            "report_item_information", "report_leftover_map_axis", "report_leftover_map_coverage",
        )):
            return []
        raise AssertionError(f"unexpected repository query: {sql}")

    @staticmethod
    def _source_row(post_id: str) -> dict[str, Any]:
        """Return complete nullable persisted score columns without recomputing them."""
        row = {
            "grouping_kind": "corporate_entity", "grouping_key": "tenant-a",
            "period_code": "2026-W36", "post_id": post_id,
            "post_title": "Synthetic stored evidence", "visibility_code": "public",
            "corporate_entity_id": "tenant-a", "process_unit_id": "unit-a",
            "has_real_source_context": True, "theta_eap": 1.25, "theta_sd": 0.2,
            "ticket_due_date": None, "ticket_title": None, "ticket_status_code": None,
            "pair_kind": "closest", "criterion_code": "synthetic-criterion",
            "leftover_distance": 0.125, "leftover_residual": -0.25,
        }
        for field in (
            "observed_response", "expected_response", "leftover_map_rank",
            "leftover_map_unexplained", "leftover_map_cross_share", "leftover_map_reconstruction",
            "leftover_map_unexplained_share", "leftover_map_explained_share",
            "leftover_map_person_axis_1", "leftover_map_person_axis_2",
            "leftover_map_item_axis_1", "leftover_map_item_axis_2",
        ):
            row[field] = None
        return row

    async def fetchrow(self, _query: str, *_args: object) -> dict[str, str]:
        """Resolve the synthetic grouping label without any catalog mutation."""
        return {"entity_name": "Synthetic tenant"}


async def _load(connection: _PopulationConnection, consumer: str) -> list[dict[str, Any]]:
    if consumer == "list":
        return await report_ingestion.list_period_report_summaries(connection, "corporate_entity")
    if consumer == "detail":
        return await report_ingestion.fetch_period_reports(connection, "corporate_entity", "2026-W36")
    return await report_ingestion.fetch_period_comparison(connection, "2026-W36")


@pytest.mark.anyio
@pytest.mark.parametrize("consumer", ["list", "detail", "comparison"])
async def test_report_repository_carries_canonical_eligibility_for_complete_population(consumer: str) -> None:
    """Actual loaders retain stored identities and project canonical eligibility for all evidence."""
    connection = _PopulationConnection()
    rows = await _load(connection, consumer)
    assert len(rows) == 1
    assert [member["post_id"] for member in rows[0]["members"]] == ["stored-member", "contracted-member"]
    assert all(member.get("source_eligible") is True for member in rows[0]["members"])
    assert [pair["post_id"] for pair in rows[0]["leftover_pairs"]] == ["stored-pair"]
    assert rows[0]["leftover_pairs"][0]["source_eligible"] is True
    canonical = " ".join(SOURCE_POST_ELIGIBILITY_SQL.format(alias="p").split())
    contributor_queries = [
        part
        for sql in connection.queries
        if "from report_member_score" in sql or "from report_leftover_pair" in sql
        for part in sql.split(" union all ")
    ]
    assert len(contributor_queries) == 2
    for sql in contributor_queries:
        projection, rest = sql.split("from report_", 1)
        assert canonical in projection
        assert "p.post_id is not null and (" in projection
        assert "as source_eligible" in projection
        assert "left join source_post p" in rest
        # Exclusion belongs to admission, not contributor retrieval.
        assert "source_draft_code" not in rest
        assert "source_deleted_flag" not in rest
        assert "source_eligible" not in rest
    assert rows[0]["mean_theta"] == 2.75


async def _consume(monkeypatch: Any, connection: _PopulationConnection, consumer: str) -> list[dict[str, Any]]:
    """Exercise the actual route and repository, replacing only DB acquisition."""
    async def fetch_rows(_conn: object, *_args: object) -> list[dict[str, Any]]:
        return await _load(connection, consumer)

    monkeypatch.setattr(main, "has_real_source_context", _no_real_source_context)
    if consumer == "list":
        monkeypatch.setattr(main, "list_period_report_summaries", fetch_rows)
        payload = await main.list_period_reports("corporate_entity", _account(), _Pool())
        return payload["periods"]
    if consumer == "detail":
        monkeypatch.setattr(main, "fetch_period_reports", fetch_rows)
        payload = await main.read_period_reports("corporate_entity", "2026-W36", _account(), _Pool())
        return payload["reports"]
    monkeypatch.setattr(main, "fetch_period_comparison", fetch_rows)
    payload = await main.compare_period_groupings("2026-W36", _account(), _Pool())
    return payload["groupings"]


@pytest.mark.anyio
@pytest.mark.parametrize("consumer", ["list", "detail", "comparison"])
@pytest.mark.parametrize("contributor", ["member", "pair"])
@pytest.mark.parametrize("revocation", ["draft", "deleted", "global_synthetic", "missing_source"])
async def test_report_consumers_suppress_whole_report_after_eligibility_contraction(
    monkeypatch: Any, consumer: str, contributor: str, revocation: str,
) -> None:
    """Canonical false/missing sources suppress stored aggregates, not just member rows."""
    connection = _PopulationConnection()
    before = await _consume(monkeypatch, connection, consumer)
    assert len(before) == 1
    assert before[0]["mean_theta"] == 2.75
    assert before[0]["post_count"] == 2
    source_id = "contracted-member" if contributor == "member" else "stored-pair"
    if revocation == "missing_source":
        connection.missing_source = source_id
    else:
        connection.revoked_source = source_id
        connection.revocation = revocation
    # The transport seam executes the canonical eligibility expression on
    # synthetic lifecycle columns, without inventing an outcome or refitting.
    stored = await _load(connection, consumer)
    assert len(stored[0]["members"]) == 2
    assert len(stored[0]["leftover_pairs"]) == 1
    assert await _consume(monkeypatch, connection, consumer) == []


@pytest.mark.anyio
@pytest.mark.parametrize("consumer", ["list", "detail", "comparison"])
async def test_report_consumer_positive_keeps_stored_scores_without_internal_flags(
    monkeypatch: Any, consumer: str,
) -> None:
    """Authorized nonempty results preserve persisted scores and hide admission metadata."""
    rows = await _consume(monkeypatch, _PopulationConnection(), consumer)
    assert len(rows) == 1
    assert rows[0]["mean_theta"] == 2.75
    assert rows[0]["post_count"] == 2
    if consumer == "detail":
        assert rows[0]["members"][0]["theta_eap"] == 1.25
    if consumer != "list":
        assert rows[0]["leftover_pairs"][0]["leftover_distance"] == 0.125
    def check(value: Any) -> None:
        if isinstance(value, dict):
            assert "source_eligible" not in value
            assert "has_real_source_context" not in value
            for child in value.values():
                check(child)
        elif isinstance(value, list):
            for child in value:
                check(child)
    check(rows)


@pytest.mark.parametrize("invalid_outcome", [None, False, 1, "true"])
@pytest.mark.parametrize("contributor", ["member", "pair"])
def test_report_population_requires_exact_boolean_eligibility(invalid_outcome: Any, contributor: str) -> None:
    """Unknown and truthy nonboolean eligibility must not authorize persisted statistics."""
    member = _PopulationConnection._source_row("stored-member")
    pair = _PopulationConnection._source_row("stored-pair")
    member["source_eligible"] = pair["source_eligible"] = True
    (member if contributor == "member" else pair)["source_eligible"] = invalid_outcome
    assert main._report_population_is_fully_visible(
        _account(), {"members": [member], "leftover_pairs": [pair]}, set(),
    ) is False


@pytest.mark.parametrize("contributor", ["member", "pair"])
def test_report_population_rejects_missing_eligibility_outcome(contributor: str) -> None:
    """Legacy or malformed contributor metadata fails closed instead of guessing eligibility."""
    member = _PopulationConnection._source_row("stored-member")
    pair = _PopulationConnection._source_row("stored-pair")
    member["source_eligible"] = pair["source_eligible"] = True
    del (member if contributor == "member" else pair)["source_eligible"]
    assert main._report_population_is_fully_visible(
        _account(), {"members": [member], "leftover_pairs": [pair]}, set(),
    ) is False
