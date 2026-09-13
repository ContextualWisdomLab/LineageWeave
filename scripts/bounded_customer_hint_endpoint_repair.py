"""Temporary bounded patch for the Customer Master hint endpoint."""

from pathlib import Path

path = Path("backend/app/main.py")
text = path.read_text(encoding="utf-8")
start_marker = '@app.post("/api/customer-master/resolve-hint")\n'
end_marker = '\n\n@app.get("/api/lineage")\n'
if text.count(start_marker) != 1:
    raise SystemExit(f"expected one endpoint start marker, found {text.count(start_marker)}")
start = text.index(start_marker)
end = text.index(end_marker, start)
replacement = '''@app.post("/api/customer-master/resolve-hint")
async def resolve_customer_master_hint(
    request: CustomerHintResolveRequest,
    account: CurrentAccount = Depends(get_current_account),
    pool: asyncpg.Pool = Depends(get_pool),
) -> dict[str, Any]:
    """Corroborate one visible customer hint without changing source ownership.

    ``post_admin`` admits the write action, while the authenticated
    corporate/process scope bounds every source post used as model evidence.
    Customer identity is persisted separately from tenant authorization
    ownership (ADR 0042 / Proposed ADR 0374).
    """
    _require_post_admin(account)
    try:
        resolution = await resolve_customer_hint(
            pool,
            _customer_hint_resolution_client(),
            _relation_verification_client(),
            request.hint_code,
            list(account.corporate_entity_ids),
            list(account.process_unit_ids),
        )
    except (HttpClientError, OSError) as exc:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Hint resolution is unavailable: the orchestrator or search provider did not respond",
        ) from exc
    except Exception as exc:  # noqa: BLE001 - provider boundary is fail-closed.
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Hint resolution is unavailable: the orchestrator or search provider did not respond",
        ) from exc
    if resolution is None:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "this hint could not be resolved to a corroborated organization name",
        )
    return resolution
'''
path.write_text(text[:start] + replacement.rstrip() + text[end:], encoding="utf-8")
