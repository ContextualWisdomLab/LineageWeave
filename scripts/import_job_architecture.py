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

_FIELDS = {
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
_KINDS = {"job_family", "job_series"}
_SOURCE_CODE = re.compile(r"^[a-z][a-z0-9_]{0,62}$")
_SHA256 = re.compile(r"^[0-9a-fA-F]{64}$")


@dataclass(frozen=True)
class JobArchitectureNode:
    """One exact node from an authorized source snapshot."""

    code: str
    kind: str
    name: str
    description: str | None
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

    node_code: str
    scheme_iri: str
    scheme_version: str
    occupation_code: str
    source_relation_code: str


def _optional_date(value: str, field: str) -> date | None:
    """Parse an optional ISO date without inventing a missing instant."""
    text = value.strip()
    if not text:
        return None
    try:
        return date.fromisoformat(text)
    except ValueError as exc:
        raise ValueError(f"invalid {field}: {value!r}") from exc


def _https_url(value: str, field: str) -> str:
    """Validate an HTTPS URL with no embedded credentials."""
    parsed = urlsplit(value)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
    ):
        raise ValueError(f"{field} must be an HTTPS URL without userinfo")
    return value


def read_job_architecture(
    path: Path,
) -> tuple[
    list[JobArchitectureNode],
    list[JobArchitectureEdge],
    list[OccupationBinding],
    int,
]:
    """Return exact nodes, hierarchy edges, and explicit occupation bindings."""
    nodes: dict[str, JobArchitectureNode] = {}
    edges: set[JobArchitectureEdge] = set()
    bindings: set[OccupationBinding] = set()
    row_count = 0
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        missing = sorted(_FIELDS - set(reader.fieldnames or ()))
        if missing:
            raise ValueError(f"missing CSV columns: {', '.join(missing)}")
        for line_number, row in enumerate(reader, start=2):
            row_count += 1
            if None in row or any(value is None for value in row.values()):
                raise ValueError(f"malformed CSV row: {line_number}")
            code = row["Node Code"].strip()
            kind = row["Node Kind"].strip()
            name = row["Node Name"].strip()
            if not code or not name or kind not in _KINDS:
                raise ValueError(f"invalid node identity at row {line_number}")
            valid_from = _optional_date(row["Valid From"], "valid from")
            valid_to = _optional_date(row["Valid To"], "valid to")
            if valid_from and valid_to and valid_from > valid_to:
                raise ValueError(f"inverted validity interval at row {line_number}")
            node = JobArchitectureNode(
                code,
                kind,
                name,
                row.get("Description", "").strip() or None,
                valid_from,
                valid_to,
            )
            if code in nodes and nodes[code] != node:
                raise ValueError(f"conflicting node identity: {code}")
            nodes[code] = node
            parent = row["Parent Code"].strip()
            hierarchy_relation = row["Hierarchy Relation"].strip()
            if parent:
                if not hierarchy_relation:
                    raise ValueError(f"missing hierarchy relation at row {line_number}")
                edges.add(JobArchitectureEdge(parent, code, hierarchy_relation))
            scheme = row["Occupation Scheme IRI"].strip()
            version = row["Occupation Scheme Version"].strip()
            occupation = row["Occupation Code"].strip()
            occupation_relation = row["Occupation Relation"].strip()
            supplied = (bool(scheme), bool(version), bool(occupation))
            if any(supplied) and not all(supplied):
                raise ValueError(f"partial occupation binding at row {line_number}")
            if all(supplied):
                parsed = urlsplit(scheme)
                if (
                    parsed.scheme not in {"http", "https"}
                    or not parsed.hostname
                    or parsed.username is not None
                    or parsed.password is not None
                ):
                    raise ValueError(f"invalid occupation scheme IRI at row {line_number}")
                if not occupation_relation:
                    raise ValueError(f"missing binding relation at row {line_number}")
                bindings.add(
                    OccupationBinding(
                        code,
                        scheme,
                        version,
                        occupation,
                        occupation_relation,
                    )
                )
    if not nodes:
        raise ValueError("job architecture file has no rows")
    for edge in edges:
        if edge.broader_code not in nodes:
            raise ValueError(f"unknown parent node: {edge.broader_code}")
        if edge.broader_code == edge.narrower_code:
            raise ValueError(f"self hierarchy edge: {edge.broader_code}")
    children: dict[str, set[str]] = {code: set() for code in nodes}
    for edge in edges:
        children[edge.broader_code].add(edge.narrower_code)
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(code: str) -> None:
        if code in visiting:
            raise ValueError(f"cyclic job architecture hierarchy: {code}")
        if code in visited:
            return
        visiting.add(code)
        for child in children[code]:
            visit(child)
        visiting.remove(code)
        visited.add(code)

    for code in nodes:
        visit(code)
    return (
        list(nodes.values()),
        sorted(edges, key=repr),
        sorted(bindings, key=repr),
        row_count,
    )


