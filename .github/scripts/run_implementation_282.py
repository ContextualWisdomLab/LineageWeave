"""Run the PR #282 implementation with exact current-branch overrides."""

from __future__ import annotations

import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).with_name("implement_282_tepp_project_history.py")
SPEC = importlib.util.spec_from_file_location("implement_282", SCRIPT)
if SPEC is None or SPEC.loader is None:
    raise SystemExit("could not load implementation module")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
ORIGINAL_PATCH_TESTS = MODULE.patch_tests


def patch_client() -> None:
    """Align the strict client with TEPP's lower-snake-case code contract."""
    path = "lineageweave/tepp_project_history.py"
    source = MODULE.read(path)
    source = MODULE.replace_once(
        source,
        "from dataclasses import dataclass\n",
        "import re\n\nfrom dataclasses import dataclass\n",
        label="client regex import",
    )
    anchor = "_MAX_IDENTITY_TEXT = 256\n"
    source = MODULE.replace_once(
        source,
        anchor,
        anchor + "_CODE_PATTERN = re.compile(r\"^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$\")\n",
        label="client code pattern",
    )
    helper_anchor = "def _parse_utc_timestamp(value: Any, *, name: str) -> datetime:\n"
    helper = '''def _require_code(value: Any, *, name: str, maximum: int = 128) -> str:\n    """Return one closed lower-snake-case code."""\n    code = _require_text(value, name=name, maximum=maximum)\n    if _CODE_PATTERN.fullmatch(code) is None:\n        raise TeppProjectHistoryUnavailable(f"{name} must be lower snake_case")\n    return code\n\n\n'''
    if helper not in source:
        source = MODULE.replace_once(
            source,
            helper_anchor,
            helper + helper_anchor,
            label="client code validator",
        )
    source = source.replace(
        '''"event_type_code": _require_text(\n                self.event_type_code, name="event_type_code", maximum=96\n            ),''',
        '''"event_type_code": _require_code(\n                self.event_type_code, name="event_type_code", maximum=96\n            ),''',
    )
    source = source.replace(
        '''"availability_basis": _require_text(\n                self.availability_basis, name="availability_basis", maximum=128\n            ),''',
        '''"availability_basis": _require_code(\n                self.availability_basis, name="availability_basis", maximum=128\n            ),''',
    )
    source = source.replace(
        '''event_type_code=_require_text(\n                payload.get("event_type_code"), name="event_type_code", maximum=96\n            ),''',
        '''event_type_code=_require_code(\n                payload.get("event_type_code"), name="event_type_code", maximum=96\n            ),''',
    )
    source = source.replace(
        '''availability_basis=_require_text(\n                payload.get("availability_basis"), name="availability_basis", maximum=128\n            ),''',
        '''availability_basis=_require_code(\n                payload.get("availability_basis"), name="availability_basis", maximum=128\n            ),''',
    )
    MODULE.write(path, source)


