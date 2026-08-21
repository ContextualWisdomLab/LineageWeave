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
    """Add strict TEPP metadata types to the canonical timeline contract."""

    replace_once(
        "frontend/src/projectHistory.ts",
        'export type ProjectHistoryTruthStatus = "observed" | "inferred";\n'
        'export type ResponsibilityTransitionCode = "continuous" | "handoff" | "assignment_gap";\n',
        'export type ProjectHistoryTruthStatus = "observed" | "inferred";\n\n'
        'export type TeppProjectHistoryFindingCode =\n'
        '  | "contract_award_before_focus"\n'
        '  | "specification_change_before_focus"\n'
        '  | "delivery_before_focus"\n'
        '  | "handoff_before_focus"\n'
        '  | "rebid_after_focus"\n'
        '  | "specification_change_and_handoff_before_focus";\n\n'
        'export interface TeppProjectHistoryFinding {\n'
        '  finding_code: TeppProjectHistoryFindingCode;\n'
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
        'export type TeppProjectHistoryValidation =\n'
        '  | {\n'
        '      status: "validated";\n'
        '      project_history: TeppProjectHistoryMetadata;\n'
        '      next_action_code: "open_source_evidence";\n'
        '    }\n'
        '  | {\n'
        '      status: "not_configured";\n'
        '      project_history: null;\n'
        '      next_action_code: "configure_tepp_project_history";\n'
        '    }\n'
        '  | {\n'
        '      status: "unavailable";\n'
        '      project_history: null;\n'
        '      next_action_code: "retry_tepp_project_history";\n'
        '    }\n'
        '  | {\n'
        '      status: "invalid_evidence";\n'
        '      project_history: null;\n'
        '      next_action_code: "open_source_evidence";\n'
        '    };\n\n'
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
    """Render TEPP metadata inside the reusable canonical timeline."""

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
    """Attach optional TEPP validation after the authorized read model is built."""

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


def patch_strict_client() -> None:
    """Reject provider-authored finding vocabularies and invalid responses."""

    replace_once(
        "lineageweave/tepp_project_history.py",
        "PROJECT_HISTORY_ACTOR_LIMIT = 64\n",
        "PROJECT_HISTORY_ACTOR_LIMIT = 64\n"
        "PROJECT_HISTORY_FINDING_CODES = frozenset(\n"
        "    {\n"
        '        "contract_award_before_focus",\n'
        '        "specification_change_before_focus",\n'
        '        "delivery_before_focus",\n'
        '        "handoff_before_focus",\n'
        '        "rebid_after_focus",\n'
        '        "specification_change_and_handoff_before_focus",\n'
        "    }\n"
        ")\n",
    )
    replace_once(
        "lineageweave/tepp_project_history.py",
        """class TeppProjectHistoryUnavailable(RuntimeError):
    \"\"\"TEPP was absent or returned a response outside the public contract.\"\"\"


""",
        """class TeppProjectHistoryUnavailable(RuntimeError):
    \"\"\"TEPP was absent or the project-history exchange could not complete.\"\"\"


class TeppProjectHistoryInvalidResponse(TeppProjectHistoryUnavailable):
    \"\"\"TEPP returned data outside the accepted public response contract.\"\"\"


""",
    )
    replace_once(
        "lineageweave/tepp_project_history.py",
        """    related_ids = [_text(item, \"related_event_id\", 256) for item in related]
    evidence_ids = [_text(item, \"evidence_post_id\", 256) for item in evidence]
    if (
        not related_ids
        or not evidence_ids
        or not set(related_ids).issubset(event_ids)
        or not set(evidence_ids).issubset(source_post_ids)
    ):
        raise TeppProjectHistoryUnavailable(\"finding cites evidence outside the bundle\")
    return {
        \"finding_code\": _code(payload[\"finding_code\"], \"finding_code\"),
        \"summary\": _text(payload[\"summary\"], \"finding summary\", 4096),
        \"related_event_ids\": related_ids,
        \"evidence_post_ids\": evidence_ids,
    }
""",
        """    related_ids = [_text(item, \"related_event_id\", 256) for item in related]
    evidence_ids = [_text(item, \"evidence_post_id\", 256) for item in evidence]
    if (
        not related_ids
        or not evidence_ids
        or len(related_ids) != len(set(related_ids))
        or len(evidence_ids) != len(set(evidence_ids))
        or not set(related_ids).issubset(event_ids)
        or not set(evidence_ids).issubset(source_post_ids)
    ):
        raise TeppProjectHistoryUnavailable(\"finding cites invalid evidence references\")
    finding_code = _code(payload[\"finding_code\"], \"finding_code\")
    if finding_code not in PROJECT_HISTORY_FINDING_CODES:
        raise TeppProjectHistoryUnavailable(\"finding code is outside the public vocabulary\")
    return {
        \"finding_code\": finding_code,
        \"summary\": _text(payload[\"summary\"], \"finding summary\", 4096),
        \"related_event_ids\": related_ids,
        \"evidence_post_ids\": evidence_ids,
    }
""",
    )
    replace_once(
        "lineageweave/tepp_project_history.py",
        "        return validate_tepp_project_history_projection(response, request=payload)\n",
        """        try:
            return validate_tepp_project_history_projection(response, request=payload)
        except TeppProjectHistoryUnavailable as exc:
            raise TeppProjectHistoryInvalidResponse(
                \"TEPP project-history response failed validation\"
            ) from exc
""",
    )


def patch_backend_adapter() -> None:
    """Expose invalid TEPP responses separately from transport outages."""

    replace_once(
        "backend/app/tepp_project_history.py",
        "    TeppProjectHistoryClient,\n    TeppProjectHistoryUnavailable,\n",
        "    TeppProjectHistoryClient,\n"
        "    TeppProjectHistoryInvalidResponse,\n"
        "    TeppProjectHistoryUnavailable,\n",
    )
    replace_once(
        "backend/app/tepp_project_history.py",
        """    try:
        validated = TeppProjectHistoryClient(transport_url).project(request)
    except TeppProjectHistoryUnavailable:
        return {
            \"status\": \"unavailable\",
            \"project_history\": None,
            \"next_action_code\": \"retry_tepp_project_history\",
        }
""",
        """    try:
        validated = TeppProjectHistoryClient(transport_url).project(request)
    except TeppProjectHistoryInvalidResponse:
        return {
            \"status\": \"invalid_evidence\",
            \"project_history\": None,
            \"next_action_code\": \"open_source_evidence\",
        }
    except TeppProjectHistoryUnavailable:
        return {
            \"status\": \"unavailable\",
            \"project_history\": None,
            \"next_action_code\": \"retry_tepp_project_history\",
        }
""",
    )


def patch_versions() -> None:
    """Keep package metadata aligned with the documented release slice."""

    replace_once(
        "pyproject.toml",
        'version = "2.18.0"\n',
        'version = "2.19.0"\n',
    )
    replace_once(
        "frontend/package.json",
        '  "version": "2.18.0",\n',
        '  "version": "2.19.0",\n',
    )
    replace_once(
        "uv.lock",
        'name = "lineageweave"\nversion = "2.18.0"\n',
        'name = "lineageweave"\nversion = "2.19.0"\n',
    )


def patch_documents() -> None:
    """Record the recovered integration and the remaining Ask-surface gap."""

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
- Accepted findings are limited to TEPP #159's closed temporal-association vocabulary;
  provider-authored prose is not used as Buyer-facing interpretation.
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
    patch_strict_client()
    patch_backend_adapter()
    patch_versions()
    patch_documents()


if __name__ == "__main__":
    main()
