from __future__ import annotations

from pathlib import Path
from textwrap import dedent


def read(path: str) -> str:
    return Path(path).read_text()


def write(path: str, content: str) -> None:
    Path(path).write_text(content.rstrip() + "\n")


def replace_once(path: str, old: str, new: str) -> None:
    text = read(path)
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{path}: expected one anchor, found {count}: {old[:80]!r}")
    write(path, text.replace(old, new, 1))


write(
    "backend/app/corporate_entity_ingestion.py",
    dedent(
        '''
        """Resolve an organization mention to the corporate hierarchy catalog.

        Existing similarity matches are reused.  A previously unseen entity is
        created only after inference proposes its complete hierarchy placement
        and external verification corroborates that placement.  Parent failure,
        cycles, and excessive depth all fail closed.  See ADR 0010.
        """

        from __future__ import annotations

        import asyncio
        import hashlib

        import asyncpg

        from lineageweave.corporate_hierarchy_inference import (
            CorporateHierarchyInferenceClient,
            HierarchyProposal,
        )
        from lineageweave.corporate_hierarchy_resolution import (
            CorporateEntityCandidate,
            resolve_corporate_entity,
        )
        from lineageweave.relation_verification import (
            STATUS_CORROBORATED,
            RelationVerificationClient,
        )

        _AUTO_CODE_PREFIX = "AUTO-"
        _MAX_HIERARCHY_DEPTH = 4


        def _auto_entity_code(organization_name: str) -> str:
            """Return a deterministic, namespace-separated code."""
            digest = hashlib.sha256(organization_name.encode("utf-8")).hexdigest()[:16]
            return f"{_AUTO_CODE_PREFIX}{digest}"


        def _hierarchy_verification_label(proposal: HierarchyProposal) -> str:
            """Describe every persisted hierarchy field in one claim."""
            parent = proposal.parent_name if proposal.parent_name is not None else "NO_PARENT"
            return f"corporate hierarchy level={proposal.level_code}; immediate_parent={parent}"


        async def _create_entity(
            conn: asyncpg.Connection,
            organization_name: str,
            level_code: str,
            parent_entity_id: str | None,
        ) -> str:
            """Insert one entity atomically and return its catalog id."""
            row = await conn.fetchrow(
                """
                insert into corporate_entity
                    (parent_entity_id, corporate_entity_code, entity_name, entity_level_code)
                values ($1, $2, $3, $4)
                on conflict (corporate_entity_code) do update set
                    entity_name = excluded.entity_name,
                    entity_level_code = excluded.entity_level_code,
                    parent_entity_id = excluded.parent_entity_id
                returning corporate_entity_id
                """,
                parent_entity_id,
                _auto_entity_code(organization_name),
                organization_name,
                level_code,
            )
            return str(row["corporate_entity_id"])


        async def get_or_create_corporate_entity(
            conn: asyncpg.Connection,
            organization_name: str,
            context_text: str,
            inference_client: CorporateHierarchyInferenceClient,
            verification_client: RelationVerificationClient,
            candidates: list[CorporateEntityCandidate],
            *,
            _depth: int = 0,
            _visited_names: frozenset[str] = frozenset(),
        ) -> str | None:
            """Return a verified catalog id, otherwise ``None``.

            A proposed parent must independently corroborate and resolve before
            the child can be inserted.  Repeated names in the recursion path are
            cycles, including multi-node cycles such as A -> B -> A.
            """
            normalized_name = organization_name.strip()
            if not normalized_name:
                return None
            visit_key = normalized_name.casefold()
            if visit_key in _visited_names:
                return None

            existing_id = resolve_corporate_entity(normalized_name, candidates)
            if existing_id is not None:
                return existing_id
            if _depth >= _MAX_HIERARCHY_DEPTH or not inference_client.available:
                return None

            proposal = await asyncio.to_thread(
                inference_client.infer,
                normalized_name,
                context_text,
            )
            if proposal is None or not verification_client.available:
                return None

            placement_result = await asyncio.to_thread(
                verification_client.verify,
                normalized_name,
                _hierarchy_verification_label(proposal),
            )
            if placement_result.status_code != STATUS_CORROBORATED:
                return None

            visited_names = _visited_names | {visit_key}
            parent_entity_id: str | None = None
            if proposal.parent_name is not None:
                normalized_parent = proposal.parent_name.strip()
                if not normalized_parent or normalized_parent.casefold() in visited_names:
                    return None
                parent_result = await asyncio.to_thread(
                    verification_client.verify,
                    normalized_parent,
                    f"immediate parent of {normalized_name}",
                )
                if parent_result.status_code != STATUS_CORROBORATED:
                    return None
                parent_entity_id = await get_or_create_corporate_entity(
                    conn,
                    normalized_parent,
                    context_text,
                    inference_client,
                    verification_client,
                    candidates,
                    _depth=_depth + 1,
                    _visited_names=visited_names,
                )
                if parent_entity_id is None:
                    return None

            new_id = await _create_entity(
                conn,
                normalized_name,
                proposal.level_code,
                parent_entity_id,
            )
            candidates.append(
                CorporateEntityCandidate(
                    corporate_entity_id=new_id,
                    entity_name=normalized_name,
                )
            )
            return new_id
        '''
    ),
)

