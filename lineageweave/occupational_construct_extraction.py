"""Catalog-bound occupational-construct selection through contextual-orchestrator."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Protocol

from .http_client import chat_completion_content, post_json


@dataclass(frozen=True)
class OccupationalConstructCandidate:
    """One official catalog node offered for evidence-bound selection."""

    construct_iri: str
    preferred_label: str
    description: str | None


@dataclass(frozen=True)
class OccupationalConstructSelection:
    """One exact catalog node and its verbatim supporting span."""

    construct_iri: str
    evidence_text: str


class OccupationalConstructExtractionClient(Protocol):
    """Select applicable nodes from one bounded official-catalog sibling set."""

    available: bool

    def select(
        self,
        unit_text: str,
        candidates: tuple[OccupationalConstructCandidate, ...],
    ) -> tuple[OccupationalConstructSelection, ...]:
        """Return only exact candidate IRIs with verbatim evidence spans."""
        raise NotImplementedError


class NullOccupationalConstructExtractionClient:
    """Fail-closed client used when contextual-orchestrator is unavailable."""

    available = False

    def select(
        self,
        unit_text: str,
        candidates: tuple[OccupationalConstructCandidate, ...],
    ) -> tuple[OccupationalConstructSelection, ...]:
        """Reject extraction because no orchestrator is configured."""
        raise RuntimeError("occupational construct extraction is unavailable")


def parse_occupational_construct_selections(
    content: str,
    unit_text: str,
    candidates: tuple[OccupationalConstructCandidate, ...],
) -> tuple[OccupationalConstructSelection, ...]:
    """Validate model output against the offered catalog and source unit."""
    try:
        rows = json.loads(content.strip())
    except json.JSONDecodeError as exc:
        raise ValueError("occupational construct response is not JSON") from exc
    if not isinstance(rows, list):
        raise ValueError("occupational construct response must be an array")
    allowed = {candidate.construct_iri for candidate in candidates}
    selections: list[OccupationalConstructSelection] = []
    seen: set[str] = set()
    for row in rows:
        if not isinstance(row, dict) or set(row) != {"construct_iri", "evidence_text"}:
            raise ValueError("occupational construct selection has invalid fields")
        iri = row["construct_iri"]
        evidence = row["evidence_text"]
        if not isinstance(iri, str) or iri not in allowed or iri in seen:
            raise ValueError("occupational construct selection is not an offered unique IRI")
        if not isinstance(evidence, str) or not evidence.strip() or evidence not in unit_text:
            raise ValueError("occupational construct evidence is not a verbatim unit span")
        seen.add(iri)
        selections.append(OccupationalConstructSelection(iri, evidence))
    return tuple(selections)


class ContextualOrchestratorOccupationalConstructExtractionClient:
    """Use the gateway's multi-agent conduct workflow for exact catalog selection."""

    available = True

    def __init__(self, base_url: str, api_key: str, *, timeout: float = 180.0) -> None:
        self._url = f"{base_url.rstrip('/')}/v1/chat/completions"
        self._api_key = api_key
        self._timeout = timeout

    def select(
        self,
        unit_text: str,
        candidates: tuple[OccupationalConstructCandidate, ...],
    ) -> tuple[OccupationalConstructSelection, ...]:
        """Select every supported child without scores, ranking, or inferred terms."""
        catalog = "\n".join(
            f"- {item.construct_iri} | {item.preferred_label} | {item.description or ''}"
            for item in candidates
        )
        prompt = f"""\
Select every catalog entry directly supported by the semantic unit. Do not infer
a person trait, ability score, job requirement, cause, confidence, or intensity.
For each selection copy the shortest non-empty verbatim supporting span from the
unit. Reply only as a JSON array of objects with exactly construct_iri and
evidence_text. Use only the offered IRIs. Return [] when none applies.

Semantic unit:
{unit_text}

Official catalog candidates:
{catalog}
"""
        body = post_json(
            self._url,
            {
                "messages": [{"role": "user", "content": prompt}],
                "mode": "conduct",
                "reasoning_effort": "auto",
            },
            headers={"authorization": f"Bearer {self._api_key}"},
            timeout=self._timeout,
        )
        return parse_occupational_construct_selections(
            chat_completion_content(body), unit_text, candidates
        )
