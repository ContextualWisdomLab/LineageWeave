"""Typed public-claim envelopes for Global Ask external verification.

Implements ADR 0229 / issue #272. A claim is admitted only when a
persisted envelope names a public post, a governed claim kind, and
egress eligibility. Question-token overlap is not admission. Person,
Keyman, TEPP, and fast-mlsirm evidence cannot be stored or dispatched.

Grounded in FEVER (Thorne, Vlachos, Christodoulopoulos, & Mittal, 2018):
retrieve public web evidence, then classify supported / refuted /
not-enough-information. Polarity other than organization-presence
footprint stays unavailable until contextual-orchestrator classifies
retrieved passages. This module never forces ``mode="verify"``.
"""

from __future__ import annotations

import ipaddress
from dataclasses import dataclass
from typing import Any, Protocol
from urllib.parse import quote, urlparse

from .http_client import HttpClientError, get_json
from .relation_verification import _SEARCH_HOST_MARKERS, corroborating_evidence_url

KIND_ORGANIZATION_PRESENCE = "claim_organization_presence"
KIND_PUBLIC_EVENT = "claim_public_event"
KIND_PUBLIC_RELATIONSHIP = "claim_public_relationship"
ADMITTED_CLAIM_KINDS = frozenset(
    {
        KIND_ORGANIZATION_PRESENCE,
        KIND_PUBLIC_EVENT,
        KIND_PUBLIC_RELATIONSHIP,
    }
)
INELIGIBLE_CLAIM_KINDS = frozenset(
    {
        "person",
        "keyman",
        "cataloged_person",
        "tepp",
        "fast_mlsirm",
        "fast-mlsirm",
    }
)

STATUS_UNAVAILABLE = "claim_unavailable"
STATUS_SUPPORTED = "claim_supported"
STATUS_REFUTED = "claim_refuted"
STATUS_NOT_ENOUGH_INFORMATION = "claim_not_enough_information"

_PRIVATE_HOSTS = frozenset({"localhost", "localhost.localdomain", "ip6-localhost"})
_SEARCH_URL_LIMIT = 5


@dataclass(frozen=True)
class PublicClaimEnvelope:
    """One persisted public claim bound to an exact source post."""

    public_claim_envelope_id: str
    source_post_id: str
    source_post_title: str
    claim_kind_code: str
    subject_label: str
    claim_text: str
    truth_status_code: str
    event_occurred_at: str | None
    egress_eligible: bool
    visibility_code: str


@dataclass(frozen=True)
class PublicClaimVerdict:
    """Buyer-visible verification of one envelope."""

    public_claim_envelope_id: str
    source_post_id: str
    source_post_title: str
    claim_kind_code: str
    subject_label: str
    claim_text: str
    status_code: str
    external_evidence_urls: tuple[str, ...]
    next_action: str


class PublicClaimSearchClient(Protocol):
    """Retrieves public HTTP(S) URLs for a persisted claim text."""

    available: bool

    def search_urls(self, claim_text: str, *, limit: int = _SEARCH_URL_LIMIT) -> tuple[str, ...]:
        """Return bounded public evidence URLs, never search or private hosts."""
        raise NotImplementedError


class NullPublicClaimSearchClient:
    """No SearXNG channel — verification stays unavailable."""

    available = False

    def search_urls(self, claim_text: str, *, limit: int = _SEARCH_URL_LIMIT) -> tuple[str, ...]:  # pragma: no cover
        """Search is not a missing-channel placeholder."""
        raise RuntimeError(
            "NullPublicClaimSearchClient has no search channel; check .available first"
        )


