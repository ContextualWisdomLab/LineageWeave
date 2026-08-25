"""Operational case semantic-response contract tests."""

import json

from lineageweave.operations_case_analysis import OperationsEvidenceSource, parse_operations_case_response


def test_parses_multiple_cases_and_grounded_facts() -> None:
    """One record may support multiple case kinds without losing evidence."""
    body = "The revised specification caused the claim. Mina agreed with Alex to rebid."
    payload = [
        {"case_kind_code": "claim_investigation", "summary_text": "Specification-linked claim", "evidence_text": "The revised specification caused the claim.", "facts": [{"fact_type_code": "specification_change", "value_text": "revised specification", "evidence_text": "The revised specification caused the claim."}], "missing_fact_type_codes": ["order", "originating_order", "sales_pool"]},
        {"case_kind_code": "rebid_handover", "summary_text": "Rebid agreement", "evidence_text": "Mina agreed with Alex to rebid.", "facts": [{"fact_type_code": "counterparty", "value_text": "Mina and Alex", "evidence_text": "Mina agreed with Alex to rebid."}], "missing_fact_type_codes": ["discussion", "our_owner", "decision"]},
    ]
    result = parse_operations_case_response(json.dumps(payload), body)
    assert result is not None
    assert [case.case_kind_code for case in result] == ["claim_investigation", "rebid_handover"]


def test_rejects_uncited_model_claim() -> None:
    """A plausible answer absent from the source is not persisted."""
    payload = [{"case_kind_code": "external_information", "summary_text": "Market note", "evidence_text": "invented", "facts": [], "missing_fact_type_codes": ["external_relation"]}]
    assert parse_operations_case_response(json.dumps(payload), "source body") is None


def test_accepts_supported_no_case_result() -> None:
    """An empty semantic result remains distinct from malformed output."""
    assert parse_operations_case_response("[]", "ordinary status") == ()


def test_rejects_unknown_codes_and_malformed_json() -> None:
    """Closed vocabularies prevent provider prose from entering persistence."""
    assert parse_operations_case_response("not json", "body") is None
    assert parse_operations_case_response('[{"case_kind_code":"other"}]', "body") is None


def test_rejects_duplicate_case_kinds_and_blank_evidence() -> None:
    """One normalized key has one grounded classification, never an empty span."""
    duplicate = [
        {"case_kind_code": "repeat_issue", "summary_text": "First", "evidence_text": "body", "facts": [], "missing_fact_type_codes": ["issue_pattern", "improvement_action"]},
        {"case_kind_code": "repeat_issue", "summary_text": "Second", "evidence_text": "body", "facts": [], "missing_fact_type_codes": ["issue_pattern", "improvement_action"]},
    ]
    blank = [
        {"case_kind_code": "repeat_issue", "summary_text": "Blank", "evidence_text": "", "facts": [], "missing_fact_type_codes": ["issue_pattern", "improvement_action"]}
    ]
    assert parse_operations_case_response(json.dumps(duplicate), "body") is None
    assert parse_operations_case_response(json.dumps(blank), "body") is None


def test_linked_fact_retains_its_authorized_source_post_and_input_digest() -> None:
    """A linked specification fact is never attributed to the focal record."""
    sources = (
        OperationsEvidenceSource("focal", "Claim", "A claim was received."),
        OperationsEvidenceSource("linked", "Specification", "Specification S2 replaced S1."),
    )
    payload = [{
        "case_kind_code": "claim_investigation",
        "summary_text": "Specification changed before the claim",
        "evidence_post_id": "focal",
        "evidence_text": "A claim was received.",
        "facts": [{
            "fact_type_code": "specification_change",
            "value_text": "S2 replaced S1",
            "evidence_post_id": "linked",
            "evidence_text": "Specification S2 replaced S1.",
        }],
        "missing_fact_type_codes": ["order", "originating_order", "sales_pool"],
    }]

    result = parse_operations_case_response(json.dumps(payload), sources)

    assert result is not None
    assert result[0].facts[0].evidence_post_id == "linked"
    assert result[0].facts[0].evidence_input_sha256 == sources[1].input_sha256
    payload[0]["facts"][0]["evidence_post_id"] = "unauthorized"
    assert parse_operations_case_response(json.dumps(payload), sources) is None


def test_requires_each_case_question_to_be_supported_or_explicitly_missing() -> None:
    """The provider cannot silently omit or both support and miss a required answer."""
    payload = [{
        "case_kind_code": "external_information",
        "summary_text": "External notice",
        "evidence_text": "A public notice was published.",
        "facts": [],
        "missing_fact_type_codes": [],
    }]
    body = "A public notice was published."
    assert parse_operations_case_response(json.dumps(payload), body) is None


def test_accepts_additional_grounded_fact_beyond_required_questions() -> None:
    """Optional grounded facts do not invalidate a complete required answer set."""
    body = "The claim changed after specification S2; the sales pool was North."
    payload = [{
        "case_kind_code": "claim_investigation",
        "summary_text": "Specification-linked claim",
        "evidence_text": body,
        "facts": [
            {"fact_type_code": "specification_change", "value_text": "S2", "evidence_text": "specification S2"},
            {"fact_type_code": "sales_pool", "value_text": "North", "evidence_text": "sales pool was North"},
            {"fact_type_code": "discussion", "value_text": "Claim discussion", "evidence_text": "claim changed"},
        ],
        "missing_fact_type_codes": ["order", "originating_order"],
    }]
    result = parse_operations_case_response(json.dumps(payload), body)
    assert result is not None
    assert [fact.fact_type_code for fact in result[0].facts] == [
        "specification_change", "sales_pool", "discussion"
    ]

    payload[0]["facts"] = [{
        "fact_type_code": "external_relation",
        "value_text": "Sales opportunity",
        "evidence_text": body,
    }]
    payload[0]["missing_fact_type_codes"] = ["external_relation"]
    assert parse_operations_case_response(json.dumps(payload), body) is None


def test_accepts_grounded_nonrequired_fact_after_required_questions_are_complete() -> None:
    """A cited optional fact must not invalidate complete required answers."""
    body = "A public notice was published and assigned to the sales team."
    payload = [{
        "case_kind_code": "external_information",
        "summary_text": "External notice",
        "evidence_text": "A public notice was published",
        "facts": [
            {
                "fact_type_code": "external_relation",
                "value_text": "Sales opportunity",
                "evidence_text": body,
                "relation_target_kind_code": "sales",
            },
            {
                "fact_type_code": "our_owner",
                "value_text": "Sales team",
                "evidence_text": "assigned to the sales team",
            },
        ],
        "missing_fact_type_codes": [],
    }]

    assert parse_operations_case_response(json.dumps(payload), body) is not None


def test_external_relation_requires_a_semantic_target_type() -> None:
    """Only source-backed typed external links enter the ontology projection."""
    body = "The public tender applies to Synthetic Project A."
    fact = {
        "fact_type_code": "external_relation",
        "value_text": "Synthetic Project A",
        "evidence_text": body,
        "relation_target_kind_code": "project",
    }
    payload = [{
        "case_kind_code": "external_information",
        "summary_text": "Tender relates to a project",
        "evidence_text": body,
        "facts": [fact],
        "missing_fact_type_codes": [],
    }]

    result = parse_operations_case_response(json.dumps(payload), body)

    assert result is not None
    assert result[0].facts[0].relation_target_kind_code == "project"
    del fact["relation_target_kind_code"]
    assert parse_operations_case_response(json.dumps(payload), body) is None
    fact["relation_target_kind_code"] = "guessed"
    assert parse_operations_case_response(json.dumps(payload), body) is None
