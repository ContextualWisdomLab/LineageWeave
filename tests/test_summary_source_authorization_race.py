"""Synthetic actual-ASGI-route summary authorization races (no services)."""

import asyncio
import copy
from types import SimpleNamespace

import httpx
import pytest

from backend.app import main, post_summary_ingestion as ingestion
from backend.app.auth import CurrentAccount
from backend.app.post_eligibility import SOURCE_POST_ELIGIBILITY_SQL, source_post_scope_sql
from lineageweave.post_summary import POST_SUMMARY_CONTRACT_VERSION, PostSummary

POST_ID = "00000000-0000-0000-0000-000000000375"
ACCOUNT = CurrentAccount(
    user_account_id="synthetic-reader", external_subject_id="synthetic-subject",
    display_name="Synthetic Reader", preferred_locale="en",
    corporate_entity_ids=frozenset({"synthetic-corp"}),
    process_unit_ids=frozenset({"synthetic-pu"}),
    permission_codes=frozenset({"post_read"}),
)


class _Connection:
    """Query-aware synthetic storage; production route and serializer stay real."""

    def __init__(self, pool):
        self.pool = pool
        self.depth = 0

    def transaction(self):
        conn = self

        class Transaction:
            async def __aenter__(self):
                conn.depth += 1

            async def __aexit__(self, *_exc):
                conn.depth -= 1
        return Transaction()

    async def fetchrow(self, sql, *args):
        self.pool.queries.append((sql, args))
        if "from source_post" in sql:
            if source_post_scope_sql("source_post") in sql:
                assert args == (["synthetic-corp"], ["synthetic-pu"], POST_ID)
                assert "".join(SOURCE_POST_ELIGIBILITY_SQL.format(alias="source_post").split()) in "".join(sql.split())
                assert self.depth > 0 and "for share" in sql.lower()
                row = self.pool.source
                if row["corporate_entity_id"] != "synthetic-corp" or row["source_draft_code"] or row["source_deleted_flag"]:
                    return None
            return copy.deepcopy(self.pool.source)
        if "from post_summary_result" in sql:
            return copy.deepcopy(self.pool.header)
        raise AssertionError(f"Unexpected synthetic query: {sql}")

    async def fetch(self, sql, *_args):
        self.pool.queries.append((sql, _args))
        return []

    async def execute(self, sql, *args):
        assert self.depth > 0
        self.pool.writes.append((sql, args))
        if "insert into post_summary_result" in sql:
            self.pool.header = {"korean_summary": args[1], "summary_contract_version": args[2]}
        return "OK"


class _Pool:
    """Commit drift precisely after the first source capture lease releases."""

    def __init__(self, branch="stored", drift=None):
        self.source = dict(
            post_id=POST_ID, post_title="Synthetic authorized title",
            post_body="Synthetic authorized body", source_content_digest="synthetic-digest-a",
            visibility_code="private", corporate_entity_id="synthetic-corp",
            process_unit_id="synthetic-pu", author_account_id="synthetic-author",
            source_draft_code=None, source_deleted_flag=None,
            source_customer_code="SYNTHETIC-HINT", corporate_entity_code="SYNTHETIC",
        )
        self.header = None if branch == "generated" else {
            "korean_summary": "Synthetic stored evidence",
            "summary_contract_version": POST_SUMMARY_CONTRACT_VERSION - (branch == "stale"),
        }
        self.drift = drift
        self.leases = 0
        self.releases = 0
        self.queries = []
        self.writes = []
        self.published = []
        self.conn = _Connection(self)

    def acquire(self):
        pool = self

        class Acquire:
            async def __aenter__(self):
                pool.leases += 1
                return pool.conn

            async def __aexit__(self, *_exc):
                pool.leases -= 1
                pool.releases += 1
                if pool.releases == 1 and pool.drift:
                    pool.source.update(pool.drift)
        return Acquire()


