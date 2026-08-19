from lineageweave.post_structure import ContextualOrchestratorPostStructureClient


def test_structure_client_validates_complete_decisions(monkeypatch) -> None:
    monkeypatch.setattr(
        "lineageweave.post_structure.post_json",
        lambda *args, **kwargs: {
            "choices": [
                {
                    "message": {
                        "content": '{"decisions":[{"unit_index":0,"indent_level":0,"confidence":0.9,"evidence":"top-level heading"}]}'
                    }
                }
            ]
        },
    )
    client = ContextualOrchestratorPostStructureClient("http://orchestrator", "test-key")

    assert client.infer("Title", [{"unit_index": 0, "text": "1. Heading"}])[0].indent_level == 0
