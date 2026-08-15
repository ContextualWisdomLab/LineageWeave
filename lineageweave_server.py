#!/usr/bin/env python3
"""Run the LineageWeave direct-PostgreSQL web/API service.

The service deliberately keeps the browser outside the database. It verifies a
Keyverse session (or an explicitly enabled local development actor), builds
the graph from PostgreSQL, filters every response with ABAC/RBAC, and exposes
document-scoped mutation and inline-image inspection endpoints.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import http.server as stdlib_http_server
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from typing import Any, Mapping, Optional

import psycopg

import lineageweave as lw
import lineageweave_embeddings as lwe


PROJECT_ROOT = Path(__file__).resolve().parent
FRONTEND_ROOT = PROJECT_ROOT / "web" / "dist"
ThreadingHTTPServer = stdlib_http_server.ThreadingHTTPServer
KEYVERSE_SCOPE = "openid profile email"
KEYVERSE_STATE_TTL_SECONDS = 600
MAX_KEYVERSE_PENDING_STATES = 1_024
KEYVERSE_PRODUCT_ROLE_MAP = {
    "member": "reader",
    "reader": "reader",
    "author": "author",
    "editor": "editor",
    "admin": "admin",
}
KEYVERSE_ADMIN_ACCOUNT_LIMIT = 50
KEYVERSE_ADMIN_ROLE_LIMIT = 100
KEYVERSE_ACCOUNT_VALUE_LIMIT = 64
ENRICHMENT_TASKS = ("keyman", "product", "appointments", "all")
ENRICHMENT_BATCH_LIMIT = 64
OIDC_ISSUER_ROUTE_PARTS = frozenset(
    {
        (".well-known", "openid-configuration"),
        ("authorize",),
        ("token",),
        ("introspect",),
        ("introspection",),
        ("protocol", "openid-connect", "auth"),
        ("protocol", "openid-connect", "token"),
        ("protocol", "openid-connect", "token", "introspect"),
    }
)


def _json_ready(value: Any) -> Any:
    """Coerce mapping keys to strings so KG depth maps cannot break JSON."""
    if isinstance(value, dict):
        ready: dict[str, Any] = {}
        for key, item in value.items():
            if isinstance(key, (tuple, list)):
                mapped = ":".join(str(part) for part in key)
            elif key is None:
                mapped = "null"
            else:
                mapped = str(key)
            ready[mapped] = _json_ready(item)
        return ready
    if isinstance(value, tuple):
        return [_json_ready(item) for item in value]
    if isinstance(value, list):
        return [_json_ready(item) for item in value]
    return value


def _json_bytes(value: Any) -> bytes:
    """Serialize one API value without leaking non-JSON database objects."""
    return json.dumps(_json_ready(value), ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def _is_oidc_issuer_route(parts: list[str]) -> bool:
    """Reject issuer-shaped paths so the relying party cannot impersonate an IdP."""
    return tuple(parts) in OIDC_ISSUER_ROUTE_PARTS


def _actor_from_value(value: Any) -> Optional[dict[str, Any]]:
    """Validate a development actor or verified Keyverse claim projection."""
    if not isinstance(value, dict):
        return None
    actor = value.get("actor") if isinstance(value.get("actor"), dict) else None
    attrs = value.get("attributes")
    if actor is None and isinstance(attrs, dict):
        actor = {
            "account_id": value.get("account_id"),
            "corp_code": attrs.get("corp_code"),
            "pu_code": attrs.get("pu_code"),
            "roles": attrs.get("roles"),
            "corp_name": attrs.get("corp_name"),
            "pu_name": attrs.get("pu_name"),
        }
    if actor is None:
        actor = value
    account_id = str(actor.get("account_id") or actor.get("sub") or "").strip()
    corp_code = str(
        actor.get("corp_code")
        or actor.get("corp-code")
        or actor.get("org")
        or actor.get("corpCode")
        or ""
    ).strip()
    pu_code = str(
        actor.get("pu_code")
        or actor.get("pu-code")
        or actor.get("workspace")
        or actor.get("puCode")
        or ""
    ).strip()
    roles = actor.get("roles", actor.get("role"))
    if isinstance(roles, str):
        roles = [roles]
    if not account_id or not corp_code or not pu_code or not isinstance(roles, list):
        return None
    normalized_roles = [str(role).strip() for role in roles if str(role).strip()]
    if not normalized_roles:
        return None
    return {
        "account_id": account_id,
        "corp_code": corp_code,
        "pu_code": pu_code,
        "roles": normalized_roles,
        "corp_name": actor.get("corp_name"),
        "pu_name": actor.get("pu_name"),
    }


def _session_ttl_seconds() -> int:
    """Return a bounded local session cache TTL while Keyverse remains authoritative."""
    try:
        requested = int(os.environ.get("LINEAGEWEAVE_SESSION_TTL_SECONDS", "3600"))
    except ValueError:
        requested = 3600
    return max(60, min(requested, 86_400))


def _cookie_value(headers: Any, name: str) -> str:
    """Return one named cookie value without accepting duplicate delimiters."""
    for part in str(headers.get("Cookie") or "").split(";"):
        cookie_name, separator, value = part.strip().partition("=")
        if separator and cookie_name == name:
            return value
    return ""


def _cookie_header(name: str, value: str, max_age: int) -> str:
    """Build a secure, host-independent browser cookie header."""
    cookie = f"{name}={value}; Path=/; Max-Age={max(0, int(max_age))}; HttpOnly; SameSite=Lax"
    if _cookie_should_be_secure():
        cookie += "; Secure"
    return cookie


_EMAIL_ADDRESS_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _normalized_email_address(value: object) -> str:
    """Accept one email address and reject empty or control-bearing input."""
    email = str(value or "").strip().casefold()
    if not email or len(email) > 254 or not _EMAIL_ADDRESS_RE.match(email):
        raise RuntimeError("invalid_email_address")
    return email


def _admin_json(url: str, token: str, *, method: str = "GET", body: object | None = None) -> Any:
    """Call one Keyverse Admin REST path without logging the bearer token."""
    data = None if body is None else json.dumps(body).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {token}",
            **({"Content-Type": "application/json"} if data is not None else {}),
        },
    )
    try:
        with urllib.request.urlopen(  # nosemgrep: python.lang.security.audit.dynamic-urllib-use-detected.dynamic-urllib-use-detected
            request, timeout=15, context=_transport_context(url)
        ) as response:
            raw = response.read()
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"keyverse_admin_{exc.code}") from exc
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise RuntimeError("keyverse_admin_unavailable") from exc
    if not raw:
        return None
    parsed = json.loads(raw.decode("utf-8"))
    return parsed


def _keyverse_admin_token() -> str:
    """Exchange operator-injected admin credentials for one short admin token."""
    token_url = (os.environ.get("KEYVERSE_ADMIN_TOKEN_URL") or "").strip()
    username = (os.environ.get("KEYVERSE_ADMIN_USERNAME") or "").strip()
    password = (os.environ.get("KEYVERSE_ADMIN_PASSWORD") or "").strip()
    if not token_url or not username or not password:
        raise RuntimeError("keyverse_registration_unavailable")
    request = urllib.request.Request(
        token_url,
        data=urllib.parse.urlencode(
            {
                "grant_type": "password",
                "client_id": "admin-cli",
                "username": username,
                "password": password,
            }
        ).encode("utf-8"),
        method="POST",
    )
    try:
        with urllib.request.urlopen(  # nosemgrep: python.lang.security.audit.dynamic-urllib-use-detected.dynamic-urllib-use-detected
            request, timeout=15, context=_transport_context(token_url)
        ) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError, TimeoutError) as exc:
        raise RuntimeError("keyverse_registration_unavailable") from exc
    token = str(payload.get("access_token") or "")
    if not token:
        raise RuntimeError("keyverse_registration_unavailable")
    return token


def _keyverse_admin_context() -> tuple[str, str]:
    """Derive the one reviewed Keyverse realm-admin base and RP client id."""
    issuer = (os.environ.get("KEYVERSE_ISSUER") or "").strip()
    client_id = (os.environ.get("LINEAGEWEAVE_OIDC_CLIENT_ID") or "").strip()
    if not issuer or not client_id:
        raise RuntimeError("keyverse_admin_configuration_required")
    try:
        normalized_issuer = _https_url(issuer, "KEYVERSE_ISSUER")
    except RuntimeError as exc:
        raise RuntimeError("keyverse_admin_configuration_required") from exc
    origin, separator, realm = normalized_issuer.rpartition("/realms/")
    if not separator or not origin or not realm or "/" in realm:
        raise RuntimeError("keyverse_admin_configuration_required")
    return f"{origin}/admin/realms/{realm}", client_id


def _keyverse_admin_access_token() -> str:
    """Translate the registration adapter's missing-transport error at admin boundaries."""
    try:
        return _keyverse_admin_token()
    except RuntimeError as exc:
        if str(exc).startswith("keyverse_registration_"):
            raise RuntimeError("keyverse_admin_unavailable") from exc
        raise


def _keyverse_client_descriptor(admin_base: str, token: str, client_id: str) -> dict[str, str]:
    """Resolve exactly the configured relying-party client, never an arbitrary client."""
    query = urllib.parse.urlencode({"clientId": client_id})
    found = _admin_json(f"{admin_base}/clients?{query}", token)
    matches = [
        item
        for item in found
        if isinstance(item, dict) and str(item.get("clientId") or "") == client_id
    ] if isinstance(found, list) else []
    if len(matches) != 1 or not str(matches[0].get("id") or ""):
        raise RuntimeError("keyverse_admin_client_not_found")
    return {"id": str(matches[0]["id"]), "client_id": client_id}


def _keyverse_client_roles(admin_base: str, token: str, client_id: str) -> list[dict[str, str]]:
    """Return the bounded role catalog for the configured client only."""
    client = _keyverse_client_descriptor(admin_base, token, client_id)
    raw_roles = _admin_json(
        f"{admin_base}/clients/{urllib.parse.quote(client['id'], safe='')}/roles?max={KEYVERSE_ADMIN_ROLE_LIMIT}",
        token,
    )
    roles = [
        {
            "id": str(item.get("id") or ""),
            "name": str(item.get("name") or "").strip(),
            "description": str(item.get("description") or "").strip(),
        }
        for item in raw_roles
        if isinstance(item, dict) and str(item.get("id") or "") and str(item.get("name") or "").strip()
    ] if isinstance(raw_roles, list) else []
    if not roles:
        raise RuntimeError("keyverse_admin_roles_not_found")
    return sorted(roles, key=lambda item: item["name"])


def _keyverse_claim_value(value: object, field: str, *, required: bool) -> str:
    """Validate one scalar administrator-managed account claim."""
    if not isinstance(value, str):
        raise ValueError(f"keyverse_{field}_invalid")
    normalized = value.strip()
    if not normalized:
        if required:
            raise ValueError(f"keyverse_{field}_required")
        return ""
    if len(normalized) > KEYVERSE_ACCOUNT_VALUE_LIMIT or any(ord(char) < 32 or ord(char) == 127 for char in normalized):
        raise ValueError(f"keyverse_{field}_invalid")
    return normalized


def _keyverse_scalar_attribute(user: dict[str, Any], name: str) -> str:
    """Read a reviewed scalar Keyverse attribute without guessing multi-valued data."""
    attributes = user.get("attributes")
    if not isinstance(attributes, dict):
        return ""
    value = attributes.get(name)
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, list) and len(value) == 1 and isinstance(value[0], str):
        return value[0].strip()
    return ""


def _keyverse_account_view(user: object, roles: list[dict[str, str]]) -> dict[str, Any] | None:
    """Project a Keyverse user into the small account shape safe for an admin browser."""
    if not isinstance(user, dict):
        return None
    account_id = str(user.get("id") or "").strip()
    if not account_id:
        return None
    return {
        "account_id": account_id,
        "username": str(user.get("username") or ""),
        "email": str(user.get("email") or ""),
        "enabled": bool(user.get("enabled")),
        "org": _keyverse_scalar_attribute(user, "org"),
        "workspace": _keyverse_scalar_attribute(user, "workspace"),
        "roles": sorted({role["name"] for role in roles if role.get("name")}),
    }


def _keyverse_role_mappings(admin_base: str, token: str, user_id: str, client_uuid: str) -> list[dict[str, str]]:
    """Read only the configured client's direct user-role mappings."""
    url = f"{admin_base}/users/{urllib.parse.quote(user_id, safe='')}/role-mappings/clients/{urllib.parse.quote(client_uuid, safe='')}"
    raw = _admin_json(url, token)
    if not isinstance(raw, list):
        raise RuntimeError("keyverse_admin_roles_invalid")
    return [
        {"id": str(item.get("id") or ""), "name": str(item.get("name") or "").strip()}
        for item in raw
        if isinstance(item, dict) and str(item.get("name") or "").strip()
    ]


def _keyverse_role_assignment(role: dict[str, str]) -> dict[str, str]:
    """Keep Keycloak role writes limited to the role identity fields."""
    return {key: role[key] for key in ("id", "name") if role.get(key)}


_LOCAL_DEVELOPMENT_HTTP_HOSTS = frozenset(
    {"127.0.0.1", "localhost", "::1", "host.docker.internal"}
)


def loopback_oidc_url(url: str) -> str:
    """Expose browser-facing local Keyverse URLs on the OIDC-valid localhost host."""
    parsed = urllib.parse.urlsplit(url)
    if parsed.hostname != "127.0.0.1":
        return url
    host = "localhost" if parsed.port is None else f"localhost:{parsed.port}"
    return urllib.parse.urlunsplit(
        (parsed.scheme, host, parsed.path, parsed.query, parsed.fragment)
    )


def _local_http_oidc_enabled() -> bool:
    """Allow local Keyverse HTTP only with both explicit development switches."""
    return (
        os.environ.get("LINEAGEWEAVE_DEV_MODE") == "1"
        and os.environ.get("LINEAGEWEAVE_COOKIE_SECURE") == "0"
    )


def _render_keyverse_redirect_uri(
    redirect_uri: str, request_headers: Mapping[str, str] | None
) -> str:
    """Replace `{origin}` only from operator configuration, never request headers."""
    del request_headers
    if "{origin}" not in redirect_uri:
        return redirect_uri
    origin = (os.environ.get("LINEAGEWEAVE_PUBLIC_ORIGIN") or "").strip().rstrip("/")
    parsed = urllib.parse.urlsplit(origin)
    if (
        not origin
        or not parsed.hostname
        or parsed.path
        or parsed.query
        or parsed.fragment
        or parsed.username is not None
        or parsed.password is not None
    ):
        return redirect_uri
    return redirect_uri.replace("{origin}", origin)


def _https_url(value: str, setting: str, *, preserve_trailing_slash: bool = False) -> str:
    """Validate an operator-configured issuer or redirect URL.

    Production Keyverse endpoints stay HTTPS. An allowlisted HTTP endpoint is
    available only for an explicitly enabled local Keyverse integration.
    """
    candidate = value.strip() if preserve_trailing_slash else value.strip().rstrip("/")
    parsed = urllib.parse.urlsplit(candidate)
    if (
        not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
    ):
        raise RuntimeError(f"{setting}_must_be_https_url")
    host = parsed.hostname.lower()
    if parsed.scheme == "https":
        return candidate
    if (
        parsed.scheme == "http"
        and _local_http_oidc_enabled()
        and host in _LOCAL_DEVELOPMENT_HTTP_HOSTS
    ):
        return candidate
    raise RuntimeError(f"{setting}_must_be_https_url")


def _transport_context(url: str):
    """Use verified TLS for HTTPS; HTTP is only the explicit local Keyverse origin."""
    if urllib.parse.urlsplit(url).scheme == "http":
        return None
    return lw.verified_ssl_context("KEYVERSE_CA_BUNDLE")


def _cookie_should_be_secure() -> bool:
    """Allow an insecure OIDC state cookie only for explicit local development."""
    return not _local_http_oidc_enabled()