def patch_backend_adapter() -> None:
    """Load a bounded complete authorized project history and its explicit actors."""
    path = "backend/app/tepp_project_history.py"
    source = MODULE.read(path)
    if "import asyncio\n" not in source:
        source = MODULE.replace_once(
            source,
            "import hashlib\n",
            "import asyncio\nimport hashlib\n",
            label="adapter asyncio import",
        )
    if "from backend.app.post_eligibility import SOURCE_POST_ELIGIBILITY_SQL" not in source:
        source = MODULE.replace_once(
            source,
            "import asyncpg\n\n",
            "import asyncpg\n\nfrom backend.app.post_eligibility import SOURCE_POST_ELIGIBILITY_SQL\n\n",
            label="adapter eligibility import",
        )
    source = source.replace('"handoff": "operational_handoff",', '"handoff": "handoff_recorded",')
    source = source.replace(
        '"operational_handoff": "operational_handoff",',
        '"operational_handoff": "handoff_recorded",',
    )
    source = source.replace('"go_live": "operational_handoff",', '"go_live": "handoff_recorded",')
    source = source.replace(
        'availability_basis="source_post.created_at",',
        'availability_basis="source_created_at_proxy",',
    )

    start, end, _ = MODULE.function_region(
        source,
        "async def _load_project_rows(",
        next_markers=("\n\nasync def project_history_for_post_ids(",),
    )
    replacement = '''async def _load_project_rows(\n    conn: asyncpg.Connection,\n    *,\n    focus_post_id: str,\n    source_post_ids: Sequence[str],\n    corporate_entity_ids: Iterable[str],\n    knowledge_cutoff: datetime,\n) -> list[Mapping[str, Any]]:\n    """Load at most 128 eligible, authorized rows for the focus post's exact project.\n\n    ``source_post_ids`` remains a caller-compatibility input, not an\n    authorization shortcut.  The focus post is always retained inside the\n    bounded set; the remaining slots contain the most recent eligible records.\n    """\n    _ = source_post_ids\n    authorized_entities = list(corporate_entity_ids)\n    focus = await conn.fetchrow(\n        f"""\n        select post.post_id, post.source_project_code, post.source_project_name\n          from source_post post\n         where post.post_id = $1::uuid\n           and post.created_at <= $3\n           and {SOURCE_POST_ELIGIBILITY_SQL.format(alias='post')}\n           and (\n               post.visibility_code = 'public'\n               or post.corporate_entity_id::text = any($2::text[])\n           )\n        """,\n        focus_post_id,\n        authorized_entities,\n        knowledge_cutoff,\n    )\n    if focus is None or not str(focus["source_project_code"] or "").strip():\n        return []\n    project_key = str(focus["source_project_code"]).strip()\n    rows = await conn.fetch(\n        f"""\n        with bounded_project_history as (\n            select post.post_id,\n                   post.post_title,\n                   post.source_stage_code,\n                   post.voc_type_code,\n                   post.source_project_code,\n                   post.source_project_name,\n                   btrim(left(source_post_search_text(post.post_body), 2000)) as post_body_excerpt,\n                   post.created_at,\n                   array(\n                       select actor.actor_id\n                         from (\n                             select post.author_account_id::text as actor_id\n                             union\n                             select mention.person_id::text as actor_id\n                               from post_person_mention mention\n                              where mention.post_id = post.post_id\n                         ) actor\n                        where actor.actor_id is not null\n                          and btrim(actor.actor_id) <> ''\n                        order by actor.actor_id\n                   ) as actor_ids\n              from source_post post\n             where post.source_project_code = $1\n               and post.created_at <= $2\n               and {SOURCE_POST_ELIGIBILITY_SQL.format(alias='post')}\n               and (\n                   post.visibility_code = 'public'\n                   or post.corporate_entity_id::text = any($3::text[])\n               )\n             order by case when post.post_id = $4::uuid then 0 else 1 end,\n                      post.created_at desc, post.post_id desc\n             limit 128\n        )\n        select *\n          from bounded_project_history\n         order by created_at, post_id\n        """,\n        project_key,\n        knowledge_cutoff,\n        authorized_entities,\n        focus_post_id,\n    )\n    return [dict(row) for row in rows]\n'''
    source = source[:start] + replacement + source[end:]
    source = MODULE.replace_once(
        source,
        "        projection = client.project(request)\n",
        "        projection = await asyncio.to_thread(client.project, request)\n",
        label="adapter off-loop TEPP call",
    )
    MODULE.write(path, source)


def patch_tests() -> None:
    """Apply the base tests and pin the authorization/bounding query contract."""
    ORIGINAL_PATCH_TESTS()
    path = "tests/test_tepp_project_history_ingestion.py"
    source = MODULE.read(path)
    anchor = '''    assert all(event.availability_basis == "source_created_at_proxy" for event in request.events)\n'''
    addition = '''\n\ndef test_project_history_loader_keeps_focus_bounded_and_uses_explicit_actor_evidence() -> None:\n    source = Path("backend/app/tepp_project_history.py").read_text(encoding="utf-8")\n    assert "SOURCE_POST_ELIGIBILITY_SQL" in source\n    assert "post.source_project_code = $1" in source\n    assert "case when post.post_id = $4::uuid then 0 else 1 end" in source\n    assert "limit 128" in source\n    assert "from post_person_mention mention" in source\n    assert "await asyncio.to_thread(client.project, request)" in source\n'''
    if addition not in source:
        if anchor not in source:
            raise RuntimeError("project-history loader test anchor drifted")
        source = source.rstrip() + addition + "\n"
    MODULE.write(path, source)


MODULE.patch_client = patch_client
MODULE.patch_backend_adapter = patch_backend_adapter
MODULE.patch_tests = patch_tests
MODULE.main()