async def _request(monkeypatch, pool, *, available=False, inspect_external=False, failure=None, summarize_hook=None):
    """Use actual FastAPI dispatch with synthetic storage and inference only."""
    class Client:
        def __init__(self):
            self.available = available

        def summarize(self, title, body):
            if inspect_external:
                assert pool.leases == 0 and pool.conn.depth == 0
            assert title == "Synthetic authorized title"
            assert body == "Synthetic authorized body"
            if summarize_hook is not None:
                summarize_hook()
            if failure is not None:
                raise failure
            return PostSummary(korean_summary="Synthetic generated evidence")

    def normalize(body):
        if inspect_external:
            assert pool.leases == 0 and pool.conn.depth == 0
        return SimpleNamespace(text=body)

    async def hints(*_args):
        return "Synthetic lookup hints"

    async def edges(conn, _post_id):
        assert conn.depth > 0
        return []

    async def complete(*_args, **_kwargs):
        return False

    async def job(conn, post_id, body, **_kwargs):
        assert conn.depth > 0
        assert body == "Synthetic authorized body"
        return SimpleNamespace(should_publish=True, post_id=post_id, source_body_sha256="synthetic-job-digest")

    async def publish(_valkey, **kwargs):
        assert pool.leases == 0 and pool.conn.depth == 0
        pool.published.append(kwargs)

    monkeypatch.setattr(main, "_post_summary_client", Client)
    monkeypatch.setattr(main, "normalize_post_body", normalize)
    monkeypatch.setattr(main, "_load_post_semantic_hints", hints)
    monkeypatch.setattr(ingestion, "persist_edges_for_post", edges)
    monkeypatch.setattr(main, "post_content_is_complete", complete)
    monkeypatch.setattr(main, "ensure_post_content_job", job)
    monkeypatch.setattr(main, "publish_post_content_event", publish)
    overrides = dict(main.app.dependency_overrides)
    main.app.dependency_overrides.update({
        main.get_current_account: lambda: ACCOUNT,
        main.get_pool: lambda: pool,
        main.get_valkey: lambda: object(),
    })
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=main.app), base_url="http://synthetic.test") as client:
            return await client.get(f"/api/posts/{POST_ID}/summary")
    finally:
        main.app.dependency_overrides.clear()
        main.app.dependency_overrides.update(overrides)


def test_initial_foreign_summary_preserves_forbidden_contract(monkeypatch):
    """Initial foreign ownership keeps 403 without reading or generating a body."""
    pool = _Pool()
    pool.source["corporate_entity_id"] = "synthetic-foreign"
    response = asyncio.run(_request(monkeypatch, pool))
    assert response.status_code == 403, response.text
    assert not pool.writes and not pool.published


@pytest.mark.parametrize("revoke", [False, True])
def test_current_stored_summary_reauthorizes_after_capture(monkeypatch, revoke):
    """Stored positives remain readable; committed revocation denies disclosure."""
    pool = _Pool(drift={"corporate_entity_id": "synthetic-foreign"} if revoke else None)
    response = asyncio.run(_request(monkeypatch, pool))
    assert response.status_code == (409 if revoke else 200), response.text
    if not revoke:
        assert response.json()["korean_summary"] == "Synthetic stored evidence"
        assert response.json()["summary_status"] == "current"
    assert not pool.writes and not pool.published


@pytest.mark.parametrize("revoke", [False, True])
def test_stale_fallback_reauthorizes_after_capture(monkeypatch, revoke):
    """Stale continuity keeps its label but cannot bypass committed revocation."""
    pool = _Pool("stale", {"corporate_entity_id": "synthetic-foreign"} if revoke else None)
    response = asyncio.run(_request(monkeypatch, pool))
    assert response.status_code == (409 if revoke else 200), response.text
    if not revoke:
        assert response.json()["summary_status"] == "stale"
    assert not pool.writes and not pool.published


