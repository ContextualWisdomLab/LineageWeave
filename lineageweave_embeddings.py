"""Bounded semantic-unit embeddings for the direct-PostgreSQL product.

This module keeps HTML, data URIs, and inline bytes out of model input.  It
embeds only the DOM-sized text units already materialized by ``lineageweave``
and persists vectors as an evidence-linked index rather than as graph truth.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import urllib.error
import urllib.request
from typing import Any, Callable, Dict, Iterable, List, Sequence

import psycopg
from psycopg.types.json import Json

import lineageweave as lw


MAX_EMBEDDING_CHUNK_CHARS = 4_096
MAX_EMBEDDING_CHUNKS_PER_DOCUMENT = 32
MAX_SEMANTIC_NEIGHBORS = 24
# ponytail: bounded in-process ranking; move candidate ranking into pgvector when this cap becomes material.
MAX_SEMANTIC_CANDIDATE_ROWS = 10_000
# ponytail: bounded multilingual floor; replace with per-model calibration after a larger labeled set exists.
MIN_SEMANTIC_RELATEDNESS = 0.40
ANALYSIS_EMBEDDING_MODEL_TABLE = "analysis_embedding_model_catalog"
ANALYSIS_CONTENT_EMBEDDING_TABLE = "analysis_content_chunk_embeddings"


def _normalized_text(value: Any) -> str:
    """Return one whitespace-normalized semantic unit without markup bytes."""
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _split_text(text: str, maximum_chars: int) -> List[str]:
    """Split a DOM unit at a sentence or word boundary when it exceeds a cap."""
    normalized = _normalized_text(text)
    if not normalized:
        return []
    if maximum_chars < 1:
        raise ValueError("embedding chunk size must be positive")
    chunks: List[str] = []
    remaining = normalized
    while len(remaining) > maximum_chars:
        window = remaining[: maximum_chars + 1]
        candidates = [window.rfind(mark) + 1 for mark in (". ", "! ", "? ", "。", "！", "？")]
        cut = min(max(candidates), maximum_chars)
        if cut < maximum_chars // 2:
            cut = window.rfind(" ")
        if cut < 1:
            cut = maximum_chars
        chunks.append(remaining[:cut].strip())
        remaining = remaining[cut:].strip()
    chunks.append(remaining)
    return chunks


def build_embedding_chunks(
    document_no: str,
    content_structure: Dict[str, List[Dict[str, Any]]],
    *,
    maximum_chars: int = MAX_EMBEDDING_CHUNK_CHARS,
    maximum_chunks: int = MAX_EMBEDDING_CHUNKS_PER_DOCUMENT,
) -> List[Dict[str, Any]]:
    """Create stable, source-linked text chunks from persisted-safe DOM blocks."""
    document = str(document_no or "").strip()
    if not document:
        raise ValueError("embedding chunks require a document number")
    if maximum_chunks < 1:
        raise ValueError("embedding chunk count must be positive")
    chunks: List[Dict[str, Any]] = []
    for fallback_index, block in enumerate(content_structure.get("blocks") or []):
        if not isinstance(block, dict):
            continue
        try:
            block_index = int(block.get("block_index", fallback_index))
        except (TypeError, ValueError):
            block_index = fallback_index
        source_evidence_id = str(block.get("source_evidence_id") or "").strip()
        if not source_evidence_id:
            continue
        try:
            source_position = int(block.get("source_position") or 0)
        except (TypeError, ValueError):
            source_position = 0
        for chunk_index, chunk_text in enumerate(_split_text(block.get("text_content"), maximum_chars)):
            digest = hashlib.sha256(chunk_text.encode("utf-8")).hexdigest()
            chunks.append(
                {
                    "chunk_id": f"emb-{document}-{block_index}-{chunk_index}-{digest[:12]}",
                    "document_no": document,
                    "block_index": block_index,
                    "chunk_index": chunk_index,
                    "source_evidence_id": source_evidence_id,
                    "source_position": source_position,
                    "chunk_text": chunk_text,
                    "chunk_sha256": digest,
                }
            )
            if len(chunks) >= maximum_chunks:
                return chunks
    return chunks


def _vector_values(value: Any) -> List[float]:
    """Validate one finite, non-empty embedding vector before persistence."""
    raw = json.loads(value) if isinstance(value, str) else value
    if not isinstance(raw, list) or not raw:
        raise ValueError("embedding vector is missing")
    try:
        vector = [float(item) for item in raw]
    except (TypeError, ValueError) as exc:
        raise ValueError("embedding vector is non-numeric") from exc
    if not all(math.isfinite(item) for item in vector):
        raise ValueError("embedding vector is non-finite")
    return vector


def _embedding_response(payload: Dict[str, Any], expected_count: int, fallback_model: str) -> Dict[str, Any]:
    """Normalize an OpenAI-compatible embedding response in request order."""
    data = payload.get("data") or []
    if not isinstance(data, list) or not data:
        raise RuntimeError("embedding_response_count_mismatch")
    if any(not isinstance(item, dict) for item in data):
        raise RuntimeError("embedding_response_item_invalid")
    if len(data) != expected_count:
        raise RuntimeError("embedding_response_count_mismatch")
    vectors: List[List[float] | None] = [None] * expected_count
    for position, item in enumerate(data):
        try:
            index = int(item.get("index", position))
        except (TypeError, ValueError) as exc:
            raise RuntimeError("embedding_response_index_invalid") from exc
        if index < 0 or index >= expected_count or vectors[index] is not None:
            raise RuntimeError("embedding_response_index_invalid")
        vectors[index] = _vector_values(item.get("embedding"))
    complete = [vector for vector in vectors if vector is not None]
    if len(complete) != expected_count or len({len(vector) for vector in complete}) != 1:
        raise RuntimeError("embedding_response_dimensions_invalid")
    return {
        "model_name": str(payload.get("model") or fallback_model),
        "provider_kind": "live_gateway",
        "vector_dimensions": len(complete[0]),
        "vectors": complete,
    }


def _discover_embedding_model(base_url: str, token: str) -> str:
    """Choose a configured gateway embedding model without logging model inventory."""
    request = urllib.request.Request(
        base_url.rstrip("/") + "/v1/models",
        headers={"authorization": f"Bearer {token}"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(
            request,
            timeout=15,
            context=lw.verified_gateway_ssl_context(),
        ) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError) as exc:
        raise RuntimeError("embedding_model_discovery_unavailable") from exc
    candidates = sorted(
        {
            str(item.get("id") or "").strip()
            for item in (payload.get("data") or [])
            if isinstance(item, dict) and "embed" in str(item.get("id") or "").casefold()
        }
    )
    if not candidates:
        raise RuntimeError("embedding_model_unavailable")
    return candidates[0]


def post_live_embeddings(
    inputs: Sequence[str],
    *,
    base_url: str,
    token: str,
    model_name: str,
    timeout: int,
) -> Dict[str, Any]:
    """Call one verified live embedding endpoint with bounded DOM-unit text."""
    values = [_normalized_text(item) for item in inputs]
    if not values or any(not item for item in values):
        raise ValueError("embedding inputs are required")
    if any(len(item) > MAX_EMBEDDING_CHUNK_CHARS for item in values):
        raise ValueError("embedding input exceeds the semantic chunk limit")
    request = urllib.request.Request(
        base_url.rstrip("/") + "/v1/embeddings",
        data=json.dumps({"model": model_name, "input": values}, ensure_ascii=False).encode("utf-8"),
        headers={"authorization": f"Bearer {token}", "content-type": "application/json"},
        method="POST",
    )
    try:
        payload = lw._post_json_from_request(
            request,
            timeout=timeout,
            context=lw.verified_gateway_ssl_context(),
        )
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"embedding_gateway_http_{exc.code}") from exc
    except (urllib.error.URLError, json.JSONDecodeError) as exc:
        raise RuntimeError("embedding_gateway_unavailable") from exc
    if not isinstance(payload, dict):
        raise RuntimeError("embedding_response_invalid")
    return _embedding_response(payload, len(values), model_name)


def make_live_embedding_transport() -> Callable[[Sequence[str]], Dict[str, Any]]:
    """Build the direct, verified HTTPS embedding transport from runtime config."""
    base_url, token, _chat_model = lw.live_http_config()
    model_name = str(os.environ.get("LINEAGEWEAVE_EMBEDDING_MODEL") or "").strip()
    if not model_name:
        model_name = _discover_embedding_model(base_url, token)
    timeout = lw.resolve_llm_timeout("LINEAGEWEAVE_EMBEDDING_TIMEOUT", default=60, maximum=180)

    def transport(inputs: Sequence[str]) -> Dict[str, Any]:
        """Embed one bounded sequence of semantic chunks through the selected gateway."""
        return post_live_embeddings(
            inputs,
            base_url=base_url,
            token=token,
            model_name=model_name,
            timeout=timeout,
        )

    transport.__name__ = "live_embedding_http_transport"
    return transport


def derive_document_embeddings(
    chunks: Sequence[Dict[str, Any]],
    *,
    transport: Callable[[Sequence[str]], Dict[str, Any]],
) -> Dict[str, Any]:
    """Attach verified vector values to safe chunks without exposing source text later."""
    rows = [dict(chunk) for chunk in chunks]
    if not rows:
        return {"model_name": "", "provider_kind": "unavailable", "vector_dimensions": 0, "rows": []}
    response = transport([str(row.get("chunk_text") or "") for row in rows])
    vectors = response.get("vectors") if isinstance(response, dict) else None
    if not isinstance(vectors, list) or len(vectors) != len(rows):
        raise RuntimeError("embedding_response_count_mismatch")
    dimensions = int(response.get("vector_dimensions") or 0)
    if dimensions < 1:
        raise RuntimeError("embedding_response_dimensions_invalid")
    for row, raw_vector in zip(rows, vectors):
        vector = _vector_values(raw_vector)
        if len(vector) != dimensions:
            raise RuntimeError("embedding_response_dimensions_invalid")
        row["vector_values"] = vector
        row.pop("chunk_text", None)
    model_name = str(response.get("model_name") or "").strip()
    if not model_name:
        raise RuntimeError("embedding_model_missing")
    for row in rows:
        row["model_name"] = model_name
    return {
        "model_name": model_name,
        "provider_kind": str(response.get("provider_kind") or "live_gateway"),
        "vector_dimensions": dimensions,
        "rows": rows,
    }


def ensure_embedding_tables(connection: psycopg.Connection) -> None:
    """Create normalized model catalog and DOM-chunk embedding tables."""
    for table_name in (ANALYSIS_EMBEDDING_MODEL_TABLE, ANALYSIS_CONTENT_EMBEDDING_TABLE):
        lw.assert_common_table_name(table_name)
    lw.ensure_content_structure_tables(connection)
    lw._database_exec(
        connection,
        f"""
        CREATE TABLE IF NOT EXISTS {ANALYSIS_EMBEDDING_MODEL_TABLE} (
            model_name text PRIMARY KEY,
            provider_kind text NOT NULL,
            vector_dimensions integer NOT NULL CHECK (vector_dimensions > 0),
            created_at timestamptz NOT NULL DEFAULT now()
        )
        """,
    )
    lw._database_exec(
        connection,
        f"""
        CREATE TABLE IF NOT EXISTS {ANALYSIS_CONTENT_EMBEDDING_TABLE} (
            document_no text NOT NULL,
            block_index integer NOT NULL CHECK (block_index >= 0),
            chunk_index integer NOT NULL CHECK (chunk_index >= 0),
            model_name text NOT NULL REFERENCES {ANALYSIS_EMBEDDING_MODEL_TABLE} (model_name),
            chunk_sha256 text NOT NULL,
            vector_values jsonb NOT NULL,
            created_at timestamptz NOT NULL DEFAULT now(),
            PRIMARY KEY (document_no, block_index, chunk_index, model_name),
            FOREIGN KEY (document_no, block_index)
                REFERENCES {lw.ANALYSIS_CONTENT_BLOCK_TABLE} (document_no, block_index)
                ON DELETE CASCADE
        )
        """,
    )


def persist_document_embeddings(
    connection: psycopg.Connection,
    document_no: str,
    embedding_result: Dict[str, Any],
) -> int:
    """Replace one document/model index after the corresponding DOM blocks exist."""
    document = str(document_no or "").strip()
    rows = list(embedding_result.get("rows") or [])
    if not document or not rows:
        return 0
    model_name = str(embedding_result.get("model_name") or "").strip()
    dimensions = int(embedding_result.get("vector_dimensions") or 0)
    if not model_name or dimensions < 1:
        raise ValueError("embedding model metadata is required")
    ensure_embedding_tables(connection)
    lw._database_exec(
        connection,
        f"""
        INSERT INTO {ANALYSIS_EMBEDDING_MODEL_TABLE} (model_name, provider_kind, vector_dimensions)
        VALUES (%s, %s, %s)
        ON CONFLICT (model_name) DO UPDATE SET
            provider_kind = EXCLUDED.provider_kind,
            vector_dimensions = EXCLUDED.vector_dimensions
        """,
        (model_name, str(embedding_result.get("provider_kind") or "live_gateway"), dimensions),
    )
    lw._database_exec(
        connection,
        f"DELETE FROM {ANALYSIS_CONTENT_EMBEDDING_TABLE} WHERE document_no = %s AND model_name = %s",
        (document, model_name),
    )
    with connection.cursor() as cursor:
        cursor.executemany(
            f"""
            INSERT INTO {ANALYSIS_CONTENT_EMBEDDING_TABLE}
                (document_no, block_index, chunk_index, model_name, chunk_sha256, vector_values)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            [
                (
                    document,
                    int(row["block_index"]),
                    int(row["chunk_index"]),
                    model_name,
                    str(row["chunk_sha256"]),
                    Json(_vector_values(row.get("vector_values"))),
                )
                for row in rows
            ],
        )
    return len(rows)


