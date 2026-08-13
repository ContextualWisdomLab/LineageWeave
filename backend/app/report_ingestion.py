"""Load evaluation rows, calibrate a period report, persist the scores."""

from __future__ import annotations

import re
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

import asyncpg

from lineageweave.period_report import (
    ItemBank,
    PeriodReport,
    link_or_calibrate_period_report,
)
from lineageweave.post_evaluation import CRITERION_CODES, RUBRIC_VERSION

GROUPING_KINDS = frozenset({"process_unit", "corporate_entity", "thread_group"})
_WEEK_PERIOD = re.compile(r"^(\d{4})-W(\d{2})$")
_MONTH_PERIOD = re.compile(r"^(\d{4})-(\d{2})$")


def parse_period_code(period_code: str) -> tuple[str, int, int]:
    """Return ``(kind, year, week_or_month)`` or raise ValueError."""
    week = _WEEK_PERIOD.fullmatch(period_code)
    if week:
        year, week_no = int(week.group(1)), int(week.group(2))
        if not 1 <= week_no <= 53:
            raise ValueError("ISO week must be 01..53")
        return ("week", year, week_no)
    month = _MONTH_PERIOD.fullmatch(period_code)
    if month:
        year, month_no = int(month.group(1)), int(month.group(2))
        if not 1 <= month_no <= 12:
            raise ValueError("month must be 01..12")
        return ("month", year, month_no)
    raise ValueError("period must look like 2026-W02 or 2026-01")


def grouping_value(kind: str, row: asyncpg.Record) -> str | None:
    """The grouping key for one source_post row, or None if unset."""
    if kind == "process_unit":
        value = row["process_unit_id"]
    elif kind == "corporate_entity":
        value = row["corporate_entity_id"]
    else:
        value = row["thread_group_key"]
    if value is None:
        return None
    text = str(value).strip()
    return text or None


async def load_period_evaluation_rows(
    conn: asyncpg.Connection,
    grouping_kind: str,
    period_code: str,
) -> list[asyncpg.Record]:
    """Evaluation cells whose post falls in ``period_code``."""
    kind, year, number = parse_period_code(period_code)
    if kind == "week":
        period_filter = "to_char(p.created_at at time zone 'UTC', 'IYYY-\"W\"IW') = $2"
    else:
        period_filter = "to_char(p.created_at at time zone 'UTC', 'YYYY-MM') = $2"
    return await conn.fetch(
        f"""
        select e.post_id, e.criterion_code, e.response_category,
               p.process_unit_id, p.corporate_entity_id, p.thread_group_key,
               p.visibility_code, p.post_title
        from post_evaluation_response e
        join source_post p on p.post_id = e.post_id
        where e.rubric_version = $1 and {period_filter}
        """,
        RUBRIC_VERSION,
        period_code,
    )


async def load_anchor_item_bank(
    conn: asyncpg.Connection,
    grouping_kind: str,
    grouping_key: str,
    period_code: str,
) -> tuple[ItemBank, float] | None:
    """Latest earlier period's item bank and mean θ, if one exists."""
    kind, _, _ = parse_period_code(period_code)
    kind_filter = (
        "and period_code like '%-W%'" if kind == "week" else "and period_code not like '%-W%'"
    )
    header = await conn.fetchrow(
        f"""
        select period_code, selected_model, mean_theta
        from report_period_score
        where grouping_kind = $1 and grouping_key = $2
          and rubric_version = $3 and period_code < $4
          {kind_filter}
        order by period_code desc
        limit 1
        """,
        grouping_kind,
        grouping_key,
        RUBRIC_VERSION,
        period_code,
    )
    if header is None:
        return None
    items = await conn.fetch(
        """
        select item_code, item_index, slope, cat_params
        from report_item_parameter
        where grouping_kind = $1 and grouping_key = $2
          and period_code = $3 and rubric_version = $4
        order by item_index
        """,
        grouping_kind,
        grouping_key,
        header["period_code"],
        RUBRIC_VERSION,
    )
    if not items:
        return None
    return (
        ItemBank(
            model=str(header["selected_model"]),
            item_codes=tuple(str(row["item_code"]) for row in items),
            slope=tuple(float(row["slope"]) for row in items),
            cat_params=tuple(tuple(float(value) for value in row["cat_params"]) for row in items),
            source_period_code=str(header["period_code"]),
        ),
        float(header["mean_theta"]),
    )


