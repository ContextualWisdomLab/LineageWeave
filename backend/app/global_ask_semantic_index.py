"""Exact ABAC-scoped Global Ask retrieval through RankWeave snapshots."""

from __future__ import annotations

import asyncio
import hashlib
from dataclasses import dataclass
from datetime import date
from typing import Any

import asyncpg

from backend.app.post_eligibility import SOURCE_POST_ELIGIBILITY_SQL
from lineageweave.rankweave_client import RankWeaveNotAvailable, _import_rankweave


@dataclass(frozen=True)
class ExactEmbeddingCandidate:
    """One owner-ranked candidate already bounded by caller ABAC."""

    post_id: str
    unit_index: int
    evidence_open_available: bool
    channel_rank: int


class GlobalAskExactSemanticIndex:
    """Own one reusable exact RankWeave snapshot for Global Ask."""

    def __init__(self) -> None:
        self._replacement_lock = asyncio.Lock()
        self._index: Any | None = None
        self._projection_version: int | None = None
        self._snapshot_version: str | None = None
        self._model_identity: str | None = None
        self._vector_dimension: int | None = None

    async def rank_authorized(
        self,
        conn: asyncpg.Connection,
        *,
        model_identity: str,
        query_vector: list[float],
        authorized_corporate_entity_ids: list[str],
        authorized_process_unit_ids: list[str],
        start_date: date | None,
        end_date: date | None,
        limit: int,
    ) -> list[ExactEmbeddingCandidate]:
        """Rank every authorized unit and reject any owner authorization leak."""
        if limit <= 0:
            return []
        vector_dimension = len(query_vector)
        async with conn.transaction(isolation="repeatable_read", readonly=True):
            projection_version = int(
                await conn.fetchval(
                    """
                        select projection_version
                          from post_content_embedding_exact_projection_state
                         where singleton
                        """
                )
            )
            snapshot_version = (
                f"lineageweave.embedding-projection.v1:{projection_version}:"
                f"{model_identity}:{vector_dimension}"
            )
            index = await self._snapshot(
                conn,
                projection_version=projection_version,
                snapshot_version=snapshot_version,
                model_identity=model_identity,
                vector_dimension=vector_dimension,
            )

            packed_authorization = bytes(
                await conn.fetchval(
                    f"""
                    select int8send(count(*)) || coalesce(
                               string_agg(
                                   int8send(octet_length(projection.post_id::text))
                                   || convert_to(projection.post_id::text, 'UTF8')
                                   || int8send(octet_length(projection.post_content_unit_id::text))
                                   || convert_to(projection.post_content_unit_id::text, 'UTF8'),
                                   ''::bytea
                                   order by projection.post_id,
                                            projection.post_content_unit_id
                               ),
                               ''::bytea
                           )
                      from post_content_embedding_exact_projection projection
                      join source_post post on post.post_id = projection.post_id
                     where projection.embedding_model_code = $1
                       and projection.embedding_dimension_count = $2
                       and (post.visibility_code = 'public'
                            or (post.corporate_entity_id::text = any($3::text[])
                                and (cardinality($4::text[]) = 0
                                     or post.process_unit_id::text = any($4::text[]))))
                       and {SOURCE_POST_ELIGIBILITY_SQL.format(alias="post")}
                       and ($5::date is null or (coalesce(post.event_occurred_at, post.created_at) at time zone 'Asia/Seoul')::date >= $5)
                       and ($6::date is null or (coalesce(post.event_occurred_at, post.created_at) at time zone 'Asia/Seoul')::date <= $6)
                    """,  # nosemgrep: python.lang.security.audit.sqli.asyncpg-sqli.asyncpg-sqli
                    model_identity,
                    vector_dimension,
                    authorized_corporate_entity_ids,
                    authorized_process_unit_ids,
                    start_date,
                    end_date,
                )
            )
            if packed_authorization == b"\x00" * 8:
                return []
            try:
                report = await asyncio.to_thread(
                    index.rank_authorized_packed,
                    model_identity,
                    query_vector,
                    packed_authorization,
                )
            except (AttributeError, TypeError, ValueError) as exc:
                raise RankWeaveNotAvailable(
                    "rankweave_not_available: exact semantic index rejected the query"
                ) from exc
            if report.snapshot.snapshot_version != snapshot_version:
                raise RankWeaveNotAvailable(
                    "rankweave_not_available: exact semantic snapshot changed during query"
                )
            owner_results = list(report.results[:limit])
            authorized_rows = await conn.fetch(
                f"""
                    select projection.post_id::text as item_id,
                           projection.post_content_unit_id::text as unit_id,
                           projection.unit_index,
                           unit.source_evidence_reference is not null
                               as evidence_open_available
                      from unnest($7::text[], $8::text[])
                           with ordinality as requested(item_id, unit_id, ordinal)
                      join post_content_embedding_exact_projection projection
                        on projection.post_id::text = requested.item_id
                       and projection.post_content_unit_id::text = requested.unit_id
                      join source_post post on post.post_id = projection.post_id
                      join post_content_unit unit
                        on unit.post_content_unit_id = projection.post_content_unit_id
                     where projection.embedding_model_code = $1
                       and projection.embedding_dimension_count = $2
                       and (post.visibility_code = 'public'
                            or (post.corporate_entity_id::text = any($3::text[])
                                and (cardinality($4::text[]) = 0
                                     or post.process_unit_id::text = any($4::text[]))))
                       and {SOURCE_POST_ELIGIBILITY_SQL.format(alias="post")}
                       and ($5::date is null or (coalesce(post.event_occurred_at, post.created_at) at time zone 'Asia/Seoul')::date >= $5)
                       and ($6::date is null or (coalesce(post.event_occurred_at, post.created_at) at time zone 'Asia/Seoul')::date <= $6)
                     order by requested.ordinal
                    """,  # nosemgrep: python.lang.security.audit.sqli.asyncpg-sqli.asyncpg-sqli
                model_identity,
                vector_dimension,
                authorized_corporate_entity_ids,
                authorized_process_unit_ids,
                start_date,
                end_date,
                [result.item_id for result in owner_results],
                [result.winning_unit_id for result in owner_results],
            )
            authorized_by_identity = {
                (str(row["item_id"]), str(row["unit_id"])): row
                for row in authorized_rows
            }
            ranked: list[ExactEmbeddingCandidate] = []
            for result in owner_results:
                identity = (result.item_id, result.winning_unit_id)
                row = authorized_by_identity.get(identity)
                if row is None:
                    raise RankWeaveNotAvailable(
                        "rankweave_not_available: exact semantic index returned an unauthorized identity"
                    )
                ranked.append(
                    ExactEmbeddingCandidate(
                        post_id=result.item_id,
                        unit_index=int(row["unit_index"]),
                        evidence_open_available=bool(row["evidence_open_available"]),
                        channel_rank=len(ranked) + 1,
                    )
                )
            return ranked

    async def _snapshot(
        self,
        conn: asyncpg.Connection,
        *,
        projection_version: int,
        snapshot_version: str,
        model_identity: str,
        vector_dimension: int,
    ) -> Any:
        """Return the matching immutable snapshot, replacing it only when stale."""
        current = self._matching_snapshot(
            snapshot_version, model_identity, vector_dimension
        )
        if current is not None:
            return current
        async with self._replacement_lock:
            current = self._matching_snapshot(
                snapshot_version, model_identity, vector_dimension
            )
            if current is not None:
                return current
            if (
                self._projection_version is not None
                and self._projection_version > projection_version
            ):
                raise RankWeaveNotAvailable(
                    "rankweave_not_available: exact semantic projection advanced during query"
                )
            replacement = await self._build_snapshot(
                conn,
                snapshot_version=snapshot_version,
                model_identity=model_identity,
                vector_dimension=vector_dimension,
            )
            self._index = replacement
            self._projection_version = projection_version
            self._snapshot_version = snapshot_version
            self._model_identity = model_identity
            self._vector_dimension = vector_dimension
            return replacement

    def _matching_snapshot(
        self,
        snapshot_version: str,
        model_identity: str,
        vector_dimension: int,
    ) -> Any | None:
        """Return the active immutable snapshot only when all evidence matches."""
        if (
            self._index is not None
            and self._snapshot_version == snapshot_version
            and self._model_identity == model_identity
            and self._vector_dimension == vector_dimension
        ):
            return self._index
        return None

    async def _build_snapshot(
        self,
        conn: asyncpg.Connection,
        *,
        snapshot_version: str,
        model_identity: str,
        vector_dimension: int,
    ) -> Any:
        """Load and validate a complete projection before activation."""
        rows = await conn.fetch(
            """
            select post_id::text as item_id,
                   post_content_unit_id::text as unit_id,
                   vector_bytes,
                   vector_sha256
              from post_content_embedding_exact_projection
             where embedding_model_code = $1
               and embedding_dimension_count = $2
             order by post_id, post_content_unit_id
            """,
            model_identity,
            vector_dimension,
        )
        if not rows:
            raise RankWeaveNotAvailable(
                "rankweave_not_available: exact semantic projection is empty"
            )
        candidate_ids: list[tuple[str, str]] = []
        vector_chunks: list[bytes] = []
        for row in rows:
            vector_bytes = bytes(row["vector_bytes"])
            if hashlib.sha256(vector_bytes).hexdigest() != str(row["vector_sha256"]):
                raise RankWeaveNotAvailable(
                    "rankweave_not_available: exact semantic projection digest mismatch"
                )
            candidate_ids.append((str(row["item_id"]), str(row["unit_id"])))
            vector_chunks.append(vector_bytes)
        packed_vectors = b"".join(vector_chunks)
        try:
            owner_type = _import_rankweave().SemanticUnitExactIndex
            replacement = await asyncio.to_thread(
                owner_type,
                snapshot_version,
                model_identity,
                vector_dimension,
                candidate_ids,
                packed_vectors,
            )
        except (AttributeError, ImportError, TypeError, ValueError) as exc:
            raise RankWeaveNotAvailable(
                "rankweave_not_available: exact semantic owner contract is unavailable"
            ) from exc
        evidence = replacement.snapshot_evidence
        if (
            evidence.snapshot_version != snapshot_version
            or evidence.vector_dimension != vector_dimension
            or evidence.candidate_count != len(candidate_ids)
        ):
            raise RankWeaveNotAvailable(
                "rankweave_not_available: exact semantic snapshot evidence mismatch"
            )
        return replacement


def build_global_ask_exact_semantic_index() -> GlobalAskExactSemanticIndex | None:
    """Activate only when the pinned RankWeave exposes the accepted contract."""
    try:
        owner_type = _import_rankweave().SemanticUnitExactIndex
    except (AttributeError, ImportError):
        return None
    if not callable(owner_type) or not callable(
        getattr(owner_type, "rank_authorized_packed", None)
    ):
        return None
    return GlobalAskExactSemanticIndex()
