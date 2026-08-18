"""TEPP consume reads clues from the opened post. Never invents a theta."""

from lineageweave.tepp_client import AnalysisRunRequest, TeppClient
from lineageweave.tepp_consume import (
    CUSTOMER_EMPTY_NEXT_ACTION,
    TEPP_UNAVAILABLE_NEXT_ACTION,
    TIME_WINDOW_EMPTY_NEXT_ACTION,
    clues_from_opened_post,
    consume_tepp_for_clues,
    missing_clue_next_action,
    needs_tepp_consume,
)


def test_missing_time_window_fail_closes() -> None:
    clues = clues_from_opened_post(
        project_id="A-100",
        customer_id="corp-1",
        customer_name="Demo Corp",
        org_id="pu-1",
        org_name="Demo Lineage PU",
        created_at=None,
    )
    assert missing_clue_next_action(clues) == TIME_WINDOW_EMPTY_NEXT_ACTION


def test_missing_customer_fail_closes_after_time() -> None:
    clues = clues_from_opened_post(
        project_id="A-100",
        customer_id=None,
        customer_name=None,
        org_id="pu-1",
        org_name="Demo Lineage PU",
        created_at="2026-01-12T00:00:00Z",
    )
    assert missing_clue_next_action(clues) == CUSTOMER_EMPTY_NEXT_ACTION


def test_unavailable_tepp_does_not_invent_a_theta() -> None:
    clues = clues_from_opened_post(
        project_id="A-100",
        customer_id="corp-1",
        customer_name="Demo Corp",
        org_id="pu-1",
        org_name="Demo Lineage PU",
        created_at="2026-01-12",
    )
    result = consume_tepp_for_clues(TeppClient(), clues)
    assert result.consumed is False
    assert result.empty_next_action == TEPP_UNAVAILABLE_NEXT_ACTION


def test_accepted_ack_is_not_a_completed_measurement() -> None:
    clues = clues_from_opened_post(
        project_id="A-100",
        customer_id="corp-1",
        customer_name="Demo Corp",
        org_id="pu-1",
        org_name="Demo Lineage PU",
        created_at="2026-01-12",
    )
    calls: list[dict] = []

    def transport(payload: dict) -> dict:
        calls.append(payload)
        return {
            "contract_version": 1,
            "run_id": "run-1",
            "run_state": "accepted",
            "idempotency_key": payload["idempotency_key"],
        }

    result = consume_tepp_for_clues(TeppClient(transport=transport), clues)
    assert calls == []
    assert result.consumed is False
    assert result.empty_next_action == TEPP_UNAVAILABLE_NEXT_ACTION
    assert "theta" not in (result.empty_next_action or "").lower()


def test_time_question_needs_tepp_consume() -> None:
    assert needs_tepp_consume("이 글의 시간창은 무엇인가요?")
    assert not needs_tepp_consume("누가 관련되었나요?")


def test_request_shape_stays_the_published_envelope() -> None:
    payload = AnalysisRunRequest(
        idempotency_key="k",
        tenant_workspace_id="corp-1",
        snapshot_id="A-100",
        knowledge_cutoff="2026-01-12T00:00:00Z",
        model_contract_version="tepp-analysis-run-v1",
        output_profile="calibrated_event_measurement",
    ).to_json()
    assert "theta" not in payload
