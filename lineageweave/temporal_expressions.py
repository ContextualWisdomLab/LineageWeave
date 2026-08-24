"""Resolves Korean relative-time expressions in a Global Ask question into a
concrete `(start_date, end_date)` retrieval bound.

A question like "어제 무슨 일이 있었나요?" ("what happened yesterday?") names a
time window the account already has in mind, but `source_post.created_at` is
the record ingestion clock -- bulk imports cluster it. ADR 0168 binds the
resolved window to `event_occurred_at` with a `created_at` fallback.
Without resolving the expression, Global Ask's keyword retrieval (ADR 0047)
treats "어제" as a literal, near-meaningless search token instead of a date
filter, and a fresh answer can surface a post from months ago that only
happens to rank highest on unrelated keywords.

Only the calendar-day/-year/-month arithmetic lives here; `resolve` never
touches the database or the account's timezone/locale settings -- callers
pass `today` explicitly (server-local date) so this stays a pure function,
trivial to unit test against a fixed date.
"""

from __future__ import annotations

import re
from datetime import date, timedelta

__all__ = ["TEMPORAL_STOPWORDS", "resolve_korean_relative_time"]

_DateRange = tuple[date, date]
_MatchedRange = tuple[int, _DateRange]
_EMPTY_DATE_RANGE = (date.max, date.min)


def _days_in_month(year: int, month: int) -> int:
    """Number of calendar days in `year`-`month` (1-12)."""
    if month == 12:
        return 31
    return (date(year, month + 1, 1) - date(year, month, 1)).days


def _shift_months(day: date, months: int) -> date:
    """`day` shifted by a signed number of whole months, clamped to a
    valid day-of-month (e.g. Jan 31 - 1 month -> Feb 28/29, never Feb 31).
    """
    total = day.year * 12 + (day.month - 1) + months
    year, zero_based_month = divmod(total, 12)
    month = zero_based_month + 1
    return date(year, month, min(day.day, _days_in_month(year, month)))


def _day_range(day: date) -> tuple[date, date]:
    return day, day


def _year_range(year: int) -> tuple[date, date]:
    return date(year, 1, 1), date(year, 12, 31)


def _month_range(anchor: date) -> tuple[date, date]:
    start = date(anchor.year, anchor.month, 1)
    end = date(anchor.year, anchor.month, _days_in_month(anchor.year, anchor.month))
    return start, end


def _week_range(anchor: date) -> tuple[date, date]:
    start = anchor - timedelta(days=anchor.weekday())  # Monday
    return start, start + timedelta(days=6)


def _around(anchor: date, window_days: int) -> tuple[date, date]:
    return anchor - timedelta(days=window_days), anchor + timedelta(days=window_days)


# "이맘때쯤"'s "-쯤" ("approximately") means the account is not asking for an
# exact anniversary date, so same-time-last/year-before-last-year matches
# get a fuzz window instead of a single day.
_SAME_TIME_WINDOW_DAYS = 5

# Ordered most-specific-first: "재작년"/"재작년 이맘때" must be checked before
# the bare "작년" pattern, since "작년" is a substring of "재작년".
_FIXED_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"재작년\s*이맘때\S*"), "same_time_two_years_ago"),
    (re.compile(r"(?:작년|지난해)\s*이맘때\S*"), "same_time_last_year"),
    (re.compile(r"재작년"), "two_years_ago"),
    (re.compile(r"작년|지난해"), "last_year"),
    (re.compile(r"내년"), "next_year"),
    (re.compile(r"올해|금년"), "this_year"),
    (re.compile(r"그끄제|그끄저께"), "three_days_ago"),
    (re.compile(r"그제|그저께"), "two_days_ago"),
    (re.compile(r"어제"), "yesterday"),
    (re.compile(r"오늘"), "today"),
    (re.compile(r"다음\s*주"), "next_week"),
    (re.compile(r"지난\s*주"), "last_week"),
    (re.compile(r"이번\s*주|금주"), "this_week"),
    (re.compile(r"다음\s*달"), "next_month"),
    (re.compile(r"지난\s*달"), "last_month"),
    (re.compile(r"이번\s*달|이달"), "this_month"),
)

# "언젠가" ("someday"/"at some point") is a temporal expression that
# explicitly declines to name a bound -- it must not fall through to the
# generic patterns below and must not become a search keyword either.
_UNBOUNDED_PATTERN = re.compile(r"언젠가")

_N_DAYS_AGO = re.compile(r"(\d+)\s*일\s*전")
_N_WEEKS_AGO = re.compile(r"(\d+)\s*주\s*전")
_N_MONTHS_AGO = re.compile(r"(\d+)\s*(?:개월|달)\s*전")
_N_YEARS_AGO = re.compile(r"(\d+)\s*년\s*전")

