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


@dataclass
class _PendingExactQuery:
    query_vector: list[float]
    scope: _AuthorizationScope
    start_date: date | None
    end_date: date | None
    limit: int
    future: asyncio.Future[list[ExactEmbeddingCandidate]]


_READINESS_MAX_SECONDS = 0.020
_GLOBAL_ASK_SOURCE_LIMIT = 4
_EMPTY_PACKED_AUTHORIZATION = b"\x00" * 8
_EMPTY_EXACT_SNAPSHOT = object()


class GlobalAskExactSemanticIndex:
    """Own one reusable exact RankWeave snapshot for Global Ask."""

    def __init__(self, pool: asyncpg.Pool | None = None) -> None:
        self._pool = pool
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
        self._pending_batches: dict[tuple[object, ...], list[_PendingExactQuery]] = {}
        self._batch_tasks: set[asyncio.Task[None]] = set()

    def _bind_pool(self, pool: asyncpg.Pool) -> None:
        if self._pool is not None and self._pool is not pool:
            raise RankWeaveNotAvailable(
                "rankweave_not_available: exact semantic pool identity changed"
            )
        self._pool = pool

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
        return (
            self._matching_snapshot(snapshot_version, model_identity, vector_dimension)
            is not None
            and self._authorization_version == authorization_version
            and all(
                prepared.projection_version == projection_version
                and prepared.authorization_version == authorization_version
                and prepared.model_identity == model_identity
                and prepared.vector_dimension == vector_dimension
                for prepared in self._prepared_authorizations.values()
            )
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
                prepared_scope = _PreparedAuthorization(
                    projection_version=projection_version,
                    authorization_version=authorization_version,
                    model_identity=model_identity,
                    vector_dimension=vector_dimension,
                    scope_digest=self._scope_digest(scope),
                    packed_digest=hashlib.sha256(packed).hexdigest(),
                    packed_authorization=packed,
                )
                if packed == _EMPTY_PACKED_AUTHORIZATION:
                    await self._validate_empty_scope(conn, prepared_scope)
                    elapsed = await self._validate_empty_scope(conn, prepared_scope)
                    if elapsed > _READINESS_MAX_SECONDS:
                        raise RankWeaveNotAvailable(
                            "rankweave_not_available: exact empty authorization preflight exceeds readiness SLO"
                        )
                else:
                    await self._preflight_scope(
                        conn,
                        index=index,
                        snapshot_version=snapshot_version,
                        model_identity=model_identity,
                        vector_dimension=vector_dimension,
                        scope=scope,
                        packed_authorization=packed,
                        projection_version=projection_version,
                        authorization_version=authorization_version,
                    )
                    elapsed = await self._preflight_scope(
                        conn,
                        index=index,
                        snapshot_version=snapshot_version,
                        model_identity=model_identity,
                        vector_dimension=vector_dimension,
                        scope=scope,
                        packed_authorization=packed,
                        projection_version=projection_version,
                        authorization_version=authorization_version,
                    )
                    if elapsed > _READINESS_MAX_SECONDS:
                        raise RankWeaveNotAvailable(
                            "rankweave_not_available: exact authorization preflight exceeds readiness SLO"
                        )
                prepared[scope] = prepared_scope
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
        scope = self._scope(
            authorized_corporate_entity_ids,
            authorized_process_unit_ids,
            process_scope_limited=process_scope_limited,
        )
        prepared = self._prepared_authorizations.get(scope)
        packed_is_empty = (
            prepared is not None
            and prepared.packed_authorization == _EMPTY_PACKED_AUTHORIZATION
        )
        if (
            prepared is None
            or prepared.model_identity != model_identity
            or (not packed_is_empty and prepared.vector_dimension != vector_dimension)
            or prepared.scope_digest != self._scope_digest(scope)
            or prepared.packed_digest
            != hashlib.sha256(prepared.packed_authorization).hexdigest()
        ):
            raise RankWeaveNotAvailable(
                "rankweave_not_available: exact authorization scope is not prepared"
            )
        snapshot_version = (
            f"lineageweave.embedding-projection.v1:{prepared.projection_version}:"
            f"{model_identity}:{prepared.vector_dimension}"
        )
        if (
            self._matching_snapshot(
                snapshot_version, model_identity, prepared.vector_dimension
            )
            is None
        ):
            raise RankWeaveNotAvailable(
                "rankweave_not_available: exact semantic snapshot is not prepared"
            )
        if packed_is_empty:
            await self._validate_empty_scope(conn, prepared)
            return []
        batch_key = (
            snapshot_version,
            prepared.projection_version,
            prepared.authorization_version,
            model_identity,
            vector_dimension,
            prepared.scope_digest,
            prepared.packed_digest,
            start_date is not None or end_date is not None,
        )
        future = asyncio.get_running_loop().create_future()
        pending = _PendingExactQuery(
            query_vector=list(query_vector),
            scope=scope,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
            future=future,
        )
        batch = self._pending_batches.setdefault(batch_key, [])
        batch.append(pending)
        if len(batch) == 1:
            task = asyncio.create_task(self._flush_batch(batch_key, prepared))
            self._batch_tasks.add(task)
            task.add_done_callback(self._batch_tasks.discard)
        return await future

    async def _flush_batch(
        self,
        batch_key: tuple[object, ...],
        prepared: _PreparedAuthorization,
    ) -> None:
        """Run one scheduler-turn batch for one immutable authorization digest."""
        await asyncio.sleep(0)
        pending = self._pending_batches.pop(batch_key, [])
        if not pending:
            return
        pool = self._pool
        if pool is None:
            error = RankWeaveNotAvailable(
                "rankweave_not_available: exact semantic postauthorization pool is unavailable"
            )
            for request in pending:
                if not request.future.done():
                    request.future.set_exception(error)
            return
        snapshot_version = str(batch_key[0])
        model_identity = str(batch_key[3])
        vector_dimension = int(batch_key[4])
        try:
            index = self._matching_snapshot(
                snapshot_version, model_identity, vector_dimension
            )
            if index is None:
                raise RankWeaveNotAvailable(
                    "rankweave_not_available: exact semantic snapshot is not prepared"
                )
            try:
                requires_full_ranking = bool(batch_key[7])
                if not requires_full_ranking:
                    reports = await asyncio.to_thread(
                        index.rank_authorized_top_k_batch_packed,
                        model_identity,
                        [request.query_vector for request in pending],
                        prepared.packed_authorization,
                        max(request.limit for request in pending),
                    )
                elif len(pending) == 1:
                    reports = [
                        await asyncio.to_thread(
                            index.rank_authorized_packed,
                            model_identity,
                            pending[0].query_vector,
                            prepared.packed_authorization,
                        )
                    ]
                else:
                    reports = await asyncio.to_thread(
                        index.rank_authorized_batch_packed,
                        model_identity,
                        [request.query_vector for request in pending],
                        prepared.packed_authorization,
                    )
            except (AttributeError, TypeError, ValueError) as exc:
                raise RankWeaveNotAvailable(
                    "rankweave_not_available: exact semantic index rejected the query"
                ) from exc
            if len(reports) != len(pending):
                raise RankWeaveNotAvailable(
                    "rankweave_not_available: exact semantic batch result mismatch"
                )
            for report in reports:
                self._validate_owner_snapshot(report, snapshot_version)
            async with pool.acquire() as conn:
                async with conn.transaction(isolation="repeatable_read", readonly=True):
                    results = await self._postauthorize_batch(
                        conn,
                        pending=pending,
                        reports=reports,
                        model_identity=model_identity,
                        vector_dimension=vector_dimension,
                        projection_version=prepared.projection_version,
                        authorization_version=prepared.authorization_version,
                    )
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            for request in pending:
                if not request.future.done():
                    request.future.set_exception(exc)
            return
        for request, result in zip(pending, results, strict=True):
            if not request.future.done():
                request.future.set_result(result)

    async def _postauthorize_batch(
        self,
        conn: asyncpg.Connection,
        *,
        pending: list[_PendingExactQuery],
        reports: list[Any],
        model_identity: str,
        vector_dimension: int,
        projection_version: int,
        authorization_version: int,
    ) -> list[list[ExactEmbeddingCandidate]]:
        """Reauthorize one immutable-scope batch in one PostgreSQL snapshot."""
        scope = pending[0].scope
        if any(request.scope != scope for request in pending):
            raise RankWeaveNotAvailable(
                "rankweave_not_available: exact semantic batch scope mismatch"
            )
        request_ids: list[int] = []
        ordinals: list[int] = []
        item_ids: list[str] = []
        unit_ids: list[str] = []
        start_dates: list[date | None] = []
        end_dates: list[date | None] = []
        for request_id, (request, report) in enumerate(
            zip(pending, reports, strict=True)
        ):
            for ordinal, result in enumerate(report.results):
                request_ids.append(request_id)
                ordinals.append(ordinal)
                item_ids.append(result.item_id)
                unit_ids.append(result.winning_unit_id)
                start_dates.append(request.start_date)
                end_dates.append(request.end_date)
        if not request_ids:
            raise RankWeaveNotAvailable(
                "rankweave_not_available: exact semantic batch result is empty"
            )
        query_args: list[object] = [
            model_identity,
            vector_dimension,
            list(scope.corporate_entity_ids),
            list(scope.process_unit_ids),
            scope.process_scope_limited,
            request_ids,
            ordinals,
            item_ids,
            unit_ids,
            start_dates,
            end_dates,
        ]
        requested_cte = """
            requested as (
                select *
                  from unnest(
                           $6::integer[], $7::bigint[], $8::text[], $9::text[],
                           $10::date[], $11::date[]
                       ) as value(
                           request_id, ordinal, item_id, unit_id,
                           start_date, end_date
                       )
            )
        """
        # The packed scope was built with SOURCE_POST_ELIGIBILITY_SQL, and every
        # source_post mutation advances authorization_version. Matching the
        # current version below therefore proves eligibility is unchanged;
        # this final check re-evaluates row identity and ABAC without repeating
        # the corpus-wide fallback probe that is already version-bound.
        rows = await conn.fetch(
            f"""
            with {requested_cte}, state as (
                select projection_state.projection_version,
                       auth_state.authorization_version
                  from post_content_embedding_exact_projection_state projection_state
                  cross join global_ask_exact_authorization_state auth_state
                 where projection_state.singleton and auth_state.singleton
            )
            select authorized.request_id,
                   authorized.ordinal,
                   authorized.item_id,
                   authorized.unit_id,
                   authorized.unit_index,
                   authorized.evidence_open_available,
                   authorized.date_eligible,
                   state.projection_version,
                   state.authorization_version
              from state
              left join lateral (
                  select requested.request_id,
                         requested.ordinal,
                         projection.post_id::text as item_id,
                         projection.post_content_unit_id::text as unit_id,
                         projection.unit_index,
                         unit.source_evidence_reference is not null
                             as evidence_open_available,
                         (requested.start_date is null
                          or (coalesce(post.event_occurred_at, post.created_at)
                              at time zone 'Asia/Seoul')::date >= requested.start_date)
                         and (requested.end_date is null
                              or (coalesce(post.event_occurred_at, post.created_at)
                                  at time zone 'Asia/Seoul')::date <= requested.end_date)
                             as date_eligible
                    from requested
                    join post_content_embedding_exact_projection projection
                      on projection.post_id = requested.item_id::uuid
                     and projection.post_content_unit_id = requested.unit_id::uuid
                    join source_post post on post.post_id = projection.post_id
                    join post_content_unit unit
                      on unit.post_content_unit_id = projection.post_content_unit_id
                   where projection.embedding_model_code = $1
                     and projection.embedding_dimension_count = $2
                     and (post.visibility_code = 'public'
                          or (post.corporate_entity_id::text = any($3::text[])
                              and (not $5::boolean
                                   or post.process_unit_id::text = any($4::text[]))))
              ) authorized on true
             order by authorized.request_id nulls first, authorized.ordinal
            """,  # nosemgrep: python.lang.security.audit.sqli.asyncpg-sqli.asyncpg-sqli
            *query_args,
        )
        if not rows:
            raise RankWeaveNotAvailable(
                "rankweave_not_available: exact authorization state is unavailable"
            )
        if (
            int(rows[0]["projection_version"]) != projection_version
            or int(rows[0]["authorization_version"]) != authorization_version
        ):
            raise RankWeaveNotAvailable(
                "rankweave_not_available: exact authorization scope is not prepared"
            )
        rows_by_request: list[list[Any]] = [[] for _ in pending]
        for row in rows:
            if row["request_id"] is None:
                continue
            request_id = int(row["request_id"])
            if request_id < 0 or request_id >= len(rows_by_request):
                raise RankWeaveNotAvailable(
                    "rankweave_not_available: exact semantic batch request mismatch"
                )
            rows_by_request[request_id].append(row)
        results: list[list[ExactEmbeddingCandidate]] = []
        for request, report, authorized_rows in zip(
            pending, reports, rows_by_request, strict=True
        ):
            owner_results = list(report.results)
            if len(authorized_rows) != len(owner_results):
                raise RankWeaveNotAvailable(
                    "rankweave_not_available: exact semantic postauthorization mismatch"
                )
            ranked: list[ExactEmbeddingCandidate] = []
            for result, row in zip(owner_results, authorized_rows, strict=True):
                if (str(row["item_id"]), str(row["unit_id"])) != (
                    result.item_id,
                    result.winning_unit_id,
                ):
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
                if len(ranked) == request.limit:
                    break
            results.append(ranked)
        return results

    @staticmethod
    async def _validate_empty_scope(
        conn: asyncpg.Connection, prepared: _PreparedAuthorization
    ) -> float:
        """Revalidate the authoritative versions for an exact empty result."""
        started = time.perf_counter()
        current_projection_version, current_authorization_version = (
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
        if (
            current_projection_version != prepared.projection_version
            or current_authorization_version != prepared.authorization_version
        ):
            raise RankWeaveNotAvailable(
                "rankweave_not_available: exact authorization scope is not prepared"
            )
        return time.perf_counter() - started

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
        projection_version: int,
        authorization_version: int,
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
                      cross join post_content_embedding_exact_projection_state projection_state
                      cross join global_ask_exact_authorization_state auth_state
                     where projection.embedding_model_code = $1
                       and projection.embedding_dimension_count = $2
                       and (post.visibility_code = 'public'
                            or (post.corporate_entity_id::text = any($3::text[])
                                and (not $5::boolean
                                     or post.process_unit_id::text = any($4::text[]))))
                       and {SOURCE_POST_ELIGIBILITY_SQL.format(alias="post")}
                       and projection_state.singleton
                       and projection_state.projection_version = $10
                       and auth_state.singleton
                       and auth_state.authorization_version = $11
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
            projection_version,
            authorization_version,
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
        projection_version: int,
        authorization_version: int,
    ) -> float:
        """Exercise real complete and top-k modes; return the slower seconds."""
        complete_started = time.perf_counter()
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
            projection_version=projection_version,
            authorization_version=authorization_version,
        )
        complete_elapsed = time.perf_counter() - complete_started

        top_k_started = time.perf_counter()
        try:
            top_k_report = await asyncio.to_thread(
                index.preflight_authorized_top_k_packed,
                model_identity,
                packed_authorization,
                _GLOBAL_ASK_SOURCE_LIMIT,
            )
        except (AttributeError, TypeError, ValueError) as exc:
            raise RankWeaveNotAvailable(
                "rankweave_not_available: exact top-k authorization preflight failed"
            ) from exc
        self._validate_owner_snapshot(top_k_report, snapshot_version)
        pending = _PendingExactQuery(
            query_vector=[],
            scope=scope,
            start_date=None,
            end_date=None,
            limit=_GLOBAL_ASK_SOURCE_LIMIT,
            future=asyncio.get_running_loop().create_future(),
        )
        await self._postauthorize_batch(
            conn,
            pending=[pending],
            reports=[top_k_report],
            model_identity=model_identity,
            vector_dimension=vector_dimension,
            projection_version=projection_version,
            authorization_version=authorization_version,
        )
        top_k_elapsed = time.perf_counter() - top_k_started
        return max(complete_elapsed, top_k_elapsed)

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
                select readers.user_account_id,
                       coalesce(
                           array_agg(
                               distinct affiliation.corporate_entity_id::text
                               order by affiliation.corporate_entity_id::text
                           ) filter (
                               where affiliation.corporate_entity_id is not null
                           ),
                           array[]::text[]
                       ) as entity_ids,
                       array[]::text[] as process_ids,
                       false as process_scope_limited
                  from readers
                  left join account_affiliation affiliation
                    on affiliation.user_account_id = readers.user_account_id
                 group by readers.user_account_id
            ), atomic_scope as (
                select affiliation.user_account_id,
                       array[affiliation.corporate_entity_id::text] as entity_ids,
                       array[affiliation.process_unit_id::text] as process_ids,
                       true as process_scope_limited
                  from account_affiliation affiliation
                  join readers on readers.user_account_id = affiliation.user_account_id
                 where affiliation.process_unit_id is not null
            ), active_job_scope as (
                select job.global_ask_job_id,
                       coalesce(
                           array(
                               select distinct captured.corporate_entity_id::text
                                 from global_ask_job_corporate_entity_scope captured
                                 join account_affiliation affiliation
                                   on affiliation.corporate_entity_id =
                                      captured.corporate_entity_id
                                  and affiliation.user_account_id =
                                      job.requesting_account_id
                                where captured.global_ask_job_id =
                                      job.global_ask_job_id
                                order by captured.corporate_entity_id::text
                           ),
                           array[]::text[]
                       ) as entity_ids,
                       coalesce(
                           array(
                               select distinct captured.process_unit_id::text
                                 from global_ask_job_process_unit_scope captured
                                 join account_affiliation affiliation
                                   on affiliation.process_unit_id =
                                      captured.process_unit_id
                                  and affiliation.user_account_id =
                                      job.requesting_account_id
                                where captured.global_ask_job_id =
                                      job.global_ask_job_id
                                order by captured.process_unit_id::text
                           ),
                           array[]::text[]
                       ) as process_ids,
                       exists (
                           select 1
                             from global_ask_job_process_unit_scope captured
                            where captured.global_ask_job_id =
                                  job.global_ask_job_id
                       ) as process_scope_limited
                  from global_ask_job job
                  join readers on readers.user_account_id =
                                  job.requesting_account_id
                 where job.job_status_code in ('queued', 'running')
            )
            select entity_ids, process_ids, process_scope_limited from local_scope
            union
            select entity_ids, process_ids, process_scope_limited from atomic_scope
            union
            select entity_ids, process_ids, process_scope_limited
              from active_job_scope
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
        if vector_dimension == 0:
            dimensions = await conn.fetch(
                """
                select distinct embedding_dimension_count
                  from post_content_embedding_exact_projection
                 where embedding_model_code = $1
                 order by embedding_dimension_count
                """,
                model_identity,
            )
            if dimensions:
                raise RankWeaveNotAvailable(
                    "rankweave_not_available: exact semantic projection changed during preparation"
                )
            return _EMPTY_EXACT_SNAPSHOT
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


def build_global_ask_exact_semantic_index(
    pool: asyncpg.Pool | None = None,
) -> GlobalAskExactSemanticIndex | None:
    """Activate only when the pinned RankWeave exposes the accepted contract."""
    from backend.app.config import load_settings

    if load_settings().rankweave_disabled:
        return None
    try:
        owner_type = _import_rankweave().SemanticUnitExactIndex
    except (AttributeError, ImportError):
        return None
    required_methods = (
        "preflight_authorized_packed",
        "preflight_authorized_top_k_packed",
        "rank_authorized_packed",
        "rank_authorized_batch_packed",
        "rank_authorized_top_k_batch_packed",
    )
    if not callable(owner_type) or any(
        not callable(getattr(owner_type, method, None)) for method in required_methods
    ):
        return None
    return GlobalAskExactSemanticIndex(pool)