def _parser() -> argparse.ArgumentParser:
    """Build the explicit source-snapshot import contract."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target-dsn", required=True)
    parser.add_argument("--corporate-entity-code", required=True)
    parser.add_argument("--source-system-code", required=True)
    parser.add_argument("--source-snapshot-code", required=True)
    parser.add_argument("--source-name", required=True)
    parser.add_argument("--source-url", required=True)
    parser.add_argument("--source-sha256", required=True)
    parser.add_argument("--source-row-count", type=int, required=True)
    parser.add_argument("--source-file", type=Path, required=True)
    return parser


async def import_job_architecture(args: argparse.Namespace) -> dict[str, object]:
    """Validate one pinned snapshot before transactionally persisting it."""
    if not _SOURCE_CODE.fullmatch(args.source_system_code):
        raise ValueError("source system code must be lower snake case")
    for field in ("corporate_entity_code", "source_snapshot_code", "source_name"):
        if not str(getattr(args, field)).strip():
            raise ValueError(f"{field} must not be blank")
    _https_url(args.source_url, "source URL")
    if not _SHA256.fullmatch(args.source_sha256):
        raise ValueError("source SHA-256 must be one digest")
    if args.source_row_count <= 0 or not args.source_file.is_file():
        raise ValueError("source row count and file must be valid")
    digest = hashlib.sha256(args.source_file.read_bytes()).hexdigest()
    if digest != args.source_sha256.lower():
        raise ValueError("source artifact SHA-256 mismatch")
    nodes, edges, bindings, row_count = read_job_architecture(args.source_file)
    if row_count != args.source_row_count:
        raise ValueError("source artifact row-count mismatch")
    conn = await asyncpg.connect(args.target_dsn)
    try:
        async with conn.transaction():
            entity_id = await conn.fetchval(
                "select corporate_entity_id from corporate_entity where corporate_entity_code = $1",
                args.corporate_entity_code,
            )
            if entity_id is None:
                raise ValueError("corporate entity must already exist")
            key = (entity_id, args.source_system_code, args.source_snapshot_code)
            await conn.execute(
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
                *key,
                args.source_name,
                args.source_url,
                digest,
                row_count,
            )
            await conn.executemany(
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
                [(*key, n.code, n.kind, n.name, n.description, n.valid_from, n.valid_to) for n in nodes],
            )
            await conn.executemany(
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
                [(*key, e.broader_code, e.narrower_code, e.source_relation_code) for e in edges],
            )
            await conn.executemany(
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
                [(*key, b.node_code, b.scheme_iri, b.scheme_version, b.occupation_code, b.source_relation_code) for b in bindings],
            )
    finally:
        await conn.close()
    return {
        "source_snapshot_code": args.source_snapshot_code,
        "imported_nodes": len(nodes),
        "imported_hierarchy_edges": len(edges),
        "imported_occupation_bindings": len(bindings),
        "source_sha256": digest,
    }


def main() -> None:
    """Run the importer and print aggregate, non-identifying evidence."""
    print(json.dumps(asyncio.run(import_job_architecture(_parser().parse_args())), sort_keys=True))


if __name__ == "__main__":
    main()