class LineageApplication:
    """Own the direct database connection boundary and cached graph snapshot."""

    def __init__(self, dsn: str, source_table: str) -> None:
        """Initialize connection settings and bounded in-process auth state."""
        self.dsn = dsn
        self.source_table = lw.resolve_source_table(source_table)
        self._payload: Optional[dict[str, Any]] = None
        self._payload_lock = threading.RLock()
        self._sessions: dict[str, dict[str, Any]] = {}
        self._keyverse_states: dict[str, dict[str, Any]] = {}
        self._session_lock = threading.RLock()
        self._keyverse_metadata_cache: dict[str, str] | None = None
        self._keyverse_metadata_expires_at = 0.0
        self._document_work_lock = threading.RLock()
        self._document_work_inflight: set[str] = set()
        self._enrichment_lock = threading.RLock()
        self._enrichment_inflight: dict[str, dict[str, Any]] = {}

    def _flush_event_outbox(self) -> int:
        """Deliver committed mutation events to Valkey with at-least-once semantics."""
        published = 0
        try:
            with psycopg.connect(self.dsn) as connection:
                for event in lw.pending_event_outbox(connection):
                    try:
                        lw.publish_valkey_event(
                            {
                                "event_id": event.get("event_id"),
                                "event_type": event.get("event_type"),
                                "document_no": event.get("document_no"),
                                "actor_id": event.get("actor_id"),
                                "payload": event.get("payload") or {},
                            }
                        )
                    except (OSError, RuntimeError, ValueError):
                        break
                    lw.mark_event_published(connection, str(event.get("event_id") or ""))
                    published += 1
        except Exception:
            return published
        return published

    def refresh_persisted_reports(self) -> int:
        """Refresh only stale report scores from persisted metadata under one DB advisory lock."""
        # ponytail: one global maintenance lock; shard by report set only if refresh throughput becomes material.
        lock_name = "lineageweave_period_report_refresh"
        with psycopg.connect(self.dsn) as connection:
            acquired = lw._database_query(
                connection,
                "SELECT pg_try_advisory_lock(hashtext(%s)) AS locked",
                (lock_name,),
            )
            if not acquired or acquired[0].get("locked") is not True:
                return 0
            try:
                persisted = lw.load_period_reports(connection)
                stale_report_ids = {
                    str(report.get("report_id") or "")
                    for report in persisted
                    if str((report.get("judge") or {}).get("source") or "") == "unavailable"
                    or not report.get("linked_scores")
                }
                if persisted and not stale_report_ids:
                    return 0
                refresh_limit = lw.resolve_runtime_int(
                    "LINEAGEWEAVE_REPORT_REFRESH_MAX_SLICES",
                    default=3,
                    minimum=1,
                    maximum=100,
                )
                refresh_attempts = lw.resolve_runtime_int(
                    "LINEAGEWEAVE_REPORT_REFRESH_MAX_ATTEMPTS",
                    default=1,
                    minimum=1,
                    maximum=3,
                )
                documents = lw.load_report_document_nodes(connection)
                if not documents:
                    return 0
                try:
                    judge_transport, _judge_mode = lw.resolve_product_transport()
                except RuntimeError:
                    return 0
                mlsirm_transport, _mlsirm_mode = lw.resolve_mlsirm_transport()
                slices = lw.build_period_report_slices(documents)
                if not slices:
                    return 0
                if persisted:
                    stale_slices = [
                        report for report in slices
                        if str(report.get("report_id") or "") in stale_report_ids
                    ]
                    if {str(report.get("report_id") or "") for report in stale_slices} != stale_report_ids:
                        return 0
                    stale_slices = stale_slices[:refresh_limit]
                else:
                    stale_slices = slices
                refresh_report_ids = {
                    str(report.get("report_id") or "") for report in stale_slices
                }
                scored = lw.score_period_reports(
                    stale_slices,
                    documents,
                    judge_transport=judge_transport,
                    mlsirm_transport=mlsirm_transport,
                    judge_max_attempts=refresh_attempts,
                )
                if not scored:
                    return 0
                if persisted:
                    scored_by_id = {
                        str(report.get("report_id") or ""): report
                        for report in scored
                    }
                    if set(scored_by_id) != refresh_report_ids:
                        return 0
                    refreshed = [
                        scored_by_id.get(str(report.get("report_id") or ""), report)
                        for report in persisted
                    ]
                else:
                    refreshed = scored
                lw.persist_period_reports(connection, refreshed)
                with self._payload_lock:
                    if self._payload is not None:
                        self._payload["period_reports"] = refreshed
                        self._payload["factor_definitions"] = lw.default_factor_definitions()
                return len(scored)
            finally:
                lw._database_query(
                    connection,
                    "SELECT pg_advisory_unlock(hashtext(%s)) AS unlocked",
                    (lock_name,),
                )

    def _run_document_work(self, document: dict[str, Any]) -> None:
        """Enrich issue work after the document response has already been sent."""
        document_no = str(document.get("document_no") or "")
        try:
            transport, _mode = lw.resolve_product_transport()
            enriched = lw.enrich_pending_document_work(document, transport=transport)
            with psycopg.connect(self.dsn) as connection:
                for todo, calendar in zip(
                    enriched.get("todo_items") or [],
                    enriched.get("calendar_items") or [],
                ):
                    lw.persist_issue_work_items(connection, todo, calendar)
                connection.commit()
            if self._payload is not None:
                with self._payload_lock:
                    node = next(
                        (
                            value
                            for value in self._payload.get("nodes") or []
                            if value.get("type") == "document"
                            and value.get("document_no") == document_no
                        ),
                        None,
                    )
                    if node is not None:
                        node.update(
                            {
                                "issue_tickets": enriched.get("issue_tickets") or [],
                                "todo_items": enriched.get("todo_items") or [],
                                "calendar_items": enriched.get("calendar_items") or [],
                            }
                        )
            self._flush_event_outbox()
        except Exception:
            pass
        finally:
            with self._document_work_lock:
                self._document_work_inflight.discard(document_no)

    def _schedule_document_work(self, actor: dict[str, Any], document: dict[str, Any]) -> None:
        """Queue pending issue work without blocking the document-detail response."""
        document_no = str(document.get("document_no") or "")
        with self._document_work_lock:
            if document_no in self._document_work_inflight:
                return
            self._document_work_inflight.add(document_no)
        try:
            with psycopg.connect(self.dsn) as connection:
                lw.enqueue_event_outbox(
                    connection,
                    "document_work_enrichment_requested",
                    document_no,
                    str(actor.get("account_id") or ""),
                    {"work": "issue_work_items", "document_no": document_no},
                )
                connection.commit()
            self._flush_event_outbox()
            threading.Thread(
                target=self._run_document_work,
                args=(dict(document),),
                daemon=True,
                name=f"lineageweave-work-{document_no}",
            ).start()
        except Exception:
            with self._document_work_lock:
                self._document_work_inflight.discard(document_no)

    def _enrichment_scope(self, actor: dict[str, Any]) -> tuple[str, tuple[str, ...]]:
        """Return the same corp/PU read scope used by the document browser."""
        corp_code = str(actor.get("corp_code") or "").strip()
        if not corp_code:
            raise ValueError("enrichment_actor_corp_required")
        if "admin" in {str(role).strip().casefold() for role in actor.get("roles") or []}:
            return "d.corp_code = %s", (corp_code,)
        return (
            "d.corp_code = %s AND (d.visibility_code = %s OR d.owner_pu = %s)",
            (corp_code, lw.VISIBILITY_PUBLIC, str(actor.get("pu_code") or "").strip()),
        )

    def _enrichment_candidates(
        self,
        connection: psycopg.Connection,
        actor: dict[str, Any],
        task: str,
        limit: int,
    ) -> list[str]:
        """Select only actor-visible documents whose persisted work is pending."""
        scope_sql, scope_params = self._enrichment_scope(actor)
        selected: list[str] = []
        if task in {"keyman", "all"}:
            rows = lw._database_query(
                connection,
                f"""
                SELECT d.document_no
                FROM {lw.ANALYSIS_DOCUMENT_TABLE} AS d
                WHERE {scope_sql}
                  AND COALESCE(d.keyman_source, '') NOT IN ('llm', 'user_override')
                ORDER BY d.document_no DESC
                LIMIT %s
                """,
                scope_params + (limit,),
            )
            selected.extend(str(row["document_no"]) for row in rows if row.get("document_no"))
        if task in {"product", "all"}:
            rows = lw._database_query(
                connection,
                f"""
                SELECT DISTINCT d.document_no
                FROM {lw.ANALYSIS_DOCUMENT_TABLE} AS d
                LEFT JOIN {lw.ANALYSIS_TODO_TABLE} AS todo ON todo.document_no = d.document_no
                LEFT JOIN {lw.ANALYSIS_CALENDAR_TABLE} AS calendar ON calendar.document_no = d.document_no
                WHERE {scope_sql}
                  AND (todo.content_source = 'pending_llm' OR calendar.content_source = 'pending_llm')
                ORDER BY d.document_no DESC
                LIMIT %s
                """,
                scope_params + (limit,),
            )
            selected.extend(str(row["document_no"]) for row in rows if row.get("document_no"))
        if task in {"appointments", "all"}:
            rows = lw._database_query(
                connection,
                f"""
                SELECT DISTINCT d.document_no
                FROM {lw.ANALYSIS_DOCUMENT_TABLE} AS d
                JOIN {lw.ANALYSIS_APPOINTMENT_TABLE} AS appointment
                  ON appointment.document_no = d.document_no
                WHERE {scope_sql} AND appointment.content_source = 'extract'
                ORDER BY d.document_no DESC
                LIMIT %s
                """,
                scope_params + (limit,),
            )
            selected.extend(str(row["document_no"]) for row in rows if row.get("document_no"))
        return list(dict.fromkeys(selected))[:limit]

    def enrichment_status(self, actor: dict[str, Any]) -> dict[str, Any]:
        """Return bounded pending counts and the latest durable batch event."""
        self._require_keyverse_admin(actor)
        pending = {"keyman": 0, "product": 0, "appointments": 0}
        last_run = None
        with psycopg.connect(self.dsn) as connection:
            document_table_exists = lw._database_table_exists(connection, lw.ANALYSIS_DOCUMENT_TABLE)
            if document_table_exists:
                keyman = lw._database_query(
                    connection,
                    f"""
                    SELECT COUNT(*) AS total
                    FROM {lw.ANALYSIS_DOCUMENT_TABLE} AS d
                    WHERE d.corp_code = %s
                      AND COALESCE(d.keyman_source, '') NOT IN ('llm', 'user_override')
                    """,
                    (actor["corp_code"],),
                )
                pending["keyman"] = int((keyman[0] or {}).get("total") or 0) if keyman else 0
            if document_table_exists and lw._database_table_exists(connection, lw.ANALYSIS_TODO_TABLE):
                product = lw._database_query(
                    connection,
                    f"""
                    SELECT COUNT(DISTINCT todo.document_no) AS total
                    FROM {lw.ANALYSIS_TODO_TABLE} AS todo
                    JOIN {lw.ANALYSIS_DOCUMENT_TABLE} AS d ON d.document_no = todo.document_no
                    WHERE d.corp_code = %s AND todo.content_source = 'pending_llm'
                    """,
                    (actor["corp_code"],),
                )
                pending["product"] = int((product[0] or {}).get("total") or 0) if product else 0
            if document_table_exists and lw._database_table_exists(connection, lw.ANALYSIS_APPOINTMENT_TABLE):
                appointments = lw._database_query(
                    connection,
                    f"""
                    SELECT COUNT(DISTINCT appointment.document_no) AS total
                    FROM {lw.ANALYSIS_APPOINTMENT_TABLE} AS appointment
                    JOIN {lw.ANALYSIS_DOCUMENT_TABLE} AS d ON d.document_no = appointment.document_no
                    WHERE d.corp_code = %s AND appointment.content_source = 'extract'
                    """,
                    (actor["corp_code"],),
                )
                pending["appointments"] = int((appointments[0] or {}).get("total") or 0) if appointments else 0
            if lw._database_table_exists(connection, lw.ANALYSIS_EVENT_OUTBOX_TABLE):
                events = lw._database_query(
                    connection,
                    f"""
                    SELECT event_type, payload, created_at, published_at
                    FROM {lw.ANALYSIS_EVENT_OUTBOX_TABLE}
                    WHERE event_type IN ('llm_enrichment_batch_requested', 'llm_enrichment_batch_completed')
                    ORDER BY created_at DESC
                    LIMIT 1
                    """,
                )
                if events:
                    event = events[0]
                    payload = event.get("payload") or {}
                    if isinstance(payload, str):
                        payload = json.loads(payload)
                    last_run = {
                        "event_type": event.get("event_type"),
                        "created_at": event.get("created_at"),
                        "published": bool(event.get("published_at")),
                        **(payload if isinstance(payload, dict) else {}),
                    }
        with self._enrichment_lock:
            active = [dict(run) for run in self._enrichment_inflight.values()]
        return {"pending": pending, "active_runs": active, "last_run": last_run}

    def _persist_keyman_result(
        self,
        actor: dict[str, Any],
        document_no: str,
        item: dict[str, Any],
        derived: dict[str, Any],
        mode: str,
        *,
        allow_empty: bool = False,
    ) -> dict[str, Any]:
        """Persist one LLM Keyman result, including an explicit empty abstention."""
        our_side = derived.get("our_side") or []
        counterpart_side = derived.get("counterpart_side") or []
        if not our_side and not counterpart_side and not allow_empty:
            raise ValueError("live model returned no Keyman")
        source = "llm" if allow_empty and not our_side and not counterpart_side else derived["source"]
        status = "empty" if not our_side and not counterpart_side else derived["status"]
        with psycopg.connect(self.dsn) as connection:
            lw.ensure_keyman_override_columns(connection)
            lw._database_exec(
                connection,
                f"""
                INSERT INTO {lw.ANALYSIS_OVERRIDE_TABLE}
                    (document_no, keyman_our_side, keyman_counterpart_side,
                     keyman_source, keyman_status, updated_by, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, now())
                ON CONFLICT (document_no) DO UPDATE SET
                    keyman_our_side = EXCLUDED.keyman_our_side,
                    keyman_counterpart_side = EXCLUDED.keyman_counterpart_side,
                    keyman_source = EXCLUDED.keyman_source,
                    keyman_status = EXCLUDED.keyman_status,
                    updated_by = EXCLUDED.updated_by,
                    updated_at = now()
                """,
                (
                    document_no,
                    json.dumps(our_side, ensure_ascii=False),
                    json.dumps(counterpart_side, ensure_ascii=False),
                    source,
                    status,
                    actor["account_id"],
                ),
            )
            lw.enqueue_event_outbox(
                connection,
                "keyman_derived",
                document_no,
                actor["account_id"],
                {
                    "our_count": len(our_side),
                    "counterpart_count": len(counterpart_side),
                    "transport": mode,
                    "abstained": not our_side and not counterpart_side,
                },
            )
        self._flush_event_outbox()
        updated = dict(item)
        updated.update(
            {
                "keyman_our_side": our_side,
                "keyman_counterpart_side": counterpart_side,
                "keymen": derived.get("names") or [],
                "keyman_source": source,
                "keyman_status": status,
                "keyman_orchestration": derived.get("orchestration") or {},
            }
        )
        if self._payload is not None:
            with self._payload_lock:
                node = next(
                    node
                    for node in self._payload["nodes"]
                    if node.get("type") == "document" and node.get("document_no") == document_no
                )
                node.update(updated)
                self._payload["knowledge_graph"] = lw.refresh_document_keyman_knowledge_graph(
                    self._payload.get("knowledge_graph") or {}, node
                )
                knowledge_graph = self._payload["knowledge_graph"]
            with psycopg.connect(self.dsn) as connection:
                lw.persist_knowledge_graph_snapshot(connection, knowledge_graph)
            updated = node
        return updated

    def _persist_product_enrichment(
        self,
        actor: dict[str, Any],
        document: dict[str, Any],
        transport: Any,
        *,
        include_appointments: bool,
    ) -> None:
        """Persist subject classification, R&R, pending work, and appointments."""
        document_no = str(document.get("document_no") or "")
        role_result = lw.derive_entity_role_via_llm(
            document,
            enum_values=lw.load_common_enum_values(lw.DEFAULT_ENUM_ROWS),
            transport=transport,
        )
        if role_result.get("entity_role"):
            document["entity_role"] = role_result["entity_role"]
            document["entity_role_uri"] = lw.entity_role_ontology_uri(role_result["entity_role"])
        roles = lw.derive_roles_and_responsibilities_via_llm(document, transport=transport)
        enriched = lw.enrich_pending_document_work(document, transport=transport)
        appointments = list(document.get("appointments") or [])
        if include_appointments:
            text = " ".join(str(value) for value in (document.get("title_sample"), document.get("korean_summary")) if value)
            appointments = lw.derive_appointments_via_llm(
                text,
                transport=transport,
                document_no=document_no,
                fallback_date=str(document.get("first_row_ts") or "")[:10],
            )
            for appointment in appointments:
                appointment["document_no"] = document_no
                appointment["appointment_id"] = lw._stable_id(
                    "apt", document_no, appointment.get("occurred_on"), appointment.get("excerpt")
                )
        with psycopg.connect(self.dsn) as connection:
            lw._ensure_operational_tables(connection)
            lw._database_exec(
                connection,
                f"""
                UPDATE {lw.ANALYSIS_DOCUMENT_TABLE}
                SET entity_role = %s, roles_and_responsibilities = %s, issue_tickets = %s
                WHERE document_no = %s
                """,
                (
                    document.get("entity_role"),
                    lw.Json(roles),
                    lw.Json(enriched.get("issue_tickets") or document.get("issue_tickets") or []),
                    document_no,
                ),
            )
            for todo, calendar in zip(
                enriched.get("todo_items") or [], enriched.get("calendar_items") or []
            ):
                lw.persist_issue_work_items(connection, todo, calendar)
            if include_appointments:
                lw._database_exec(
                    connection,
                    f"DELETE FROM {lw.ANALYSIS_APPOINTMENT_TABLE} WHERE document_no = %s",
                    (document_no,),
                )
                with connection.cursor() as cursor:
                    cursor.executemany(
                        f"""
                        INSERT INTO {lw.ANALYSIS_APPOINTMENT_TABLE}
                            (appointment_id, document_no, occurred_on, label, excerpt, content_source)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        ON CONFLICT (appointment_id) DO UPDATE SET
                            occurred_on = EXCLUDED.occurred_on,
                            label = EXCLUDED.label,
                            excerpt = EXCLUDED.excerpt,
                            content_source = EXCLUDED.content_source
                        """,
                        [
                            (
                                appointment.get("appointment_id"),
                                document_no,
                                appointment.get("occurred_on"),
                                appointment.get("label") or "고객 약속",
                                appointment.get("excerpt") or "",
                                appointment.get("source") or "extract",
                            )
                            for appointment in appointments
                            if appointment.get("appointment_id") and appointment.get("occurred_on")
                        ],
                    )
            lw.enqueue_event_outbox(
                connection,
                "llm_enrichment_document_completed",
                document_no,
                actor["account_id"],
                {
                    "entity_role_source": role_result.get("source") or "llm_abstention",
                    "entity_role_confidence": role_result.get("confidence") or 0.0,
                    "roles_source": "llm" if any(item.get("source") == "llm" for item in roles) else "observed_code",
                    "pending_work_remaining": any(
                        item.get("source") == "pending_llm"
                        for item in (enriched.get("todo_items") or []) + (enriched.get("calendar_items") or [])
                    ),
                    "appointment_source": "llm" if any(item.get("source") == "llm" for item in appointments) else "extract",
                },
            )
        with self._payload_lock:
            if self._payload is not None:
                node = next(
                    node
                    for node in self._payload["nodes"]
                    if node.get("type") == "document" and node.get("document_no") == document_no
                )
                node["roles_and_responsibilities"] = roles
                node["entity_role"] = document.get("entity_role") or node.get("entity_role")
                node["entity_role_uri"] = document.get("entity_role_uri") or lw.entity_role_ontology_uri(node.get("entity_role"))
                node["entity_role_source"] = role_result.get("source") or "llm_abstention"
                node["entity_role_confidence"] = role_result.get("confidence") or 0.0
                node["issue_tickets"] = enriched.get("issue_tickets") or node.get("issue_tickets") or []
                node["todo_items"] = enriched.get("todo_items") or node.get("todo_items") or []
                node["calendar_items"] = enriched.get("calendar_items") or node.get("calendar_items") or []
                if include_appointments:
                    node["appointments"] = appointments

    def _run_enrichment_batch(
        self,
        actor: dict[str, Any],
        task: str,
        document_numbers: list[str],
        run_id: str,
    ) -> None:
        """Run one bounded batch and persist a durable completion event."""
        counts = {"requested": len(document_numbers), "completed": 0, "failed": 0, "abstained": 0}
        keyman_transport = None
        product_transport = None
        try:
            if task in {"keyman", "all"}:
                keyman_transport, _ = lw.resolve_keyman_transport()
            if task in {"product", "appointments", "all"}:
                product_transport, _ = lw.resolve_product_transport()
            for document_no in document_numbers:
                try:
                    with psycopg.connect(self.dsn) as connection:
                        detail = lw.load_persisted_document_detail(
                            connection,
                            document_no,
                            persist_predicted_relatedness=True,
                        )
                    if not detail:
                        raise KeyError(document_no)
                    document = detail["document"]
                    if str(document.get("corp_code") or "").strip() != str(actor.get("corp_code") or "").strip():
                        raise PermissionError("enrichment_document_scope_changed")
                    if keyman_transport is not None and task in {"keyman", "all"}:
                        derived = lw.derive_keymen_via_llm(
                            document.get("title_sample"),
                            transport=keyman_transport,
                            authors={
                                "created_by": document.get("created_by"),
                                "changed_by": document.get("changed_by"),
                                "user_id": document.get("user_id"),
                            },
                        )
                        self._persist_keyman_result(
                            actor,
                            document_no,
                            document,
                            derived,
                            "live_http",
                            allow_empty=True,
                        )
                        counts["abstained"] += int(not derived.get("our_side") and not derived.get("counterpart_side"))
                    if product_transport is not None and task in {"product", "all"}:
                        self._persist_product_enrichment(
                            actor,
                            document,
                            product_transport,
                            include_appointments=task == "all",
                        )
                    elif product_transport is not None and task == "appointments":
                        self._persist_product_enrichment(
                            actor,
                            document,
                            product_transport,
                            include_appointments=True,
                        )
                    counts["completed"] += 1
                except (KeyError, RuntimeError, ValueError, PermissionError, OSError):
                    counts["failed"] += 1
            with psycopg.connect(self.dsn) as connection:
                lw.enqueue_event_outbox(
                    connection,
                    "llm_enrichment_batch_completed",
                    "batch",
                    actor["account_id"],
                    {"run_id": run_id, "task": task, **counts},
                )
        except (RuntimeError, OSError):
            counts["failed"] = counts["requested"] - counts["completed"]
        finally:
            self._flush_event_outbox()
            with self._enrichment_lock:
                self._enrichment_inflight.pop(run_id, None)

    def run_enrichment(self, actor: dict[str, Any], body: dict[str, Any]) -> dict[str, Any]:
        """Queue a bounded admin-only LLM enrichment batch through PostgreSQL outbox."""
        self._require_keyverse_admin(actor)
        task = str(body.get("task") or "all").strip().casefold()
        if task not in ENRICHMENT_TASKS:
            raise ValueError("unknown_enrichment_task")
        try:
            requested_limit = int(body.get("limit") or 16)
        except (TypeError, ValueError) as exc:
            raise ValueError("enrichment_limit_invalid") from exc
        limit = max(1, min(requested_limit, ENRICHMENT_BATCH_LIMIT))
        with psycopg.connect(self.dsn) as connection:
            document_numbers = self._enrichment_candidates(connection, actor, task, limit)
            run_id = f"enrichment-{secrets.token_urlsafe(12)}"
            lw.enqueue_event_outbox(
                connection,
                "llm_enrichment_batch_requested",
                "batch",
                actor["account_id"],
                {"run_id": run_id, "task": task, "requested": len(document_numbers)},
            )
        if not document_numbers:
            self._flush_event_outbox()
            return {"status": "empty", "run_id": run_id, "task": task, "requested": 0}
        run = {"run_id": run_id, "task": task, "requested": len(document_numbers), "status": "running"}
        with self._enrichment_lock:
            self._enrichment_inflight[run_id] = run
        threading.Thread(
            target=self._run_enrichment_batch,
            args=(dict(actor), task, document_numbers, run_id),
            daemon=True,
            name=f"lineageweave-enrichment-{run_id}",
        ).start()
        self._flush_event_outbox()
        return {**run, "status": "queued"}

    def tepp_status(self, actor: dict[str, Any]) -> dict[str, Any]:
        """Return administrator-scoped TEPP configuration and persisted run metadata."""
        self._require_keyverse_admin(actor)
        try:
            lw.tepp_http_config()
            configured = True
            reason = "configured"
        except RuntimeError as exc:
            configured = False
            reason = str(exc)
        with psycopg.connect(self.dsn) as connection:
            runs = lw.load_tepp_run_records(connection, actor)
        return {
            "contract_version": lw.TEPP_CONTRACT_VERSION,
            "configured": configured,
            "status": "ready" if configured else "unavailable",
            "reason": reason,
            "runs": runs,
        }

    def refresh_reports(self, actor: dict[str, Any]) -> dict[str, Any]:
        """Retry stale report judging/linking for an administrator without inventing scores."""
        self._require_keyverse_admin(actor)
        refreshed = self.refresh_persisted_reports()
        with psycopg.connect(self.dsn) as connection:
            lw.enqueue_event_outbox(
                connection,
                "period_report_refresh_completed",
                "reports",
                actor["account_id"],
                {"refreshed": refreshed},
            )
            connection.commit()
        self._flush_event_outbox()
        return {"status": "refreshed" if refreshed else "unchanged", "refreshed": refreshed}

    def submit_tepp_analysis(self, actor: dict[str, Any], body: dict[str, Any]) -> dict[str, Any]:
        """Submit an idempotent TEPP analysis request through the external HTTP boundary."""
        self._require_keyverse_admin(actor)
        request = lw.normalize_tepp_analysis_request(body)
        with psycopg.connect(self.dsn) as connection:
            existing = lw.load_tepp_run_by_idempotency(connection, actor, request["idempotency_key"])
        if existing:
            if existing["request_sha256"] != request["request_sha256"]:
                raise ValueError("tepp_idempotency_conflict")
            return {"status": "existing", **existing}
        base_url, token = lw.tepp_http_config()
        response = lw.post_tepp_analysis_run(request, base_url=base_url, token=token)
        with psycopg.connect(self.dsn) as connection:
            record = lw.persist_tepp_run_record(connection, actor, request, response)
            lw.enqueue_event_outbox(
                connection,
                "tepp_analysis_run_submitted",
                f"tepp:{record['run_id']}",
                actor["account_id"],
                {"run_id": record["run_id"], "state": record["remote_state"]},
            )
        self._flush_event_outbox()
        return {"status": "accepted", **record}

    def refresh_tepp_analysis(self, actor: dict[str, Any], run_id: str) -> dict[str, Any]:
        """Refresh one same-corp TEPP run and persist only its bounded lifecycle metadata."""
        self._require_keyverse_admin(actor)
        base_url, token = lw.tepp_http_config()
        response = lw.get_tepp_analysis_run(run_id, base_url=base_url, token=token)
        with psycopg.connect(self.dsn) as connection:
            return lw.update_tepp_run_state(connection, actor, run_id, response)

    def event_queue_health(self) -> dict[str, Any]:
        """Expose queue liveness and durable outbox backlog without secrets."""
        pending = 0
        try:
            with psycopg.connect(self.dsn) as connection:
                pending = len(lw.pending_event_outbox(connection))
        except Exception:
            pass
        try:
            ready = lw.valkey_ping()
        except (OSError, RuntimeError, ValueError):
            ready = False
        return {"stream": lw.VALKEY_EVENT_STREAM, "ready": ready, "pending_outbox": pending}

    def _development_actor(self) -> Optional[dict[str, Any]]:
        """Read an explicit local actor only when development mode is enabled."""
        if os.environ.get("LINEAGEWEAVE_DEV_MODE") != "1":
            return None
        raw = os.environ.get("LINEAGEWEAVE_DEV_ACTOR_JSON")
        if not raw:
            return None
        try:
            parsed = json.loads(raw)
            actor = _actor_from_value(parsed)
            if actor:
                return actor
        except json.JSONDecodeError:
            pass
        unquoted = raw.strip()
        if (unquoted.startswith("'") and unquoted.endswith("'")) or (unquoted.startswith('"') and unquoted.endswith('"')):
            unquoted = unquoted[1:-1]
            try:
                actor = _actor_from_value(json.loads(unquoted))
                if actor:
                    return actor
            except json.JSONDecodeError:
                pass
        if "\\" in unquoted:
            try:
                escaped = unquoted.encode("utf-8").decode("unicode_escape")
                actor = _actor_from_value(json.loads(escaped))
                if actor:
                    return actor
            except (json.JSONDecodeError, UnicodeDecodeError, ValueError):
                pass
        return None

    def _keyverse_settings(
        self, request_headers: Mapping[str, str] | None = None
    ) -> dict[str, str]:
        """Load the required confidential Keyverse OIDC relying-party settings."""
        issuer = (os.environ.get("KEYVERSE_ISSUER") or "").strip()
        client_id = (os.environ.get("LINEAGEWEAVE_OIDC_CLIENT_ID") or "").strip()
        client_secret = (os.environ.get("LINEAGEWEAVE_OIDC_CLIENT_SECRET") or "").strip()
        redirect_uri = _render_keyverse_redirect_uri(
            (os.environ.get("LINEAGEWEAVE_OIDC_REDIRECT_URI") or "").strip(),
            request_headers,
        )
        if not issuer or not client_id or not client_secret or not redirect_uri:
            raise RuntimeError("keyverse_oidc_configuration_required")
        return {
            "issuer": _https_url(issuer, "KEYVERSE_ISSUER"),
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": _https_url(
                redirect_uri, "LINEAGEWEAVE_OIDC_REDIRECT_URI", preserve_trailing_slash=True
            ),
        }

    def _keyverse_metadata(
        self, request_headers: Mapping[str, str] | None = None
    ) -> dict[str, str]:
        """Discover and cache only the exact Keyverse OIDC endpoints we use."""
        settings = self._keyverse_settings(request_headers=request_headers)
        now = time.time()
        with self._session_lock:
            cached = self._keyverse_metadata_cache
            if cached and cached.get("issuer") == settings["issuer"] and now < self._keyverse_metadata_expires_at:
                return {**cached, **settings}
        discovery_url = settings["issuer"] + "/.well-known/openid-configuration"
        request = urllib.request.Request(discovery_url, headers={"accept": "application/json"})
        try:
            with urllib.request.urlopen(  # nosemgrep: python.lang.security.audit.dynamic-urllib-use-detected.dynamic-urllib-use-detected
                request, timeout=10, context=_transport_context(discovery_url)
            ) as response:
                metadata = json.loads(response.read().decode("utf-8"))
        except (urllib.error.HTTPError, urllib.error.URLError, json.JSONDecodeError) as exc:
            raise RuntimeError("keyverse_discovery_failed") from exc
        if not isinstance(metadata, dict) or str(metadata.get("issuer") or "").rstrip("/") != settings["issuer"]:
            raise RuntimeError("keyverse_discovery_invalid")
        endpoints: dict[str, str] = {"issuer": settings["issuer"]}
        issuer_origin = urllib.parse.urlsplit(settings["issuer"]).netloc.lower()
        for field in ("authorization_endpoint", "token_endpoint", "introspection_endpoint"):
            try:
                endpoint = _https_url(str(metadata.get(field) or ""), field)
            except RuntimeError as exc:
                raise RuntimeError("keyverse_discovery_invalid") from exc
            if urllib.parse.urlsplit(endpoint).netloc.lower() != issuer_origin:
                raise RuntimeError("keyverse_discovery_invalid")
            endpoints[field] = endpoint
        with self._session_lock:
            self._keyverse_metadata_cache = endpoints
            self._keyverse_metadata_expires_at = now + 300
        return {**endpoints, **settings}

    def _prune_auth_state(self) -> None:
        """Bound opaque local state by its Keyverse access-token lifetime."""
        now = time.time()
        for token, session in list(self._sessions.items()):
            if float(session.get("expires_at") or 0) <= now:
                self._sessions.pop(token, None)
        for state, pending in list(self._keyverse_states.items()):
            if float(pending.get("expires_at") or 0) <= now:
                self._keyverse_states.pop(state, None)

    @staticmethod
    def _pkce_challenge(verifier: str) -> str:
        """Return the required S256 PKCE code challenge."""
        digest = hashlib.sha256(verifier.encode("ascii")).digest()
        return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")

    def begin_keyverse_login(
        self, request_headers: Mapping[str, str] | None = None, *, email_address: object
    ) -> tuple[str, str]:
        """Create an authorization-code + PKCE request for a Keyverse account."""
        email = _normalized_email_address(email_address)
        metadata = self._keyverse_metadata(request_headers=request_headers)
        state = secrets.token_urlsafe(32)
        verifier = secrets.token_urlsafe(64)
        with self._session_lock:
            self._prune_auth_state()
            if len(self._keyverse_states) >= MAX_KEYVERSE_PENDING_STATES:
                raise RuntimeError("keyverse_login_capacity")
            self._keyverse_states[state] = {
                "code_verifier": verifier,
                "issuer": metadata["issuer"],
                "client_id": metadata["client_id"],
                "redirect_uri": metadata["redirect_uri"],
                "expires_at": time.time() + KEYVERSE_STATE_TTL_SECONDS,
            }
        query = urllib.parse.urlencode(
            {
                "response_type": "code",
                "client_id": metadata["client_id"],
                "redirect_uri": metadata["redirect_uri"],
                "scope": KEYVERSE_SCOPE,
                "login_hint": email,
                "state": state,
                "code_challenge": self._pkce_challenge(verifier),
                "code_challenge_method": "S256",
            }
        )
        return loopback_oidc_url(metadata["authorization_endpoint"] + "?" + query), state

    @staticmethod
    def _client_basic_auth(metadata: dict[str, str]) -> str:
        """Encode the confidential client credentials without logging either value."""
        client_id = urllib.parse.quote(metadata["client_id"], safe="")
        client_secret = urllib.parse.quote(metadata["client_secret"], safe="")
        encoded = base64.b64encode(f"{client_id}:{client_secret}".encode("utf-8")).decode("ascii")
        return "Basic " + encoded

    def _keyverse_form_post(
        self,
        endpoint: str,
        fields: dict[str, str],
        metadata: dict[str, str],
        *,
        failure: str,
    ) -> dict[str, Any]:
        """POST a confidential OAuth form over verified TLS without reflecting secrets."""
        request = urllib.request.Request(
            endpoint,
            data=urllib.parse.urlencode(fields).encode("utf-8"),
            headers={
                "accept": "application/json",
                "content-type": "application/x-www-form-urlencoded",
                "authorization": self._client_basic_auth(metadata),
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(  # nosemgrep: python.lang.security.audit.dynamic-urllib-use-detected.dynamic-urllib-use-detected
                request, timeout=10, context=_transport_context(endpoint)
            ) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (urllib.error.HTTPError, urllib.error.URLError, json.JSONDecodeError) as exc:
            raise RuntimeError(failure) from exc
        if not isinstance(payload, dict):
            raise RuntimeError(failure)
        return payload

    def _actor_from_keyverse_access_token(
        self, access_token: str, metadata: dict[str, str]
    ) -> tuple[dict[str, Any], float]:
        """Ask Keyverse to validate a bearer token and enforce its RP claims."""
        token = access_token.strip()
        if not token or len(token) > 16_384:
            raise RuntimeError("keyverse_token_invalid")
        claims = self._keyverse_form_post(
            metadata["introspection_endpoint"],
            {"token": token, "token_type_hint": "access_token"},
            metadata,
            failure="keyverse_introspection_failed",
        )
        if claims.get("active") is not True:
            raise RuntimeError("keyverse_token_invalid")
        if str(claims.get("iss") or "").rstrip("/") != metadata["issuer"]:
            raise RuntimeError("keyverse_token_invalid")
        audience = claims.get("aud")
        audiences = [audience] if isinstance(audience, str) else audience if isinstance(audience, list) else []
        authorized_audiences = {str(item) for item in audiences}
        if (
            metadata["client_id"] not in authorized_audiences
            and str(claims.get("azp") or "") != metadata["client_id"]
        ):
            raise RuntimeError("keyverse_token_invalid")
        if str(claims.get("client_id") or "") != metadata["client_id"]:
            raise RuntimeError("keyverse_token_invalid")
        try:
            expires_at = float(claims.get("exp"))
        except (TypeError, ValueError) as exc:
            raise RuntimeError("keyverse_token_invalid") from exc
        if expires_at <= time.time():
            raise RuntimeError("keyverse_token_invalid")
        raw_roles = claims.get("role")
        if isinstance(raw_roles, list):
            roles = [KEYVERSE_PRODUCT_ROLE_MAP.get(str(value).strip().casefold()) for value in raw_roles]
        else:
            roles = [KEYVERSE_PRODUCT_ROLE_MAP.get(str(raw_roles or "").strip().casefold())]
        actor = _actor_from_value(
            {
                "sub": claims.get("sub"),
                "org": claims.get("org"),
                "workspace": claims.get("workspace"),
                "roles": [role for role in roles if role],
            }
        )
        if not actor:
            raise RuntimeError("keyverse_claims_invalid")
        return actor, expires_at

    def complete_keyverse_login(
        self, code: str, state: str, state_cookie: str, request_headers: Mapping[str, str] | None = None
    ) -> tuple[str, dict[str, Any], int]:
        """Exchange a PKCE code, introspect its access token, and issue a bounded local session."""
        if (
            not code
            or len(code) > 4_096
            or not state
            or len(state) > 256
            or not state.isascii()
            or not state_cookie.isascii()
        ):
            raise RuntimeError("keyverse_callback_invalid")
        if not state_cookie or not hmac.compare_digest(state, state_cookie):
            raise RuntimeError("keyverse_callback_invalid")
        with self._session_lock:
            self._prune_auth_state()
            pending = self._keyverse_states.pop(state, None)
        if not pending:
            raise RuntimeError("keyverse_callback_invalid")
        metadata = self._keyverse_metadata(request_headers=request_headers)
        if any(pending.get(field) != metadata.get(field) for field in ("issuer", "client_id", "redirect_uri")):
            raise RuntimeError("keyverse_callback_invalid")
        token_response = self._keyverse_form_post(
            metadata["token_endpoint"],
            {
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": metadata["redirect_uri"],
                "code_verifier": str(pending["code_verifier"]),
            },
            metadata,
            failure="keyverse_token_exchange_failed",
        )
        if str(token_response.get("token_type") or "").casefold() != "bearer":
            raise RuntimeError("keyverse_token_exchange_failed")
        actor, token_expires_at = self._actor_from_keyverse_access_token(
            str(token_response.get("access_token") or ""), metadata
        )
        ttl = min(_session_ttl_seconds(), max(0, int(token_expires_at - time.time())))
        if ttl <= 0:
            raise RuntimeError("keyverse_token_invalid")
        session_token = secrets.token_urlsafe(32)
        with self._session_lock:
            self._sessions[session_token] = {
                "actor": actor,
                "expires_at": time.time() + ttl,
            }
        return session_token, actor, ttl

    @staticmethod
    def _require_keyverse_admin(actor: dict[str, Any]) -> str:
        """Require a verified same-product administrator and return its corp scope."""
        roles = {str(role).strip().casefold() for role in actor.get("roles") or []}
        corp_code = str(actor.get("corp_code") or "").strip()
        if "admin" not in roles or not corp_code:
            raise PermissionError("keyverse_admin_required")
        return corp_code

    def keyverse_admin_accounts(
        self, actor: dict[str, Any], *, query: str = "", limit: int = KEYVERSE_ADMIN_ACCOUNT_LIMIT
    ) -> dict[str, Any]:
        """List tenant-scoped Keyverse accounts through the server-owned Admin REST adapter."""
        corp_code = self._require_keyverse_admin(actor)
        admin_base, client_id = _keyverse_admin_context()
        token = _keyverse_admin_access_token()
        roles = _keyverse_client_roles(admin_base, token, client_id)
        bounded_limit = max(1, min(int(limit), KEYVERSE_ADMIN_ACCOUNT_LIMIT))
        normalized_query = str(query or "").strip()
        if len(normalized_query) > 128:
            raise ValueError("keyverse_account_query_too_long")
        parameters = {"first": "0", "max": str(bounded_limit)}
        if normalized_query:
            parameters["search"] = normalized_query
        raw_users = _admin_json(f"{admin_base}/users?{urllib.parse.urlencode(parameters)}", token)
        if not isinstance(raw_users, list):
            raise RuntimeError("keyverse_admin_accounts_invalid")
        client = _keyverse_client_descriptor(admin_base, token, client_id)
        accounts: list[dict[str, Any]] = []
        for raw_user in raw_users:
            account = _keyverse_account_view(raw_user, [])
            if account is None or (account["org"] and account["org"] != corp_code):
                continue
            mappings = _keyverse_role_mappings(admin_base, token, account["account_id"], client["id"])
            account["roles"] = sorted({mapping["name"] for mapping in mappings if mapping.get("name")})
            accounts.append(account)
        return {
            "corp_code": corp_code,
            "client_id": client_id,
            "available_roles": roles,
            "accounts": accounts,
        }

    def update_keyverse_account(
        self, actor: dict[str, Any], user_id: str, body: dict[str, Any]
    ) -> dict[str, Any]:
        """Update only reviewed org/workspace claims and direct roles for one same-client account."""
        corp_code = self._require_keyverse_admin(actor)
        account_id = str(user_id or "").strip()
        if not account_id or len(account_id) > 128 or any(char in account_id for char in "?/\\"):
            raise ValueError("keyverse_account_id_invalid")
        admin_base, client_id = _keyverse_admin_context()
        token = _keyverse_admin_access_token()
        client = _keyverse_client_descriptor(admin_base, token, client_id)
        roles = _keyverse_client_roles(admin_base, token, client_id)
        role_by_name = {role["name"]: role for role in roles}
        target_url = f"{admin_base}/users/{urllib.parse.quote(account_id, safe='')}"
        target = _admin_json(target_url, token)
        if not isinstance(target, dict) or str(target.get("id") or "") != account_id:
            raise KeyError(account_id)
        existing_org = _keyverse_scalar_attribute(target, "org")
        if existing_org and existing_org != corp_code:
            raise PermissionError("keyverse_account_cross_corp")
        requested_org = _keyverse_claim_value(body.get("org", corp_code), "org", required=True)
        if requested_org != corp_code:
            raise PermissionError("keyverse_account_cross_corp")
        workspace = _keyverse_claim_value(body.get("workspace"), "workspace", required=True)
        requested_roles = body.get("roles")
        if not isinstance(requested_roles, list):
            raise ValueError("keyverse_roles_required")
        role_names: list[str] = []
        for role in requested_roles:
            normalized_role = _keyverse_claim_value(role, "role", required=True)
            if normalized_role not in role_by_name:
                raise ValueError("keyverse_role_unavailable")
            if normalized_role not in role_names:
                role_names.append(normalized_role)
        attributes = dict(target.get("attributes") or {}) if isinstance(target.get("attributes"), dict) else {}
        attributes["org"] = [requested_org]
        attributes["workspace"] = [workspace]
        _admin_json(target_url, token, method="PUT", body={"attributes": attributes})
        current_mappings = _keyverse_role_mappings(admin_base, token, account_id, client["id"])
        current_names = {mapping["name"] for mapping in current_mappings}
        additions = [_keyverse_role_assignment(role_by_name[name]) for name in role_names if name not in current_names]
        removals = [
            _keyverse_role_assignment(mapping)
            for mapping in current_mappings
            if mapping["name"] not in role_names
        ]
        mapping_url = f"{admin_base}/users/{urllib.parse.quote(account_id, safe='')}/role-mappings/clients/{urllib.parse.quote(client['id'], safe='')}"
        if additions:
            _admin_json(mapping_url, token, method="POST", body=additions)
        if removals:
            _admin_json(mapping_url, token, method="DELETE", body=removals)
        updated = dict(target)
        updated["attributes"] = attributes
        return _keyverse_account_view(
            updated,
            [{"id": role_by_name[name]["id"], "name": name} for name in role_names],
        )

    def logout(self, session_token: str) -> None:
        """Remove only the local RP session; Keyverse remains the IdP authority."""
        if session_token:
            with self._session_lock:
                self._sessions.pop(session_token, None)

    def actor_for_request(self, handler: BaseHTTPRequestHandler) -> Optional[dict[str, Any]]:
        """Resolve an explicit development actor, local OIDC session, or verified bearer token."""
        development_actor = self._development_actor()
        if development_actor:
            return development_actor
        session_token = _cookie_value(handler.headers, "lw_session")
        with self._session_lock:
            self._prune_auth_state()
            session = self._sessions.get(session_token)
            if session:
                actor = session.get("actor")
                return actor if isinstance(actor, dict) else None
        authorization = str(handler.headers.get("Authorization") or "")
        scheme, separator, access_token = authorization.partition(" ")
        if separator and scheme.casefold() == "bearer":
            try:
                actor, _expires_at = self._actor_from_keyverse_access_token(
                    access_token, self._keyverse_metadata(handler.headers)
                )
                return actor
            except RuntimeError:
                return None
        return None

    def payload(self) -> dict[str, Any]:
        """Load the persisted PostgreSQL snapshot, rebuilding only when empty."""
        with self._payload_lock:
            if self._payload is not None:
                return self._payload
            with psycopg.connect(self.dsn) as connection:
                persisted = lw.load_persisted_analysis_payload(
                    connection, include_knowledge_graph=True
                )
                if persisted.get("nodes"):
                    lw.load_database_overrides(connection, persisted)
                    if not (persisted.get("knowledge_graph") or {}).get("nodes"):
                        persisted["knowledge_graph"] = lw.build_knowledge_graph(
                            persisted.get("nodes") or [],
                            persisted.get("edges") or [],
                            customer_master=persisted.get("customer_master") or {},
                        )
                        lw.persist_knowledge_graph_snapshot(
                            connection, persisted["knowledge_graph"]
                        )
                    else:
                        persisted["knowledge_graph"] = lw.attach_customer_master_knowledge_graph(
                            persisted["knowledge_graph"],
                            persisted.get("customer_master") or {},
                        )
                        persisted["knowledge_graph"], repaired_edges = (
                            lw.merge_lineage_evidence_into_knowledge_graph(
                                persisted["knowledge_graph"], persisted.get("edges") or []
                            )
                        )
                        if repaired_edges:
                            lw.persist_knowledge_graph_snapshot(
                                connection, persisted["knowledge_graph"]
                            )
                    self._payload = persisted
                    return self._payload
                rows = lw._database_query(connection, lw.build_source_query(self.source_table))
                enum_values = lw.ensure_common_enum_table(connection)
            transport, mode = lw.resolve_keyman_transport_optional()
            product_transport, product_mode = lw.resolve_product_transport_optional()
            payload = lw.build_payload(
                rows,
                enum_values=enum_values,
                keyman_transport=transport,
                product_transport=product_transport,
                keyman_limit=int(os.environ.get("LINEAGEWEAVE_KEYMAN_LIMIT", "0")),
            )
            payload["metadata"]["keyman_transport"] = mode
            payload["metadata"]["product_transport"] = product_mode
            payload["knowledge_graph"] = lw.build_knowledge_graph(
                payload.get("nodes") or [],
                payload.get("edges") or [],
                customer_master=payload.get("customer_master") or {},
            )
            with psycopg.connect(self.dsn) as connection:
                lw.persist_analysis_payload(
                    connection, payload, release_schema_locks=True
                )
                lw.load_database_overrides(connection, payload)
            self._payload = payload
            return payload

    def filtered_payload(self, actor: dict[str, Any]) -> dict[str, Any]:
        """Return an authorization-filtered snapshot for one verified actor."""
        return lw.filter_payload_for_actor(self.payload(), actor)

    def workspace_surface(self, actor: dict[str, Any]) -> dict[str, Any]:
        """Return analytics, reports, and affiliate clues without the full graph."""
        with psycopg.connect(self.dsn) as connection:
            surface = lw.load_workspace_surface(connection, actor=actor)
            visible_document_numbers = lw.load_authorized_report_document_numbers(connection, actor)
        return {
            "metadata": surface.get("metadata") or {},
            "analytics": surface.get("analytics") or {},
            "affiliate_tree": surface.get("affiliate_tree") or {"nodes": [], "edges": [], "parent_of": {}},
            "period_reports": lw.filter_period_reports_for_actor(
                surface.get("period_reports") or [],
                actor,
                visible_document_numbers=visible_document_numbers,
            ),
            "customer_master": surface.get("customer_master") or {},
            "factor_definitions": surface.get("factor_definitions")
            or lw.default_factor_definitions(),
        }

    def customer_surface(
        self, actor: dict[str, Any], *, query: str = "", limit: int = 100
    ) -> dict[str, Any]:
        """Return an evidence-scoped customer master with searched-account ancestry intact."""
        normalized_query = str(query or "").strip().casefold()
        if len(normalized_query) > 128:
            raise ValueError("customer_query_too_long")
        bounded_limit = max(1, min(int(limit), 200))
        with psycopg.connect(self.dsn) as connection:
            surface = lw.load_workspace_surface(connection, actor=actor)
        customer_master = surface.get("customer_master") or {}
        all_accounts = [
            dict(account)
            for account in customer_master.get("accounts") or []
        ]
        matched_accounts = [
            account
            for account in all_accounts
            if not normalized_query
            or normalized_query in " ".join(
                str(account.get(field) or "").casefold()
                for field in ("account_name", "parent_name", "tier", "entity_role")
            )
        ][:bounded_limit]
        matched_names = {
            str(account.get("account_name") or "")
            for account in matched_accounts
            if str(account.get("account_name") or "")
        }
        account_by_name = {
            str(account.get("account_name") or ""): account
            for account in all_accounts
            if str(account.get("account_name") or "")
        }
        account_names = set(matched_names)
        pending_names = set(account_names)
        parent_of = customer_master.get("parent_of") or {}
        while pending_names:
            parent_names = {
                str(parent_of.get(name) or "").strip()
                for name in pending_names
            } & set(account_by_name)
            pending_names = parent_names - account_names
            account_names.update(pending_names)
        accounts = matched_accounts + [
            account
            for account in all_accounts
            if str(account.get("account_name") or "") in account_names
            and str(account.get("account_name") or "") not in matched_names
        ]
        edges = [
            dict(edge)
            for edge in customer_master.get("edges") or []
            if str(edge.get("parent") or "") in account_names
            and str(edge.get("child") or "") in account_names
        ]
        return {
            "source": customer_master.get("source") or "empty",
            "accounts": accounts,
            "nodes": sorted(account_names),
            "edges": edges,
            "parent_of": {str(edge["child"]): str(edge["parent"]) for edge in edges},
        }

    def lineage_review_edges(
        self, actor: dict[str, Any], *, query: str = "", limit: int = 100
    ) -> dict[str, Any]:
        """Return same-corp inferred lineage candidates for the admin review screen."""
        self._require_keyverse_admin(actor)
        with psycopg.connect(self.dsn) as connection:
            return lw.load_lineage_review_edges(connection, actor, query=query, limit=limit)

    def update_lineage_edge_override(
        self, actor: dict[str, Any], body: dict[str, Any]
    ) -> dict[str, Any]:
        """Suppress or restore one non-transition inferred edge with an audit event."""
        self._require_keyverse_admin(actor)
        source_node = str(body.get("source_node") or "").strip()
        target_node = str(body.get("target_node") or "").strip()
        relation = str(body.get("relation") or body.get("relation_name") or "").strip()
        override_status = str(body.get("override_status") or body.get("decision") or "").strip()
        reason = str(body.get("reason") or "관리자 Lineage 검토").strip()
        if not source_node or not target_node or not relation:
            raise ValueError("lineage_edge_identity_required")
        if len(source_node) > 256 or len(target_node) > 256 or len(relation) > 128:
            raise ValueError("lineage_edge_identity_too_long")
        if override_status not in {"suppressed", "restored"}:
            raise ValueError("unknown_lineage_edge_override_status")
        if len(reason) > 500:
            raise ValueError("lineage_edge_reason_too_long")
        with psycopg.connect(self.dsn) as connection:
            review = lw.load_lineage_review_edges(connection, actor, limit=500)
            item = next(
                (
                    candidate
                    for candidate in review["items"]
                    if candidate["source_node"] == source_node
                    and candidate["target_node"] == target_node
                    and candidate["relation"] == relation
                ),
                None,
            )
            if item is None:
                raise KeyError("lineage_edge_not_found")
            if item["evidence_status"] not in {lw.EVIDENCE_INFERRED, lw.EVIDENCE_PREDICTED}:
                raise PermissionError("observed_transition_not_overridable")
            lw.persist_lineage_edge_override(
                connection,
                source_node=source_node,
                target_node=target_node,
                relation_name=relation,
                override_status=override_status,
                reason=reason or "관리자 Lineage 검토",
                updated_by=str(actor["account_id"]),
            )
            lw.enqueue_event_outbox(
                connection,
                "lineage_edge_override_changed",
                str(item["source_document"]),
                str(actor["account_id"]),
                {
                    "source_node": source_node,
                    "target_node": target_node,
                    "relation": relation,
                    "override_status": override_status,
                },
            )
        with self._payload_lock:
            self._payload = None
        self._flush_event_outbox()
        return {**item, "override_status": override_status, "reason": reason or "관리자 Lineage 검토"}

    def document(self, actor: dict[str, Any], document_no: str) -> dict[str, Any]:
        """Return one visible document, its rows, and its visible graph edges."""
        cached = self._payload is not None
        if cached:
            payload = self.filtered_payload(actor)
            documents = {
                node.get("document_no"): node
                for node in payload.get("nodes") or []
                if node.get("type") == "document"
            }
            document = documents.get(document_no)
            if not document:
                raise KeyError(document_no)
            rows = [
                node
                for node in payload.get("nodes") or []
                if node.get("type") == "row" and node.get("document_no") == document_no
            ]
            edges = [
                edge
                for edge in payload.get("edges") or []
                if edge.get("source") == document.get("id")
                or edge.get("target") == document.get("id")
                or edge.get("acthguid") == document.get("acthguid")
            ]
            knowledge_graph = lw.related_knowledge_graph(
                payload.get("knowledge_graph") or {}, document_no
            )
            event_lineage = None
        else:
            with psycopg.connect(self.dsn) as connection:
                detail = lw.load_persisted_document_detail(connection, document_no)
            if not detail:
                raise KeyError(document_no)
            document = detail["document"]
            decision = lw.authorize_access(actor=actor, resource=document, action="read")
            if not decision["allowed"]:
                raise KeyError(document_no)
            rows = list(detail.get("rows") or [])
            edges = list(detail.get("edges") or [])
            knowledge_graph = detail.get("knowledge_graph") or {"nodes": [], "edges": []}
            event_lineage = detail.get("event_lineage")
        persisted_appointments: list[dict[str, Any]] = []
        try:
            with psycopg.connect(self.dsn) as connection:
                persisted_appointments = lw._database_query(
                    connection,
                    f"""
                    SELECT appointment_id, document_no, occurred_on, label, excerpt, content_source
                    FROM {lw.ANALYSIS_APPOINTMENT_TABLE}
                    WHERE document_no = %s
                    """,
                    (document_no,),
                )
        except Exception:
            persisted_appointments = []
        appointments = lw.resolve_document_appointments(
            document, persisted=persisted_appointments or None
        )
        if appointments:
            document = dict(document)
            document["appointments"] = appointments
        our_side, counterpart_side = lw.separate_keyman_sides(
            document.get("keyman_our_side"),
            document.get("keyman_counterpart_side"),
            title=document.get("title_sample"),
            authors={
                "created_by": document.get("created_by"),
                "changed_by": document.get("changed_by"),
                "user_id": document.get("user_id"),
            },
        )
        if (
            our_side != (document.get("keyman_our_side") or [])
            or counterpart_side != (document.get("keyman_counterpart_side") or [])
        ):
            document = dict(document)
            document["keyman_our_side"] = our_side
            document["keyman_counterpart_side"] = counterpart_side
        pending_work = any(
            str(item.get("source") or item.get("content_source") or "") == "pending_llm"
            for item in (document.get("todo_items") or []) + (document.get("calendar_items") or [])
        ) or (bool(document.get("issue_tickets")) and not document.get("todo_items"))
        if pending_work:
            self._schedule_document_work(actor, document)
        if event_lineage is None:
            event_lineage = lw.build_event_lineage(document, edges)
        return {
            "document": document,
            "rows": rows,
            "edges": edges,
            "knowledge_graph": knowledge_graph,
            "event_lineage": event_lineage,
            "ticket_status_options": [
                {"code": row["enum_code"], "label": row["enum_label"]}
                for row in lw.DEFAULT_ENUM_ROWS
                if row["enum_family"] == "ticket_status"
            ],
        }

    def document_index(
        self,
        actor: dict[str, Any],
        limit: int,
        offset: int = 0,
        search: str = "",
    ) -> dict[str, Any]:
        """Return a bounded, authorization-filtered document index for the React list."""
        with psycopg.connect(self.dsn) as connection:
            # The index stays a bounded SQL read even after another endpoint has
            # warmed the full graph; scanning/filtering that cache stalls searches.
            return lw.load_visible_document_index(connection, actor, limit, offset, search)

    def knowledge(self, actor: dict[str, Any], document_no: str, query: dict[str, list[str]]) -> dict[str, Any]:
        """Return a Keyman-centered neighborhood from the persisted KG, not one document."""
        node_id = (query.get("node") or [""])[0]
        person = (query.get("person") or [""])[0]
        raw_depth = (query.get("depth") or [""])[0]
        try:
            depth = None if not raw_depth else max(0, min(int(raw_depth), 8))
        except ValueError as exc:
            raise ValueError("depth must be an integer") from exc
        try:
            with psycopg.connect(self.dsn) as connection:
                detail = lw.load_persisted_document_detail(connection, document_no)
                if detail:
                    decision = lw.authorize_access(
                        actor=actor, resource=detail["document"], action="read"
                    )
                    if not decision["allowed"]:
                        raise KeyError(document_no)
                    if person:
                        neighborhood = lw.load_persisted_keyman_neighborhood(
                            connection, person, depth=depth
                        )
                        if neighborhood.get("nodes"):
                            return neighborhood
                    seeds = {node_id} if node_id else {f"kg:document:{document_no}", f"doc:{document_no}"}
                    neighborhood = lw.load_persisted_knowledge_neighborhood(
                        connection, seeds, depth=depth
                    )
                    if neighborhood.get("nodes"):
                        return neighborhood
        except KeyError:
            raise
        except Exception:
            neighborhood = {"nodes": [], "edges": [], "depths": {}}
        if self._payload is not None:
            graph = self.filtered_payload(actor).get("knowledge_graph") or {}
        else:
            detail = self.document(actor, document_no)
            graph = detail.get("knowledge_graph") or {}
            if not graph.get("nodes"):
                graph = lw.build_knowledge_graph(
                    [detail["document"]], detail.get("edges") or []
                )
        if person:
            return lw.related_keyman_graph(graph, person, depth=depth)
        if node_id:
            return lw.knowledge_neighborhood(graph, {node_id}, depth=depth)
        return lw.related_knowledge_graph(graph, document_no, depth=depth)

    def _document_content_records(self, document_no: str) -> list[dict[str, Any]]:
        """Read authorized document cells directly from PostgreSQL for local processing."""
        with psycopg.connect(self.dsn) as connection:
            return lw._database_query(
                connection,
                f"""
                SELECT guid_field, source_row_number, voccts_field
                FROM {self.source_table}
                WHERE docnosub_field = %s
                ORDER BY source_row_number
                """,
                (document_no,),
            )

    def _document_content_structure(self, document_no: str) -> dict[str, list[dict[str, Any]]]:
        """Build location-preserving DOM and asset profiles without raw source output."""
        blocks: list[dict[str, Any]] = []
        assets: list[dict[str, Any]] = []
        for record in self._document_content_records(document_no):
            evidence_id = str(record.get("guid_field") or record.get("source_row_number") or "unknown")
            source_row_number = record.get("source_row_number")
            structure = lw.extract_content_structure(record.get("voccts_field"))
            for block in structure["blocks"]:
                profile = dict(block)
                profile.update(
                    {
                        "block_index": len(blocks),
                        "source_evidence_id": evidence_id,
                        "source_row_number": source_row_number,
                    }
                )
                blocks.append(profile)
            for asset in structure["assets"]:
                profile = dict(asset)
                profile.update(
                    {
                        "asset_index": len(assets),
                        "source_evidence_id": evidence_id,
                        "source_row_number": source_row_number,
                    }
                )
                assets.append(profile)
        return {"blocks": blocks, "assets": assets}

    def _materialize_document_content(self, document_no: str) -> dict[str, list[dict[str, Any]]]:
        """Persist one safe content profile and its semantic KG slice before use."""
        structure = self._document_content_structure(document_no)
        with self._payload_lock:
            graph = None
            if self._payload is not None:
                graph = lw.attach_document_content_knowledge_graph(
                    self._payload.get("knowledge_graph") or {}, document_no, structure
                )
                self._payload["knowledge_graph"] = graph
            with psycopg.connect(self.dsn) as connection:
                lw.persist_document_content_structure(connection, document_no, structure)
                if graph is not None:
                    lw.persist_knowledge_graph_snapshot(connection, graph)
        return structure

    def _document_assets(self, document_no: str) -> list[dict[str, Any]]:
        """Materialize private document-local asset handles after authorization."""
        assets: list[dict[str, Any]] = []
        for record in self._document_content_records(document_no):
            for asset in lw.extract_inline_assets(record.get("voccts_field")):
                private = dict(asset)
                private["asset_index"] = len(assets)
                private["row_guid"] = record.get("guid_field")
                private["source_row_number"] = record.get("source_row_number")
                private["asset_sha256"] = lw.content_asset_sha256(private)
                assets.append(private)
        return assets

    def content_manifest(self, actor: dict[str, Any], document_no: str) -> dict[str, Any]:
        """Return a visible document's persisted DOM semantics and asset metadata."""
        self.document(actor, document_no)
        try:
            structure = self._materialize_document_content(document_no)
            assets = structure["assets"]
        except Exception:
            structure = {"blocks": [], "assets": []}
            assets = []
        inspections: list[dict[str, Any]] = []
        label_rows: list[dict[str, Any]] = []
        try:
            with psycopg.connect(self.dsn) as connection:
                lw.ensure_content_inspection_tables(connection)
                inspections = lw._database_query(
                    connection,
                    f"""
                    SELECT asset_index, source_evidence_id, source_row_number, source_position,
                           mime_type, asset_sha256, ocr_text, model_name, inspected_by, inspected_at
                    FROM {lw.ANALYSIS_INSPECTION_TABLE}
                    WHERE document_no = %s
                    ORDER BY asset_index
                    """,
                    (document_no,),
                )
                label_rows = lw._database_query(
                    connection,
                    f"""
                    SELECT link.asset_index, catalog.label_name, link.label_description,
                           link.label_position
                    FROM {lw.ANALYSIS_INSPECTION_LABEL_TABLE} AS link
                    JOIN {lw.ANALYSIS_OBJECT_LABEL_TABLE} AS catalog
                      ON catalog.label_name = link.label_name
                    WHERE link.document_no = %s
                    ORDER BY link.asset_index, link.label_position, catalog.label_name
                    """,
                    (document_no,),
                )
        except Exception:
            inspections = []
            label_rows = []
        labels_by_asset: dict[int, list[dict[str, str]]] = {}
        for label_row in label_rows:
            labels_by_asset.setdefault(int(label_row["asset_index"]), []).append(
                {
                    "label": str(label_row.get("label_name") or ""),
                    "description": str(label_row.get("label_description") or ""),
                }
            )
        inspections_by_asset = {int(item["asset_index"]): item for item in inspections}
        matched_inspections: list[dict[str, Any]] = []
        public_assets: list[dict[str, Any]] = []
        for asset in assets:
            public = lw.public_asset_metadata(asset)
            inspection = inspections_by_asset.get(int(asset["asset_index"]))
            if inspection and inspection.get("asset_sha256") == asset["asset_sha256"]:
                inspection = dict(inspection)
                inspection["object_labels"] = labels_by_asset.get(int(asset["asset_index"]), [])
                inspection.pop("asset_sha256", None)
                public["inspection"] = inspection
                matched_inspections.append(inspection)
            public_assets.append(public)
        return {
            "document_no": document_no,
            "assets": public_assets,
            "asset_count": len(public_assets),
            "inspections": matched_inspections,
            "semantic_blocks": [
                lw.public_content_block(block)
                for block in structure["blocks"][:lw.MAX_CONTENT_MANIFEST_BLOCKS]
            ],
            "semantic_block_count": len(structure["blocks"]),
        }

    def index_document_embeddings(self, actor: dict[str, Any], document_no: str) -> dict[str, Any]:
        """Embed one authorized document's persisted DOM units through the live gateway."""
        item = self.document(actor, document_no)["document"]
        decision = lw.authorize_access(actor=actor, resource=item, action="manage_lineage")
        if not decision["allowed"]:
            raise PermissionError(decision["reason"])
        structure = self._materialize_document_content(document_no)
        chunks = lwe.build_embedding_chunks(document_no, structure)
        if not chunks:
            raise ValueError("document has no embeddable semantic text")
        embedding_result = lwe.derive_document_embeddings(
            chunks,
            transport=lwe.make_live_embedding_transport(),
        )
        with psycopg.connect(self.dsn) as connection:
            embedded_count = lwe.persist_document_embeddings(connection, document_no, embedding_result)
            lw.enqueue_event_outbox(
                connection,
                "document_semantic_indexed",
                document_no,
                actor["account_id"],
                {
                    "chunk_count": embedded_count,
                    "model_name": embedding_result["model_name"],
                    "vector_dimensions": embedding_result["vector_dimensions"],
                },
            )
        self._flush_event_outbox()
        return {
            "document_no": document_no,
            "chunk_count": embedded_count,
            "model_name": embedding_result["model_name"],
            "vector_dimensions": embedding_result["vector_dimensions"],
            "source": embedding_result["provider_kind"],
        }

    def semantic_related_documents(
        self,
        actor: dict[str, Any],
        document_no: str,
        limit: int = 12,
    ) -> dict[str, Any]:
        """Rank only visible, previously indexed documents as inferred semantic relatedness."""
        self.document(actor, document_no)
        with psycopg.connect(self.dsn) as connection:
            anchors = lwe.load_document_embeddings(connection, document_no)
            if not anchors:
                return {"document_no": document_no, "status": "index_required", "items": []}
            candidates, truncated = lwe.load_authorized_embedding_candidates(
                connection,
                actor,
                str(anchors[0]["model_name"]),
            )
        document_by_no = {
            str(row["document_no"]): {
                "title": row.get("title"),
                "visibility": row.get("visibility"),
            }
            for row in candidates
            if row.get("document_no")
        }
        related = lwe.rank_related_documents(document_no, anchors, candidates, limit=limit)
        return {
            "document_no": document_no,
            "status": "candidate_limit_reached" if truncated else "ready",
            "items": [
                {
                    **row,
                    "title": document_by_no.get(row["document_no"], {}).get("title"),
                    "visibility": document_by_no.get(row["document_no"], {}).get("visibility"),
                }
                for row in related
            ],
        }

    def semantic_search_documents(
        self,
        actor: dict[str, Any],
        query: str,
        limit: int = 12,
    ) -> dict[str, Any]:
        """Rank actor-visible indexed documents for one bounded natural-language query."""
        term = str(query or "").strip()
        if len(term) < 2:
            raise ValueError("semantic search query must contain at least two characters")
        if len(term) > 200:
            raise ValueError("semantic search query is too long")
        chunks = lwe.build_embedding_chunks(
            "semantic-query",
            {
                "blocks": [
                    {
                        "block_index": 0,
                        "source_evidence_id": "query",
                        "source_position": 0,
                        "text_content": term,
                    }
                ]
            },
            maximum_chunks=1,
        )
        query_embedding = lwe.derive_document_embeddings(
            chunks,
            transport=lwe.make_live_embedding_transport(),
        )
        with psycopg.connect(self.dsn) as connection:
            candidates, truncated = lwe.load_authorized_embedding_candidates(
                connection,
                actor,
                query_embedding["model_name"],
            )
        if not candidates:
            return {"query": term, "status": "index_required", "items": []}
        document_by_no = {
            str(row["document_no"]): {
                "title": row.get("title"),
                "visibility": row.get("visibility"),
            }
            for row in candidates
            if row.get("document_no")
        }
        related = lwe.rank_related_documents("", query_embedding["rows"], candidates, limit=limit)
        if not related:
            with psycopg.connect(self.dsn) as connection:
                keyword_matches = lw.load_visible_document_index(
                    connection, actor, limit=limit, search=term
                )
            if keyword_matches["items"]:
                return {
                    "query": term,
                    "status": "keyword_fallback",
                    "items": keyword_matches["items"],
                }
        return {
            "query": term,
            "status": "candidate_limit_reached" if truncated else "ready",
            "items": [
                {
                    **row,
                    **document_by_no.get(row["document_no"], {}),
                }
                for row in related
            ],
        }

    def asset_bytes(self, actor: dict[str, Any], document_no: str, asset_index: int) -> tuple[str, bytes]:
        """Fetch one authorized inline image without placing it in the graph."""
        self.document(actor, document_no)
        assets = self._document_assets(document_no)
        if asset_index < 0 or asset_index >= len(assets):
            raise KeyError(asset_index)
        asset = assets[asset_index]
        data_uri = asset["data_uri"]
        header, encoded = data_uri.split(",", 1)
        mime = header[5:].split(";", 1)[0]
        if ";base64" in header:
            return mime, base64.b64decode(re.sub(r"\s+", "", encoded), validate=True)
        return mime, urllib.parse.unquote_to_bytes(encoded)

    def inspect_content_asset(
        self,
        actor: dict[str, Any],
        document_no: str,
        asset_index: int,
    ) -> dict[str, Any]:
        """Run a bounded live OCR/object inspection and persist its normalized result."""
        item = self.document(actor, document_no)["document"]
        decision = lw.authorize_access(actor=actor, resource=item, action="manage_content_inspections")
        if not decision["allowed"]:
            raise PermissionError(decision["reason"])
        assets = self._document_assets(document_no)
        if asset_index < 0 or asset_index >= len(assets):
            raise KeyError(asset_index)
        asset = assets[asset_index]
        try:
            transport = lw.make_live_content_inspection_transport()
        except RuntimeError:
            lw.ensure_compose_standin()
            inspection = lw.derive_content_inspection_via_llm(
                asset, transport=lw.compose_standin_transport
            )
            transport_mode = "compose_live_proxy"
        else:
            inspection = lw.derive_content_inspection_via_llm(
                asset, transport=transport
            )
            transport_mode = "live_http"
        with psycopg.connect(self.dsn) as connection:
            lw.persist_content_inspection(connection, document_no, asset, inspection, actor["account_id"])
            lw.enqueue_event_outbox(
                connection,
                "content_inspected",
                document_no,
                actor["account_id"],
                {
                    "asset_index": asset_index,
                    "ocr_char_count": len(inspection["ocr_text"]),
                    "object_label_count": len(inspection["object_labels"]),
                    "transport": transport_mode,
                },
            )
        self._flush_event_outbox()
        public_inspection = dict(inspection)
        public_inspection.pop("asset_sha256", None)
        return {
            "asset": lw.public_asset_metadata(asset),
            "inspection": public_inspection,
            "transport": transport_mode,
        }

    def image_search(self, actor: dict[str, Any], query: str, limit: int = 24) -> dict[str, Any]:
        """Search OCR text and normalized labels within the actor's visible documents."""
        term = query.strip()
        if len(term) < 2:
            raise ValueError("image search query must contain at least two characters")
        if len(term) > 160:
            raise ValueError("image search query is too long")
        visible_documents = [
            str(node.get("document_no"))
            for node in self.filtered_payload(actor).get("nodes") or []
            if node.get("type") == "document" and node.get("document_no")
        ]
        if not visible_documents:
            return {"query": term, "items": []}
        bounded_limit = max(1, min(int(limit), 100))
        pattern = f"%{term}%"
        with psycopg.connect(self.dsn) as connection:
            rows = lw._database_query(
                connection,
                f"""
                SELECT inspection.document_no, inspection.asset_index, inspection.mime_type,
                       inspection.ocr_text, inspection.inspected_at,
                       COALESCE(
                           jsonb_agg(
                               jsonb_build_object(
                                   'label', catalog.label_name,
                                   'description', link.label_description
                               ) ORDER BY link.label_position
                           ) FILTER (WHERE catalog.label_name IS NOT NULL),
                           '[]'::jsonb
                       ) AS object_labels
                FROM {lw.ANALYSIS_INSPECTION_TABLE} AS inspection
                LEFT JOIN {lw.ANALYSIS_INSPECTION_LABEL_TABLE} AS link
                  ON link.document_no = inspection.document_no
                 AND link.asset_index = inspection.asset_index
                LEFT JOIN {lw.ANALYSIS_OBJECT_LABEL_TABLE} AS catalog
                  ON catalog.label_name = link.label_name
                WHERE inspection.document_no = ANY(%s)
                  AND (
                      inspection.ocr_text ILIKE %s
                      OR catalog.label_name ILIKE %s
                      OR link.label_description ILIKE %s
                  )
                GROUP BY inspection.document_no, inspection.asset_index, inspection.mime_type,
                         inspection.ocr_text, inspection.inspected_at
                ORDER BY inspection.inspected_at DESC, inspection.document_no, inspection.asset_index
                LIMIT %s
                """,
                (visible_documents, pattern, pattern, pattern, bounded_limit),
            )
        return {"query": term, "items": rows}

    def source_evidence(self, actor: dict[str, Any], document_no: str, guid: str) -> dict[str, Any]:
        """Return one bounded, authorized source row for the evidence drawer."""
        detail = self.document(actor, document_no)
        events = lw.chat_events_from_document_detail(detail)
        candidates = lw.voc_evidence_guid_candidates(guid, document_no, events)
        rows: list[dict[str, Any]] = []
        with psycopg.connect(self.dsn) as connection:
            for candidate in candidates:
                rows = lw._database_query(
                    connection,
                    f"""
                    SELECT guid_field, docnosub_field, acthguid_field,
                           title_field, voctp_field, ststs_field, dtsts_field,
                           grade_field, bukrs_field, pucode_field, userid_field,
                           erdat_field, erzet_field, aedat_field, aezet_field,
                           source_row_number, octet_length(voccts_field) AS content_bytes,
                           left(voccts_field, 4000) AS content_preview
                    FROM {self.source_table}
                    WHERE docnosub_field = %s AND guid_field = %s
                    LIMIT 1
                    """,
                    (document_no, candidate),
                )
                if rows:
                    break
            if not rows:
                rows = lw._database_query(
                    connection,
                    f"""
                    SELECT guid_field, docnosub_field, acthguid_field,
                           title_field, voctp_field, ststs_field, dtsts_field,
                           grade_field, bukrs_field, pucode_field, userid_field,
                           erdat_field, erzet_field, aedat_field, aezet_field,
                           source_row_number, octet_length(voccts_field) AS content_bytes,
                           left(voccts_field, 4000) AS content_preview
                    FROM {self.source_table}
                    WHERE docnosub_field = %s
                    ORDER BY erdat_field, erzet_field, guid_field
                    LIMIT 1
                    """,
                    (document_no,),
                )
        if not rows:
            raise KeyError(guid)
        row = rows[0]
        return {
            "evidence_id": row.get("guid_field"),
            "document_no": row.get("docnosub_field"),
            "thread_id": row.get("acthguid_field"),
            "title": row.get("title_field"),
            "event": row.get("voctp_field"),
            "stage": row.get("ststs_field"),
            "state": row.get("dtsts_field"),
            "grade": row.get("grade_field"),
            "corp_code": row.get("bukrs_field"),
            "pu_code": row.get("pucode_field"),
            "user_id": row.get("userid_field"),
            "created_at": f"{row.get('erdat_field') or ''} {row.get('erzet_field') or ''}".strip(),
            "changed_at": f"{row.get('aedat_field') or ''} {row.get('aezet_field') or ''}".strip(),
            "source_row_number": row.get("source_row_number"),
            "content_bytes": int(row.get("content_bytes") or 0),
            "content_preview": row.get("content_preview") or "",
        }

    def verify_lineage_inferences(self, actor: dict[str, Any], document_no: str) -> dict[str, Any]:
        """Run bounded internal/external evidence verification for inferred KG links."""
        self.payload()
        detail = self.document(actor, document_no)
        document = detail["document"]
        decision = lw.authorize_access(actor=actor, resource=document, action="manage_lineage")
        if not decision["allowed"]:
            raise PermissionError(decision["reason"])
        graph = detail.get("knowledge_graph") or {"nodes": [], "edges": []}
        candidates = lw.inference_candidates_for_document(graph, document_no)
        verification_rows: list[dict[str, Any]] = []
        search_modes: set[str] = set()
        transport = None
        if candidates:
            try:
                transport = lw.resolve_product_transport()[0]
            except RuntimeError:
                transport = None
        for candidate in candidates:
            internal = lw.search_internal_inference_evidence(graph, candidate)
            external_result = lw.search_external_inference_evidence(
                lw.inference_organization_labels(graph, candidate)
            )
            search_modes.add(str(external_result["mode"]))
            external = list(external_result["evidence"])
            if transport is None:
                verification = {
                    "decision": "insufficient",
                    "confidence": 0.0,
                    "rationale": "product transport unavailable",
                    "evidence_ids": [],
                    "model": "offline",
                }
            else:
                verification = lw.derive_ontology_relationship_verification(
                    candidate,
                    internal_evidence=internal,
                    external_evidence=external,
                    transport=transport,
                )
            verification_rows.append(
                {
                    "candidate": candidate,
                    "verification": verification,
                    "evidence": internal + external,
                }
            )
        external_search_mode = ",".join(sorted(search_modes)) or "not_applicable"
        with psycopg.connect(self.dsn) as connection:
            persisted = lw.persist_inference_verification_run(
                connection,
                document_no=document_no,
                requested_by=actor["account_id"],
                external_search_mode=external_search_mode,
                verification_rows=verification_rows,
            )
            lw.enqueue_event_outbox(
                connection,
                "lineage_inferences_verified",
                document_no,
                actor["account_id"],
                {
                    "run_id": persisted["run_id"],
                    "candidate_count": persisted["candidate_count"],
                    "external_search_mode": external_search_mode,
                },
            )
            connection.commit()
        self._flush_event_outbox()
        return {
            **persisted,
            "external_search_mode": external_search_mode,
            "items": [
                {
                    **row["candidate"],
                    **row["verification"],
                    "evidence": [
                        {
                            key: item.get(key)
                            for key in ("evidence_id", "evidence_kind", "title", "source_uri", "source_rank")
                        }
                        for item in row["evidence"]
                    ],
                }
                for row in verification_rows
            ],
        }

    def resolve_organization_alias(
        self,
        actor: dict[str, Any],
        document_no: str,
        alias_name: object,
    ) -> dict[str, Any]:
        """Resolve one document-scoped organization alias with live LLM and SearXNG evidence."""
        detail = self.document(actor, document_no)
        document = detail["document"]
        decision = lw.authorize_access(actor=actor, resource=document, action="manage_lineage")
        if not decision["allowed"]:
            raise PermissionError(decision["reason"])
        alias = str(alias_name or "").strip()
        if len(alias) < 2 or len(alias) > 160 or any(ord(char) < 32 for char in alias):
            raise ValueError("organization alias must contain 2-160 visible characters")
        external_result = lw.search_external_organization_alias_evidence(alias)
        context = {
            "document_no": document_no,
            "title": document.get("title_sample"),
            "summary": document.get("korean_summary"),
            "entity_role": document.get("entity_role"),
            "content_semantics": lw.content_semantic_context(
                self._document_content_structure(document_no)
            ),
        }
        resolution = lw.derive_organization_alias_resolution(
            alias,
            document_context=context,
            external_evidence=external_result["evidence"],
            transport=lw.resolve_product_transport()[0],
        )
        graph, candidate = lw.attach_verified_organization_alias(
            {"nodes": [], "edges": []},
            resolution,
            document_no=document_no,
        )
        verification_rows = [
            {
                "candidate": candidate,
                "verification": resolution,
                "evidence": list(external_result["evidence"]),
            }
        ]
        with psycopg.connect(self.dsn) as connection:
            persisted = lw.persist_inference_verification_run(
                connection,
                document_no=document_no,
                requested_by=actor["account_id"],
                external_search_mode=str(external_result["mode"]),
                verification_rows=verification_rows,
            )
            if resolution["decision"] == "verified":
                alias_node_ids = {candidate["source_node"], candidate["target_node"]}
                lw.persist_knowledge_graph_additions(
                    connection,
                    {
                        "nodes": [
                            node
                            for node in graph.get("nodes") or []
                            if node.get("id") in alias_node_ids
                        ],
                        "edges": [
                            edge
                            for edge in graph.get("edges") or []
                            if edge.get("source") == candidate["source_node"]
                            and edge.get("target") == candidate["target_node"]
                            and edge.get("relation") == candidate["relation_name"]
                        ],
                    },
                )
            lw.enqueue_event_outbox(
                connection,
                "organization_alias_resolved",
                document_no,
                actor["account_id"],
                {
                    "run_id": persisted["run_id"],
                    "candidate_id": candidate["candidate_id"],
                    "decision": resolution["decision"],
                    "external_search_mode": external_result["mode"],
                },
            )
            connection.commit()
        if resolution["decision"] == "verified":
            with self._payload_lock:
                if self._payload is not None:
                    self._payload["knowledge_graph"], _candidate = (
                        lw.attach_verified_organization_alias(
                            self._payload.get("knowledge_graph") or {"nodes": [], "edges": []},
                            resolution,
                            document_no=document_no,
                        )
                    )
        self._flush_event_outbox()
        return {
            **persisted,
            **resolution,
            "candidate": candidate,
            "external_search_mode": external_result["mode"],
            "evidence": [
                {
                    key: item.get(key)
                    for key in ("evidence_id", "evidence_kind", "title", "source_uri", "source_rank")
                }
                for item in external_result["evidence"]
            ],
        }

    def derive_keymen(self, actor: dict[str, Any], document_no: str) -> dict[str, Any]:
        """Run the live LLM Keyman worker for one authorized document."""
        item = self.document(actor, document_no)["document"]
        decision = lw.authorize_access(actor=actor, resource=item, action="manage_keymen")
        if not decision["allowed"]:
            raise PermissionError(decision["reason"])
        transport, mode = lw.resolve_keyman_transport()
        derived = lw.derive_keymen_via_llm(
            item.get("title_sample"),
            transport=transport,
            authors={
                "created_by": item.get("created_by"),
                "changed_by": item.get("changed_by"),
                "user_id": item.get("user_id"),
            },
        )
        if not derived["our_side"] and not derived["counterpart_side"]:
            raise ValueError("live model returned no Keyman")
        with psycopg.connect(self.dsn) as connection:
            lw.ensure_keyman_override_columns(connection)
            lw._database_exec(
                connection,
                f"""
                INSERT INTO {lw.ANALYSIS_OVERRIDE_TABLE}
                    (document_no, keyman_our_side, keyman_counterpart_side,
                     keyman_source, keyman_status, updated_by, updated_at)
                VALUES (%s, %s, %s, 'llm', 'orchestrator', %s, now())
                ON CONFLICT (document_no) DO UPDATE SET
                    keyman_our_side = EXCLUDED.keyman_our_side,
                    keyman_counterpart_side = EXCLUDED.keyman_counterpart_side,
                    keyman_source = EXCLUDED.keyman_source,
                    keyman_status = EXCLUDED.keyman_status,
                    updated_by = EXCLUDED.updated_by,
                    updated_at = now()
                """,
                (
                    document_no,
                    json.dumps(derived["our_side"], ensure_ascii=False),
                    json.dumps(derived["counterpart_side"], ensure_ascii=False),
                    actor["account_id"],
                ),
            )
            lw.enqueue_event_outbox(
                connection,
                "keyman_derived",
                document_no,
                actor["account_id"],
                {"our_count": len(derived["our_side"]), "counterpart_count": len(derived["counterpart_side"]), "transport": mode},
            )
        self._flush_event_outbox()
        updated = dict(item)
        updated.update(
            {
                "keyman_our_side": derived["our_side"],
                "keyman_counterpart_side": derived["counterpart_side"],
                "keymen": derived["names"],
                "keyman_source": derived["source"],
                "keyman_status": derived["status"],
                "keyman_orchestration": derived["orchestration"],
            }
        )
        if self._payload is not None:
            with self._payload_lock:
                node = next(
                    node
                    for node in self._payload["nodes"]
                    if node.get("type") == "document" and node.get("document_no") == document_no
                )
                node.update(updated)
                self._payload["knowledge_graph"] = lw.refresh_document_keyman_knowledge_graph(
                    self._payload.get("knowledge_graph") or {}, node
                )
                knowledge_graph = self._payload["knowledge_graph"]
            with psycopg.connect(self.dsn) as connection:
                lw.persist_knowledge_graph_snapshot(connection, knowledge_graph)
            updated = node
        return {"document": updated, "keyman": derived, "transport": mode}

    def chat(self, actor: dict[str, Any], document_no: str, message: str) -> dict[str, Any]:
        """Ask the live model about an event interval with source references."""
        detail = self.document(actor, document_no)
        message = message.strip()
        if not message:
            raise ValueError("message is required")
        if len(message) > 4000:
            raise ValueError("message is too long")
        document = detail["document"]
        events = lw.chat_events_from_document_detail(detail)
        self._materialize_document_content(document_no)
        if self._payload is not None:
            scoped_graph = lw.related_knowledge_graph(
                self.filtered_payload(actor).get("knowledge_graph") or {}, document_no
            )
        else:
            scoped_graph = detail.get("knowledge_graph") or {}
            if not scoped_graph.get("nodes"):
                scoped_graph = lw.build_knowledge_graph(
                    [document], detail.get("edges") or []
                )
        semantic_node_ids = [
            str(node.get("id"))
            for node in scoped_graph.get("nodes") or []
            if node.get("id")
        ]
        if f"kg:document:{document_no}" not in semantic_node_ids:
            semantic_node_ids.append(f"kg:document:{document_no}")
        with psycopg.connect(self.dsn) as connection:
            semantic_context = lw.load_knowledge_semantic_context(
                connection, semantic_node_ids
            )
            content_structure = lw.load_document_content_structure(connection, document_no)
        if not semantic_context.get("node_terms"):
            raise RuntimeError("knowledge_semantic_context_unavailable")
        body = {
            "task": "event_lineage_chat",
            "document_no": document_no,
            "question": message,
            "title": document.get("title_sample"),
            "events": events,
            "context": {
                "entity_role": document.get("entity_role"),
                "summary": document.get("korean_summary"),
                "edges": detail["edges"],
                "semantic_layer": semantic_context,
                "content_semantics": lw.content_semantic_context(content_structure),
            },
        }
        try:
            response = lw.make_live_event_chat_transport()(body)
        except RuntimeError:
            lw.ensure_compose_standin()
            response = lw.compose_standin_transport(body)
        return lw.normalize_event_chat_response(
            response, events, document_no, semantic_context=semantic_context
        )

    def set_visibility(self, actor: dict[str, Any], document_no: str, visibility: str) -> dict[str, Any]:
        """Persist a publish decision in PostgreSQL and update the cache."""
        item = self.document(actor, document_no)["document"]
        updated = lw.apply_visibility(item, visibility, actor)
        with psycopg.connect(self.dsn) as connection:
            lw.persist_visibility(
                connection,
                document_no,
                visibility,
                actor["account_id"],
                {"visibility": visibility},
            )
        self._flush_event_outbox()
        if self._payload is not None:
            with self._payload_lock:
                node = next(
                    node
                    for node in self._payload["nodes"]
                    if node.get("type") == "document" and node.get("document_no") == document_no
                )
                node.update(updated)
        return updated

    def set_keymen(self, actor: dict[str, Any], document_no: str, body: dict[str, Any]) -> dict[str, Any]:
        """Persist user-managed two-sided Keyman rows."""
        item = self.document(actor, document_no)["document"]
        decision = lw.authorize_access(actor=actor, resource=item, action="manage_keymen")
        if not decision["allowed"]:
            raise PermissionError(decision["reason"])
        our_side = lw.normalize_keyman_side(body.get("our_side"))
        counterpart_side = lw.normalize_keyman_side(body.get("counterpart_side"))
        if not our_side and not counterpart_side:
            raise ValueError("at least one Keyman is required")
        with psycopg.connect(self.dsn) as connection:
            lw.ensure_keyman_override_columns(connection)
            lw._database_exec(
                connection,
                f"""
                INSERT INTO {lw.ANALYSIS_OVERRIDE_TABLE}
                    (document_no, keyman_our_side, keyman_counterpart_side,
                     keyman_source, keyman_status, updated_by, updated_at)
                VALUES (%s, %s, %s, 'user_override', 'managed', %s, now())
                ON CONFLICT (document_no) DO UPDATE SET
                    keyman_our_side = EXCLUDED.keyman_our_side,
                    keyman_counterpart_side = EXCLUDED.keyman_counterpart_side,
                    keyman_source = EXCLUDED.keyman_source,
                    keyman_status = EXCLUDED.keyman_status,
                    updated_by = EXCLUDED.updated_by,
                    updated_at = now()
                """,
                (document_no, json.dumps(our_side), json.dumps(counterpart_side), actor["account_id"]),
            )
            lw.enqueue_event_outbox(
                connection,
                "keyman_overridden",
                document_no,
                actor["account_id"],
                {"our_count": len(our_side), "counterpart_count": len(counterpart_side)},
            )
        self._flush_event_outbox()
        if self._payload is not None:
            with self._payload_lock:
                node = next(
                    node
                    for node in self._payload["nodes"]
                    if node.get("type") == "document" and node.get("document_no") == document_no
                )
                node["keyman_our_side"] = our_side
                node["keyman_counterpart_side"] = counterpart_side
                node["keymen"] = [
                    lw.keyman_actor_name(person)
                    for person in our_side + counterpart_side
                    if lw.keyman_actor_name(person)
                ]
                node["keyman_source"] = "user_override"
                node["keyman_status"] = "managed"
                self._payload["knowledge_graph"] = lw.refresh_document_keyman_knowledge_graph(
                    self._payload.get("knowledge_graph") or {}, node
                )
                knowledge_graph = self._payload["knowledge_graph"]
            with psycopg.connect(self.dsn) as connection:
                lw.persist_knowledge_graph_snapshot(connection, knowledge_graph)
        return {"our_side": our_side, "counterpart_side": counterpart_side}

    def create_ticket(self, actor: dict[str, Any], document_no: str, body: dict[str, Any]) -> dict[str, Any]:
        """Create one issue ticket after the document permission check."""
        item = self.document(actor, document_no)["document"]
        decision = lw.authorize_access(actor=actor, resource=item, action="manage_tickets")
        if not decision["allowed"]:
            raise PermissionError(decision["reason"])
        title = str(body.get("title") or "").strip()
        if not title:
            raise ValueError("ticket title is required")
        digest = hashlib.sha256(
            f"{document_no}\x00{title}\x00{actor['account_id']}".encode("utf-8")
        ).hexdigest()[:16]
        ticket_id = f"tkt-{document_no}-{digest}"
        ticket = {
            "ticket_id": ticket_id,
            "document_no": document_no,
            "title": title,
            "status": lw.validate_ticket_status(body.get("status") or "open"),
            "assignee": str(body.get("assignee") or "") or None,
            "created_by": actor["account_id"],
        }
        try:
            transport, _mode = lw.resolve_product_transport()
            mapped = lw.derive_issue_work_items_via_llm(ticket, item, transport=transport)
        except RuntimeError:
            mapped = lw.map_issue_to_work_items(ticket, item)
        ticket["todo"] = mapped["todo"]
        ticket["calendar"] = mapped["calendar"]
        with psycopg.connect(self.dsn) as connection:
            lw._database_exec(
                connection,
                f"""
                INSERT INTO {lw.ANALYSIS_TICKET_TABLE}
                    (ticket_id, document_no, title, status, assignee, created_by)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (ticket_id) DO UPDATE SET
                    title = EXCLUDED.title,
                    status = EXCLUDED.status,
                    assignee = EXCLUDED.assignee,
                    updated_at = now()
                """,
                (
                    ticket["ticket_id"],
                    ticket["document_no"],
                    ticket["title"],
                    ticket["status"],
                    ticket["assignee"],
                    ticket["created_by"],
                ),
            )
            lw.persist_issue_work_items(connection, mapped["todo"], mapped["calendar"])
            lw.enqueue_event_outbox(
                connection,
                "issue_ticket_changed",
                document_no,
                actor["account_id"],
                {"ticket_id": ticket_id, "status": ticket["status"]},
            )
        self._flush_event_outbox()
        if self._payload is not None:
            with self._payload_lock:
                node = next(
                    node
                    for node in self._payload["nodes"]
                    if node.get("type") == "document" and node.get("document_no") == document_no
                )
                node.setdefault("issue_tickets", []).append(ticket)
                node.setdefault("todo_items", []).append(mapped["todo"])
                node.setdefault("calendar_items", []).append(mapped["calendar"])
        return ticket

    def update_ticket(
        self,
        actor: dict[str, Any],
        document_no: str,
        ticket_id: str,
        body: dict[str, Any],
    ) -> dict[str, Any]:
        """Persist one authorized issue-ticket status transition and its To Do state."""
        item = self.document(actor, document_no)["document"]
        decision = lw.authorize_access(actor=actor, resource=item, action="manage_tickets")
        if not decision["allowed"]:
            raise PermissionError(decision["reason"])
        status = lw.validate_ticket_status(body.get("status"))
        with psycopg.connect(self.dsn) as connection:
            tickets = lw._database_query(
                connection,
                f"""
                SELECT ticket_id, document_no, title, status, assignee, created_by
                FROM {lw.ANALYSIS_TICKET_TABLE}
                WHERE ticket_id = %s AND document_no = %s
                """,
                (ticket_id, document_no),
            )
            if not tickets:
                raise KeyError(ticket_id)
            ticket = dict(tickets[0])
            lw._database_exec(
                connection,
                f"""
                UPDATE {lw.ANALYSIS_TICKET_TABLE}
                SET status = %s, updated_at = now()
                WHERE ticket_id = %s AND document_no = %s
                """,
                (status, ticket_id, document_no),
            )
            lw._database_exec(
                connection,
                f"""
                UPDATE {lw.ANALYSIS_TODO_TABLE}
                SET status = %s
                WHERE ticket_id = %s AND document_no = %s
                """,
                (status, ticket_id, document_no),
            )
            lw.enqueue_event_outbox(
                connection,
                "issue_ticket_changed",
                document_no,
                actor["account_id"],
                {"ticket_id": ticket_id, "status": status},
            )
        self._flush_event_outbox()
        ticket["status"] = status
        if self._payload is not None:
            with self._payload_lock:
                node = next(
                    (
                        candidate
                        for candidate in self._payload["nodes"]
                        if candidate.get("type") == "document"
                        and candidate.get("document_no") == document_no
                    ),
                    None,
                )
                if node is not None:
                    for entry in node.get("issue_tickets") or []:
                        if entry.get("ticket_id") == ticket_id:
                            entry["status"] = status
                    for entry in node.get("todo_items") or []:
                        if entry.get("ticket_id") == ticket_id:
                            entry["status"] = status
        return ticket

    def reports(self, actor: dict[str, Any]) -> dict[str, Any]:
        """Return persisted weekly/monthly slices, building them once when empty."""
        with psycopg.connect(self.dsn) as connection:
            persisted = lw.load_period_reports(connection)
            visible_document_numbers = lw.load_authorized_report_document_numbers(connection, actor)
        reports = lw.filter_period_reports_for_actor(
            persisted,
            actor,
            visible_document_numbers=visible_document_numbers,
        )
        if persisted:
            return {
                "reports": reports,
                "factor_definitions": lw.default_factor_definitions(),
                "source": "persisted",
            }
        payload = self.filtered_payload(actor)
        documents = [node for node in payload.get("nodes") or [] if node.get("type") == "document"]
        slices = lw.build_period_report_slices(documents)
        try:
            judge_transport, judge_mode = lw.resolve_product_transport()
        except RuntimeError as exc:
            judge_transport, judge_mode = None, str(exc)
        mlsirm_transport, mlsirm_mode = lw.resolve_mlsirm_transport()
        scored = lw.score_period_reports(
            slices,
            documents,
            judge_transport=judge_transport,
            mlsirm_transport=mlsirm_transport,
        )
        with psycopg.connect(self.dsn) as connection:
            lw.persist_period_reports(connection, scored)
        with self._payload_lock:
            if self._payload is not None:
                self._payload["period_reports"] = scored
                self._payload["factor_definitions"] = lw.default_factor_definitions()
        return {
            "reports": scored,
            "factor_definitions": lw.default_factor_definitions(),
            "source": "built",
            "judge_transport": judge_mode,
            "mlsirm_transport": mlsirm_mode,
        }


class LineageHandler(BaseHTTPRequestHandler):
    """HTTP adapter for the LineageWeave product API and compiled React app."""

    application: LineageApplication

    def log_message(self, format: str, *args: Any) -> None:
        """Keep source identifiers out of default server logs."""
        return

    def _send(
        self,
        status: int,
        value: Any,
        content_type: str = "application/json",
        cookies: list[str] | None = None,
    ) -> None:
        """Write a no-store JSON or binary response with optional cookies."""
        body = _json_bytes(value) if content_type == "application/json" else value
        if isinstance(body, str):
            body = body.encode("utf-8")
        try:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            for cookie in cookies or []:
                self.send_header("Set-Cookie", cookie)
            self.end_headers()
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            # A browser may cancel a large response after navigating away. The
            # client has already gone, so a second error response would only
            # create noisy tracebacks and cannot change the request outcome.
            return

    def _error(self, status: int, reason: str) -> None:
        """Return one normalized JSON API error without exposing internals."""
        self._send(status, {"error": reason})

    def _redirect(self, location: str, cookies: list[str] | None = None) -> None:
        """Send a no-store redirect with optional secure cookie updates."""
        self.send_response(HTTPStatus.FOUND)
        self.send_header("Location", location)
        for cookie in cookies or []:
            self.send_header("Set-Cookie", cookie)
        self.send_header("Cache-Control", "no-store")
        self.end_headers()

    def _actor(self) -> Optional[dict[str, Any]]:
        """Resolve the verified actor or emit the consistent unauthorized response."""
        actor = self.application.actor_for_request(self)
        if not actor:
            self._error(HTTPStatus.UNAUTHORIZED, "keyverse_session_required")
        return actor

    def _body(self) -> dict[str, Any]:
        """Parse one bounded JSON object request body."""
        length = int(self.headers.get("Content-Length") or "0")
        if length > 1_000_000:
            raise ValueError("request body too large")
        raw = self.rfile.read(length) if length else b"{}"
        parsed = json.loads(raw.decode("utf-8"))
        if not isinstance(parsed, dict):
            raise ValueError("JSON object required")
        return parsed

    def _path_parts(self) -> list[str]:
        """Return URL-decoded path components while discarding the query string."""
        return [urllib.parse.unquote(item) for item in self.path.split("?", 1)[0].split("/") if item]

    def do_GET(self) -> None:
        """Serve health/session/API routes or the compiled React app."""
        parts = self._path_parts()
        if _is_oidc_issuer_route(parts):
            self._error(HTTPStatus.NOT_FOUND, "not_found")
            return
        if parts in (["api", "register"], ["api", "register", "complete"]):
            self._error(HTTPStatus.NOT_FOUND, "not_found")
            return
        if parts == ["api", "health"]:
            try:
                with psycopg.connect(self.application.dsn) as connection:
                    lw._database_query(connection, "SELECT 1 AS healthy")
                self._send(HTTPStatus.OK, {"status": "ok", "database": "ok"})
            except Exception:
                self._send(HTTPStatus.SERVICE_UNAVAILABLE, {"status": "error", "reason": "database_unavailable"})
            return
        if parts == ["api", "session"]:
            actor = self.application.actor_for_request(self)
            if actor:
                self._send(HTTPStatus.OK, {"authenticated": True, "actor": actor})
            else:
                self._error(HTTPStatus.UNAUTHORIZED, "keyverse_session_required")
            return
        if parts == ["api", "queue", "health"]:
            if not self._actor():
                return
            self._send(HTTPStatus.OK, self.application.event_queue_health())
            return
        if parts == ["api", "login"]:
            query = urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query, keep_blank_values=True)
            try:
                email_address = _normalized_email_address((query.get("email_address") or [""])[0])
            except RuntimeError:
                self._error(HTTPStatus.BAD_REQUEST, "invalid_email_address")
                return
            try:
                location, state = self.application.begin_keyverse_login(
                    self.headers, email_address=email_address
                )
                self._redirect(
                    location,
                    [_cookie_header("lw_oidc_state", state, KEYVERSE_STATE_TTL_SECONDS)],
                )
            except RuntimeError:
                self._error(HTTPStatus.SERVICE_UNAVAILABLE, "keyverse_oidc_unavailable")
            return
        if parts == ["api", "oidc", "callback"]:
            query = urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query)
            code = str((query.get("code") or [""])[0])
            state = str((query.get("state") or [""])[0])
            if not code or not state:
                self._error(HTTPStatus.UNAUTHORIZED, "keyverse_oidc_denied")
                return
            try:
                token, _actor, ttl = self.application.complete_keyverse_login(
                    code, state, _cookie_value(self.headers, "lw_oidc_state"), self.headers
                )
                self._redirect(
                    "/",
                    [
                        _cookie_header("lw_session", token, ttl),
                        _cookie_header("lw_oidc_state", "", 0),
                    ],
                )
            except RuntimeError:
                self._error(HTTPStatus.UNAUTHORIZED, "keyverse_oidc_callback_failed")
            return
        if parts == ["api", "logout"]:
            self.application.logout(_cookie_value(self.headers, "lw_session"))
            self._redirect("/", [_cookie_header("lw_session", "", 0)])
            return
        if not parts or parts[:1] != ["api"]:
            self._serve_frontend()
            return
        actor = self._actor()
        if not actor:
            return
        try:
            if parts == ["api", "customers"]:
                query = urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query)
                self._send(
                    HTTPStatus.OK,
                    self.application.customer_surface(
                        actor,
                        query=str((query.get("q") or [""])[0]),
                        limit=int((query.get("limit") or ["100"])[0]),
                    ),
                )
                return
            if parts == ["api", "admin", "keyverse", "accounts"]:
                query = urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query)
                self._send(
                    HTTPStatus.OK,
                    self.application.keyverse_admin_accounts(
                        actor,
                        query=str((query.get("q") or [""])[0]),
                        limit=int((query.get("limit") or [str(KEYVERSE_ADMIN_ACCOUNT_LIMIT)])[0]),
                    ),
                )
                return
            if parts == ["api", "admin", "lineage", "edges"]:
                query = urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query)
                self._send(
                    HTTPStatus.OK,
                    self.application.lineage_review_edges(
                        actor,
                        query=str((query.get("q") or [""])[0]),
                        limit=int((query.get("limit") or ["100"])[0]),
                    ),
                )
                return
            if parts == ["api", "admin", "enrichment", "status"]:
                self._send(HTTPStatus.OK, self.application.enrichment_status(actor))
                return
            if parts == ["api", "admin", "tepp", "status"]:
                self._send(HTTPStatus.OK, self.application.tepp_status(actor))
                return
            if len(parts) == 5 and parts[:4] == ["api", "admin", "tepp", "analysis-runs"]:
                self._send(HTTPStatus.OK, self.application.refresh_tepp_analysis(actor, parts[4]))
                return
            if parts == ["api", "analytics"]:
                self._send(HTTPStatus.OK, self.application.workspace_surface(actor))
                return
            if parts == ["api", "reports"]:
                self._send(HTTPStatus.OK, self.application.reports(actor))
                return
            if parts == ["api", "images", "search"]:
                query = urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query)
                self._send(
                    HTTPStatus.OK,
                    self.application.image_search(
                        actor,
                        str((query.get("q") or [""])[0]),
                        int((query.get("limit") or ["24"])[0]),
                    ),
                )
                return
            if parts == ["api", "documents"]:
                query = urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query)
                self._send(
                    HTTPStatus.OK,
                    self.application.document_index(
                        actor,
                        int((query.get("limit") or ["100"])[0]),
                        int((query.get("offset") or ["0"])[0]),
                        str((query.get("q") or [""])[0]),
                    ),
                )
                return
            if parts == ["api", "documents", "semantic-search"]:
                query = urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query)
                self._send(
                    HTTPStatus.OK,
                    self.application.semantic_search_documents(
                        actor,
                        str((query.get("q") or [""])[0]),
                        int((query.get("limit") or ["12"])[0]),
                    ),
                )
                return
            if parts == ["api", "threads"]:
                filtered = self.application.filtered_payload(actor)
                limit = int(urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query).get("limit", ["200"])[0])
                documents = [node for node in filtered["nodes"] if node.get("type") == "document"]
                by_thread: dict[str, list[dict[str, Any]]] = {}
                for node in documents:
                    by_thread.setdefault(str(node.get("acthguid") or "UNKNOWN"), []).append(node)
                items = []
                for thread_id, nodes in sorted(by_thread.items(), key=lambda item: (-len(item[1]), item[0])):
                    if len(nodes) < 2:
                        continue
                    items.append({
                        "thread_id": thread_id,
                        "doc_count": len(nodes),
                        "documents": [
                            {"document_no": n["document_no"], "title": n.get("title_sample"), "row_count": n.get("row_count", 0)}
                            for n in nodes
                        ],
                    })
                    if len(items) >= max(1, min(limit, 500)):
                        break
                self._send(HTTPStatus.OK, {"items": items})
                return
            if len(parts) == 3 and parts[1] == "threads":
                thread_id = parts[2]
                filtered = self.application.filtered_payload(actor)
                docs = [
                    node for node in filtered["nodes"]
                    if node.get("type") == "document" and str(node.get("acthguid")) == thread_id
                ]
                if not docs:
                    self._error(HTTPStatus.NOT_FOUND, "thread_not_found")
                    return
                ids = {node["id"] for node in docs}
                ids.update(node["id"] for node in filtered["nodes"] if node.get("type") == "row" and node.get("document_no") in {n["document_no"] for n in docs})
                edges = [edge for edge in filtered["edges"] if edge.get("source") in ids and edge.get("target") in ids]
                self._send(HTTPStatus.OK, {"documents": docs, "edges": edges})
                return
            if len(parts) == 3 and parts[1] == "documents":
                self._send(HTTPStatus.OK, self.application.document(actor, parts[2]))
                return
            if len(parts) == 4 and parts[1] == "documents" and parts[3] == "content":
                self._send(HTTPStatus.OK, self.application.content_manifest(actor, parts[2]))
                return
            if len(parts) == 5 and parts[1] == "documents" and parts[3] == "evidence":
                self._send(HTTPStatus.OK, self.application.source_evidence(actor, parts[2], parts[4]))
                return
            if len(parts) == 4 and parts[1] == "documents" and parts[3] == "knowledge":
                query = urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query)
                self._send(HTTPStatus.OK, self.application.knowledge(actor, parts[2], query))
                return
            if len(parts) == 4 and parts[1] == "documents" and parts[3] == "semantic-related":
                query = urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query)
                self._send(
                    HTTPStatus.OK,
                    self.application.semantic_related_documents(
                        actor,
                        parts[2],
                        int((query.get("limit") or ["12"])[0]),
                    ),
                )
                return
            if len(parts) == 5 and parts[1] == "documents" and parts[3] == "assets":
                mime, content = self.application.asset_bytes(actor, parts[2], int(parts[4]))
                self._send(HTTPStatus.OK, content, mime)
                return
            self._error(HTTPStatus.NOT_FOUND, "not_found")
        except KeyError:
            self._error(HTTPStatus.NOT_FOUND, "not_found")
        except PermissionError as exc:
            self._error(HTTPStatus.FORBIDDEN, str(exc))
        except ValueError as exc:
            self._error(HTTPStatus.BAD_REQUEST, str(exc))
        except RuntimeError as exc:
            reason = str(exc) if str(exc).startswith("keyverse_admin_") else "live_model_unavailable"
            self._error(HTTPStatus.SERVICE_UNAVAILABLE, reason)
        except Exception:
            self._error(HTTPStatus.INTERNAL_SERVER_ERROR, "request_failed")

    def do_POST(self) -> None:
        """Serve document-scoped writes; Keyverse login uses authorization-code redirects."""
        parts = self._path_parts()
        if _is_oidc_issuer_route(parts):
            self._error(HTTPStatus.NOT_FOUND, "not_found")
            return
        if parts == ["api", "session"]:
            self._error(HTTPStatus.METHOD_NOT_ALLOWED, "keyverse_oidc_redirect_required")
            return
        if parts == ["api", "login"]:
            try:
                email_address = _normalized_email_address(self._body().get("email_address"))
                location, state = self.application.begin_keyverse_login(
                    self.headers, email_address=email_address
                )
                self._send(
                    HTTPStatus.OK,
                    {"authorization_url": location},
                    cookies=[_cookie_header("lw_oidc_state", state, KEYVERSE_STATE_TTL_SECONDS)],
                )
            except RuntimeError as exc:
                if str(exc) == "invalid_email_address":
                    self._error(HTTPStatus.BAD_REQUEST, "invalid_email_address")
                else:
                    self._error(HTTPStatus.SERVICE_UNAVAILABLE, "keyverse_oidc_unavailable")
            except ValueError:
                self._error(HTTPStatus.BAD_REQUEST, "invalid_request")
            return
        if parts in (["api", "register"], ["api", "register", "complete"]):
            self._error(HTTPStatus.NOT_FOUND, "not_found")
            return
        actor = self._actor()
        if not actor:
            return
        try:
            body = self._body()
            if len(parts) == 6 and parts[:4] == ["api", "admin", "keyverse", "accounts"] and parts[5] == "claims":
                self._send(
                    HTTPStatus.OK,
                    self.application.update_keyverse_account(actor, parts[4], body),
                )
                return
            if parts == ["api", "admin", "lineage", "edges", "override"]:
                self._send(
                    HTTPStatus.OK,
                    self.application.update_lineage_edge_override(actor, body),
                )
                return
            if parts == ["api", "admin", "enrichment", "run"]:
                self._send(
                    HTTPStatus.ACCEPTED,
                    self.application.run_enrichment(actor, body),
                )
                return
            if parts == ["api", "admin", "reports", "refresh"]:
                self._send(HTTPStatus.OK, self.application.refresh_reports(actor))
                return
            if parts == ["api", "admin", "tepp", "analysis-runs"]:
                self._send(
                    HTTPStatus.ACCEPTED,
                    self.application.submit_tepp_analysis(actor, body),
                )
                return
            if len(parts) == 4 and parts[1] == "documents" and parts[3] == "visibility":
                self._send(HTTPStatus.OK, {"document": self.application.set_visibility(actor, parts[2], str(body.get("visibility") or ""))})
                return
            if len(parts) == 4 and parts[1] == "documents" and parts[3] == "keymen":
                self._send(HTTPStatus.OK, self.application.set_keymen(actor, parts[2], body))
                return
            if len(parts) == 5 and parts[1] == "documents" and parts[3] == "keymen" and parts[4] == "derive":
                self._send(HTTPStatus.OK, self.application.derive_keymen(actor, parts[2]))
                return
            if len(parts) == 6 and parts[1] == "documents" and parts[3] == "assets" and parts[5] == "inspect":
                self._send(
                    HTTPStatus.OK,
                    self.application.inspect_content_asset(actor, parts[2], int(parts[4])),
                )
                return
            if len(parts) == 4 and parts[1] == "documents" and parts[3] == "tickets":
                self._send(HTTPStatus.CREATED, self.application.create_ticket(actor, parts[2], body))
                return
            if len(parts) == 5 and parts[1] == "documents" and parts[3] == "tickets":
                self._send(
                    HTTPStatus.OK,
                    self.application.update_ticket(actor, parts[2], parts[4], body),
                )
                return
            if len(parts) == 4 and parts[1] == "documents" and parts[3] == "chat":
                self._send(HTTPStatus.OK, self.application.chat(actor, parts[2], str(body.get("message") or "")))
                return
            if len(parts) == 5 and parts[1] == "documents" and parts[3] == "lineage" and parts[4] == "verify":
                self._send(HTTPStatus.OK, self.application.verify_lineage_inferences(actor, parts[2]))
                return
            if len(parts) == 5 and parts[1] == "documents" and parts[3] == "organizations" and parts[4] == "resolve":
                self._send(
                    HTTPStatus.OK,
                    self.application.resolve_organization_alias(
                        actor,
                        parts[2],
                        body.get("alias_name"),
                    ),
                )
                return
            if len(parts) == 4 and parts[1] == "documents" and parts[3] == "semantic-index":
                self._send(HTTPStatus.OK, self.application.index_document_embeddings(actor, parts[2]))
                return
            self._error(HTTPStatus.NOT_FOUND, "not_found")
        except PermissionError as exc:
            self._error(HTTPStatus.FORBIDDEN, str(exc))
        except KeyError:
            self._error(HTTPStatus.NOT_FOUND, "not_found")
        except ValueError as exc:
            self._error(HTTPStatus.BAD_REQUEST, str(exc))
        except RuntimeError as exc:
            reason = str(exc) if str(exc).startswith("keyverse_admin_") else "live_model_unavailable"
            self._error(HTTPStatus.SERVICE_UNAVAILABLE, reason)
        except Exception:
            self._error(HTTPStatus.INTERNAL_SERVER_ERROR, "request_failed")

    def _serve_frontend(self) -> None:
        """Serve the compiled React entrypoint, never source-derived data files."""
        index = FRONTEND_ROOT / "index.html"
        if not index.is_file():
            self._error(HTTPStatus.SERVICE_UNAVAILABLE, "frontend_not_built_run_npm_build")
            return
        relative = self.path.split("?", 1)[0].lstrip("/")
        candidate = (FRONTEND_ROOT / relative).resolve() if relative else index
        if FRONTEND_ROOT not in candidate.parents and candidate != FRONTEND_ROOT:
            self._error(HTTPStatus.NOT_FOUND, "not_found")
            return
        if not candidate.is_file():
            candidate = index
        content_type = {
            ".html": "text/html; charset=utf-8",
            ".js": "application/javascript; charset=utf-8",
            ".css": "text/css; charset=utf-8",
            ".svg": "image/svg+xml",
        }.get(candidate.suffix, "application/octet-stream")
        self._send(HTTPStatus.OK, candidate.read_bytes(), content_type)


def _run_report_refresh_in_background(application: LineageApplication) -> None:
    """Run report maintenance without surfacing an operator outage to request threads."""
    try:
        application.refresh_persisted_reports()
    except Exception:
        return


def main() -> None:
    """Start the product server on the configured host and port."""
    host = os.environ.get("LINEAGEWEAVE_HOST", "127.0.0.1")
    port = int(os.environ.get("LINEAGEWEAVE_PORT", "8000"))
    dsn = (os.environ.get("LINEAGEWEAVE_DSN") or "").strip()
    source_table = os.environ.get("LINEAGE_SOURCE_TABLE", "")
    if not dsn:
        raise RuntimeError("LINEAGEWEAVE_DSN is required")
    if not source_table:
        raise RuntimeError("LINEAGE_SOURCE_TABLE is required")
    with psycopg.connect(dsn) as connection:
        lw.demote_legacy_shared_thread_edges(connection)
    application = LineageApplication(dsn, source_table)
    server = ThreadingHTTPServer((host, port), LineageHandler)
    LineageHandler.application = application
    threading.Thread(
        target=_run_report_refresh_in_background,
        args=(application,),
        daemon=True,
        name="lineageweave-report-refresh",
    ).start()
    print(f"LineageWeave listening on http://{host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
