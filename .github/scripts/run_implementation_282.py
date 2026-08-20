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
ORIGINAL_PATCH_COMPONENT = MODULE.patch_component


def patch_client() -> None:
    """Validate TEPP event codes while preserving explicit provenance paths."""
    path = "lineageweave/tepp_project_history.py"
    source = MODULE.read(path)
    if "import re\n" not in source:
        source = MODULE.replace_once(
            source,
            "from dataclasses import dataclass\n",
            "import re\n\nfrom dataclasses import dataclass\n",
            label="client regex import",
        )
    anchor = "_MAX_IDENTITY_TEXT = 256\n"
    pattern = "_CODE_PATTERN = re.compile(r\"^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$\")\n"
    if pattern not in source:
        source = MODULE.replace_once(
            source,
            anchor,
            anchor + pattern,
            label="client code pattern",
        )
    helper_anchor = "def _parse_utc_timestamp(value: Any, *, name: str) -> datetime:\n"
    helpers = '''def _require_code(value: Any, *, name: str, maximum: int = 128) -> str:\n    """Return one closed lower-snake-case code."""\n    code = _require_text(value, name=name, maximum=maximum)\n    if _CODE_PATTERN.fullmatch(code) is None:\n        raise TeppProjectHistoryUnavailable(f"{name} must be lower snake_case")\n    return code\n\n\ndef _require_availability_basis(value: Any) -> str:\n    """Accept only LineageWeave's persisted source-post availability clock."""\n    basis = _require_text(value, name="availability_basis", maximum=128)\n    if basis != "source_post.created_at":\n        raise TeppProjectHistoryUnavailable("unsupported availability_basis")\n    return basis\n\n\n'''
    if helpers not in source:
        source = MODULE.replace_once(
            source,
            helper_anchor,
            helpers + helper_anchor,
            label="client code and availability validators",
        )
    source = source.replace(
        '''"event_type_code": _require_text(\n                self.event_type_code, name="event_type_code", maximum=96\n            ),''',
        '''"event_type_code": _require_code(\n                self.event_type_code, name="event_type_code", maximum=96\n            ),''',
    )
    source = source.replace(
        '''"availability_basis": _require_text(\n                self.availability_basis, name="availability_basis", maximum=128\n            ),''',
        '''"availability_basis": _require_availability_basis(self.availability_basis),''',
    )
    source = source.replace(
        '''event_type_code=_require_text(\n                payload.get("event_type_code"), name="event_type_code", maximum=96\n            ),''',
        '''event_type_code=_require_code(\n                payload.get("event_type_code"), name="event_type_code", maximum=96\n            ),''',
    )
    source = source.replace(
        '''availability_basis=_require_text(\n                payload.get("availability_basis"), name="availability_basis", maximum=128\n            ),''',
        '''availability_basis=_require_availability_basis(\n                payload.get("availability_basis")\n            ),''',
    )
    MODULE.write(path, source)


def patch_backend_adapter() -> None:
    """Load bounded exact-project evidence, explicit actors, and call TEPP off-loop."""
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

    start, end, _ = MODULE.function_region(
        source,
        "async def _load_project_rows(",
        next_markers=("\n\nasync def project_history_for_post_ids(",),
    )
    replacement = '''async def _load_project_rows(\n    conn: asyncpg.Connection,\n    *,\n    focus_post_id: str,\n    source_post_ids: Sequence[str],\n    corporate_entity_ids: Iterable[str],\n    knowledge_cutoff: datetime,\n) -> list[Mapping[str, Any]]:\n    """Load at most 128 eligible, authorized rows for one exact project.\n\n    Source/citation IDs are prioritization hints, not the retrieval boundary.\n    The focus and cited evidence remain inside the bounded set while earlier\n    authorized project events are also available to the Buyer timeline.\n    """\n    authorized_entities = [str(value) for value in corporate_entity_ids]\n    preferred_ids = list(\n        dict.fromkeys([focus_post_id, *(str(value) for value in source_post_ids)])\n    )\n    focus = await conn.fetchrow(\n        f"""\n        select post.post_id, post.source_project_code, post.source_project_name\n          from source_post post\n         where post.post_id = $1::uuid\n           and post.created_at <= $3\n           and {SOURCE_POST_ELIGIBILITY_SQL.format(alias='post')}\n           and (\n               post.visibility_code = 'public'\n               or post.corporate_entity_id::text = any($2::text[])\n           )\n        """,\n        focus_post_id,\n        authorized_entities,\n        knowledge_cutoff,\n    )\n    if focus is None or not str(focus["source_project_code"] or "").strip():\n        return []\n    project_key = str(focus["source_project_code"]).strip()\n    rows = await conn.fetch(\n        f"""\n        with bounded_project_history as (\n            select post.post_id,\n                   post.post_title,\n                   post.source_stage_code,\n                   post.voc_type_code,\n                   post.source_project_code,\n                   post.source_project_name,\n                   btrim(left(source_post_search_text(post.post_body), 2000)) as post_body_excerpt,\n                   post.created_at,\n                   array(\n                       select actor.actor_id\n                         from (\n                             select 'user_account:' || post.author_account_id::text as actor_id\n                             union\n                             select 'cataloged_person:' || mention.person_id::text as actor_id\n                               from post_person_mention mention\n                              where mention.post_id = post.post_id\n                             union\n                             select 'cataloged_person:' || summary_mention.person_id::text as actor_id\n                               from post_summary_person_mention summary_mention\n                              where summary_mention.post_id = post.post_id\n                         ) actor\n                        where actor.actor_id is not null\n                          and btrim(actor.actor_id) <> ''\n                        order by actor.actor_id\n                   ) as actor_ids\n              from source_post post\n             where post.source_project_code = $1\n               and post.created_at <= $2\n               and {SOURCE_POST_ELIGIBILITY_SQL.format(alias='post')}\n               and (\n                   post.visibility_code = 'public'\n                   or post.corporate_entity_id::text = any($3::text[])\n               )\n             order by case when post.post_id = $4::uuid then 0 else 1 end,\n                      case when array_position($5::uuid[], post.post_id) is not null then 0 else 1 end,\n                      post.created_at desc,\n                      post.post_id desc\n             limit 128\n        )\n        select *\n          from bounded_project_history\n         order by created_at, post_id\n        """,\n        project_key,\n        knowledge_cutoff,\n        authorized_entities,\n        focus_post_id,\n        preferred_ids,\n    )\n    return [dict(row) for row in rows]\n'''
    source = source[:start] + replacement + source[end:]
    source = MODULE.replace_once(
        source,
        "        projection = client.project(request)\n",
        "        projection = await asyncio.to_thread(client.project, request)\n",
        label="adapter off-loop TEPP call",
    )
    MODULE.write(path, source)