class SearxngPublicClaimSearchClient:
    """Queries self-hosted SearXNG JSON search for a persisted claim text."""

    available = True

    def __init__(self, base_url: str, *, timeout: float = 15.0) -> None:
        parsed = urlparse(base_url)
        if parsed.scheme not in {"http", "https"}:
            raise ValueError(f"unsupported Searxng base URL scheme: {parsed.scheme or 'missing'}")
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

    def search_urls(self, claim_text: str, *, limit: int = _SEARCH_URL_LIMIT) -> tuple[str, ...]:
        """Return bounded public URLs for ``claim_text``."""
        query = claim_text.strip()
        if not query:
            return ()
        body = get_json(
            f"{self._base_url}/search?q={quote(query, safe='')}&format=json",
            timeout=self._timeout,
            service_peer_name="searxng",
        )
        results = body.get("results")
        if not isinstance(results, list):
            return ()
        urls: list[str] = []
        for result in results:
            if not isinstance(result, dict):
                continue
            url = public_evidence_url(result.get("url"))
            if url is None or url in urls:
                continue
            urls.append(url)
            if len(urls) >= limit:
                break
        return tuple(urls)


def envelope_from_authorized_row(row: Any) -> PublicClaimEnvelope | None:
    """Build an envelope from a visibility-checked database row.

    Hidden, private, ineligible-kind, or non-egress rows are dropped
    rather than repaired. Callers must already have applied ABAC.
    """
    kind = str(row["claim_kind_code"] or "")
    if kind in INELIGIBLE_CLAIM_KINDS or kind not in ADMITTED_CLAIM_KINDS:
        return None
    if str(row["visibility_code"] or "") != "public":
        return None
    if not bool(row["egress_eligible"]):
        return None
    subject = str(row["subject_label"] or "").strip()
    claim_text = str(row["claim_text"] or "").strip()
    title = str(row["source_post_title"] or "").strip()
    post_id = str(row["source_post_id"] or "").strip()
    envelope_id = str(row["public_claim_envelope_id"] or "").strip()
    if not (subject and claim_text and title and post_id and envelope_id):
        return None
    event_at = row["event_occurred_at"]
    return PublicClaimEnvelope(
        public_claim_envelope_id=envelope_id,
        source_post_id=post_id,
        source_post_title=title,
        claim_kind_code=kind,
        subject_label=subject,
        claim_text=claim_text,
        truth_status_code=str(row["truth_status_code"] or ""),
        event_occurred_at=None if event_at is None else str(event_at),
        egress_eligible=True,
        visibility_code="public",
    )


def public_evidence_url(raw: object) -> str | None:
    """Accept only public http(s) URLs; drop search, localhost, and literal private hosts."""
    if not isinstance(raw, str) or not raw.strip():
        return None
    parsed = urlparse(raw.strip())
    if parsed.scheme not in {"http", "https"}:
        return None
    if parsed.username or parsed.password:
        return None
    host = (parsed.hostname or "").lower().rstrip(".")
    if not host or host in _PRIVATE_HOSTS or host.endswith(".localhost") or host.endswith(".local"):
        return None
    if any(marker in host for marker in _SEARCH_HOST_MARKERS):
        return None
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return raw.strip()
    if (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    ):
        return None
    return raw.strip()


def classify_public_claim(
    envelope: PublicClaimEnvelope,
    urls: tuple[str, ...],
    *,
    search_available: bool,
) -> PublicClaimVerdict:
    """Classify one authorized envelope against retrieved public URLs.

    Missing search is unavailable, not not-enough-information. Other
    kinds with retrieved URLs stay unavailable until orchestrator-owned
    polarity exists — this function does not invent refutation.
    """
    title = envelope.source_post_title
    if not search_available:
        return _verdict(
            envelope,
            STATUS_UNAVAILABLE,
            (),
            f"Web verification is unavailable until the search service is connected. Open that post.",
        )
    if not urls:
        return _verdict(
            envelope,
            STATUS_NOT_ENOUGH_INFORMATION,
            (),
            "No usable public web evidence. Open that post.",
        )
    if envelope.claim_kind_code == KIND_ORGANIZATION_PRESENCE:
        supporting = tuple(
            url
            for url in urls
            if corroborating_evidence_url(
                envelope.subject_label, {"url": url, "content": url}
            )
            is not None
        )
        if supporting:
            return _verdict(
                envelope,
                STATUS_SUPPORTED,
                supporting,
                "Public web evidence supports this claim. Open that post.",
            )
        return _verdict(
            envelope,
            STATUS_NOT_ENOUGH_INFORMATION,
            urls,
            "No usable public web evidence. Open that post.",
        )
    return _verdict(
        envelope,
        STATUS_UNAVAILABLE,
        urls,
        f"Public claim is on {title}. Open that post.",
    )


