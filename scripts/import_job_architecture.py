"""Validate and import one authorized job-family/job-series snapshot."""

from __future__ import annotations

import argparse
import asyncio
import csv
import hashlib
import json
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit

import asyncpg

_SOURCE_COLUMN_NAMES = {
    "Node Code",
    "Node Kind",
    "Node Name",
    "Parent Code",
    "Hierarchy Relation",
    "Valid From",
    "Valid To",
    "Occupation Scheme IRI",
    "Occupation Scheme Version",
    "Occupation Code",
    "Occupation Relation",
}
_JOB_ARCHITECTURE_KIND_CODES = {"job_family", "job_series"}
_SOURCE_SYSTEM_CODE_PATTERN = re.compile(r"^[a-z][a-z0-9_]{0,62}$")
_SHA256_PATTERN = re.compile(r"^[0-9a-fA-F]{64}$")


@dataclass(frozen=True)
class JobArchitectureNode:
    """One exact node from an authorized source snapshot."""

    job_architecture_code: str
    job_architecture_kind_code: str
    job_architecture_name: str
    job_architecture_description: str | None
    valid_from: date | None
    valid_to: date | None


@dataclass(frozen=True)
class JobArchitectureEdge:
    """One source-declared broader-to-narrower relationship."""

    broader_code: str
    narrower_code: str
    source_relation_code: str


@dataclass(frozen=True)
class OccupationBinding:
    """One explicit source binding to an external occupation code."""

    job_architecture_code: str
    occupation_scheme_iri: str
    occupation_scheme_version: str
    occupation_code: str
    source_relation_code: str


def _optional_date(source_date_text: str, field_label: str) -> date | None:
    """Parse an optional ISO date without inventing a missing instant."""
    normalized_date_text = source_date_text.strip()
    if not normalized_date_text:
        return None
    try:
        return date.fromisoformat(normalized_date_text)
    except ValueError as exc:
        raise ValueError(f"invalid {field_label}: {source_date_text!r}") from exc


def _https_url(source_url: str, field_label: str) -> str:
    """Validate an HTTPS URL with no embedded credentials."""
    parsed_url = urlsplit(source_url)
    if (
        parsed_url.scheme != "https"
        or not parsed_url.hostname
        or parsed_url.username is not None
        or parsed_url.password is not None
    ):
        raise ValueError(f"{field_label} must be an HTTPS URL without userinfo")
    return source_url


