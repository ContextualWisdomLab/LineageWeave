"""Opaque source-cursor integrity, scope, and snapshot regressions."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from lineageweave.knowledge_graph import EDGE_MENTION, NODE_PERSON, NODE_POST
from lineageweave.ontology_neighborhood import OntologyNeighborhoodError
from lineageweave.ontology_source_cursor import (
    OntologySourceKey,
    SOURCE_CURSOR_PREFIX,
    mint_source_cursor,
    source_cursor_secret_from_env,
    verify_source_cursor,
)

SECRET = b"ontology-source-cursor-secret-32b"
ACCOUNT = "account-aaaaaaaa-aaaa-aaaa-aaaa-01"
POST_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa1"
PERSON_ID = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbb1"
T0 = datetime(2026, 1, 10, 12, 0, tzinfo=timezone.utc)
SNAPSHOT = datetime(2026, 1, 10, 12, 5, tzinfo=timezone.utc)

LAST_KEY = OntologySourceKey(
    hop_depth=0,
    edge_type_code=EDGE_MENTION,
    source_node_type_code=NODE_PERSON,
    source_node_id=PERSON_ID,
    target_node_type_code=NODE_POST,
    target_node_id=POST_ID,
)


def _mint(**overrides: object) -> str:
    values: dict[str, object] = {
        "secret": SECRET,
        "user_account_id": ACCOUNT,
        "focus_node_type_code": NODE_POST,
        "focus_node_id": POST_ID,
        "knowledge_cutoff": T0,
        "maximum_depth": 2,
        "maximum_nodes": 40,
        "maximum_edges": 80,
        "allowed_property_codes": None,
        "last_key": LAST_KEY,
        "snapshot_at": SNAPSHOT,
        "visible_post_ids": [POST_ID],
        "now": SNAPSHOT,
    }
    values.update(overrides)
    return mint_source_cursor(**values)  # type: ignore[arg-type]


def _verify(token: str, **overrides: object) -> object:
    values: dict[str, object] = {
        "secret": SECRET,
        "user_account_id": ACCOUNT,
        "focus_node_type_code": NODE_POST,
        "focus_node_id": POST_ID,
        "knowledge_cutoff": T0,
        "maximum_depth": 2,
        "maximum_nodes": 40,
        "maximum_edges": 80,
        "allowed_property_codes": None,
        "visible_post_ids": [POST_ID],
        "now": SNAPSHOT,
    }
    values.update(overrides)
    return verify_source_cursor(token, **values)  # type: ignore[arg-type]


def test_missing_or_short_secret_keeps_source_cursor_closed() -> None:
    assert source_cursor_secret_from_env("") is None
    assert source_cursor_secret_from_env("short") is None
    assert source_cursor_secret_from_env(SECRET.decode()) == SECRET


def test_round_trip_hides_sql_keys_and_account_ids() -> None:
    token = _mint()
    assert token.startswith(SOURCE_CURSOR_PREFIX)
    assert ACCOUNT not in token
    assert PERSON_ID not in token
    assert EDGE_MENTION not in token
    assert "after:" not in token
    claims = _verify(token)
    assert claims.last_key == LAST_KEY
    assert claims.snapshot_at == SNAPSHOT


def test_tampered_token_fails_closed() -> None:
    token = _mint()
    mutated = token[:-2] + ("A" if token[-2] != "A" else "B") + token[-1]
    with pytest.raises(OntologyNeighborhoodError) as raised:
        _verify(mutated)
    assert raised.value.code == "malformed_cursor"


def test_scope_focus_cutoff_bounds_and_version_fail_closed() -> None:
    token = _mint()
    with pytest.raises(OntologyNeighborhoodError) as scope:
        _verify(token, user_account_id="other-account-bbbbbbbb-02")
    assert scope.value.code == "malformed_cursor"
    with pytest.raises(OntologyNeighborhoodError) as focus:
        _verify(token, focus_node_id="cccccccc-cccc-cccc-cccc-ccccccccccc1")
    assert focus.value.code == "malformed_cursor"
    with pytest.raises(OntologyNeighborhoodError) as cutoff:
        _verify(token, knowledge_cutoff=None)
    assert cutoff.value.code == "malformed_cursor"
    with pytest.raises(OntologyNeighborhoodError) as bounds:
        _verify(token, maximum_edges=10)
    assert bounds.value.code == "malformed_cursor"


def test_changed_visible_posts_fail_as_stale_snapshot() -> None:
    token = _mint()
    with pytest.raises(OntologyNeighborhoodError) as raised:
        _verify(token, visible_post_ids=[POST_ID, "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa2"])
    assert raised.value.code == "stale_snapshot"


def test_cursor_claims_can_be_authenticated_before_eligibility_reconstruction() -> None:
    """Continuation can recover its sealed snapshot before rebuilding its post set."""
    token = _mint()
    claims = _verify(token, visible_post_ids=[], validate_eligibility=False)
    assert claims.snapshot_at == SNAPSHOT
    assert claims.last_key == LAST_KEY


def test_expired_cursor_fails_closed() -> None:
    token = _mint(now=SNAPSHOT)
    with pytest.raises(OntologyNeighborhoodError) as raised:
        _verify(token, now=SNAPSHOT + timedelta(minutes=16))
    assert raised.value.code == "malformed_cursor"


def test_unknown_prefix_fails_closed() -> None:
    with pytest.raises(OntologyNeighborhoodError) as raised:
        _verify("after:mentions:post-person")
    assert raised.value.code == "malformed_cursor"


def test_v1_custom_cursor_format_is_rejected_after_aead_upgrade() -> None:
    legacy_token = _mint().replace("src.v2.", "src.v1.", 1)
    with pytest.raises(OntologyNeighborhoodError) as raised:
        _verify(legacy_token)
    assert raised.value.code == "malformed_cursor"
