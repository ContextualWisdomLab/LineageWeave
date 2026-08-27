"""Contracts for authorized job-family/job-series snapshot imports."""

import csv
from pathlib import Path

import pytest

from scripts.import_job_architecture import read_job_architecture


_FIELDS = [
    "Node Code",
    "Node Kind",
    "Node Name",
    "Description",
    "Parent Code",
    "Hierarchy Relation",
    "Valid From",
    "Valid To",
    "Occupation Scheme IRI",
    "Occupation Scheme Version",
    "Occupation Code",
    "Occupation Relation",
]


def _write(path: Path, rows: list[dict[str, str]]) -> Path:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    return path


def _row(code: str, kind: str, name: str, **values: str) -> dict[str, str]:
    row = dict.fromkeys(_FIELDS, "")
    row.update({"Node Code": code, "Node Kind": kind, "Node Name": name}, **values)
    return row


def test_snapshot_preserves_multiple_membership_and_explicit_binding(tmp_path: Path) -> None:
    path = _write(
        tmp_path / "architecture.csv",
        [
            _row("F-A", "job_family", "Synthetic family A"),
            _row("F-B", "job_family", "Synthetic family B"),
            _row(
                "S-1",
                "job_series",
                "Synthetic series",
                **{
                    "Parent Code": "F-A",
                    "Hierarchy Relation": "source_broader",
                    "Valid From": "2026-01-01",
                    "Occupation Scheme IRI": "https://example.test/occupation-scheme",
                    "Occupation Scheme Version": "2026",
                    "Occupation Code": "SYN-1",
                    "Occupation Relation": "source_classification",
                },
            ),
            _row(
                "S-1",
                "job_series",
                "Synthetic series",
                **{
                    "Parent Code": "F-B",
                    "Hierarchy Relation": "source_broader",
                    "Valid From": "2026-01-01",
                    "Occupation Scheme IRI": "https://example.test/occupation-scheme",
                    "Occupation Scheme Version": "2026",
                    "Occupation Code": "SYN-1",
                    "Occupation Relation": "source_classification",
                },
            ),
        ],
    )

    nodes, edges, bindings, row_count = read_job_architecture(path)

    assert row_count == 4
    assert len(nodes) == 3
    assert {(edge.broader_code, edge.narrower_code) for edge in edges} == {
        ("F-A", "S-1"),
        ("F-B", "S-1"),
    }
    assert len(bindings) == 1
    assert bindings[0].occupation_code == "SYN-1"


def test_label_never_creates_an_occupation_binding(tmp_path: Path) -> None:
    path = _write(
        tmp_path / "unbound.csv",
        [_row("S-1", "job_series", "15-1252 Software developers")],
    )

    _, _, bindings, _ = read_job_architecture(path)

    assert bindings == []


@pytest.mark.parametrize(
    ("rows", "message"),
    [
        (
            [
                _row("F-A", "job_family", "Family", **{"Parent Code": "S-1", "Hierarchy Relation": "broader"}),
                _row("S-1", "job_series", "Series", **{"Parent Code": "F-A", "Hierarchy Relation": "broader"}),
            ],
            "cyclic",
        ),
        (
            [_row("S-1", "job_series", "Series", **{"Occupation Scheme IRI": "https://example.test/scheme"})],
            "partial occupation binding",
        ),
        (
            [_row("S-1", "job_series", "Series", **{"Parent Code": "missing", "Hierarchy Relation": "broader"})],
            "unknown parent",
        ),
    ],
)
def test_invalid_source_relationships_fail_closed(
    tmp_path: Path,
    rows: list[dict[str, str]],
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        read_job_architecture(_write(tmp_path / "invalid.csv", rows))