def read_job_architecture(
    source_file_path: Path,
) -> tuple[
    list[JobArchitectureNode],
    list[JobArchitectureEdge],
    list[OccupationBinding],
    int,
]:
    """Return exact nodes, hierarchy edges, and explicit occupation bindings."""
    job_architecture_nodes_by_code: dict[str, JobArchitectureNode] = {}
    hierarchy_edges_by_codes: dict[tuple[str, str], JobArchitectureEdge] = {}
    occupation_bindings_by_identity: dict[
        tuple[str, str, str, str], OccupationBinding
    ] = {}
    source_row_count = 0
    with source_file_path.open(encoding="utf-8-sig", newline="") as source_file:
        source_row_reader = csv.DictReader(source_file)
        missing_columns = sorted(
            _SOURCE_COLUMN_NAMES - set(source_row_reader.fieldnames or ())
        )
        if missing_columns:
            raise ValueError(f"missing CSV columns: {', '.join(missing_columns)}")
        for line_number, source_row in enumerate(source_row_reader, start=2):
            source_row_count += 1
            if None in source_row or any(
                column_value is None for column_value in source_row.values()
            ):
                raise ValueError(f"malformed CSV row: {line_number}")
            job_architecture_code = source_row["Node Code"].strip()
            job_architecture_kind_code = source_row["Node Kind"].strip()
            job_architecture_name = source_row["Node Name"].strip()
            if (
                not job_architecture_code
                or not job_architecture_name
                or job_architecture_kind_code not in _JOB_ARCHITECTURE_KIND_CODES
            ):
                raise ValueError(f"invalid node identity at row {line_number}")
            valid_from = _optional_date(source_row["Valid From"], "valid from")
            valid_to = _optional_date(source_row["Valid To"], "valid to")
            if valid_from and valid_to and valid_from > valid_to:
                raise ValueError(f"inverted validity interval at row {line_number}")
            job_architecture_node = JobArchitectureNode(
                job_architecture_code,
                job_architecture_kind_code,
                job_architecture_name,
                source_row.get("Description", "").strip() or None,
                valid_from,
                valid_to,
            )
            if (
                job_architecture_code in job_architecture_nodes_by_code
                and job_architecture_nodes_by_code[job_architecture_code]
                != job_architecture_node
            ):
                raise ValueError(f"conflicting node identity: {job_architecture_code}")
            job_architecture_nodes_by_code[job_architecture_code] = (
                job_architecture_node
            )
            broader_job_architecture_code = source_row["Parent Code"].strip()
            hierarchy_relation_code = source_row["Hierarchy Relation"].strip()
            if broader_job_architecture_code:
                if not hierarchy_relation_code:
                    raise ValueError(f"missing hierarchy relation at row {line_number}")
                hierarchy_edge = JobArchitectureEdge(
                    broader_job_architecture_code,
                    job_architecture_code,
                    hierarchy_relation_code,
                )
                hierarchy_edge_identity = (
                    broader_job_architecture_code,
                    job_architecture_code,
                )
                if (
                    hierarchy_edge_identity in hierarchy_edges_by_codes
                    and hierarchy_edges_by_codes[hierarchy_edge_identity]
                    != hierarchy_edge
                ):
                    raise ValueError(
                        f"conflicting hierarchy relation at row {line_number}"
                    )
                hierarchy_edges_by_codes[hierarchy_edge_identity] = hierarchy_edge
            occupation_scheme_iri = source_row["Occupation Scheme IRI"].strip()
            occupation_scheme_version = source_row["Occupation Scheme Version"].strip()
            occupation_code = source_row["Occupation Code"].strip()
            occupation_relation_code = source_row["Occupation Relation"].strip()
            occupation_binding_presence = (
                bool(occupation_scheme_iri),
                bool(occupation_scheme_version),
                bool(occupation_code),
                bool(occupation_relation_code),
            )
            if any(occupation_binding_presence) and not all(
                occupation_binding_presence
            ):
                raise ValueError(f"partial occupation binding at row {line_number}")
            if all(occupation_binding_presence):
                parsed_scheme_iri = urlsplit(occupation_scheme_iri)
                if (
                    parsed_scheme_iri.scheme not in {"http", "https"}
                    or not parsed_scheme_iri.hostname
                    or parsed_scheme_iri.username is not None
                    or parsed_scheme_iri.password is not None
                ):
                    raise ValueError(
                        f"invalid occupation scheme IRI at row {line_number}"
                    )
                if not occupation_relation_code:
                    raise ValueError(f"missing binding relation at row {line_number}")
                occupation_binding = OccupationBinding(
                    job_architecture_code,
                    occupation_scheme_iri,
                    occupation_scheme_version,
                    occupation_code,
                    occupation_relation_code,
                )
                occupation_binding_identity = (
                    job_architecture_code,
                    occupation_scheme_iri,
                    occupation_scheme_version,
                    occupation_code,
                )
                if (
                    occupation_binding_identity in occupation_bindings_by_identity
                    and occupation_bindings_by_identity[occupation_binding_identity]
                    != occupation_binding
                ):
                    raise ValueError(
                        f"conflicting occupation relation at row {line_number}"
                    )
                occupation_bindings_by_identity[occupation_binding_identity] = (
                    occupation_binding
                )
    if not job_architecture_nodes_by_code:
        raise ValueError("job architecture file has no rows")
    for hierarchy_edge in hierarchy_edges_by_codes.values():
        if hierarchy_edge.broader_code not in job_architecture_nodes_by_code:
            raise ValueError(f"unknown parent node: {hierarchy_edge.broader_code}")
        if hierarchy_edge.broader_code == hierarchy_edge.narrower_code:
            raise ValueError(f"self hierarchy edge: {hierarchy_edge.broader_code}")
    child_codes_by_parent: dict[str, set[str]] = {
        job_architecture_code: set()
        for job_architecture_code in job_architecture_nodes_by_code
    }
    incoming_edge_count_by_code = dict.fromkeys(job_architecture_nodes_by_code, 0)
    for hierarchy_edge in hierarchy_edges_by_codes.values():
        child_codes_by_parent[hierarchy_edge.broader_code].add(
            hierarchy_edge.narrower_code
        )
        incoming_edge_count_by_code[hierarchy_edge.narrower_code] += 1
    ready_node_codes = [
        job_architecture_code
        for job_architecture_code, incoming_edge_count in incoming_edge_count_by_code.items()
        if incoming_edge_count == 0
    ]
    visited_node_count = 0
    while ready_node_codes:
        job_architecture_code = ready_node_codes.pop()
        visited_node_count += 1
        for child_node_code in child_codes_by_parent[job_architecture_code]:
            incoming_edge_count_by_code[child_node_code] -= 1
            if incoming_edge_count_by_code[child_node_code] == 0:
                ready_node_codes.append(child_node_code)
    if visited_node_count != len(job_architecture_nodes_by_code):
        raise ValueError("cyclic job architecture hierarchy")
    return (
        list(job_architecture_nodes_by_code.values()),
        sorted(hierarchy_edges_by_codes.values(), key=repr),
        sorted(occupation_bindings_by_identity.values(), key=repr),
        source_row_count,
    )


