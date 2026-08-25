import json

import pytest

from lineageweave.post_structure import (
    ContextualOrchestratorPostStructureClient,
    _response_content,
)


def test_structure_client_validates_complete_decisions(monkeypatch) -> None:
    captured = []

    def fake_post_json(*args, **kwargs):
        captured.append(args[1])
        units = json.loads(args[1]["messages"][1]["content"])["ordered_units"]
        return {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            {"decisions": [
                                {
                                    "unit_index": int(unit["unit_index"]),
                                    "indent_level": 0,
                                    "confidence": 0.9,
                                    "evidence": "top-level heading",
                                }
                                for unit in units
                            ]}
                        )
                    }
                }
            ]
        }

    monkeypatch.setattr(
        "lineageweave.post_structure.post_json",
        fake_post_json,
    )
    client = ContextualOrchestratorPostStructureClient("http://orchestrator", "test-key")

    assert client.timeout == 600.0
    assert client.infer("Title", [{"unit_index": 0, "text": "1. Heading"}])[0].indent_level == 0
    assert len(captured) == 1
    response_format = captured[0]["response_format"]
    assert response_format["type"] == "json_schema"
    assert response_format["json_schema"]["strict"] is True
    assert response_format["json_schema"]["schema"]["required"] == ["decisions"]
    assert captured[0]["max_tokens"] == 4096


@pytest.mark.parametrize(
    "response",
    [{"choices": ["provider secret"]}, {"choices": [{"message": "provider secret"}]}],
)
def test_structure_response_rejects_raw_provider_shapes(response: object) -> None:
    with pytest.raises(ValueError, match="structure adjudication response") as error:
        _response_content(response)
    assert "provider secret" not in str(error.value)
