from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from unittest.mock import patch


_ROOT = Path(__file__).resolve().parents[1]
_MODULE_PATH = _ROOT / "docker" / "contextual-orchestrator" / "start.py"
_SPEC = importlib.util.spec_from_file_location("lineageweave_orchestrator_start", _MODULE_PATH)
assert _SPEC and _SPEC.loader
sys.path.insert(0, str(_MODULE_PATH.parent))
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)


def test_discover_chat_model_skips_non_chat_models() -> None:
    class Response:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return None

        def read(self):
            return json.dumps(
                {
                    "data": [
                        {"id": "text-embedding-3-large"},
                        {"id": "gpt-4.1-mini"},
                    ]
                }
            ).encode()

    response = Response()
    with patch.object(_MODULE.urllib.request, "urlopen", return_value=response):
        assert _MODULE._discover_chat_model("https://gateway.example/v1", "secret") == "gpt-4.1-mini"
