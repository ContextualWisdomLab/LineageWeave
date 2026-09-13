"""Apply bounded Customer Master hint-resolution review repairs."""

from pathlib import Path


def replace_once(path: str, old: str, new: str) -> None:
    target = Path(path)
    text = target.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{path}: expected one anchor, found {count}: {old[:80]!r}")
    target.write_text(text.replace(old, new, 1), encoding="utf-8")


replace_once(
    "backend/app/main.py",
    "from typing import Any, Literal\n",
    "from typing import Annotated, Any, Literal\n",
)
replace_once(
    "backend/app/main.py",
    "from pydantic import BaseModel\n",
    "from pydantic import BaseModel, StringConstraints\n",
)
replace_once(
    "backend/app/main.py",
    '''class CustomerHintResolveRequest(BaseModel):\n    """Body of a POST /api/customer-master/resolve-hint request."""\n\n    hint_code: str\n''',
    '''class CustomerHintResolveRequest(BaseModel):\n    """Body of a POST /api/customer-master/resolve-hint request."""\n\n    hint_code: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]\n''',
)
replace_once(
    "backend/app/main.py",
    '''                       resolution.verification_status_code,\n                       resolution.verification_evidence_url\n                  from source_post\n''',
    '''                       resolution.verification_status_code,\n                       resolution.verification_evidence_url,\n                       resolution.resolved_at\n                  from source_post\n''',
)
replace_once(
    "backend/app/main.py",
    '''                  left join source_post_customer_resolution resolution\n                    on resolution.post_id = source_post.post_id\n                   and resolution.source_customer_code = btrim(source_post.source_customer_code)\n''',
    '''                  left join source_post_customer_resolution resolution\n                    on resolution.post_id = source_post.post_id\n                   and resolution.source_customer_code = source_post.source_customer_code\n''',
)
replace_once(
    "backend/app/main.py",
    '''                       row_number() over (\n                           partition by customer_code, customer_name_group\n                           order by created_at desc, post_id desc\n                       ) as related_rank\n                  from scoped\n            ), groups as (\n''',
    '''                       row_number() over (\n                           partition by customer_code, customer_name_group\n                           order by created_at desc, post_id desc\n                       ) as related_rank,\n                       row_number() over (\n                           partition by customer_code, customer_name_group\n                           order by resolved_at desc nulls last, post_id desc\n                       ) as resolution_rank\n                  from scoped\n            ), groups as (\n''',
)
replace_once(
    "backend/app/main.py",
    '''                       count(distinct resolved_corporate_entity_id) as resolution_entity_count,\n                       max(resolved_corporate_entity_id) as resolved_corporate_entity_id,\n                       max(resolved_entity_name) as resolved_entity_name,\n                       max(verification_status_code) as verification_status_code,\n                       max(verification_evidence_url) as verification_evidence_url\n''',
    '''                       count(distinct resolved_corporate_entity_id) as resolution_entity_count,\n                       max(resolved_corporate_entity_id) filter (where resolution_rank = 1)\n                           as resolved_corporate_entity_id,\n                       max(resolved_entity_name) filter (where resolution_rank = 1)\n                           as resolved_entity_name,\n                       max(verification_status_code) filter (where resolution_rank = 1)\n                           as verification_status_code,\n                       max(verification_evidence_url) filter (where resolution_rank = 1)\n                           as verification_evidence_url\n''',
)