def _job_architecture_import_parser() -> argparse.ArgumentParser:
    """Build the explicit source-snapshot import contract."""
    import_parser = argparse.ArgumentParser(description=__doc__)
    import_parser.add_argument("--target-dsn", required=True)
    import_parser.add_argument("--corporate-entity-code", required=True)
    import_parser.add_argument("--source-system-code", required=True)
    import_parser.add_argument("--source-snapshot-code", required=True)
    import_parser.add_argument("--source-name", required=True)
    import_parser.add_argument("--source-url", required=True)
    import_parser.add_argument("--source-sha256", required=True)
    import_parser.add_argument("--source-row-count", type=int, required=True)
    import_parser.add_argument("--source-file", type=Path, required=True)
    return import_parser


async def import_job_architecture(
    command_arguments: argparse.Namespace,
) -> dict[str, object]:
    """Validate one pinned snapshot before transactionally persisting it."""
    if not _SOURCE_SYSTEM_CODE_PATTERN.fullmatch(command_arguments.source_system_code):
        raise ValueError("source system code must be lower snake case")
    for required_field_name in (
        "corporate_entity_code",
        "source_snapshot_code",
        "source_name",
    ):
        if not str(getattr(command_arguments, required_field_name)).strip():
            raise ValueError(f"{required_field_name} must not be blank")
    _https_url(command_arguments.source_url, "source URL")
    if not _SHA256_PATTERN.fullmatch(command_arguments.source_sha256):
        raise ValueError("source SHA-256 must be one digest")
    if (
        command_arguments.source_row_count <= 0
        or not command_arguments.source_file.is_file()
    ):
        raise ValueError("source row count and file must be valid")
    source_artifact_sha256 = hashlib.sha256(
        command_arguments.source_file.read_bytes()
    ).hexdigest()
    if source_artifact_sha256 != command_arguments.source_sha256.lower():
        raise ValueError("source artifact SHA-256 mismatch")
    (
        job_architecture_nodes,
        hierarchy_edges,
        occupation_bindings,
        source_row_count,
    ) = read_job_architecture(command_arguments.source_file)
    if source_row_count != command_arguments.source_row_count:
        raise ValueError("source artifact row-count mismatch")
    database_connection = await asyncpg.connect(command_arguments.target_dsn)
    try:
        async with database_connection.transaction():
            corporate_entity_id = await database_connection.fetchval(
                "select corporate_entity_id from corporate_entity where corporate_entity_code = $1",
                command_arguments.corporate_entity_code,
            )
            if corporate_entity_id is None:
                raise ValueError("corporate entity must already exist")
            source_snapshot_identity = (
                corporate_entity_id,
                command_arguments.source_system_code,
                command_arguments.source_snapshot_code,
            )
            await database_connection.execute(
                """insert into job_architecture_source
                       (corporate_entity_id, source_system_code, source_snapshot_code,
                        source_name, source_artifact_url, source_artifact_sha256,
                        source_row_count)
                   values ($1,$2,$3,$4,$5,$6,$7)
                   on conflict (corporate_entity_id, source_system_code, source_snapshot_code)
                   do update set source_name = excluded.source_name
                   where row(job_architecture_source.source_name,
                             job_architecture_source.source_artifact_url,
                             job_architecture_source.source_artifact_sha256,
                             job_architecture_source.source_row_count)
                     is distinct from row(excluded.source_name,
                                          excluded.source_artifact_url,
                                          excluded.source_artifact_sha256,
                                          excluded.source_row_count)""",
                *source_snapshot_identity,
                command_arguments.source_name,
                command_arguments.source_url,
                source_artifact_sha256,
                source_row_count,
            )
            await database_connection.executemany(
                """insert into job_architecture_node
                       (corporate_entity_id, source_system_code, source_snapshot_code,
                        job_architecture_code, job_architecture_kind_code,
                        job_architecture_name, job_architecture_description,
                        valid_from, valid_to)
                   values ($1,$2,$3,$4,$5,$6,$7,$8,$9)
                   on conflict (corporate_entity_id, source_system_code,
                                source_snapshot_code, job_architecture_code)
                   do update set job_architecture_name = excluded.job_architecture_name
                   where row(job_architecture_node.job_architecture_kind_code,
                             job_architecture_node.job_architecture_name,
                             job_architecture_node.job_architecture_description,
                             job_architecture_node.valid_from,
                             job_architecture_node.valid_to)
                     is distinct from row(excluded.job_architecture_kind_code,
                                          excluded.job_architecture_name,
                                          excluded.job_architecture_description,
                                          excluded.valid_from, excluded.valid_to)""",
                [
                    (
                        *source_snapshot_identity,
                        job_architecture_node.job_architecture_code,
                        job_architecture_node.job_architecture_kind_code,
                        job_architecture_node.job_architecture_name,
                        job_architecture_node.job_architecture_description,
                        job_architecture_node.valid_from,
                        job_architecture_node.valid_to,
                    )
                    for job_architecture_node in job_architecture_nodes
                ],
            )
            await database_connection.executemany(
                """insert into job_architecture_hierarchy_edge
                       (corporate_entity_id, source_system_code, source_snapshot_code,
                        broader_job_architecture_code, narrower_job_architecture_code,
                        source_relation_code)
                   values ($1,$2,$3,$4,$5,$6)
                   on conflict (corporate_entity_id, source_system_code,
                                source_snapshot_code, broader_job_architecture_code,
                                narrower_job_architecture_code)
                   do update set source_relation_code = excluded.source_relation_code
                   where job_architecture_hierarchy_edge.source_relation_code
                         is distinct from excluded.source_relation_code""",
                [
                    (
                        *source_snapshot_identity,
                        hierarchy_edge.broader_code,
                        hierarchy_edge.narrower_code,
                        hierarchy_edge.source_relation_code,
                    )
                    for hierarchy_edge in hierarchy_edges
                ],
            )
            await database_connection.executemany(
                """insert into job_architecture_occupation_binding
                       (corporate_entity_id, source_system_code, source_snapshot_code,
                        job_architecture_code, occupation_scheme_iri,
                        occupation_scheme_version, occupation_code, source_relation_code)
                   values ($1,$2,$3,$4,$5,$6,$7,$8)
                   on conflict (corporate_entity_id, source_system_code,
                                source_snapshot_code, job_architecture_code,
                                occupation_scheme_iri, occupation_scheme_version,
                                occupation_code)
                   do update set source_relation_code = excluded.source_relation_code
                   where job_architecture_occupation_binding.source_relation_code
                         is distinct from excluded.source_relation_code""",
                [
                    (
                        *source_snapshot_identity,
                        occupation_binding.job_architecture_code,
                        occupation_binding.occupation_scheme_iri,
                        occupation_binding.occupation_scheme_version,
                        occupation_binding.occupation_code,
                        occupation_binding.source_relation_code,
                    )
                    for occupation_binding in occupation_bindings
                ],
            )
    finally:
        await database_connection.close()
    return {
        "source_snapshot_code": command_arguments.source_snapshot_code,
        "imported_nodes": len(job_architecture_nodes),
        "imported_hierarchy_edges": len(hierarchy_edges),
        "imported_occupation_bindings": len(occupation_bindings),
        "source_sha256": source_artifact_sha256,
    }


def main() -> None:
    """Run the importer and print aggregate, non-identifying evidence."""
    command_arguments = _job_architecture_import_parser().parse_args()
    print(
        json.dumps(
            asyncio.run(import_job_architecture(command_arguments)), sort_keys=True
        )
    )


if __name__ == "__main__":
    main()