def _embedding_rows(rows: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Drop malformed persisted vectors instead of treating them as semantic evidence."""
    parsed: List[Dict[str, Any]] = []
    for row in rows:
        try:
            vector = _vector_values(row.get("vector_values"))
        except ValueError:
            continue
        item = dict(row)
        item["vector_values"] = vector
        parsed.append(item)
    return parsed


def load_document_embeddings(connection: psycopg.Connection, document_no: str) -> List[Dict[str, Any]]:
    """Load all valid vectors for one document, retaining source-evidence linkage."""
    if not (
        lw._database_table_exists(connection, ANALYSIS_CONTENT_EMBEDDING_TABLE)
        and lw._database_table_exists(connection, lw.ANALYSIS_CONTENT_BLOCK_TABLE)
    ):
        return []
    rows = lw._database_query(
        connection,
        f"""
        SELECT embedding.document_no, embedding.block_index, embedding.chunk_index,
               embedding.model_name, embedding.chunk_sha256, embedding.vector_values,
               block.source_evidence_id, block.source_position
        FROM {ANALYSIS_CONTENT_EMBEDDING_TABLE} AS embedding
        JOIN {lw.ANALYSIS_CONTENT_BLOCK_TABLE} AS block
          ON block.document_no = embedding.document_no
         AND block.block_index = embedding.block_index
        WHERE embedding.document_no = %s
        ORDER BY embedding.created_at DESC, embedding.block_index, embedding.chunk_index
        """,
        (str(document_no),),
    )
    return _embedding_rows(rows)


def load_visible_embeddings(
    connection: psycopg.Connection,
    document_nos: Sequence[str],
    model_name: str,
) -> List[Dict[str, Any]]:
    """Load only a caller-authorized document set for one embedding model."""
    visible = sorted({str(item).strip() for item in document_nos if str(item).strip()})
    if not visible or not model_name or not lw._database_table_exists(connection, ANALYSIS_CONTENT_EMBEDDING_TABLE):
        return []
    rows = lw._database_query(
        connection,
        f"""
        SELECT embedding.document_no, embedding.block_index, embedding.chunk_index,
               embedding.model_name, embedding.chunk_sha256, embedding.vector_values,
               block.source_evidence_id, block.source_position
        FROM {ANALYSIS_CONTENT_EMBEDDING_TABLE} AS embedding
        JOIN {lw.ANALYSIS_CONTENT_BLOCK_TABLE} AS block
          ON block.document_no = embedding.document_no
         AND block.block_index = embedding.block_index
        WHERE embedding.model_name = %s AND embedding.document_no = ANY(%s)
        ORDER BY embedding.document_no, embedding.block_index, embedding.chunk_index
        """,
        (model_name, visible),
    )
    return _embedding_rows(rows)


def load_authorized_embedding_candidates(
    connection: psycopg.Connection,
    actor: Dict[str, Any],
    model_name: str,
) -> tuple[List[Dict[str, Any]], bool]:
    """Load bounded direct-PostgreSQL vectors only from the actor's readable documents."""
    if not (
        model_name
        and lw._database_table_exists(connection, ANALYSIS_CONTENT_EMBEDDING_TABLE)
        and lw._database_table_exists(connection, lw.ANALYSIS_CONTENT_BLOCK_TABLE)
        and lw._database_table_exists(connection, lw.ANALYSIS_DOCUMENT_TABLE)
    ):
        return [], False
    corp_code = str(actor.get("corp_code") or "").strip()
    if not corp_code:
        return [], False
    pu_code = str(actor.get("pu_code") or "").strip()
    if "admin" in set(actor.get("roles") or []):
        access_sql = "document.corp_code = %s"
        access_params: tuple[Any, ...] = (corp_code,)
    else:
        access_sql = "document.corp_code = %s AND (document.visibility_code = %s OR document.owner_pu = %s)"
        access_params = (corp_code, lw.VISIBILITY_PUBLIC, pu_code)
    rows = lw._database_query(
        connection,
        f"""
        SELECT embedding.document_no, embedding.block_index, embedding.chunk_index,
               embedding.model_name, embedding.chunk_sha256, embedding.vector_values,
               block.source_evidence_id, block.source_position,
               document.title_sample AS title, document.visibility_code AS visibility
        FROM {ANALYSIS_CONTENT_EMBEDDING_TABLE} AS embedding
        JOIN {lw.ANALYSIS_CONTENT_BLOCK_TABLE} AS block
          ON block.document_no = embedding.document_no
         AND block.block_index = embedding.block_index
        JOIN {lw.ANALYSIS_DOCUMENT_TABLE} AS document
          ON document.document_no = embedding.document_no
        WHERE embedding.model_name = %s AND {access_sql}
        ORDER BY embedding.document_no, embedding.block_index, embedding.chunk_index
        LIMIT %s
        """,
        (model_name, *access_params, MAX_SEMANTIC_CANDIDATE_ROWS + 1),
    )
    return _embedding_rows(rows[:MAX_SEMANTIC_CANDIDATE_ROWS]), len(rows) > MAX_SEMANTIC_CANDIDATE_ROWS


def cosine_similarity(left: Sequence[float], right: Sequence[float]) -> float:
    """Calculate cosine similarity only for equal, finite vector dimensions."""
    if not left or len(left) != len(right):
        raise ValueError("embedding dimensions must match")
    numerator = sum(a * b for a, b in zip(left, right))
    denominator = math.sqrt(sum(a * a for a in left)) * math.sqrt(sum(b * b for b in right))
    if denominator == 0:
        raise ValueError("embedding vectors must have magnitude")
    return numerator / denominator


def rank_related_documents(
    document_no: str,
    anchor_rows: Sequence[Dict[str, Any]],
    candidate_rows: Sequence[Dict[str, Any]],
    *,
    limit: int = 12,
) -> List[Dict[str, Any]]:
    """Return inferred semantic candidates with source IDs, never a transition claim."""
    bounded_limit = max(1, min(int(limit), MAX_SEMANTIC_NEIGHBORS))
    best: Dict[str, Dict[str, Any]] = {}
    for candidate in candidate_rows:
        candidate_document = str(candidate.get("document_no") or "")
        if not candidate_document or candidate_document == str(document_no):
            continue
        for anchor in anchor_rows:
            if str(anchor.get("model_name") or "") != str(candidate.get("model_name") or ""):
                continue
            try:
                score = cosine_similarity(anchor["vector_values"], candidate["vector_values"])
            except (KeyError, ValueError):
                continue
            if score < MIN_SEMANTIC_RELATEDNESS:
                continue
            prior = best.get(candidate_document)
            if prior is None or score > float(prior["similarity"]):
                best[candidate_document] = {
                    "document_no": candidate_document,
                    "similarity": round(score, 6),
                    "relation": "semantic_related",
                    "evidence_status": lw.EVIDENCE_INFERRED,
                    "source_evidence_id": str(candidate.get("source_evidence_id") or ""),
                    "source_position": int(candidate.get("source_position") or 0),
                    "model_name": str(candidate.get("model_name") or ""),
                }
    return sorted(best.values(), key=lambda item: (-float(item["similarity"]), item["document_no"]))[:bounded_limit]
