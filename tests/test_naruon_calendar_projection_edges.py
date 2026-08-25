"""Low-level edge tests for the strict calendar projection parser."""

from __future__ import annotations

from datetime import datetime

import pytest

import lineageweave.naruon_calendar_projection as calendar_projection


class _NaiveDateTimeFactory:
    @classmethod
    def fromisoformat(cls, value: str) -> datetime:
        del value
        return datetime(2026, 8, 21, 9, 0, 0)


class _NoOffsetValue:
    tzinfo = object()

    def utcoffset(self) -> None:
        return None


class _NoOffsetDateTimeFactory:
    @classmethod
    def fromisoformat(cls, value: str) -> _NoOffsetValue:
        del value
        return _NoOffsetValue()


def test_rfc3339_parser_rejects_calendar_invalid_date() -> None:
    with pytest.raises(
        calendar_projection.NaruonCalendarContractError,
        match="RFC 3339",
    ):
        calendar_projection._parse_rfc3339(
            "2026-13-21T09:00:00Z",
            field_name="observed_at",
        )


@pytest.mark.parametrize(
    "factory",
    [_NaiveDateTimeFactory, _NoOffsetDateTimeFactory],
)
def test_rfc3339_parser_rejects_runtime_without_usable_offset(
    monkeypatch: pytest.MonkeyPatch,
    factory: object,
) -> None:
    monkeypatch.setattr(calendar_projection, "datetime", factory)

    with pytest.raises(
        calendar_projection.NaruonCalendarContractError,
        match="include an offset",
    ):
        calendar_projection._parse_rfc3339(
            "2026-08-21T09:00:00Z",
            field_name="observed_at",
        )
