"""Contracts for the official O*NET occupation-rating CSV importer."""

import asyncio
import hashlib
from datetime import date
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts.import_onet_ratings import (
    import_ratings,
    read_rating_file,
    read_scale_file,
)


def _write(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8", newline="")
    return path


def test_official_csv_preserves_decimal_missingness_and_uncertainty(
    tmp_path: Path,
) -> None:
    scales = read_scale_file(
        _write(
            tmp_path / "scales.csv",
            "Scale ID,Scale Name,Minimum,Maximum\nIM,Importance,1,5\n",
        )
    )
    ratings = read_rating_file(
        _write(
            tmp_path / "abilities.csv",
            "O*NET-SOC Code,Title,Element ID,Element Name,Scale ID,Scale Name,Data Value,N,Standard Error,Lower CI Bound,Upper CI Bound,Recommend Suppress,Not Relevant,Date,Domain Source\n"
            "15-1252.00,Synthetic occupation,1.A.1.a.1,Oral Comprehension,IM,Importance,4.10,120,0.08,3.94,4.26,N,,08/2026,Analyst\n",
        ),
        scales,
        today=date(2026, 8, 27),
    )

    assert len(ratings) == 1
    assert ratings[0].data_value == Decimal("4.10")
    assert ratings[0].data_value.as_tuple().exponent == -2
    assert ratings[0].standard_error == Decimal("0.08")
    assert ratings[0].lower_ci_bound == Decimal("3.94")
    assert ratings[0].upper_ci_bound == Decimal("4.26")
    assert ratings[0].not_relevant is None
    assert ratings[0].source_updated_month == "08/2026"


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("Data Value", "5.01", "outside scale"),
        ("Standard Error", "-0.01", "standard error"),
        ("Date", "09/2026", "future"),
        ("Date", "8/2026", "invalid source update date"),
        ("Recommend Suppress", "maybe", "flag"),
    ],
)
def test_invalid_source_measurement_fails_before_persistence(
    tmp_path: Path,
    field: str,
    value: str,
    message: str,
) -> None:
    scales = read_scale_file(
        _write(
            tmp_path / "scales.csv",
            "Scale ID,Scale Name,Minimum,Maximum\nIM,Importance,1,5\n",
        )
    )
    row = {
        "O*NET-SOC Code": "15-1252.00",
        "Title": "Synthetic occupation",
        "Element ID": "1.A.1.a.1",
        "Element Name": "Oral Comprehension",
        "Scale ID": "IM",
        "Scale Name": "Importance",
        "Data Value": "4.10",
        "N": "120",
        "Standard Error": "0.08",
        "Lower CI Bound": "3.94",
        "Upper CI Bound": "4.26",
        "Recommend Suppress": "N",
        "Not Relevant": "",
        "Date": "08/2026",
        "Domain Source": "Analyst",
    }
    row[field] = value
    path = tmp_path / "invalid.csv"
    import csv

    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=row)
        writer.writeheader()
        writer.writerow(row)

    with pytest.raises(ValueError, match=message):
        read_rating_file(path, scales, today=date(2026, 8, 27))


def test_conflicting_reference_name_fails_closed(tmp_path: Path) -> None:
    scales = read_scale_file(
        _write(
            tmp_path / "scales.csv",
            "Scale ID,Scale Name,Minimum,Maximum\nIM,Importance,1,5\n",
        )
    )
    path = _write(
        tmp_path / "conflict.csv",
        "O*NET-SOC Code,Title,Element ID,Element Name,Scale ID,Scale Name,Data Value,N,Standard Error,Lower CI Bound,Upper CI Bound,Recommend Suppress,Not Relevant,Date,Domain Source\n"
        "15-1252.00,Synthetic occupation,1.A.1.a.1,Oral Comprehension,IM,Importance,4.10,,,,,N,,08/2026,Analyst\n"
        "15-1252.00,Conflicting title,1.A.1.a.1,Oral Comprehension,IM,Importance,4.20,,,,,N,,08/2026,Analyst\n",
    )

    with pytest.raises(ValueError, match="conflicting occupation title"):
        read_rating_file(path, scales, today=date(2026, 8, 27))


def test_category_table_may_omit_not_relevant_without_inventing_false(
    tmp_path: Path,
) -> None:
    scales = read_scale_file(
        _write(
            tmp_path / "scales.csv",
            "Scale ID,Scale Name,Minimum,Maximum\nPT,Percent,0,100\n",
        )
    )
    rows = read_rating_file(
        _write(
            tmp_path / "education.csv",
            "O*NET-SOC Code,Title,Element ID,Element Name,Scale ID,Scale Name,Category,Data Value,N,Standard Error,Lower CI Bound,Upper CI Bound,Recommend Suppress,Date,Domain Source\n"
            "15-1252.00,Synthetic occupation,2.D.1,Education,PT,Percent,6,42.50,100,1.2,40.1,44.9,N,08/2026,Incumbent\n",
        ),
        scales,
        today=date(2026, 8, 27),
    )

    assert rows[0].category_value == 6
    assert rows[0].not_relevant is None


def test_machine_generated_profile_keeps_unpublished_uncertainty_missing(
    tmp_path: Path,
) -> None:
    scales = read_scale_file(
        _write(
            tmp_path / "scales.csv",
            "Scale ID,Scale Name,Minimum,Maximum\nDR,Distinctiveness Rank,0,7\n",
        )
    )
    rows = read_rating_file(
        _write(
            tmp_path / "work_styles.csv",
            "O*NET-SOC Code,Title,Element ID,Element Name,Scale ID,Scale Name,Data Value,Date,Domain Source\n"
            "15-1252.00,Synthetic occupation,1.D.1.a,Innovation,DR,Distinctiveness Rank,7.00,08/2026,AI/Expert\n",
        ),
        scales,
        today=date(2026, 8, 27),
    )

    assert rows[0].sample_size is None
    assert rows[0].standard_error is None
    assert rows[0].recommend_suppress is None


def test_scales_digest_fails_before_database_connection(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scales = _write(
        tmp_path / "scales.csv",
        "Scale ID,Scale Name,Minimum,Maximum\nIM,Importance,1,5\n",
    )
    ratings = _write(
        tmp_path / "abilities.csv",
        "O*NET-SOC Code,Title,Element ID,Element Name,Scale ID,Scale Name,Data Value,N,Standard Error,Lower CI Bound,Upper CI Bound,Recommend Suppress,Not Relevant,Date,Domain Source\n"
        "15-1252.00,Synthetic occupation,1.A.1.a.1,Oral Comprehension,IM,Importance,4.10,120,0.08,3.94,4.26,N,,08/2026,Analyst\n",
    )
    connected = False

    async def fake_connect(_dsn: str) -> None:
        nonlocal connected
        connected = True

    monkeypatch.setattr("scripts.import_onet_ratings.asyncpg.connect", fake_connect)
    args = SimpleNamespace(
        target_dsn="postgresql://unused",
        release_code="onet-31.0-synthetic",
        release_version="31.0-synthetic",
        source_table_code="abilities",
        source_table_name="Abilities",
        source_url="https://example.test/abilities.csv",
        source_sha256=hashlib.sha256(ratings.read_bytes()).hexdigest(),
        source_row_count=1,
        publisher="Synthetic publisher",
        license_url="https://example.test/license",
        scales_file=scales,
        scales_url="https://example.test/scales.csv",
        scales_sha256="0" * 64,
        scales_row_count=1,
        ratings_file=ratings,
    )

    with pytest.raises(ValueError, match="scales artifact SHA-256 mismatch"):
        asyncio.run(import_ratings(args))
    assert connected is False
