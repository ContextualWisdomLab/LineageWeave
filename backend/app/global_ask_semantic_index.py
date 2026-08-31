"""Exact ABAC-scoped Global Ask retrieval through RankWeave snapshots."""

from __future__ import annotations

import asyncio
import hashlib
import time
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


@dataclass(frozen=True)
class _AuthorizationScope:
    corporate_entity_ids: tuple[str, ...]
    process_unit_ids: tuple[str, ...]
    process_scope_limited: bool


@dataclass(frozen=True)
class _PreparedAuthorization:
    projection_version: int
    authorization_version: int
    model_identity: str
    vector_dimension: int
    scope_digest: str
    packed_digest: str
    packed_authorization: bytes


_READINESS_MAX_SECONDS = 0.020


class GlobalAskExactSemanticIndex:
    """Own one reusable exact RankWeave snapshot for Global Ask."""

    def __init__(self) -> None:
        self._replacement_lock = asyncio.Lock()
        self._index: Any | None = None
        self._projection_version: int | None = None
        self._snapshot_version: str | None = None
        self._model_identity: str | None = None
        self._vector_dimension: int | None = None
        self._authorization_version: int | None = None
        self._prepared_authorizations: dict[
            _AuthorizationScope, _PreparedAuthorization
        ] = {}

    async def is_prepared_for(
        self,
        conn: asyncpg.Connection,
        *,
        model_identity: str,
        vector_dimension: int,
    ) -> bool:
        """Return whether the active immutable snapshot matches PostgreSQL."""
        projection_version, authorization_version = (
            int(value)
            for value in await conn.fetchrow(
                """
                select projection.projection_version,
                       auth_state.authorization_version
                  from post_content_embedding_exact_projection_state projection
                  cross join global_ask_exact_authorization_state auth_state
                 where projection.singleton and auth_state.singleton
                """
            )
        )
        snapshot_version = (
            f"lineageweave.embedding-projection.v1:{projection_version}:"
            f"{model_identity}:{vector_dimension}"
        )
        return bool(self._prepared_authorizations) and (
            self._matching_snapshot(snapshot_version, model_identity, vector_dimension)
            is not None
            and self._authorization_version == authorization_version
        )

    async def prepare(
        self,
        conn: asyncpg.Connection,
        *,
        model_identity: str,
        vector_dimension: int,
    ) -> None:
        """Build and atomically activate the current complete snapshot."""
        async with conn.transaction(isolation="repeatable_read", readonly=True):
            projection_version, authorization_version = (
                int(value)
                for value in await conn.fetchrow(
                    """
                    select projection.projection_version,
                           auth_state.authorization_version
                      from post_content_embedding_exact_projection_state projection
                      cross join global_ask_exact_authorization_state auth_state
                     where projection.singleton and auth_state.singleton
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
            scopes = await self._active_authorization_scopes(conn)
            if (
                self._authorization_version == authorization_version
                and set(self._prepared_authorizations) == set(scopes)
                and all(
                    prepared.projection_version == projection_version
                    and prepared.model_identity == model_identity
                    and prepared.vector_dimension == vector_dimension
                    for prepared in self._prepared_authorizations.values()
                )
            ):
                return
            prepared: dict[_AuthorizationScope, _PreparedAuthorization] = {}
            for scope in scopes:
                packed = await self._pack_authorization_scope(
                    conn,
                    model_identity=model_identity,
                    vector_dimension=vector_dimension,
                    scope=scope,
                )
                if packed == b"\x00" * 8:
                    raise RankWeaveNotAvailable(
                        "rankweave_not_available: configured authorization scope is empty"
                    )
                prepared_scope = _PreparedAuthorization(
                    projection_version=projection_version,
                    authorization_version=authorization_version,
                    model_identity=model_identity,
                    vector_dimension=vector_dimension,
                    scope_digest=self._scope_digest(scope),
                    packed_digest=hashlib.sha256(packed).hexdigest(),
                    packed_authorization=packed,
                )
                await self._preflight_scope(
                    conn,
                    index=index,
                    snapshot_version=snapshot_version,
                    model_identity=model_identity,
                    vector_dimension=vector_dimension,
                    scope=scope,
                    packed_authorization=packed,
                )
                elapsed = await self._preflight_scope(
                    conn,
                    index=index,
                    snapshot_version=snapshot_version,
                    model_identity=model_identity,
                    vector_dimension=vector_dimension,
                    scope=scope,
                    packed_authorization=packed,
                )
                if elapsed > _READINESS_MAX_SECONDS:
                    raise RankWeaveNotAvailable(
                        "rankweave_not_available: exact authorization preflight exceeds readiness SLO"
                    )
                prepared[scope] = prepared_scope
            if not prepared:
                raise RankWeaveNotAvailable(
                    "rankweave_not_available: no configured authorization scope"
                )
            self._prepared_authorizations = prepared
            self._authorization_version = authorization_version

    async def rank_authorized(
        self,
        conn: asyncpg.Connection,
        *,
        model_identity: str,
        query_vector: list[float],
        authorized_corporate_entity_ids: list[str],
        authorized_process_unit_ids: list[str],
        process_scope_limited: bool = False,
        start_date: date | None,
        end_date: date | None,
        limit: int,
    ) -> list[ExactEmbeddingCandidate]:
        """Rank every authorized unit and reject any owner authorization leak."""
        if limit <= 0:
            return []
        vector_dimension = len(query_vector)
        async with conn.transaction(isolation="repeatable_read", readonly=True):
            projection_version, authorization_version = (
                int(value)
                for value in await conn.fetchrow(
                    """
                    select projection.projection_version,
                           auth_state.authorization_version
                      from post_content_embedding_exact_projection_state projection
                      cross join global_ask_exact_authorization_state auth_state
                     where projection.singleton and auth_state.singleton
                    """
                )
            )
            snapshot_version = (
                f"lineageweave.embedding-projection.v1:{projection_version}:"
                f"{model_identity}:{vector_dimension}"
            )
            index = self._matching_snapshot(
                snapshot_version, model_identity, vector_dimension
            )
            if index is None:
                raise RankWeaveNotAvailable(
                    "rankweave_not_available: exact semantic snapshot is not prepared"
                )

            scope = self._scope(
                authorized_corporate_entity_ids,
                authorized_process_unit_ids,
                process_scope_limited=process_scope_limited,
            )
            prepared = self._prepared_authorizations.get(scope)
            if (
                prepared is None
                or prepared.projection_version != projection_version
                or prepared.authorization_version != authorization_version
                or prepared.model_identity != model_identity
                or prepared.vector_dimension != vector_dimension
                or prepared.scope_digest != self._scope_digest(scope)
                or prepared.packed_digest
                != hashlib.sha256(prepared.packed_authorization).hexdigest()
            ):
                raise RankWeaveNotAvailable(
                    "rankweave_not_available: exact authorization scope is not prepared"
                )
            try:
                report = await asyncio.to_thread(
                    index.rank_authorized_packed,
                    model_identity,
                    query_vector,
                    prepared.packed_authorization,
                )
            except (AttributeError, TypeError, ValueError) as exc:
                raise RankWeaveNotAvailable(
                    "rankweave_not_available: exact semantic index rejected the query"
                ) from exc
            self._validate_owner_snapshot(report, snapshot_version)
            return await self._postauthorize_results(
                conn,
                owner_results=list(report.results),
                model_identity=model_identity,
                vector_dimension=vector_dimension,
                scope=scope,
                start_date=start_date,
                end_date=end_date,
                limit=limit,
            )

    async def _postauthorize_results(
        self,
        conn: asyncpg.Connection,
        *,
        owner_results: list[Any],
        model_identity: str,
        vector_dimension: int,
        scope: _AuthorizationScope,
        start_date: date | None,
        end_date: date | None,
        limit: int,
    ) -> list[ExactEmbeddingCandidate]:
        """Reauthorize exact owner output against current PostgreSQL state."""
        authorized_rows = await conn.fetch(
            f"""
                    select projection.post_id::text as item_id,
                           projection.post_content_unit_id::text as unit_id,
                           projection.unit_index,
                           unit.source_evidence_reference is not null
                               as evidence_open_available,
                           ($6::date is null or (coalesce(post.event_occurred_at, post.created_at) at time zone 'Asia/Seoul')::date >= $6)
                           and ($7::date is null or (coalesce(post.event_occurred_at, post.created_at) at time zone 'Asia/Seoul')::date <= $7)
                               as date_eligible
                      from unnest($8::text[], $9::text[])
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
                                and (not $5::boolean
                                     or post.process_unit_id::text = any($4::text[]))))
                       and {SOURCE_POST_ELIGIBILITY_SQL.format(alias="post")}
                     order by requested.ordinal
                    """,  # nosemgrep: python.lang.security.audit.sqli.asyncpg-sqli.asyncpg-sqli
            model_identity,
            vector_dimension,
            list(scope.corporate_entity_ids),
            list(scope.process_unit_ids),
            scope.process_scope_limited,
            start_date,
            end_date,
            [result.item_id for result in owner_results],
            [result.winning_unit_id for result in owner_results],
        )
        authorized_by_identity = {
            (str(row["item_id"]), str(row["unit_id"])): row for row in authorized_rows
        }
        ranked: list[ExactEmbeddingCandidate] = []
        for result in owner_results:
            identity = (result.item_id, result.winning_unit_id)
            row = authorized_by_identity.get(identity)
            if row is None:
                raise RankWeaveNotAvailable(
                    "rankweave_not_available: exact semantic index returned an unauthorized identity"
                )
            if not bool(row["date_eligible"]):
                continue
            ranked.append(
                ExactEmbeddingCandidate(
                    post_id=result.item_id,
                    unit_index=int(row["unit_index"]),
                    evidence_open_available=bool(row["evidence_open_available"]),
                    channel_rank=len(ranked) + 1,
                )
            )
            if len(ranked) == limit:
                break
        if len(authorized_rows) != len(owner_results):
            raise RankWeaveNotAvailable(
                "rankweave_not_available: exact semantic postauthorization mismatch"
            )
        return ranked

    async def _preflight_scope(
        self,
        conn: asyncpg.Connection,
        *,
        index: Any,
        snapshot_version: str,
        model_identity: str,
        vector_dimension: int,
        scope: _AuthorizationScope,
        packed_authorization: bytes,
    ) -> float:
        """Exercise one real scope and return owner-plus-postauth seconds."""
        started = time.perf_counter()
        try:
            report = await asyncio.to_thread(
                index.preflight_authorized_packed,
                model_identity,
                packed_authorization,
            )
        except (AttributeError, TypeError, ValueError) as exc:
            raise RankWeaveNotAvailable(
                "rankweave_not_available: exact authorization preflight failed"
            ) from exc
        self._validate_owner_snapshot(report, snapshot_version)
        await self._postauthorize_results(
            conn,
            owner_results=list(report.results),
            model_identity=model_identity,
            vector_dimension=vector_dimension,
            scope=scope,
            start_date=None,
            end_date=None,
            limit=len(report.results),
        )
        return time.perf_counter() - started

    @staticmethod
    def _scope(
        corporate_entity_ids: list[str],
        process_unit_ids: list[str],
        *,
        process_scope_limited: bool,
    ) -> _AuthorizationScope:
        """Canonicalize one caller-declared authorization scope."""
        return _AuthorizationScope(
            corporate_entity_ids=tuple(sorted(set(corporate_entity_ids))),
            process_unit_ids=(
                tuple(sorted(set(process_unit_ids))) if process_scope_limited else ()
            ),
            process_scope_limited=process_scope_limited,
        )

    @staticmethod
    def _scope_digest(scope: _AuthorizationScope) -> str:
        """Bind the exact ordered authorization-scope declaration."""
        digest = hashlib.sha256(b"lineageweave.global-ask.authorization-scope.v1\0")
        digest.update(b"\x01" if scope.process_scope_limited else b"\x00")
        for values in (scope.corporate_entity_ids, scope.process_unit_ids):
            digest.update(len(values).to_bytes(8, "big"))
            for value in values:
                encoded = value.encode()
                digest.update(len(encoded).to_bytes(8, "big"))
                digest.update(encoded)
        return digest.hexdigest()

    @staticmethod
    def _validate_owner_snapshot(report: Any, snapshot_version: str) -> None:
        """Reject an owner report from any other immutable snapshot."""
        if report.snapshot.snapshot_version != snapshot_version:
            raise RankWeaveNotAvailable(
                "rankweave_not_available: exact semantic snapshot changed during query"
            )

    async def _active_authorization_scopes(
        self, conn: asyncpg.Connection
    ) -> tuple[_AuthorizationScope, ...]:
        """Load every local and atomic scope declared by active readers."""
        rows = await conn.fetch(
            """
            with readers as (
                select distinct assignment.user_account_id
                  from account_role_assignment assignment
                  join role_permission permission
                    on permission.access_role_id = assignment.access_role_id
                 where permission.permission_code = 'post_read'
            ), local_scope as (
                select affiliation.user_account_id,
                       array_agg(distinct affiliation.corporate_entity_id::text
                                 order by affiliation.corporate_entity_id::text) as entity_ids,
                       array[]::text[] as process_ids,
                       false as process_scope_limited
                  from account_affiliation affiliation
                  join readers on readers.user_account_id = affiliation.user_account_id
                 group by affiliation.user_account_id
            ), atomic_scope as (
                select affiliation.user_account_id,
                       array[affiliation.corporate_entity_id::text] as entity_ids,
                       array[affiliation.process_unit_id::text] as process_ids,
                       true as process_scope_limited
                  from account_affiliation affiliation
                  join readers on readers.user_account_id = affiliation.user_account_id
                 where affiliation.process_unit_id is not null
            )
            select entity_ids, process_ids, process_scope_limited from local_scope
            union
            select entity_ids, process_ids, process_scope_limited from atomic_scope
            order by process_scope_limited, entity_ids, process_ids
            """
        )
        return tuple(
            dict.fromkeys(
                self._scope(
                    [str(value) for value in row["entity_ids"]],
                    [str(value) for value in row["process_ids"]],
                    process_scope_limited=bool(row["process_scope_limited"]),
                )
                for row in rows
            )
        )

    async def _pack_authorization_scope(
        self,
        conn: asyncpg.Connection,
        *,
        model_identity: str,
        vector_dimension: int,
        scope: _AuthorizationScope,
    ) -> bytes:
        """Build one canonical packed ABAC snapshot in PostgreSQL."""
        return bytes(
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
                            and (not $5::boolean
                                 or post.process_unit_id::text = any($4::text[]))))
                   and {SOURCE_POST_ELIGIBILITY_SQL.format(alias="post")}
                """,  # nosemgrep: python.lang.security.audit.sqli.asyncpg-sqli.asyncpg-sqli
                model_identity,
                vector_dimension,
                list(scope.corporate_entity_ids),
                list(scope.process_unit_ids),
                scope.process_scope_limited,
            )
        )

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