@pytest.mark.parametrize("revoke", [False, True])
def test_generated_summary_reauthorizes_before_projection(monkeypatch, revoke):
    """Generation uses captured authorized text; drift denies all post-owned writes."""
    pool = _Pool("generated", {"corporate_entity_id": "synthetic-foreign"} if revoke else None)
    response = asyncio.run(_request(monkeypatch, pool, available=True))
    assert response.status_code == (409 if revoke else 200), response.text
    if revoke:
        assert not pool.writes and not pool.published
    else:
        assert response.json()["korean_summary"] == "Synthetic generated evidence"
        assert pool.writes and len(pool.published) == 1


def test_summary_external_work_releases_database_lease(monkeypatch):
    """Neither normalization nor summary inference reserves a DB connection."""
    pool = _Pool("generated")
    response = asyncio.run(_request(monkeypatch, pool, available=True, inspect_external=True))
    assert response.status_code == 200, response.text


@pytest.mark.parametrize("branch", ["stored", "stale", "generated"])
@pytest.mark.parametrize("drift", [
    {"post_title": "Synthetic rewritten title"},
    {"post_body": "Synthetic rewritten body", "source_content_digest": "synthetic-digest-b"},
    {"process_unit_id": "synthetic-other-pu"},
    {"author_account_id": "synthetic-other-author"},
    {"visibility_code": "public"},
    {"source_draft_code": "DRAFT"},
    {"source_deleted_flag": "DELETED"},
    {"source_content_digest": "synthetic-digest-long-tail"},
])
def test_all_summary_branches_reject_identity_content_or_eligibility_drift(monkeypatch, branch, drift):
    """Content, provenance and eligibility drift all deny before post-owned writes."""
    pool = _Pool(branch, drift)
    response = asyncio.run(_request(monkeypatch, pool, available=branch == "generated"))
    assert response.status_code == 409, response.text
    assert not pool.writes and not pool.published


@pytest.mark.parametrize("revoke", [False, True])
@pytest.mark.parametrize("failure", [OSError("Synthetic provider failure"), RuntimeError("Synthetic incomplete response")])
def test_failed_refresh_stale_continuity_reauthorizes(monkeypatch, revoke, failure):
    """Provider failures retain labeled stale evidence only for unchanged sources."""
    pool = _Pool("stale")
    def during_inference():
        if revoke:
            pool.source["corporate_entity_id"] = "synthetic-foreign"
    response = asyncio.run(_request(
        monkeypatch, pool, available=True, failure=failure,
        summarize_hook=during_inference, inspect_external=True,
    ))
    assert response.status_code == (409 if revoke else 200), response.text
    if not revoke:
        assert response.json()["summary_status"] == "stale"
    assert not pool.writes and not pool.published


@pytest.mark.parametrize("branch", ["generated", "stale"])
def test_revocation_during_successful_refresh_cannot_fallback_or_write(monkeypatch, branch):
    """Final authorization conflicts bypass stale success and prevent projection writes."""
    pool = _Pool(branch)
    def during_inference():
        pool.source["corporate_entity_id"] = "synthetic-foreign"
    response = asyncio.run(_request(
        monkeypatch, pool, available=True, summarize_hook=during_inference,
        inspect_external=True,
    ))
    assert response.status_code == 409, response.text
    assert not pool.writes and not pool.published


