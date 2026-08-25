"""Operational case semantic-response contract tests."""

import json

from lineageweave.operations_case_analysis import parse_operations_case_response


def test_parses_multiple_cases_and_grounded_facts() -> None:
    """One record may support multiple case kinds without losing evidence."""
    body = "The revised specification caused the claim. Mina agreed with Alex to rebid."
    payload = [
        {"case_kind_code": "claim_investigation", "summary_text": "Specification-linked claim", "evidence_text": "The revised specification caused the claim.", "facts": [{"fact_type_code": "specification_change", "value_text": "revised specification", "evidence_text": "The revised specification caused the claim."}]},
        {"case_kind_code": "rebid_handover", "summary_text": "Rebid agreement", "evidence_text": "Mina agreed with Alex to rebid.", "facts": [{"fact_type_code": "counterparty", "value_text": "Mina and Alex", "evidence_text": "Mina agreed with Alex to rebid."}]},
    ]
    result = parse_operations_case_response(json.dumps(payload), body)
    assert result is not None
    assert [case.case_kind_code for case in result] == ["claim_investigation", "rebid_handover"]


def test_rejects_uncited_model_claim() -> None:
    """A plausible answer absent from the source is not persisted."""
    payload = [{"case_kind_code": "external_information", "summary_text": "Market note", "evidence_text": "invented", "facts": []}]
    assert parse_operations_case_response(json.dumps(payload), "source body") is None


def test_accepts_supported_no_case_result() -> None:
    """An empty semantic result remains distinct from malformed output."""
    assert parse_operations_case_response("[]", "ordinary status") == ()


def test_rejects_unknown_codes_and_malformed_json() -> None:
    """Closed vocabularies prevent provider prose from entering persistence."""
    assert parse_operations_case_response("not json", "body") is None
    assert parse_operations_case_response('[{"case_kind_code":"other"}]', "body") is None
