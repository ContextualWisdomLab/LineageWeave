"""Opaque HMAC source-window cursor for ontology neighborhoods (ADR 0124).

The in-memory ``after:`` token only pages facts already loaded. This module
mints a versioned, encrypted, HMAC-integrity-protected continuation token
so a later request can keyset-paginate the recursive SQL window. The token
never carries hidden endpoint IDs, omitted counts, or tenant identifiers in
plaintext.

Grounding: HMAC-SHA256 (Krawczyk, Bellare, & Canetti, 1997, RFC 2104);
Encrypt-then-MAC (Bellare & Namprempre, 2008).
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Mapping, Sequence

from lineageweave.ontology_neighborhood import OntologyNeighborhoodError

SOURCE_CURSOR_PREFIX = "src.v1."
SOURCE_CURSOR_VERSION = 1
SOURCE_CURSOR_TTL = timedelta(minutes=15)
SOURCE_CURSOR_MIN_SECRET_BYTES = 32
_NONCE_BYTES = 16
_MAC_BYTES = 32
_MAC_INFO = b"lw-ontology-src-mac-v1"
_ENC_INFO = b"lw-ontology-src-enc-v1"


@dataclass(frozen=True)
class OntologySourceKey:
    """Deterministic keyset position inside the recursive source window."""

    hop_depth: int
    edge_type_code: str
    source_node_type_code: str
    source_node_id: str
    target_node_type_code: str
    target_node_id: str


@dataclass(frozen=True)
class OntologySourceCursor:
    """Verified continuation claims for one neighborhood request snapshot."""

    focus_node_type_code: str
    focus_node_id: str
    knowledge_cutoff: datetime | None
    maximum_depth: int
    maximum_nodes: int
    maximum_edges: int
    allowed_property_codes: tuple[str, ...] | None
    last_key: OntologySourceKey
    snapshot_at: datetime
    eligibility_digest: str
    expires_at: datetime


def source_cursor_secret_from_env(secret: str | None) -> bytes | None:
    """Return a usable HMAC secret, or None when continuation must stay closed.

    Next action: pass this to mint/verify, and withhold ``next_cursor`` when
    it is None so a missing process secret cannot mint a fake page token.
    """
    raw = (secret if secret is not None else os.environ.get("ONTOLOGY_SOURCE_CURSOR_SECRET", "")).strip()
    if not raw:
        return None
    encoded = raw.encode("utf-8")
    if len(encoded) < SOURCE_CURSOR_MIN_SECRET_BYTES:
        return None
    return encoded


def scope_digest(secret: bytes, user_account_id: str) -> str:
    """HMAC-truncated authorization scope; never the raw account id."""
    digest = hmac.new(secret, f"scope|{user_account_id}".encode("utf-8"), hashlib.sha256).hexdigest()
    return digest[:32]


def eligibility_digest(visible_post_ids: Sequence[str]) -> str:
    """Snapshot hash of the frozen visible-post set used for paging."""
    joined = ",".join(sorted(visible_post_ids))
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()


def mint_source_cursor(
    *,
    secret: bytes,
    user_account_id: str,
    focus_node_type_code: str,
    focus_node_id: str,
    knowledge_cutoff: datetime | None,
    maximum_depth: int,
    maximum_nodes: int,
    maximum_edges: int,
    allowed_property_codes: Sequence[str] | None,
    last_key: OntologySourceKey,
    snapshot_at: datetime,
    visible_post_ids: Sequence[str],
    now: datetime | None = None,
) -> str:
    """Seal a source-window continuation token.

    Next action: return this as ``next_cursor`` when the SQL window still has
    authorized relations beyond the current page.
    """
    clock = now or datetime.now(timezone.utc)
    payload = {
        "v": SOURCE_CURSOR_VERSION,
        "focus_type": focus_node_type_code,
        "focus_id": focus_node_id,
        "cutoff": knowledge_cutoff.isoformat() if knowledge_cutoff else "",
        "depth": maximum_depth,
        "max_nodes": maximum_nodes,
        "max_edges": maximum_edges,
        "properties": ",".join(sorted(allowed_property_codes)) if allowed_property_codes else "",
        "last_depth": last_key.hop_depth,
        "last_edge_type": last_key.edge_type_code,
        "last_source_type": last_key.source_node_type_code,
        "last_source_id": last_key.source_node_id,
        "last_target_type": last_key.target_node_type_code,
        "last_target_id": last_key.target_node_id,
        "snapshot": snapshot_at.isoformat(),
        "elig": eligibility_digest(visible_post_ids),
        "scope": scope_digest(secret, user_account_id),
        "exp": int((clock + SOURCE_CURSOR_TTL).timestamp()),
    }
    plaintext = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    nonce = os.urandom(_NONCE_BYTES)
    ciphertext = _xor(plaintext, _keystream(_enc_key(secret), nonce, len(plaintext)))
    mac = hmac.new(_mac_key(secret), nonce + ciphertext, hashlib.sha256).digest()
    packed = nonce + mac + ciphertext
    return SOURCE_CURSOR_PREFIX + _b64encode(packed)


def verify_source_cursor(
    token: str,
    *,
    secret: bytes,
    user_account_id: str,
    focus_node_type_code: str,
    focus_node_id: str,
    knowledge_cutoff: datetime | None,
    maximum_depth: int,
    maximum_nodes: int,
    maximum_edges: int,
    allowed_property_codes: Sequence[str] | None,
    visible_post_ids: Sequence[str],
    validate_eligibility: bool = True,
    now: datetime | None = None,
) -> OntologySourceCursor:
    """Open a source cursor and fail closed on tamper, scope, or snapshot drift.

    ``validate_eligibility=False`` is only for the first authenticated pass of
    a continuation request. It verifies the sealed request, scope, expiry, and
    snapshot before the caller reconstructs the frozen eligibility set; the
    caller must run this function again with that reconstructed set.

    Next action: bind the returned last key into the recursive keyset query.
    """
    if not token.startswith(SOURCE_CURSOR_PREFIX):
        raise OntologyNeighborhoodError("malformed_cursor", "cursor must be an opaque source token")
    packed = _b64decode(token[len(SOURCE_CURSOR_PREFIX) :])
    if len(packed) < _NONCE_BYTES + _MAC_BYTES + 1:
        raise OntologyNeighborhoodError("malformed_cursor", "cursor is truncated")
    nonce = packed[:_NONCE_BYTES]
    mac = packed[_NONCE_BYTES : _NONCE_BYTES + _MAC_BYTES]
    ciphertext = packed[_NONCE_BYTES + _MAC_BYTES :]
    expected = hmac.new(_mac_key(secret), nonce + ciphertext, hashlib.sha256).digest()
    if not hmac.compare_digest(mac, expected):
        raise OntologyNeighborhoodError("malformed_cursor", "cursor failed integrity verification")
    try:
        payload = json.loads(_xor(ciphertext, _keystream(_enc_key(secret), nonce, len(ciphertext))))
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise OntologyNeighborhoodError("malformed_cursor", "cursor payload is not readable") from exc
    if not isinstance(payload, dict):
        raise OntologyNeighborhoodError("malformed_cursor", "cursor payload is not an object")
    return _validated_cursor(
        payload,
        secret=secret,
        user_account_id=user_account_id,
        focus_node_type_code=focus_node_type_code,
        focus_node_id=focus_node_id,
        knowledge_cutoff=knowledge_cutoff,
        maximum_depth=maximum_depth,
        maximum_nodes=maximum_nodes,
        maximum_edges=maximum_edges,
        allowed_property_codes=allowed_property_codes,
        visible_post_ids=visible_post_ids,
        validate_eligibility=validate_eligibility,
        now=now or datetime.now(timezone.utc),
    )


def source_key_from_row(row: Mapping[str, object]) -> OntologySourceKey:
    """Project one SQL fact row onto the keyset continuation key."""
    hop_depth = row["hop_depth"] if "hop_depth" in row else 0
    return OntologySourceKey(
        hop_depth=int(hop_depth or 0),
        edge_type_code=str(row["edge_type_code"]),
        source_node_type_code=str(row["source_node_type_code"]),
        source_node_id=str(row["source_node_id"]),
        target_node_type_code=str(row["target_node_type_code"]),
        target_node_id=str(row["target_node_id"]),
    )


def _validated_cursor(
    payload: Mapping[str, object],
    *,
    secret: bytes,
    user_account_id: str,
    focus_node_type_code: str,
    focus_node_id: str,
    knowledge_cutoff: datetime | None,
    maximum_depth: int,
    maximum_nodes: int,
    maximum_edges: int,
    allowed_property_codes: Sequence[str] | None,
    visible_post_ids: Sequence[str],
    validate_eligibility: bool,
    now: datetime,
) -> OntologySourceCursor:
    if payload.get("v") != SOURCE_CURSOR_VERSION:
        raise OntologyNeighborhoodError("malformed_cursor", "cursor version is not supported")
    expires_at = datetime.fromtimestamp(int(payload["exp"]), tz=timezone.utc)
    if now >= expires_at:
        raise OntologyNeighborhoodError("malformed_cursor", "cursor has expired")
    if payload.get("scope") != scope_digest(secret, user_account_id):
        raise OntologyNeighborhoodError("malformed_cursor", "cursor is outside this authorization scope")
    if payload.get("focus_type") != focus_node_type_code or payload.get("focus_id") != focus_node_id:
        raise OntologyNeighborhoodError("malformed_cursor", "cursor does not match this focus")
    expected_cutoff = knowledge_cutoff.isoformat() if knowledge_cutoff else ""
    if payload.get("cutoff") != expected_cutoff:
        raise OntologyNeighborhoodError("malformed_cursor", "cursor does not match this knowledge cutoff")
    if (
        int(payload["depth"]) != maximum_depth
        or int(payload["max_nodes"]) != maximum_nodes
        or int(payload["max_edges"]) != maximum_edges
    ):
        raise OntologyNeighborhoodError("malformed_cursor", "cursor does not match request bounds")
    expected_properties = ",".join(sorted(allowed_property_codes)) if allowed_property_codes else ""
    if payload.get("properties") != expected_properties:
        raise OntologyNeighborhoodError("malformed_cursor", "cursor does not match property filter")
    if validate_eligibility and payload.get("elig") != eligibility_digest(visible_post_ids):
        raise OntologyNeighborhoodError("stale_snapshot", "cursor snapshot no longer matches visible evidence")
    snapshot_at = datetime.fromisoformat(str(payload["snapshot"]))
    if snapshot_at.tzinfo is None:
        raise OntologyNeighborhoodError("malformed_cursor", "cursor snapshot is not offset-aware")
    last_key = OntologySourceKey(
        hop_depth=int(payload["last_depth"]),
        edge_type_code=str(payload["last_edge_type"]),
        source_node_type_code=str(payload["last_source_type"]),
        source_node_id=str(payload["last_source_id"]),
        target_node_type_code=str(payload["last_target_type"]),
        target_node_id=str(payload["last_target_id"]),
    )
    return OntologySourceCursor(
        focus_node_type_code=focus_node_type_code,
        focus_node_id=focus_node_id,
        knowledge_cutoff=knowledge_cutoff,
        maximum_depth=maximum_depth,
        maximum_nodes=maximum_nodes,
        maximum_edges=maximum_edges,
        allowed_property_codes=tuple(allowed_property_codes) if allowed_property_codes else None,
        last_key=last_key,
        snapshot_at=snapshot_at,
        eligibility_digest=str(payload["elig"]),
        expires_at=expires_at,
    )


def _mac_key(secret: bytes) -> bytes:
    return hmac.new(secret, _MAC_INFO, hashlib.sha256).digest()


def _enc_key(secret: bytes) -> bytes:
    return hmac.new(secret, _ENC_INFO, hashlib.sha256).digest()


def _keystream(enc_key: bytes, nonce: bytes, length: int) -> bytes:
    blocks: list[bytes] = []
    counter = 0
    while sum(len(block) for block in blocks) < length:
        blocks.append(hmac.new(enc_key, nonce + counter.to_bytes(4, "big"), hashlib.sha256).digest())
        counter += 1
    return b"".join(blocks)[:length]


def _xor(data: bytes, keystream: bytes) -> bytes:
    return bytes(left ^ right for left, right in zip(data, keystream, strict=True))


def _b64encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _b64decode(token: str) -> bytes:
    padding = "=" * ((4 - len(token) % 4) % 4)
    try:
        return base64.urlsafe_b64decode(token + padding)
    except (ValueError, binascii.Error) as exc:
        raise OntologyNeighborhoodError("malformed_cursor", "cursor encoding is invalid") from exc
