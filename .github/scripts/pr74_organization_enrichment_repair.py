"""One-shot reviewed repair for PR 74 transaction boundaries."""

from pathlib import Path

path = Path("backend/app/post_summary_ingestion.py")
text = path.read_text(encoding="utf-8")

old_persist = """    context_text = post_body if post_body is not None else summary.korean_summary
    # Summary replacement also replaces its team/organization projections.
    # Keyman-owned person mentions are intentionally left untouched.
    async with conn.transaction():
        await _replace_summary_projection(
            conn,
            post_id,
            summary,
            context_text,
            hierarchy_inference_client,
            verification_client,
        )
"""
new_persist = """    context_text = post_body if post_body is not None else summary.korean_summary
    candidates: list[Any] = []
    organization_entity_ids: dict[str, str | None] = {}
    if summary.roles_and_responsibilities:
        candidates = await _load_corporate_entity_candidates(conn)
        for role in summary.roles_and_responsibilities:
            if (
                role.actor_type_code == ACTOR_TYPE_ORGANIZATION
                and role.actor_name not in organization_entity_ids
            ):
                organization_entity_ids[role.actor_name] = await get_or_create_corporate_entity(
                    conn,
                    role.actor_name,
                    context_text,
                    hierarchy_inference_client,
                    verification_client,
                    candidates,
                )

    # Summary replacement also replaces its team/organization projections.
    # Keyman-owned person mentions are intentionally left untouched. Potentially
    # slow LLM/search enrichment and its own advisory-lock transaction finish
    # above; this transaction contains only the atomic replacement writes.
    async with conn.transaction():
        await _replace_summary_projection(
            conn,
            post_id,
            summary,
            candidates,
            organization_entity_ids,
        )
"""
if old_persist not in text:
    raise SystemExit("persist_post_summary replacement anchor not found")
text = text.replace(old_persist, new_persist, 1)

old_signature = """async def _replace_summary_projection(
    conn: asyncpg.Connection,
    post_id: str,
    summary: PostSummary,
    context_text: str,
    hierarchy_inference_client: CorporateHierarchyInferenceClient,
    verification_client: RelationVerificationClient,
) -> None:
    \"\"\"Write one atomic replacement of the stored summary and its mentions.\"\"\"
"""
new_signature = """async def _replace_summary_projection(
    conn: asyncpg.Connection,
    post_id: str,
    summary: PostSummary,
    candidates: list[Any],
    organization_entity_ids: dict[str, str | None],
) -> None:
    \"\"\"Write one atomic replacement using identities resolved beforehand.\"\"\"
"""
if old_signature not in text:
    raise SystemExit("_replace_summary_projection signature anchor not found")
text = text.replace(old_signature, new_signature, 1)

old_resolution = """    if summary.roles_and_responsibilities:
        candidates = await _load_corporate_entity_candidates(conn)
        for role in summary.roles_and_responsibilities:
            if role.actor_type_code == ACTOR_TYPE_TEAM:
                team_id = await upsert_team(
                    conn, role.actor_name, role.affiliated_organization_name, candidates
                )
                await conn.execute(
                    \"insert into post_team_mention (post_id, team_id) values ($1, $2) \"
                    \"on conflict do nothing\",
                    post_id,
                    team_id,
                )
            elif role.actor_type_code == ACTOR_TYPE_ORGANIZATION:
                corporate_entity_id = await get_or_create_corporate_entity(
                    conn,
                    role.actor_name,
                    context_text,
                    hierarchy_inference_client,
                    verification_client,
                    candidates,
                )
                if corporate_entity_id is not None:
                    await conn.execute(
                        \"insert into post_organization_mention (post_id, corporate_entity_id) \"
                        \"values ($1, $2) on conflict do nothing\",
                        post_id,
                        corporate_entity_id,
                    )
"""
new_resolution = """    if summary.roles_and_responsibilities:
        for role in summary.roles_and_responsibilities:
            if role.actor_type_code == ACTOR_TYPE_TEAM:
                team_id = await upsert_team(
                    conn, role.actor_name, role.affiliated_organization_name, candidates
                )
                await conn.execute(
                    \"insert into post_team_mention (post_id, team_id) values ($1, $2) \"
                    \"on conflict do nothing\",
                    post_id,
                    team_id,
                )
            elif role.actor_type_code == ACTOR_TYPE_ORGANIZATION:
                corporate_entity_id = organization_entity_ids.get(role.actor_name)
                if corporate_entity_id is not None:
                    await conn.execute(
                        \"insert into post_organization_mention (post_id, corporate_entity_id) \"
                        \"values ($1, $2) on conflict do nothing\",
                        post_id,
                        corporate_entity_id,
                    )
"""
if old_resolution not in text:
    raise SystemExit("organization resolution block anchor not found")
text = text.replace(old_resolution, new_resolution, 1)
path.write_text(text, encoding="utf-8")

changelog_path = Path("CHANGELOG.md")
changelog = changelog_path.read_text(encoding="utf-8")
marker = """- Corporate-entity creation now performs network inference/verification before acquiring
"""
addition = """- Post-summary organization enrichment now completes before the atomic replacement
  transaction, preventing external inference and a nested advisory-lock transaction
  from holding summary write locks while preserving all replacement writes as one unit.
"""
if addition not in changelog:
    if marker not in changelog:
        raise SystemExit("CHANGELOG transaction section anchor not found")
    changelog = changelog.replace(marker, addition + marker, 1)
    changelog_path.write_text(changelog, encoding="utf-8")
