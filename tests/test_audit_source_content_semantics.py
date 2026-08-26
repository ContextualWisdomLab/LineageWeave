import pytest

from scripts.audit_source_content_semantics import aggregate_results, parse_batch_result


def test_parser_rejects_the_observed_100_to_60_cardinality_mismatch() -> None:
    payload = {
        "input_count": 60,
        "items": [
            {"item_index": index, "covered": True, "missing_semantic_dimensions": []}
            for index in range(60)
        ],
    }

    import json

    with pytest.raises(ValueError, match="input_count"):
        parse_batch_result(json.dumps(payload), expected_count=100)


def test_valid_batches_aggregate_without_source_values() -> None:
    rows = parse_batch_result(
        '{"input_count":2,"items":['
        '{"item_index":0,"covered":false,"missing_semantic_dimensions":["event_or_activity"]},'
        '{"item_index":1,"covered":true,"missing_semantic_dimensions":[]}]}'
        ,
        expected_count=2,
    )

    result = aggregate_results([rows], [4])

    assert result == {
        "complete": True,
        "sample_count": 2,
        "covered_count": 1,
        "uncovered_count": 1,
        "missing_semantic_dimension_counts": {"event_or_activity": 1},
        "batch_count": 1,
        "minimum_trace_step_count": 4,
        "maximum_trace_step_count": 4,
    }


def test_parser_rejects_ungoverned_dimensions() -> None:
    with pytest.raises(ValueError, match="ungoverned"):
        parse_batch_result(
            '{"input_count":1,"items":['
            '{"item_index":0,"covered":false,"missing_semantic_dimensions":["invented"]}]}'
            ,
            expected_count=1,
        )