replace_once(
    "backend/app/customer_hint_ingestion.py",
    '''    if not resolution_client.available:\n        return None\n\n    async with pool.acquire() as database_connection:\n''',
    '''    if not resolution_client.available:\n        return None\n\n    normalized_hint_code = hint_code.strip()\n    if not normalized_hint_code:\n        return None\n\n    async with pool.acquire() as database_connection:\n''',
)
replace_once(
    "backend/app/customer_hint_ingestion.py",
    '''            process_unit_ids,\n            hint_code,\n        )\n''',
    '''            process_unit_ids,\n            normalized_hint_code,\n        )\n''',
)
replace_once(
    "backend/app/customer_hint_ingestion.py",
    '''        resolve_and_verify_organization_name,\n        hint_code,\n        excerpts,\n''',
    '''        resolve_and_verify_organization_name,\n        normalized_hint_code,\n        excerpts,\n''',
)
replace_once(
    "backend/app/customer_hint_ingestion.py",
    '''                process_unit_ids,\n                hint_code,\n                captured_post_ids,\n''',
    '''                process_unit_ids,\n                normalized_hint_code,\n                captured_post_ids,\n''',
)
replace_once(
    "backend/app/customer_hint_ingestion.py",
    '''                select source_post_id::uuid, $2, $3::uuid, $4, $5, $6, now()\n                  from unnest($1::text[]) as captured(source_post_id)\n''',
    '''                select source_post.post_id, source_post.source_customer_code,\n                       $2::uuid, $3, $4, $5, now()\n                  from unnest($1::text[]) as captured(source_post_id)\n                  join source_post on source_post.post_id = captured.source_post_id::uuid\n''',
)
replace_once(
    "backend/app/customer_hint_ingestion.py",
    '''                list(captured_post_ids),\n                hint_code,\n                resolved_corporate_entity_id,\n                entity_name,\n                verified_customer_resolution.verification_status_code,\n                verified_customer_resolution.verification_evidence_url,\n''',
    '''                list(captured_post_ids),\n                resolved_corporate_entity_id,\n                entity_name,\n                verified_customer_resolution.verification_status_code,\n                verified_customer_resolution.verification_evidence_url,\n''',
)

post_eligibility = Path("backend/app/post_eligibility.py")
post_text = post_eligibility.read_text(encoding="utf-8")
old_predicate = "         where source_customer_code = $3\n"
if post_text.count(old_predicate) != 1:
    raise SystemExit(
        "backend/app/post_eligibility.py: expected one capture hint predicate, "
        f"found {post_text.count(old_predicate)}"
    )
post_text = post_text.replace(
    old_predicate,
    "         where btrim(source_customer_code) = $3\n",
    1,
)
old_lock_predicate = "           and source_customer_code = $3\n"
if post_text.count(old_lock_predicate) != 1:
    raise SystemExit(
        "backend/app/post_eligibility.py: expected one lock hint predicate, "
        f"found {post_text.count(old_lock_predicate)}"
    )
post_text = post_text.replace(
    old_lock_predicate,
    "           and btrim(source_customer_code) = $3\n",
    1,
)
post_eligibility.write_text(post_text, encoding="utf-8")

replace_once(
    "tests/test_customer_hint_ingestion.py",
    '''class _UnavailableClient:\n    available = False\n\n\nclass _Transaction:\n''',
    '''class _UnavailableClient:\n    available = False\n\n\n_DEFAULT_CLIENT = _Client()\n\n\nclass _Transaction:\n''',
)
replace_once(
    "tests/test_customer_hint_ingestion.py",
    "def _resolve(pool, resolution_client=_Client()):\n",
    "def _resolve(pool, resolution_client=_DEFAULT_CLIENT):\n",
)

