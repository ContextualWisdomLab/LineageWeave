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


@dataclass(frozen=True)
class ProductRelationTarget:
    """One authorized normalized relation target offered to extraction."""

    target_id: str
    target_kind_code: str
    label: str
    target_locator: tuple[str, ...]


@dataclass(frozen=True)
class ProductRelation:
    """One validated closed-vocabulary relation to an authorized target."""

    mention_ordinal: int
    target_id: str
    target_kind_code: str
    relation_type_code: str
    evidence_text: str
    evidence_post_id: str
    evidence_input_sha256: str
    target_locator: tuple[str, ...]


@dataclass(frozen=True)
class ProductExtraction:
    """Validated product mentions and their authorized typed relations."""

    mentions: tuple[ProductMention, ...]
    relations: tuple[ProductRelation, ...]


_RELATION_TYPES = {
    "operations_fact": frozenset(
        {"concerns_product", "changes_product", "originates_from_product", "senses_product"}
    ),
    "project": frozenset({"used_by_project"}),
}


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
    content: str,
    sources: tuple[ProductEvidenceSource, ...],
    targets: tuple[ProductRelationTarget, ...] = (),
) -> ProductExtraction | None:
    """Validate structured output against exact authorized source spans."""
    source_by_id = {source.post_id: source for source in sources}
    try:
        payload = json.loads(content)
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict):
        return None
    raw_mentions = payload.get("mentions")
    raw_relations = payload.get("relations")
    if not isinstance(raw_mentions, list) or not isinstance(raw_relations, list):
        return None
    mentions: list[ProductMention] = []
    seen: set[tuple[str, str, str]] = set()
    for item in raw_mentions:
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
    targets_by_id = {target.target_id: target for target in targets}
    if len(targets_by_id) != len(targets):
        return None
    relations: list[ProductRelation] = []
    seen_relations: set[tuple[int, str, str]] = set()
    for item in raw_relations:
        if not isinstance(item, dict):
            return None
        ordinal = item.get("mention_ordinal")
        target_id = item.get("target_id")
        relation_type = item.get("relation_type_code")
        evidence = item.get("evidence_text")
        evidence_post_id = item.get("evidence_post_id")
        target = targets_by_id.get(target_id)
        source = source_by_id.get(evidence_post_id)
        if (
            type(ordinal) is not int
            or ordinal < 0
            or ordinal >= len(mentions)
            or target is None
            or relation_type not in _RELATION_TYPES.get(target.target_kind_code, ())
            or not isinstance(evidence, str)
            or not evidence.strip()
            or source is None
            or evidence not in source.text
        ):
            return None
        key = (ordinal, target_id, relation_type)
        if key in seen_relations:
            return None
        seen_relations.add(key)
        relations.append(
            ProductRelation(
                ordinal,
                target_id,
                target.target_kind_code,
                relation_type,
                evidence,
                evidence_post_id,
                source.input_sha256,
                target.target_locator,
            )
        )
    return ProductExtraction(tuple(mentions), tuple(relations))


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


_PROMPT = """Extract product entities and supported typed relationships from the
authorized sources semantically. Do not classify by keywords, tags, or span
overlap and do not invent a product or target. Return ONLY one JSON object with
mentions and relations arrays. Each mention has product_name, evidence_post_id,
and evidence_text. Each relation has mention_ordinal, target_id,
relation_type_code, evidence_post_id, and evidence_text. Use only the supplied
target_id and its allowed relation codes. Evidence must be a verbatim source
span. Return empty arrays when the sources support no product or relationship.

Authorized sources:
{sources}

Authorized normalized targets:
{targets}
"""


class ContextualOrchestratorProductExtractionClient:
    """Extract cited product mentions through the provider-neutral gateway."""

    available = True

    def __init__(self, base_url: str, api_key: str, *, timeout: float = 180.0) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._timeout = timeout

    def extract(
        self,
        sources: tuple[ProductEvidenceSource, ...],
        targets: tuple[ProductRelationTarget, ...] = (),
        *,
        session_id: str | None = None,
    ) -> ProductExtraction:
        """Return only fully validated, source-bound product mentions."""
        if session_id is not None and not session_id.strip():
            raise ValueError("session_id must be non-empty when provided")
        payload = {
            "model": "orchestrator/auto",
            "messages": [
                {
                    "role": "user",
                    "content": _PROMPT.format(
                        sources="\n\n".join(
                            f"post_id={source.post_id}\n{source.text}"
                            for source in sources
                        ),
                        targets=json.dumps(
                            [
                                {
                                    "target_id": target.target_id,
                                    "target_kind_code": target.target_kind_code,
                                    "label": target.label,
                                    "allowed_relation_type_codes": sorted(
                                        _RELATION_TYPES[target.target_kind_code]
                                    ),
                                }
                                for target in targets
                            ],
                            ensure_ascii=False,
                            separators=(",", ":"),
                        ),
                    ),
                }
            ],
            "mode": "auto",
            "reasoning_effort": "auto",
            "response_format": {"type": "json_object"},
        }
        if session_id is not None:
            payload["session_id"] = session_id
        response = post_json(
            f"{self._base_url}/v1/chat/completions",
            payload,
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
        parsed = parse_product_mentions(content, sources, targets)
        if parsed is None:
            raise RuntimeError("contextual-orchestrator returned invalid product evidence")
        return parsed