write(
    "backend/app/organization_name_resolution_ingestion.py",
    dedent(
        '''
        """Cache and persist verified organization-name normalization."""

        from __future__ import annotations

        import asyncio

        import asyncpg

        from lineageweave.organization_name_resolution import (
            OrganizationNameResolutionClient,
            resolve_and_verify_organization_name,
        )
        from lineageweave.relation_verification import (
            STATUS_CORROBORATED,
            RelationVerificationClient,
        )


        async def resolve_organization_name(
            conn: asyncpg.Connection,
            resolution_client: OrganizationNameResolutionClient,
            verification_client: RelationVerificationClient,
            raw_name: str,
            context_text: str,
        ) -> str:
            """Return the corroborated canonical name, otherwise ``raw_name``.

            Synchronous network adapters run in a worker thread so this async
            ingestion path does not block unrelated requests.
            """
            cached = await conn.fetchrow(
                "select resolved_organization_name, verification_status_code "
                "from organization_name_resolution where raw_organization_name = $1",
                raw_name,
            )
            if cached is not None:
                if cached["verification_status_code"] == STATUS_CORROBORATED:
                    return cached["resolved_organization_name"]
                return raw_name
            if not resolution_client.available:
                return raw_name

            resolution = await asyncio.to_thread(
                resolve_and_verify_organization_name,
                raw_name,
                context_text,
                resolution_client,
                verification_client,
            )
            if resolution is None:
                return raw_name

            await conn.execute(
                """
                insert into organization_name_resolution
                    (raw_organization_name, resolved_organization_name,
                     verification_status_code, verification_evidence_url)
                values ($1, $2, $3, $4)
                on conflict (raw_organization_name) do update set
                    resolved_organization_name = excluded.resolved_organization_name,
                    verification_status_code = excluded.verification_status_code,
                    verification_evidence_url = excluded.verification_evidence_url,
                    resolved_at = now()
                """,
                resolution.raw_organization_name,
                resolution.resolved_organization_name,
                resolution.verification_status_code,
                resolution.verification_evidence_url,
            )
            if resolution.verification_status_code == STATUS_CORROBORATED:
                return resolution.resolved_organization_name
            return raw_name
        '''
    ),
)

