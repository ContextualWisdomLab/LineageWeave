from __future__ import annotations

from datetime import date

import pytest

from lineageweave.temporal_expressions import (
    TEMPORAL_STOPWORDS,
    resolve_korean_relative_time,
)

_TODAY = date(2026, 8, 22)  # a Saturday


@pytest.mark.parametrize(
    ("question", "expected"),
    [
        ("오늘 무슨 일이 있었나요?", (date(2026, 8, 22), date(2026, 8, 22))),
        ("어제 발생한 이슈 알려줘", (date(2026, 8, 21), date(2026, 8, 21))),
        ("그제 회의 내용은?", (date(2026, 8, 20), date(2026, 8, 20))),
        ("그저께 있었던 일", (date(2026, 8, 20), date(2026, 8, 20))),
        ("그끄제 무슨 일이었지", (date(2026, 8, 19), date(2026, 8, 19))),
        ("올해 실적은 어때?", (date(2026, 1, 1), date(2026, 12, 31))),
        ("내년 계획이 뭐야", (date(2027, 1, 1), date(2027, 12, 31))),
        ("재작년에 무슨 프로젝트를 했나요?", (date(2024, 1, 1), date(2024, 12, 31))),
        ("작년에 있었던 일", (date(2025, 1, 1), date(2025, 12, 31))),
        ("지난주 이슈 정리해줘", (date(2026, 8, 10), date(2026, 8, 16))),
        ("이번주 진행상황", (date(2026, 8, 17), date(2026, 8, 23))),
        ("다음주 일정", (date(2026, 8, 24), date(2026, 8, 30))),
        ("지난달 실적", (date(2026, 7, 1), date(2026, 7, 31))),
        ("이번달 진행상황", (date(2026, 8, 1), date(2026, 8, 31))),
        ("3일 전에 있었던 일", (date(2026, 8, 19), date(2026, 8, 19))),
        # N주/N개월 전 resolve to the containing week/month, like 지난주/지난달,
        # since "2 weeks ago" means that week, not one arbitrary day in it.
        ("2주 전 이슈", (date(2026, 8, 3), date(2026, 8, 9))),
        ("6개월 전에 무슨 일이 있었죠", (date(2026, 2, 1), date(2026, 2, 28))),
        ("2년 전 계약 내용", (date(2024, 1, 1), date(2024, 12, 31))),
    ],
)
def test_resolves_named_and_generalized_expressions(
    question: str, expected: tuple[date, date]
) -> None:
    assert resolve_korean_relative_time(question, today=_TODAY) == expected


def test_same_time_last_year_gives_a_fuzz_window_around_the_anniversary() -> None:
    start, end = resolve_korean_relative_time("작년 이맘때쯤 상황이 궁금해요", today=_TODAY)
    assert start == date(2025, 8, 17)
    assert end == date(2025, 8, 27)


def test_same_time_last_year_accepts_jinanhae_synonym() -> None:
    assert resolve_korean_relative_time("지난해 이맘때 상황", today=_TODAY) == (
        date(2025, 8, 17),
        date(2025, 8, 27),
    )


def test_same_time_two_years_ago_shifts_the_anniversary_further_back() -> None:
    start, end = resolve_korean_relative_time("재작년 이맘때는 어땠나요", today=_TODAY)
    assert start == date(2024, 8, 17)
    assert end == date(2024, 8, 27)


def test_someday_is_intentionally_unbounded() -> None:
    assert resolve_korean_relative_time("언젠가 이런 이슈가 있었나요?", today=_TODAY) is None


def test_no_temporal_expression_returns_none() -> None:
    assert resolve_korean_relative_time("이 프로젝트 진행 상황이 궁금해요", today=_TODAY) is None


def test_empty_question_returns_none() -> None:
    assert resolve_korean_relative_time("", today=_TODAY) is None


def test_leap_day_anniversary_clamps_to_feb_28_in_a_non_leap_year() -> None:
    # 2024-02-29 exists (leap year); shifting the anniversary back one year
    # lands on 2023, which has no Feb 29 -- must clamp, not raise/overflow.
    start, end = resolve_korean_relative_time("작년 이맘때쯤 상황", today=date(2024, 2, 29))
    assert start == date(2023, 2, 23)
    assert end == date(2023, 3, 5)


def test_bare_generic_word_before_year_does_not_false_match() -> None:
    # "작년" must not match inside "재작년" and vice versa is covered above;
    # this guards the reverse -- a plain "작년" question must not resolve
    # to the two-years-ago range.
    start, end = resolve_korean_relative_time("작년 매출이 어땠나요", today=_TODAY)
    assert (start, end) == (date(2025, 1, 1), date(2025, 12, 31))


@pytest.mark.parametrize(
    "question",
    (
        "2026년 전",
        "999999999999개월 전",
        "999999999999주 전",
        "999999999999일 전",
    ),
)
def test_out_of_range_offsets_return_an_explicit_empty_range(question: str) -> None:
    start, end = resolve_korean_relative_time(question, today=_TODAY)
    assert start > end


@pytest.mark.parametrize(
    ("question", "expected"),
    (
        ("3일 전과 어제", (date(2026, 8, 19), date(2026, 8, 19))),
        ("다음 주와 오늘", (date(2026, 8, 24), date(2026, 8, 30))),
        ("언젠가 또는 어제", None),
        ("어제 또는 언젠가", (date(2026, 8, 21), date(2026, 8, 21))),
    ),
)
def test_first_expression_in_text_wins(
    question: str, expected: tuple[date, date] | None
) -> None:
    assert resolve_korean_relative_time(question, today=_TODAY) == expected


def test_temporal_stopwords_cover_every_fixed_literal_used_in_matching() -> None:
    for literal in ("오늘", "어제", "그제", "재작년", "작년", "올해", "내년", "언젠가"):
        assert literal in TEMPORAL_STOPWORDS
    for spaced_expression_token in ("지난", "이번", "다음"):
        assert spaced_expression_token in TEMPORAL_STOPWORDS
