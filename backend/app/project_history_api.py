"""Versioned HTTP contract for evidence-bound project-history timelines."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field

from backend.app.auth import CurrentAccount, get_current_account
from backend.app.db import get_pool
from backend.app.project_history import (
    PROJECT_HISTORY_DEFAULT_LIMIT,
    PROJECT_HISTORY_MAXIMUM_LIMIT,
    ProjectHistoryNotFound,
    fetch_project_history_projection,
)
from backend.app.source_post_revision import parse_as_of_clock

router = APIRouter()


class ProjectHistoryMatch(BaseModel):
    """One explicit or semantic fact binding a source record to a project."""

    model_config = ConfigDict(extra="forbid")

    match_kind_code: str
    matched_value: str
    truth_status_code: Literal["observed", "inferred"]
    confidence: float | None
    ontology_iri: str | None
    provenance: str


class ProjectHistoryResponsibility(BaseModel):
    """One responsibility observed in a source record, not an HR assignment."""

    model_config = ConfigDict(extra="forbid")

    actor_key: str
    actor_name: str
    actor_type_code: str
    affiliated_organization_name: str | None
    responsibility: str
    truth_status_code: Literal["observed"]
    provenance: Literal["post_summary_role"]


class ProjectHistoryPathEdge(BaseModel):
    """One persisted inferred lineage edge inside a visible prior path."""

    model_config = ConfigDict(extra="forbid")

    parent_event_id: str
    child_event_id: str
    fused_score: float


class ProjectHistoryPriorPath(BaseModel):
    """A visible-only, non-causal shortest path from a prior event."""

    model_config = ConfigDict(extra="forbid")

    source_event_id: str
    target_event_id: str
    event_ids: list[str]
    edges: list[ProjectHistoryPathEdge]
    minimum_fused_score: float
    truth_status_code: Literal["inferred"]
    source_relation_code: Literal["post_lineage_edge"]
    provenance: Literal["post_lineage_edge.fused_score"]


class ProjectHistoryEvent(BaseModel):
    """One authorized source record on the chronological Buyer timeline."""

    model_config = ConfigDict(extra="forbid")

    event_id: str
    source_post_id: str
    event_title: str
    event_type_code: str
    event_type_basis_code: Literal["display_classification"]
    occurred_at: str
    time_basis_code: Literal["document_time"]
    voc_type_code: str | None
    source_stage_code: str | None
    source_detail_state_code: str | None
    project_matches: list[ProjectHistoryMatch]
    observed_responsibilities: list[ProjectHistoryResponsibility]
    responsibility_transition_code: Literal["continuous", "handoff", "assignment_gap"] | None
    related_prior_paths: list[ProjectHistoryPriorPath]


class ProjectHistoryProjection(BaseModel):
    """Strict version-one project-history response contract."""

    model_config = ConfigDict(extra="forbid")

    contract_version: Literal[1]
    project_key: str
    normalized_project_key: str
    project_name: str
    focus_event_id: str
    time_basis_code: Literal["document_time"]
    event_count: int = Field(ge=0)
    distinct_observed_actor_count: int = Field(ge=0)
    truncated: bool
    events: list[ProjectHistoryEvent]


def _parse_knowledge_cutoff(value: str | None) -> datetime:
    """Return the explicit cutoff or the current UTC clock for a live read."""

    if value is None:
        return datetime.now(timezone.utc)
    try:
        return parse_as_of_clock(value)
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            422,
            "knowledge_cutoff must be an ISO-8601 timestamp",
        ) from exc


@router.get("/api/project-history", response_model=ProjectHistoryProjection)
async def read_project_history(
    project_key: str = Query(min_length=1, max_length=512),
    focus_post_id: UUID | None = Query(default=None),
    knowledge_cutoff: str | None = Query(default=None),
    limit: int = Query(
        default=PROJECT_HISTORY_DEFAULT_LIMIT,
        ge=1,
        le=PROJECT_HISTORY_MAXIMUM_LIMIT,
    ),
    account: CurrentAccount = Depends(get_current_account),
    pool: Any = Depends(get_pool),
) -> dict[str, Any]:
    """Return one ABAC-safe project timeline without revealing hidden matches."""

    if not account.has_permission("post_read"):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "account lacks the post_read permission",
        )
    cutoff = _parse_knowledge_cutoff(knowledge_cutoff)
    try:
        async with pool.acquire() as connection:
            projection = await fetch_project_history_projection(
                connection,
                project_key=project_key,
                focus_post_id=str(focus_post_id) if focus_post_id is not None else None,
                knowledge_cutoff=cutoff,
                corporate_entity_ids=sorted(account.corporate_entity_ids),
                limit=limit,
            )
    except ProjectHistoryNotFound as exc:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "project history not found",
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            422,
            "project history request is invalid",
        ) from exc
    return ProjectHistoryProjection.model_validate(projection).model_dump(mode="json")