@pytest.mark.parametrize("grant_admin", [False, True])
def test_route_preparation_retains_explicit_catalog_capability(monkeypatch, grant_admin):
    """The new route preparation boundary retains reader Null/admin clients."""
    captured = {}
    hierarchy = SimpleNamespace(available=True)
    verification = SimpleNamespace(available=True)
    async def prepare(_pool, _summary, **kwargs):
        captured.update(kwargs)
        return [], {}
    def forbidden():
        raise AssertionError("reader must not construct catalog clients")
    monkeypatch.setattr(main, "prepare_post_summary_identities_from_pool", prepare)
    monkeypatch.setattr(main, "_corporate_hierarchy_inference_client", (lambda: hierarchy) if grant_admin else forbidden)
    monkeypatch.setattr(main, "_relation_verification_client", (lambda: verification) if grant_admin else forbidden)
    account = ACCOUNT if not grant_admin else CurrentAccount(
        user_account_id=ACCOUNT.user_account_id, external_subject_id=ACCOUNT.external_subject_id,
        display_name=ACCOUNT.display_name, preferred_locale=ACCOUNT.preferred_locale,
        corporate_entity_ids=ACCOUNT.corporate_entity_ids, process_unit_ids=ACCOUNT.process_unit_ids,
        permission_codes=frozenset({"post_read", "post_admin"}),
    )
    asyncio.run(main._prepare_post_summary_for_account(
        object(), PostSummary(korean_summary="Synthetic evidence"),
        post_body="Synthetic body", account=account,
    ))
    assert captured["allow_catalog_enrichment"] is grant_admin
    assert captured["hierarchy_inference_client"].available is grant_admin
    assert captured["verification_client"].available is grant_admin


def test_canonical_organization_preparation_releases_lease_during_external_work():
    """Actual corporate resolver inference/verification precede pool-pinned creation."""
    from lineageweave.corporate_hierarchy_inference import HierarchyProposal
    from lineageweave.post_summary import ACTOR_TYPE_ORGANIZATION, RoleResponsibility
    from lineageweave.relation_verification import STATUS_CORROBORATED

    events = []
    class Connection:
        depth = 0
        def transaction(self):
            conn = self
            class Transaction:
                async def __aenter__(self):
                    assert conn.depth == 0
                    conn.depth = 1
                async def __aexit__(self, *_exc):
                    conn.depth = 0
            return Transaction()
        async def fetch(self, sql, *_args):
            assert pool.leases == 1
            if "organization_name_resolution" in sql:
                return []
            assert sql == "select corporate_entity_id, entity_name from corporate_entity"
            return []
        async def execute(self, sql, *_args):
            assert self.depth == 1 and pool.leases == 1
            assert "pg_advisory_xact_lock" in sql
            events.append("creation_lock")
        async def fetchrow(self, sql, *_args):
            assert self.depth == 1 and pool.leases == 1
            assert "insert into corporate_entity" in sql
            return {"corporate_entity_id": "synthetic-created-org"}
    class Pool:
        leases = 0
        conn = Connection()
        def acquire(self):
            owner = self
            class Acquire:
                async def __aenter__(self):
                    owner.leases += 1
                    return owner.conn
                async def __aexit__(self, *_exc):
                    owner.leases -= 1
            return Acquire()
    pool = Pool()
    class Inference:
        available = True
        def infer(self, *_args):
            assert pool.leases == 0 and pool.conn.depth == 0
            events.append("inference")
            return HierarchyProposal(level_code="company", parent_name=None)
    class Verification:
        available = True
        def verify(self, *_args):
            assert pool.leases == 0 and pool.conn.depth == 0
            events.append("verification")
            return SimpleNamespace(status_code=STATUS_CORROBORATED)
    prepared = asyncio.run(ingestion.prepare_post_summary_identities_from_pool(
        pool, PostSummary(korean_summary="Synthetic evidence", roles_and_responsibilities=(
            RoleResponsibility(actor_name="Synthetic Novel Org", responsibility="Synthetic role", actor_type_code=ACTOR_TYPE_ORGANIZATION),
        )), post_body="Synthetic captured body", allow_catalog_enrichment=True,
        hierarchy_inference_client=Inference(), verification_client=Verification(),
    ))
    assert prepared[1] == {0: "synthetic-created-org"}
    assert events == ["inference", "verification", "creation_lock"]
    assert pool.leases == 0 and pool.conn.depth == 0