async def persist_period_report(
    conn: asyncpg.Connection,
    grouping_kind: str,
    grouping_key: str,
    period_code: str,
    report: PeriodReport,
) -> None:
    """Replace the stored report, member scores, and item bank."""
    await conn.execute(
        """
        delete from report_period_score
        where grouping_kind = $1 and grouping_key = $2
          and period_code = $3 and rubric_version = $4
        """,
        grouping_kind,
        grouping_key,
        period_code,
        RUBRIC_VERSION,
    )
    await conn.execute(
        """
        insert into report_period_score (
            grouping_kind, grouping_key, period_code, rubric_version,
            selected_model, mean_theta, mean_theta_sd, post_count, item_count,
            fit_loglik, fit_converged, calibration_score,
            link_method, anchor_period_code, delta_mean_theta
        ) values ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15)
        """,
        grouping_kind,
        grouping_key,
        period_code,
        RUBRIC_VERSION,
        report.selected_model,
        report.mean_theta,
        report.mean_theta_sd,
        report.post_count,
        report.item_count,
        report.fit_loglik,
        report.fit_converged,
        report.calibration_score,
        report.link_method,
        report.anchor_period_code,
        report.delta_mean_theta,
    )
    for member in report.member_scores:
        await conn.execute(
            """
            insert into report_member_score (
                grouping_kind, grouping_key, period_code, rubric_version,
                post_id, theta_eap, theta_sd
            ) values ($1,$2,$3,$4,$5,$6,$7)
            """,
            grouping_kind,
            grouping_key,
            period_code,
            RUBRIC_VERSION,
            member.post_id,
            member.theta_eap,
            member.theta_sd,
        )
    bank = report.item_bank
    for index, item_code in enumerate(bank.item_codes):
        await conn.execute(
            """
            insert into report_item_parameter (
                grouping_kind, grouping_key, period_code, rubric_version,
                item_code, item_index, slope, cat_params
            ) values ($1,$2,$3,$4,$5,$6,$7,$8)
            """,
            grouping_kind,
            grouping_key,
            period_code,
            RUBRIC_VERSION,
            item_code,
            index,
            bank.slope[index],
            list(bank.cat_params[index]),
        )


async def rebuild_period_reports(
    conn: asyncpg.Connection,
    grouping_kind: str,
    period_code: str,
) -> list[PeriodReport]:
    """Calibrate every grouping key that has enough evaluations in the period."""
    if grouping_kind not in GROUPING_KINDS:
        raise ValueError(f"unknown grouping_kind {grouping_kind!r}")
    parse_period_code(period_code)
    rows = await load_period_evaluation_rows(conn, grouping_kind, period_code)
    by_group: dict[str, list[asyncpg.Record]] = defaultdict(list)
    for row in rows:
        key = grouping_value(grouping_kind, row)
        if key is not None:
            by_group[key].append(row)

    reports: list[PeriodReport] = []
    for grouping_key, group_rows in by_group.items():
        post_ids = list(dict.fromkeys(str(row["post_id"]) for row in group_rows))
        if len(post_ids) < 2:
            continue
        cells = [
            (str(row["post_id"]), row["criterion_code"], int(row["response_category"]))
            for row in group_rows
        ]
        anchor = await load_anchor_item_bank(conn, grouping_kind, grouping_key, period_code)
        item_bank, previous_mean = (anchor[0], anchor[1]) if anchor else (None, None)
        report = link_or_calibrate_period_report(
            post_ids,
            cells,
            item_bank=item_bank,
            previous_mean_theta=previous_mean,
            item_codes=CRITERION_CODES,
            source_period_code=period_code,
        )
        await persist_period_report(conn, grouping_kind, grouping_key, period_code, report)
        reports.append(report)
    return reports