write(
    "backend/app/team_ingestion.py",
    dedent(
        '''
        """Resolve an R&R team actor to one shared cross-post identity."""

        from __future__ import annotations

        import asyncpg

        from lineageweave.corporate_hierarchy_resolution import (
            CorporateEntityCandidate,
            resolve_corporate_entity,
        )


        async def upsert_team(
            conn: asyncpg.Connection,
            team_name: str,
            affiliated_organization_name: str | None,
            candidates: list[CorporateEntityCandidate],
        ) -> str:
            """Atomically return the unique team identity for the pair.

            ``UNIQUE NULLS NOT DISTINCT`` makes NULL affiliations participate
            in the same conflict rule.  One upsert removes the prior
            read-then-insert race.
            """
            corporate_entity_id = (
                resolve_corporate_entity(affiliated_organization_name, candidates)
                if affiliated_organization_name
                else None
            )
            row = await conn.fetchrow(
                """
                insert into cataloged_team
                    (team_name, affiliated_organization_name,
                     affiliated_corporate_entity_id)
                values ($1, $2, $3)
                on conflict (team_name, affiliated_organization_name) do update set
                    affiliated_corporate_entity_id = coalesce(
                        excluded.affiliated_corporate_entity_id,
                        cataloged_team.affiliated_corporate_entity_id
                    )
                returning team_id
                """,
                team_name,
                affiliated_organization_name,
                corporate_entity_id,
            )
            return str(row["team_id"])
        '''
    ),
)

path = "backend/app/keyman_ingestion.py"
text = read(path)
text = text.replace(
    "import asyncpg\n",
    "import asyncio\nfrom dataclasses import replace\n\nimport asyncpg\n",
    1,
)
helper_anchor = "\n\nasync def ingest_post_keymen(\n"
helper = dedent(
    '''


    async def _upsert_affiliation(
        conn: asyncpg.Connection,
        person_id: str,
        raw_name: str,
        resolved_name: str,
        corporate_entity_id: str | None,
        role_title: str | None,
    ) -> None:
        """Promote a raw affiliation row into one canonical identity."""
        await conn.execute(
            """
            with legacy_affiliation as (
                select affiliated_corporate_entity_id, role_title
                  from person_affiliation
                 where person_id = $1
                   and affiliated_organization_name = $2
            ),
            canonical_affiliation as (
                insert into person_affiliation
                    (person_id, affiliated_organization_name,
                     affiliated_corporate_entity_id, role_title)
                values (
                    $1,
                    $3,
                    coalesce($4, (select affiliated_corporate_entity_id from legacy_affiliation)),
                    coalesce($5, (select role_title from legacy_affiliation))
                )
                on conflict (person_id, affiliated_organization_name)
                do update set
                    affiliated_corporate_entity_id = coalesce(
                        excluded.affiliated_corporate_entity_id,
                        person_affiliation.affiliated_corporate_entity_id
                    ),
                    role_title = coalesce(
                        excluded.role_title,
                        person_affiliation.role_title
                    )
                returning person_affiliation_id
            )
            delete from person_affiliation
             where person_id = $1
               and affiliated_organization_name = $2
               and $2 <> $3
            """,
            person_id,
            raw_name,
            resolved_name,
            corporate_entity_id,
            role_title,
        )
    '''
)
if "async def _upsert_affiliation(" not in text:
    if helper_anchor not in text:
        raise SystemExit("keyman helper anchor missing")
    text = text.replace(helper_anchor, helper + helper_anchor, 1)
text = text.replace(
    "    mentions = client.extract(post_title, post_body)\n"
    "    candidates = await _load_corporate_entity_candidates(conn)\n\n"
    "    for mention in mentions:\n",
    "    mentions = await asyncio.to_thread(client.extract, post_title, post_body)\n"
    "    candidates = await _load_corporate_entity_candidates(conn)\n"
    "    normalized_mentions: list[PersonMention] = []\n\n"
    "    for mention in mentions:\n",
    1,
)
start = text.index("        for organization_name in mention.affiliated_organization_names:")
end_marker = "\n    return mentions\n"
end = text.index(end_marker, start) + len(end_marker)
replacement = dedent(
    '''
            resolved_names: list[str] = []
            for organization_name in mention.affiliated_organization_names:
                resolved_name = await resolve_organization_name(
                    conn,
                    resolution_client,
                    verification_client,
                    organization_name,
                    post_body,
                )
                corporate_entity_id = await get_or_create_corporate_entity(
                    conn,
                    resolved_name,
                    post_body,
                    hierarchy_inference_client,
                    verification_client,
                    candidates,
                )
                await _upsert_affiliation(
                    conn,
                    person_id,
                    organization_name,
                    resolved_name,
                    corporate_entity_id,
                    mention.job_title,
                )
                if resolved_name not in resolved_names:
                    resolved_names.append(resolved_name)
            normalized_mentions.append(
                replace(
                    mention,
                    affiliated_organization_names=tuple(resolved_names),
                )
            )

        if normalized_mentions:
            await persist_edges_for_post(conn, post_id)

        return normalized_mentions
    '''
)
text = text[:start] + replacement + text[end:]
write(path, text)

