"""Contracts for authorized job-family/job-series snapshot imports."""

import csv
from pathlib import Path

import pytest

from scripts.import_job_architecture import read_job_architecture

_SOURCE_COLUMN_NAMES = [
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


def _write_source_snapshot(
    source_file_path: Path, source_rows: list[dict[str, str]]
) -> Path:
    with source_file_path.open("w", encoding="utf-8", newline="") as source_file:
        source_row_writer = csv.DictWriter(source_file, fieldnames=_SOURCE_COLUMN_NAMES)
        source_row_writer.writeheader()
        source_row_writer.writerows(source_rows)
    return source_file_path


def _source_row(
    job_architecture_code: str,
    job_architecture_kind_code: str,
    job_architecture_name: str,
    **additional_values: str,
) -> dict[str, str]:
    source_row = dict.fromkeys(_SOURCE_COLUMN_NAMES, "")
    source_row.update(
        {
            "Node Code": job_architecture_code,
            "Node Kind": job_architecture_kind_code,
            "Node Name": job_architecture_name,
        },
        **additional_values,
    )
    return source_row


def test_snapshot_preserves_multiple_membership_and_explicit_binding(
    tmp_path: Path,
) -> None:
    source_file_path = _write_source_snapshot(
        tmp_path / "architecture.csv",
        [
            _source_row("F-A", "job_family", "Synthetic family A"),
            _source_row("F-B", "job_family", "Synthetic family B"),
            _source_row(
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
            _source_row(
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

    (
        job_architecture_nodes,
        hierarchy_edges,
        occupation_bindings,
        source_row_count,
    ) = read_job_architecture(source_file_path)

    assert source_row_count == 4
    assert len(job_architecture_nodes) == 3
    assert {
        (hierarchy_edge.broader_code, hierarchy_edge.narrower_code)
        for hierarchy_edge in hierarchy_edges
    } == {
        ("F-A", "S-1"),
        ("F-B", "S-1"),
    }
    assert len(occupation_bindings) == 1
    assert occupation_bindings[0].occupation_code == "SYN-1"


def test_label_never_creates_an_occupation_binding(tmp_path: Path) -> None:
    source_file_path = _write_source_snapshot(
        tmp_path / "unbound.csv",
        [_source_row("S-1", "job_series", "15-1252 Software developers")],
    )

    _, _, occupation_bindings, _ = read_job_architecture(source_file_path)

    assert occupation_bindings == []


@pytest.mark.parametrize(
    ("source_rows", "expected_message"),
    [
        (
            [
                _source_row(
                    "F-A",
                    "job_family",
                    "Family",
                    **{"Parent Code": "S-1", "Hierarchy Relation": "broader"},
                ),
                _source_row(
                    "S-1",
                    "job_series",
                    "Series",
                    **{"Parent Code": "F-A", "Hierarchy Relation": "broader"},
                ),
            ],
            "cyclic",
        ),
        (
            [
                _source_row(
                    "S-1",
                    "job_series",
                    "Series",
                    **{"Occupation Scheme IRI": "https://example.test/scheme"},
                )
            ],
            "partial occupation binding",
        ),
        (
            [
                _source_row(
                    "S-1",
                    "job_series",
                    "Series",
                    **{
                        "Parent Code": "missing",
                        "Hierarchy Relation": "broader",
                    },
                )
            ],
            "unknown parent",
        ),
    ],
)
def test_invalid_source_relationships_fail_closed(
    tmp_path: Path,
    source_rows: list[dict[str, str]],
    expected_message: str,
) -> None:
    with pytest.raises(ValueError, match=expected_message):
        read_job_architecture(
            _write_source_snapshot(tmp_path / "invalid.csv", source_rows)
        )