async def fetch_period_reports(
    conn: asyncpg.Connection,
    grouping_kind: str,
    period_code: str,
) -> list[dict[str, Any]]:
    """Stored reports plus member scores for one grouping/period."""
    headers = await conn.fetch(
        """
        select grouping_kind, grouping_key, period_code, rubric_version,
               selected_model, mean_theta, mean_theta_sd, post_count, item_count,
               fit_loglik, fit_converged, calibration_score, computed_at,
               link_method, anchor_period_code, delta_mean_theta
        from report_period_score
        where grouping_kind = $1 and period_code = $2 and rubric_version = $3
        order by grouping_key
        """,
        grouping_kind,
        period_code,
        RUBRIC_VERSION,
    )
    members = await conn.fetch(
        """
        select m.grouping_key, m.post_id, m.theta_eap, m.theta_sd, p.post_title,
               p.visibility_code, p.corporate_entity_id
        from report_member_score m
        join source_post p on p.post_id = m.post_id
        where m.grouping_kind = $1 and m.period_code = $2 and m.rubric_version = $3
        order by m.theta_eap desc
        """,
        grouping_kind,
        period_code,
        RUBRIC_VERSION,
    )
    members_by_group: dict[str, list[asyncpg.Record]] = defaultdict(list)
    for row in members:
        members_by_group[row["grouping_key"]].append(row)
    payload: list[dict[str, Any]] = []
    for header in headers:
        payload.append(
            {
                "grouping_kind": header["grouping_kind"],
                "grouping_key": header["grouping_key"],
                "period_code": header["period_code"],
                "rubric_version": header["rubric_version"],
                "selected_model": header["selected_model"],
                "mean_theta": float(header["mean_theta"]),
                "mean_theta_sd": float(header["mean_theta_sd"]),
                "post_count": int(header["post_count"]),
                "item_count": int(header["item_count"]),
                "fit_loglik": float(header["fit_loglik"]),
                "fit_converged": bool(header["fit_converged"]),
                "calibration_score": float(header["calibration_score"]),
                "computed_at": header["computed_at"].isoformat(),
                "link_method": header["link_method"],
                "anchor_period_code": header["anchor_period_code"],
                "delta_mean_theta": (
                    None
                    if header["delta_mean_theta"] is None
                    else float(header["delta_mean_theta"])
                ),
                "members": [
                    {
                        "post_id": str(row["post_id"]),
                        "post_title": row["post_title"],
                        "theta_eap": float(row["theta_eap"]),
                        "theta_sd": float(row["theta_sd"]),
                        "visibility_code": row["visibility_code"],
                        "corporate_entity_id": str(row["corporate_entity_id"]),
                    }
                    for row in members_by_group.get(header["grouping_key"], [])
                ],
            }
        )
    return payload


async def list_period_report_summaries(
    conn: asyncpg.Connection,
    grouping_kind: str,
) -> list[dict[str, Any]]:
    """One row per stored grouping/period, newest last, for the trend strip."""
    if grouping_kind not in GROUPING_KINDS:
        raise ValueError(f"unknown grouping_kind {grouping_kind!r}")
    rows = await conn.fetch(
        """
        select grouping_kind, grouping_key, period_code, selected_model,
               mean_theta, post_count, link_method, anchor_period_code,
               delta_mean_theta, fit_converged
        from report_period_score
        where grouping_kind = $1 and rubric_version = $2
        order by period_code, grouping_key
        """,
        grouping_kind,
        RUBRIC_VERSION,
    )
    members = await conn.fetch(
        """
        select m.grouping_key, m.period_code, p.visibility_code, p.corporate_entity_id
        from report_member_score m
        join source_post p on p.post_id = m.post_id
        where m.grouping_kind = $1 and m.rubric_version = $2
        """,
        grouping_kind,
        RUBRIC_VERSION,
    )
    members_by_key: dict[tuple[str, str], list[asyncpg.Record]] = defaultdict(list)
    for row in members:
        members_by_key[(row["grouping_key"], row["period_code"])].append(row)
    return [
        {
            "grouping_kind": row["grouping_kind"],
            "grouping_key": row["grouping_key"],
            "period_code": row["period_code"],
            "selected_model": row["selected_model"],
            "mean_theta": float(row["mean_theta"]),
            "post_count": int(row["post_count"]),
            "link_method": row["link_method"],
            "anchor_period_code": row["anchor_period_code"],
            "delta_mean_theta": (
                None if row["delta_mean_theta"] is None else float(row["delta_mean_theta"])
            ),
            "fit_converged": bool(row["fit_converged"]),
            "members": [
                {
                    "visibility_code": member["visibility_code"],
                    "corporate_entity_id": str(member["corporate_entity_id"]),
                }
                for member in members_by_key.get((row["grouping_key"], row["period_code"]), [])
            ],
        }
        for row in rows
    ]


def iso_week_period(when: datetime | None = None) -> str:
    """UTC ISO week label, e.g. ``2026-W02``."""
    moment = when or datetime.now(timezone.utc)
    year, week, _ = moment.isocalendar()
    return f"{year}-W{week:02d}"
