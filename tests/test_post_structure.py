import json

from lineageweave.post_structure import ContextualOrchestratorPostStructureClient


def test_structure_client_validates_complete_decisions(monkeypatch) -> None:
    captured = []

    def fake_post_json(*args, **kwargs):
        captured.append(args[1])
        target = json.loads(args[1]["messages"][1]["content"])["target_unit_index"]
        return {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            {
                                "unit_index": target,
                                "indent_level": 0,
                                "confidence": 0.9,
                                "evidence": "top-level heading",
                            }
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

    assert client.infer("Title", [{"unit_index": 0, "text": "1. Heading"}])[0].indent_level == 0
    response_format = captured[0]["response_format"]
    assert response_format["type"] == "json_schema"
    assert response_format["json_schema"]["strict"] is True
    assert response_format["json_schema"]["schema"]["required"] == [
        "unit_index",
        "indent_level",
        "confidence",
        "evidence",
    ]