def patch_tests() -> None:
    """Add clock, provenance, handoff, authorization, and async-boundary regressions."""
    client_path = "tests/test_tepp_project_history.py"
    source = MODULE.read(client_path)
    anchor = "def test_project_history_request_rejects_future_or_non_utc_cutoffs() -> None:\n"
    added = '''def test_project_history_request_allows_known_future_event_but_rejects_bad_basis() -> None:\n    request = _request()\n    future_event = ProjectHistoryEvent(\n        **{\n            **request.events[0].__dict__,\n            "event_time": "2026-08-21T00:00:00Z",\n            "available_at": "2026-08-18T00:00:00Z",\n        }\n    )\n    accepted = ProjectHistoryRequest(\n        **{**request.__dict__, "events": (future_event, request.events[1])}\n    )\n    wire = accepted.to_wire(now=datetime(2026, 8, 20, tzinfo=timezone.utc))\n    assert wire["events"][0]["event_time"] == "2026-08-21T00:00:00Z"\n\n    invalid_event = ProjectHistoryEvent(\n        **{**request.events[0].__dict__, "availability_basis": "source.post.created_at"}\n    )\n    invalid = ProjectHistoryRequest(\n        **{**request.__dict__, "events": (invalid_event, request.events[1])}\n    )\n    with pytest.raises(TeppProjectHistoryUnavailable):\n        invalid.to_wire(now=datetime(2026, 8, 20, tzinfo=timezone.utc))\n\n\n'''
    if added not in source:
        source = MODULE.replace_once(
            source,
            anchor,
            added + anchor,
            label="client future-event and provenance test",
        )
    MODULE.write(client_path, source)

    path = "tests/test_tepp_project_history_ingestion.py"
    source = MODULE.read(path)
    handoff = '''            _row(\n                "post-handoff",\n                "Operational handoff",\n                "handoff",\n                "2024-01-01T00:00:00Z",\n                actor_ids=("actor-operations",),\n            ),\n'''
    voc_anchor = '''            _row(\n                "post-voc",\n                "VOC received",\n'''
    if handoff not in source:
        source = MODULE.replace_once(
            source,
            voc_anchor,
            handoff + voc_anchor,
            label="ingestion handoff fixture",
        )
    source = source.replace(
        '''        "specification_changed",\n        "voc_received",\n''',
        '''        "specification_changed",\n        "operational_handoff",\n        "voc_received",\n''',
    )
    source = source.replace(
        '''        "post-spec",\n        "post-voc",\n''',
        '''        "post-spec",\n        "post-handoff",\n        "post-voc",\n''',
    )
    source = source.replace(
        "    async def fetchrow(self, _query: str, _post_id: str) -> dict[str, str]:\n",
        "    async def fetchrow(self, _query: str, *_arguments: Any) -> dict[str, str]:\n",
    )
    source = source.replace(
        '''    assert "post.post_id = any" not in connection.query\n    assert "limit 128" in connection.query.casefold()\n    assert connection.arguments == (\n        "project-alpha",\n        "post-voc",\n        ["post-voc"],\n        cutoff,\n        ["corporate-1"],\n    )\n''',
        '''    assert "post.post_id = any" not in connection.query\n    assert "array_position($5::uuid[], post.post_id)" in connection.query\n    assert "from post_person_mention mention" in connection.query\n    assert "from post_summary_person_mention summary_mention" in connection.query\n    assert "limit 128" in connection.query.casefold()\n    assert connection.arguments == (\n        "project-alpha",\n        cutoff,\n        ["corporate-1"],\n        "post-voc",\n        ["post-voc"],\n    )\n''',
    )
    loader_assertion = '''\n\ndef test_project_history_loader_runs_tepp_off_the_async_event_loop() -> None:\n    source = Path("backend/app/tepp_project_history.py").read_text(encoding="utf-8")\n    assert "SOURCE_POST_ELIGIBILITY_SQL" in source\n    assert "await asyncio.to_thread(client.project, request)" in source\n'''
    if loader_assertion not in source:
        source = source.rstrip() + loader_assertion + "\n"
    MODULE.write(path, source)


def patch_component() -> None:
    """Render TEPP's canonical operational-handoff event code."""
    ORIGINAL_PATCH_COMPONENT()
    path = "frontend/src/components/ProjectHistoryTimeline.tsx"
    source = MODULE.read(path).replace(
        '  handoff_recorded: "Handoff recorded",',
        '  operational_handoff: "Handoff recorded",',
    )
    MODULE.write(path, source)


MODULE.patch_client = patch_client
MODULE.patch_backend_adapter = patch_backend_adapter
MODULE.patch_tests = patch_tests
MODULE.patch_component = patch_component
MODULE.main()