replace_once(
    "backend/tests/test_api.py",
    '''    _grant_post_admin(seeded_db["dsn"])\n    admin_conn = psycopg2.connect(seeded_db["dsn"])\n''',
    '''    _grant_post_admin(seeded_db["dsn"])\n    blank_response = client.post(\n        "/api/customer-master/resolve-hint",\n        json={"hint_code": "   "},\n        headers={"Authorization": f"Bearer {demo_analyst_token}"},\n    )\n    assert blank_response.status_code == 422, blank_response.text\n\n    admin_conn = psycopg2.connect(seeded_db["dsn"])\n''',
)
replace_once(
    "backend/tests/test_api.py",
    '''                    "HINT-CODE-001",\n                    seeded_db["own_private_post_id"],\n''',
    '''                    "  HINT-CODE-001  ",\n                    seeded_db["own_private_post_id"],\n''',
)
replace_once(
    "backend/tests/test_api.py",
    '''            json={"hint_code": "HINT-CODE-001"},\n''',
    '''            json={"hint_code": "  HINT-CODE-001  "},\n''',
)
replace_once(
    "backend/tests/test_api.py",
    '''                "select post_id::text, resolved_corporate_entity_id::text "\n                "from source_post_customer_resolution order by post_id"\n            )\n            associations = cur.fetchall()\n            assert associations == [\n                (seeded_db["own_private_post_id"], body["corporate_entity_id"])\n            ]\n    finally:\n''',
    '''                "select post_id::text, resolved_corporate_entity_id::text, source_customer_code "\n                "from source_post_customer_resolution order by post_id"\n            )\n            associations = cur.fetchall()\n            assert associations == [\n                (\n                    seeded_db["own_private_post_id"],\n                    body["corporate_entity_id"],\n                    "  HINT-CODE-001  ",\n                )\n            ]\n\n            cur.execute(\n                """\n                insert into source_post (\n                    author_account_id, corporate_entity_id, process_unit_id,\n                    post_title, post_body, voc_type_code, visibility_code,\n                    source_customer_code, source_customer_name\n                )\n                select author_account_id, corporate_entity_id, process_unit_id,\n                       'Older resolved hint', post_body, voc_type_code, visibility_code,\n                       source_customer_code, source_customer_name\n                  from source_post\n                 where post_id = %s\n                returning post_id::text\n                """,\n                (seeded_db["own_private_post_id"],),\n            )\n            older_post_id = cur.fetchone()[0]\n            cur.execute(\n                """\n                insert into source_post_customer_resolution (\n                    post_id, source_customer_code, resolved_corporate_entity_id,\n                    resolved_entity_name, verification_status_code,\n                    verification_evidence_url, resolved_at\n                )\n                values (%s, %s, %s, 'Stale Name', %s,\n                        'https://example.test/stale', now() - interval '1 day')\n                """,\n                (\n                    older_post_id,\n                    "  HINT-CODE-001  ",\n                    body["corporate_entity_id"],\n                    STATUS_CORROBORATED,\n                ),\n            )\n        admin_conn.commit()\n\n        customer_master_response = client.get(\n            "/api/customer-master",\n            headers={"Authorization": f"Bearer {demo_analyst_token}"},\n        )\n        assert customer_master_response.status_code == 200, customer_master_response.text\n        hint = next(\n            item\n            for item in customer_master_response.json()["source_customer_hints"]\n            if item["customer_code"] == "HINT-CODE-001"\n        )\n        assert hint["resolved_corporate_entity_id"] == body["corporate_entity_id"]\n        assert hint["resolved_entity_name"] == "Northridge Grid"\n        assert hint["resolution_status"] == STATUS_CORROBORATED\n        assert hint["verification_evidence_url"] == "https://example.test/northridge-grid"\n    finally:\n''',
)

replace_once(
    "tests/test_customer_hint_resolution_postgresql.py",
    '''        hint_code = "SYNTH-CUSTOMER-001"\n        posts: dict[str, str] = {}\n''',
    '''        hint_code = "SYNTH-CUSTOMER-001"\n        stored_hint_code = f"  {hint_code}  "\n        posts: dict[str, str] = {}\n''',
)
replace_once(
    "tests/test_customer_hint_resolution_postgresql.py",
    '''                    hint_code,\n                ),\n''',
    '''                    stored_hint_code,\n                ),\n''',
)
replace_once(
    "tests/test_customer_hint_resolution_postgresql.py",
    '''        "hint_code": hint_code,\n    }\n''',
    '''        "hint_code": hint_code,\n        "stored_hint_code": stored_hint_code,\n    }\n''',
)
replace_once(
    "tests/test_customer_hint_resolution_postgresql.py",
    '''            select post_id::text, resolved_corporate_entity_id::text\n              from source_post_customer_resolution\n             order by post_id\n''',
    '''            select post_id::text, resolved_corporate_entity_id::text, source_customer_code\n              from source_post_customer_resolution\n             order by post_id\n''',
)
replace_once(
    "tests/test_customer_hint_resolution_postgresql.py",
    '''    assert associations == [(seeded["post_a"], seeded["resolved_id"])]\n''',
    '''    assert associations == [\n        (seeded["post_a"], seeded["resolved_id"], seeded["stored_hint_code"])\n    ]\n''',
)
