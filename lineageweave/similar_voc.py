"""Evidence-gated similar-VOC adjudication and RankWeave ordering."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Mapping, Protocol, Sequence

from .http_client import chat_completion_content, post_json
from .rankweave_client import RankWeaveClient, RankingList


@dataclass(frozen=True)
class SimilarVocEvidence:
    """A semantically equivalent VOC with extractive evidence from both posts."""

    candidate_post_id: str
    issue_summary: str
    focal_evidence_text: str
    candidate_evidence_text: str
    customer_cohort_text: str | None
    action_history: tuple[str, ...]


class SimilarVocAnalysisClient(Protocol):
    """Adjudicate embedding-retrieved candidates through the orchestrator."""

    available: bool

    def analyze(
        self, focal_title: str, focal_body: str, candidate_post_id: str,
        candidate_title: str, candidate_body: str,
    ) -> SimilarVocEvidence | None:
        """Return a cited equivalent issue, or ``None`` when it is not equivalent."""
        raise NotImplementedError


_PROMPT = """Decide whether these two business records describe the same operational issue
type. Do not use keyword matching. Use their meaning, actors, affected object, failure mode,
and outcome. Return ONLY JSON with `similar` (boolean). If false, return only that field.
If true, also return issue_summary, focal_evidence_text (verbatim from focal body),
candidate_evidence_text (verbatim from candidate body), customer_cohort_text (string or null),
and action_history (an array containing only source-supported past actions, each verbatim from
the candidate body). Customer cohort may be stated only when the records explicitly identify
the same cataloged or source customer; otherwise use null.

Focal title: {focal_title}
Focal body: {focal_body}
Candidate title: {candidate_title}
Candidate body: {candidate_body}
"""


def parse_similar_voc_response(
    content: str, candidate_post_id: str, focal_body: str, candidate_body: str,
) -> SimilarVocEvidence | None:
    """Accept only a positive result whose evidence is present in its source body."""
    try:
        payload = json.loads(content.strip())
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict) or payload.get("similar") is not True:
        return None
    summary = payload.get("issue_summary")
    focal_evidence = payload.get("focal_evidence_text")
    candidate_evidence = payload.get("candidate_evidence_text")
    cohort = payload.get("customer_cohort_text")
    actions = payload.get("action_history")
    if (
        not isinstance(summary, str) or not summary.strip()
        or not isinstance(focal_evidence, str) or focal_evidence not in focal_body
        or not isinstance(candidate_evidence, str) or candidate_evidence not in candidate_body
        or (cohort is not None and (not isinstance(cohort, str) or not cohort.strip()))
        or not isinstance(actions, list)
        or any(not isinstance(action, str) or action not in candidate_body for action in actions)
    ):
        return None
    return SimilarVocEvidence(
        candidate_post_id, summary.strip(), focal_evidence, candidate_evidence,
        cohort.strip() if isinstance(cohort, str) else None, tuple(actions),
    )


class ContextualOrchestratorSimilarVocAnalysisClient:
    """Use contextual-orchestrator auto mode for evidence-gated equivalence."""

    available = True

    def __init__(self, base_url: str, api_key: str, *, timeout: float = 180.0) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._timeout = timeout

    def analyze(
        self, focal_title: str, focal_body: str, candidate_post_id: str,
        candidate_title: str, candidate_body: str,
    ) -> SimilarVocEvidence | None:
        """Ask the governed inference boundary and validate its extractive evidence."""
        response = post_json(
            f"{self._base_url}/v1/chat/completions",
            {"messages": [{"role": "user", "content": _PROMPT.format(
                focal_title=focal_title, focal_body=focal_body,
                candidate_title=candidate_title, candidate_body=candidate_body,
            )}], "mode": "auto", "reasoning_effort": "auto"},
            headers={"authorization": f"Bearer {self._api_key}"}, timeout=self._timeout,
        )
        return parse_similar_voc_response(
            chat_completion_content(response), candidate_post_id, focal_body, candidate_body,
        )


def rank_similar_voc_candidates(
    channel_ranks: Mapping[str, Sequence[str]], titles_by_id: Mapping[str, str],
    estimated_weights: Mapping[str, float], rankweave: RankWeaveClient,
) -> RankingList:
    """Fuse semantic, customer, and temporal ranks using an exact estimated vector.

    The caller must load the vector through ``load_estimated_channel_weights``.
    Missing or partial vectors fail closed instead of receiving equal or local weights.
    """
    channels = {name: list(ids) for name, ids in channel_ranks.items() if ids}
    weights = {name: float(estimated_weights[name]) for name in channels if name in estimated_weights}
    if not channels or set(weights) != set(channels) or any(value <= 0 for value in weights.values()):
        raise ValueError("similar VOC ranking requires a complete estimated channel-weight vector")
    return rankweave.fuse_rankings(channels, titles_by_id, weights=weights)
