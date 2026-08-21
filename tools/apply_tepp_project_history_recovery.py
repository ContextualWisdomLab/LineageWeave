"""Apply the bounded TEPP project-history recovery on its stacked branch."""

from __future__ import annotations

from pathlib import Path


def replace_once(path: str, old: str, new: str) -> None:
    """Replace one exact source fragment and fail if branch context drifted."""

    file_path = Path(path)
    text = file_path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"expected one anchor in {path}, found {count}")
    file_path.write_text(text.replace(old, new, 1), encoding="utf-8")


def append_once(path: str, marker: str, content: str) -> None:
    """Append a documented section only when it is not already present."""

    file_path = Path(path)
    text = file_path.read_text(encoding="utf-8")
    if marker in text:
        return
    file_path.write_text(text.rstrip() + "\n\n" + content.strip() + "\n", encoding="utf-8")


def patch_project_history_types() -> None:
    replace_once(
        "frontend/src/projectHistory.ts",
        'export type ProjectHistoryTruthStatus = "observed" | "inferred";\n'
        'export type ResponsibilityTransitionCode = "continuous" | "handoff" | "assignment_gap";\n',
        'export type ProjectHistoryTruthStatus = "observed" | "inferred";\n\n'
        'export interface TeppProjectHistoryFinding {\n'
        '  finding_code: string;\n'
        '  summary: string;\n'
        '  related_event_ids: string[];\n'
        '  evidence_post_ids: string[];\n'
        '}\n\n'
        'export interface TeppProjectHistoryMetadata {\n'
        '  contract_version: 1;\n'
        '  project_key: string;\n'
        '  project_name: string;\n'
        '  focus_event_id: string;\n'
        '  knowledge_cutoff: string;\n'
        '  history_span_start: string;\n'
        '  history_span_end: string;\n'
        '  participant_count: number;\n'
        '  inference_status: "temporal_association_only";\n'
        '  event_count: number;\n'
        '  findings: TeppProjectHistoryFinding[];\n'
        '}\n\n'
        'export interface TeppProjectHistoryValidation {\n'
        '  status: "validated" | "not_configured" | "unavailable" | "invalid_evidence";\n'
        '  project_history: TeppProjectHistoryMetadata | null;\n'
        '  next_action_code:\n'
        '    | "open_source_evidence"\n'
        '    | "configure_tepp_project_history"\n'
        '    | "retry_tepp_project_history";\n'
        '}\n\n'
        'export type ResponsibilityTransitionCode = "continuous" | "handoff" | "assignment_gap";\n',
    )
    replace_once(
        "frontend/src/projectHistory.ts",
        "  distinct_observed_actor_count: number;\n  truncated: boolean;\n  events: ProjectHistoryEvent[];\n",
        "  distinct_observed_actor_count: number;\n  truncated: boolean;\n"
        "  tepp_validation?: TeppProjectHistoryValidation;\n"
        "  events: ProjectHistoryEvent[];\n",
    )


def patch_timeline() -> None:
    replace_once(
        "frontend/src/components/ProjectHistoryTimeline.tsx",
        'import "./ProjectHistoryTimeline.css";\n',
        'import { TeppProjectHistoryEvidence } from "./TeppProjectHistoryEvidence";\n'
        'import "./ProjectHistoryTimeline.css";\n',
    )
    replace_once(
        "frontend/src/components/ProjectHistoryTimeline.tsx",
        '      <div\n        className="project-history-tabs"\n',
        '      {projection.tepp_validation ? (\n'
        '        <TeppProjectHistoryEvidence\n'
        '          validation={projection.tepp_validation}\n'
        '          onOpenPost={onOpenPost}\n'
        '          sourceLabels={Object.fromEntries(\n'
        '            projection.events.map((event) => [event.source_post_id, event.event_title]),\n'
        '          )}\n'
        '        />\n'
        '      ) : null}\n\n'
        '      <div\n        className="project-history-tabs"\n',
    )


def patch_backend_route() -> None:
    replace_once(
        "backend/app/main.py",
        "from lineageweave.project_history import normalize_project_key\n",
        "from backend.app.tepp_project_history import (\n"
        "    tenant_workspace_reference,\n"
        "    validate_project_history_with_tepp,\n"
        ")\n"
        "from lineageweave.project_history import normalize_project_key\n",
    )
    replace_once(
        "backend/app/main.py",
        """    async with pool.acquire() as conn:
        try:
            return await fetch_project_history_projection(
                conn,
                project_key=project_key,
                focus_post_id=focus_post_id,
                knowledge_cutoff=cutoff,
                corporate_entity_ids=list(account.corporate_entity_ids),
                limit=limit,
            )
        except ProjectHistoryNotFound as exc:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "project history not found") from exc
""",
        """    async with pool.acquire() as conn:
        try:
            projection = await fetch_project_history_projection(
                conn,
                project_key=project_key,
                focus_post_id=focus_post_id,
                knowledge_cutoff=cutoff,
                corporate_entity_ids=list(account.corporate_entity_ids),
                limit=limit,
            )
        except ProjectHistoryNotFound as exc:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "project history not found") from exc
    projection["tepp_validation"] = await asyncio.to_thread(
        validate_project_history_with_tepp,
        projection=projection,
        tenant_workspace_id=tenant_workspace_reference(account.corporate_entity_ids),
        transport_url=load_settings().tepp_transport_url,
    )
    return projection
""",
    )


def patch_documents() -> None:
    replace_once(
        "CHANGELOG.md",
        "## [2.18.0] - 2026-08-20\n",
        "## [2.19.0] - 2026-08-21\n\n"
        "### Added\n\n"
        "- Recovered the credential-free TEPP project-history validation boundary on top of\n"
        "  the canonical Buyer timeline. TEPP may return only cutoff-safe temporal\n"
        "  associations over the exact authorized events; the timeline remains readable\n"
        "  when TEPP is absent, and no result is labelled as a cause (ADR 0112).\n\n"
        "## [2.18.0] - 2026-08-20\n",
    )
    append_once(
        "docs/product-technical-gap-baseline.md",
        "## Recovered TEPP project-history integration (2026-08-21)",
        """
## Recovered TEPP project-history integration (2026-08-21)

- The canonical Buyer project timeline remains owned by the stacked Project history PR.
- The previously implemented TEPP work had become stranded in a closed parent and an
  orphaned duplicate stack. This recovery consumes the canonical timeline instead of
  introducing another project query, classifier, or timeline component.
- The dependency is the exact `ContextualWisdomLab/TEPP#159` project-history contract.
  Until that contract is merged and a TEPP endpoint is deployed, the UI reports an
  actionable fail-closed state and keeps the authorized LineageWeave timeline readable.
- TEPP receives opaque actor references and bounded source-field evidence only. Browser,
  review, provider, and `TEPP_API_KEY` credentials are not forwarded.
- `temporal_association_only` is the maximum accepted authority. Buyer copy must say
  that a preceding event is related in time, not that it caused the VOC.
- The next stacked slice attaches this same canonical timeline and TEPP metadata to
  Global Ask and post-scoped Ask without re-retrieving hidden evidence.
""",
    )


def main() -> None:
    """Apply all exact-context edits."""

    patch_project_history_types()
    patch_timeline()
    patch_backend_route()
    patch_documents()


if __name__ == "__main__":
    main()