# Every literal/word this module can match, so callers (Global Ask's
# keyword-term extraction) can drop them from search terms -- otherwise a
# resolved expression like "어제" also becomes a near-meaningless literal
# keyword search against post titles/bodies.
TEMPORAL_STOPWORDS: frozenset[str] = frozenset(
    {
        "언젠가",
        "오늘",
        "어제",
        "그제",
        "그저께",
        "그끄제",
        "그끄저께",
        "재작년",
        "작년",
        "지난해",
        "올해",
        "금년",
        "내년",
        "이맘때",
        "이맘때쯤",
        "지난주",
        "이번주",
        "다음주",
        "지난",
        "이번",
        "다음",
        "금주",
        "지난달",
        "이번달",
        "다음달",
        "이달",
    }
)


def _fixed_range(label: str, today: date) -> _DateRange:
    match label:
        case "same_time_two_years_ago":
            return _around(_shift_months(today, -24), _SAME_TIME_WINDOW_DAYS)
        case "same_time_last_year":
            return _around(_shift_months(today, -12), _SAME_TIME_WINDOW_DAYS)
        case "two_years_ago":
            return _year_range(today.year - 2)
        case "last_year":
            return _year_range(today.year - 1)
        case "next_year":
            return _year_range(today.year + 1)
        case "this_year":
            return _year_range(today.year)
        case "three_days_ago":
            return _day_range(today - timedelta(days=3))
        case "two_days_ago":
            return _day_range(today - timedelta(days=2))
        case "yesterday":
            return _day_range(today - timedelta(days=1))
        case "today":
            return _day_range(today)
        case "next_week":
            return _week_range(today + timedelta(days=7))
        case "last_week":
            return _week_range(today - timedelta(days=7))
        case "this_week":
            return _week_range(today)
        case "next_month":
            return _month_range(_shift_months(today, 1))
        case "last_month":
            return _month_range(_shift_months(today, -1))
        case "this_month":
            return _month_range(today)
        case _:
            raise AssertionError(f"unknown fixed temporal label: {label}")


def _resolve_fixed(question: str, today: date) -> _MatchedRange | None:
    matches = (
        (match.start(), pattern_index, label)
        for pattern_index, (pattern, label) in enumerate(_FIXED_PATTERNS)
        if (match := pattern.search(question)) is not None
    )
    first = min(matches, default=None)
    if first is None:
        return None
    start, _, label = first
    return start, _fixed_range(label, today)


def _resolve_relative_count(question: str, today: date) -> _MatchedRange | None:
    patterns = (_N_YEARS_AGO, _N_MONTHS_AGO, _N_WEEKS_AGO, _N_DAYS_AGO)
    matches = (
        (match.start(), pattern_index, match)
        for pattern_index, pattern in enumerate(patterns)
        if (match := pattern.search(question)) is not None
    )
    first = min(matches, default=None, key=lambda item: item[:2])
    if first is None:
        return None
    start, pattern_index, match = first
    offset = int(match.group(1))
    try:
        if pattern_index == 0:
            resolved = _year_range(today.year - offset)
        elif pattern_index == 1:
            resolved = _month_range(_shift_months(today, -offset))
        elif pattern_index == 2:
            resolved = _week_range(today - timedelta(days=7 * offset))
        else:
            resolved = _day_range(today - timedelta(days=offset))
    except (OverflowError, ValueError):
        resolved = _EMPTY_DATE_RANGE
    return start, resolved


def resolve_korean_relative_time(
    question: str, *, today: date | None = None
) -> tuple[date, date] | None:
    """Resolve the first Korean relative-time expression in `question`.

    Returns an inclusive `(start_date, end_date)` window, or `None` when no
    expression is found *or* the only expression found is intentionally
    unbounded ("언젠가") -- both cases mean "apply no date filter", which is
    exactly what a caller wants to do with the result either way.
    """
    if not question:
        return None
    reference = today or date.today()
    candidates: list[tuple[int, int, _DateRange | None]] = []
    if fixed := _resolve_fixed(question, reference):
        candidates.append((fixed[0], 0, fixed[1]))
    if relative := _resolve_relative_count(question, reference):
        candidates.append((relative[0], 1, relative[1]))
    if unbounded := _UNBOUNDED_PATTERN.search(question):
        candidates.append((unbounded.start(), 2, None))
    if not candidates:
        return None
    return min(candidates, key=lambda item: item[:2])[2]
