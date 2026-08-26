"""Evidence-bound product extraction and fail-closed catalog resolution."""

from __future__ import annotations

import hashlib
import json
import unicodedata
from dataclasses import dataclass

from .http_client import chat_completion_content, post_json


@dataclass(frozen=True)
class ProductEvidenceSource:
    """One authorized source whose exact text may support a product mention."""

    post_id: str
    text: str

    @property
    def input_sha256(self) -> str:
        """Return the digest binding derived evidence to this source text."""
        return hashlib.sha256(self.text.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class ProductMention:
    """One validated product span, not yet forced onto a catalog identity."""

    extracted_product_name: str
    evidence_text: str
    evidence_post_id: str
    evidence_input_sha256: str


@dataclass(frozen=True)
class ResolvedProductMention:
    """A mention with a unique, missing, or tied catalog outcome."""

    mention: ProductMention
    resolution_status_code: str
    product_catalog_id: str | None


def normalize_product_alias(value: str) -> str:
    """Normalize catalog lookup text without deriving identity from keywords."""
    return " ".join(unicodedata.normalize("NFKC", value).casefold().split())


def product_analysis_input_sha256(
    sources: tuple[ProductEvidenceSource, ...],
) -> str:
    """Digest the exact ordered authorized source window used for extraction."""
    encoded = json.dumps(
        [(source.post_id, source.input_sha256) for source in sources],
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def parse_product_mentions(
    content: str, sources: tuple[ProductEvidenceSource, ...]
) -> tuple[ProductMention, ...] | None:
    """Validate structured output against exact authorized source spans."""
    source_by_id = {source.post_id: source for source in sources}
    try:
        payload = json.loads(content)
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, list):
        return None
    mentions: list[ProductMention] = []
    seen: set[tuple[str, str, str]] = set()
    for item in payload:
        if not isinstance(item, dict):
            return None
        name = item.get("product_name")
        evidence = item.get("evidence_text")
        post_id = item.get("evidence_post_id")
        source = source_by_id.get(post_id)
        if (
            not isinstance(name, str)
            or not name.strip()
            or not isinstance(evidence, str)
            or not evidence.strip()
            or source is None
            or evidence not in source.text
        ):
            return None
        key = (normalize_product_alias(name), evidence, post_id)
        if key in seen:
            return None
        seen.add(key)
        mentions.append(ProductMention(name.strip(), evidence, post_id, source.input_sha256))
    return tuple(mentions)


def resolve_product_mention(
    mention: ProductMention, catalog_matches: tuple[str, ...] | None
) -> ResolvedProductMention:
    """Bind only one exact normalized catalog match; preserve misses and ties."""
    if catalog_matches is None:
        return ResolvedProductMention(mention, "unavailable", None)
    distinct = tuple(dict.fromkeys(catalog_matches))
    if len(distinct) == 1:
        return ResolvedProductMention(mention, "unique", distinct[0])
    return ResolvedProductMention(
        mention, "missing" if not distinct else "tie", None
    )


_PROMPT = """Extract product entities from the authorized sources semantically.
Do not classify by keywords or tags and do not invent a product. Return ONLY a
JSON array. Each object has product_name, evidence_post_id, and evidence_text.
evidence_text must be a verbatim span that identifies the product in that same
source. Return [] when no source span supports a product entity.

Authorized sources:
{sources}
"""


class ContextualOrchestratorProductExtractionClient:
    """Extract cited product mentions through the provider-neutral gateway."""

    available = True

    def __init__(self, base_url: str, api_key: str, *, timeout: float = 180.0) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._timeout = timeout

    def extract(
        self, sources: tuple[ProductEvidenceSource, ...]
    ) -> tuple[ProductMention, ...]:
        """Return only fully validated, source-bound product mentions."""
        response = post_json(
            f"{self._base_url}/v1/chat/completions",
            {
                "model": "orchestrator/auto",
                "messages": [
                    {
                        "role": "user",
                        "content": _PROMPT.format(
                            sources="\n\n".join(
                                f"post_id={source.post_id}\n{source.text}"
                                for source in sources
                            )
                        ),
                    }
                ],
                "mode": "auto",
                "reasoning_effort": "auto",
            },
            timeout=self._timeout,
            headers={
                "authorization": f"Bearer {self._api_key}",
                "x-request-timeout-ms": str(round(self._timeout * 1000)),
            },
        )
        try:
            content = chat_completion_content(response)
        except TypeError as exc:
            raise RuntimeError(
                "contextual-orchestrator returned invalid product evidence"
            ) from exc
        parsed = parse_product_mentions(content, sources)
        if parsed is None:
            raise RuntimeError("contextual-orchestrator returned invalid product evidence")
        return parsed