def verify_public_claims(
    envelopes: tuple[PublicClaimEnvelope, ...],
    search_client: PublicClaimSearchClient,
) -> dict[str, Any]:
    """Project authorized envelopes into the Ask Agent verification contract.

    An empty authorized set is unavailable and never searches. External
    URLs stay off ``cited_post_ids``.
    """
    if not envelopes:
        return {
            "status_code": STATUS_UNAVAILABLE,
            "next_action": (
                "Public-claim verification is unavailable: no egress-eligible "
                "public claim is authorized."
            ),
            "claims": [],
        }
    verdicts: list[PublicClaimVerdict] = []
    search_available = search_client.available
    for envelope in envelopes:
        if not search_available:
            urls: tuple[str, ...] = ()
        else:
            try:
                urls = search_client.search_urls(envelope.claim_text)
            except (HttpClientError, OSError):
                search_available = False
                urls = ()
        verdicts.append(
            classify_public_claim(
                envelope, urls, search_available=search_available
            )
        )
    overall = _overall_status(tuple(verdict.status_code for verdict in verdicts))
    next_action = next(
        (verdict.next_action for verdict in verdicts if verdict.status_code == overall),
        verdicts[0].next_action,
    )
    return {
        "status_code": overall,
        "next_action": next_action,
        "claims": [
            {
                "public_claim_envelope_id": item.public_claim_envelope_id,
                "source_post_id": item.source_post_id,
                "source_post_title": item.source_post_title,
                "claim_kind_code": item.claim_kind_code,
                "subject_label": item.subject_label,
                "claim_text": item.claim_text,
                "status_code": item.status_code,
                "external_evidence_urls": list(item.external_evidence_urls),
                "next_action": item.next_action,
            }
            for item in verdicts
        ],
    }


def cited_post_ids_exclude_external(cited_post_ids: list[str], verification: dict[str, Any]) -> None:
    """Fail closed if an external URL leaked into internal citation ids."""
    external = {
        url
        for claim in verification.get("claims") or ()
        for url in (claim.get("external_evidence_urls") or ())
    }
    overlap = external.intersection(cited_post_ids)
    if overlap:
        raise ValueError("external evidence URLs cannot become cited_post_ids")


def _overall_status(codes: tuple[str, ...]) -> str:
    """Prefer a decisive label when every envelope agrees; else unavailable."""
    unique = set(codes)
    if unique == {STATUS_SUPPORTED}:
        return STATUS_SUPPORTED
    if unique == {STATUS_REFUTED}:
        return STATUS_REFUTED
    if unique == {STATUS_NOT_ENOUGH_INFORMATION}:
        return STATUS_NOT_ENOUGH_INFORMATION
    if unique == {STATUS_UNAVAILABLE}:
        return STATUS_UNAVAILABLE
    return STATUS_UNAVAILABLE


def _verdict(
    envelope: PublicClaimEnvelope,
    status_code: str,
    urls: tuple[str, ...],
    next_action: str,
) -> PublicClaimVerdict:
    """Pack one buyer-visible verdict."""
    return PublicClaimVerdict(
        public_claim_envelope_id=envelope.public_claim_envelope_id,
        source_post_id=envelope.source_post_id,
        source_post_title=envelope.source_post_title,
        claim_kind_code=envelope.claim_kind_code,
        subject_label=envelope.subject_label,
        claim_text=envelope.claim_text,
        status_code=status_code,
        external_evidence_urls=urls,
        next_action=next_action,
    )