path = "backend/app/post_summary_ingestion.py"
text = read(path)
anchor = (
    "    context_text = post_body if post_body is not None else summary.korean_summary\n"
    "    await conn.execute(\"delete from post_summary_result where post_id = $1\", post_id)\n"
)
replacement = dedent(
    '''
        context_text = post_body if post_body is not None else summary.korean_summary
        # Summary replacement also replaces its team/organization projections.
        # Keyman-owned person mentions are intentionally left untouched.
        await conn.execute(
            """
            delete from knowledge_graph_edge
             where target_node_type_code = 'node_post'
               and target_node_id = $1::uuid
               and edge_type_code in (
                   'edge_mention_team',
                   'edge_mention_organization'
               )
            """,
            post_id,
        )
        await conn.execute("delete from post_team_mention where post_id = $1", post_id)
        await conn.execute("delete from post_organization_mention where post_id = $1", post_id)
        await conn.execute("delete from post_summary_result where post_id = $1", post_id)
    '''
)
if anchor not in text:
    raise SystemExit("summary cleanup anchor missing")
text = text.replace(anchor, replacement, 1)
write(path, text)

path = "backend/app/main.py"
text = read(path)
if "import asyncio\n" not in text:
    text = text.replace(
        "from __future__ import annotations\n\n",
        "from __future__ import annotations\n\nimport asyncio\n",
        1,
    )
text = text.replace(
    "        summary = client.summarize(post[\"post_title\"], normalized_body)\n",
    "        summary = await asyncio.to_thread(\n"
    "            client.summarize, post[\"post_title\"], normalized_body\n"
    "        )\n",
    1,
)
write(path, text)

replace_once(
    "docs/ontology/lineageweave-kg.ttl",
    ''':mentionsTeam a owl:ObjectProperty ;
    rdfs:domain :Post ;
    rdfs:range :Team ;
    rdfs:label "mentions team" ;
    rdfs:comment "A post names a cataloged team (post_team_mention)." ;
''',
    ''':mentionsTeam a owl:ObjectProperty ;
    rdfs:domain :Team ;
    rdfs:range :Post ;
    rdfs:label "mentioned in post" ;
    rdfs:comment "A cataloged team is named by a post (post_team_mention)." ;
''',
)
replace_once(
    "docs/ontology/lineageweave-kg.ttl",
    ''':mentionsOrganization a owl:ObjectProperty ;
    rdfs:domain :Post ;
    rdfs:range :CorporateEntity ;
    rdfs:label "mentions organization" ;
    rdfs:comment "A post names an organization acting in its own name, resolved to a real corporate_entity (post_organization_mention)." ;
''',
    ''':mentionsOrganization a owl:ObjectProperty ;
    rdfs:domain :CorporateEntity ;
    rdfs:range :Post ;
    rdfs:label "mentioned in post" ;
    rdfs:comment "A resolved organization is named by a post (post_organization_mention)." ;
''',
)

replace_once(
    "Makefile",
    "\tKEYCLOAK_ADMIN_PASSWORD=$${KEYCLOAK_ADMIN_PASSWORD:-admin_dev_only} python3 scripts/seed_demo_data.py",
    "\t@test -n \"$${KEYCLOAK_ADMIN_PASSWORD:-}\" || { echo \"KEYCLOAK_ADMIN_PASSWORD is required\" >&2; exit 1; }; \\\n\tpython3 scripts/seed_demo_data.py",
)
