"""Authorization and response contract for governed product provisioning."""

import asyncio
from contextlib import asynccontextmanager
from uuid import UUID

import pytest

from backend.app import main
from backend.app.auth import CurrentAccount


_CORP_ID = "00000000-0000-0000-0000-000000000201"


def _account(*permissions: str, in_scope: bool = True) -> CurrentAccount:
    """Build a synthetic account with an optional organization scope."""
    return CurrentAccount(
        user_account_id="00000000-0000-0000-0000-000000000301",
        external_subject_id="synthetic-subject",
        display_name="Synthetic operator",
        preferred_locale="en",
        corporate_entity_ids=frozenset({_CORP_ID} if in_scope else set()),
        process_unit_ids=frozenset(),
        permission_codes=frozenset(permissions),
    )


class _Pool:
    """Expose one synthetic connection through the async pool shape."""

    @asynccontextmanager
    async def acquire(self):
        """Yield a connection placeholder."""
        yield object()


def _request() -> main.ProductCatalogProvisionRequest:
    return main.ProductCatalogProvisionRequest(
        preferred_label="Synthetic Model Q",
        product_level_code="product_model",
        parent_product_code="SYNTHETIC-GROUP",
        aliases=("Model Q",),
        source_corporate_entity_id=UUID(_CORP_ID),
        source_system_code="synthetic_product_master",
        source_record_key="synthetic-record-1",
    )


def test_product_catalog_endpoint_requires_admin_and_source_scope() -> None:
    """Neither a reader nor an out-of-scope admin may provision identity."""
    for account in (_account("post_read"), _account("post_admin", in_scope=False)):
        with pytest.raises(main.HTTPException) as raised:
            asyncio.run(
                main.provision_product_catalog(
                    _request(), "SYNTHETIC-MODEL-Q", account=account, pool=_Pool()
                )
            )
        assert raised.value.status_code == 403


def test_product_catalog_endpoint_returns_the_next_valid_action(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An admitted row delegates once and tells the operator what to verify."""
    observed = {}

    async def provision(conn: object, entry: object, **kwargs: object):
        observed.update(conn=conn, entry=entry, **kwargs)
        return {
            "product_catalog_id": "00000000-0000-0000-0000-000000000101",
            "source_payload_sha256": "a" * 64,
            "created": True,
        }

    monkeypatch.setattr(main, "provision_product_catalog_entry", provision)
    result = asyncio.run(
        main.provision_product_catalog(
            _request(),
            "SYNTHETIC-MODEL-Q",
            account=_account("post_admin"),
            pool=_Pool(),
        )
    )

    assert result["created"] is True
    assert result["product_catalog_code"] == "SYNTHETIC-MODEL-Q"
    assert result["ontology_iri"].endswith(
        "#node/product/00000000-0000-0000-0000-000000000101"
    )
    assert result["next_action"] == "제품 분석을 다시 실행한 뒤 원문 근거와 연결 결과를 확인하세요."
    assert observed["imported_by_account_id"].endswith("301")
