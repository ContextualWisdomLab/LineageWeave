from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


_PATH = Path(__file__).parents[1] / "docker" / "contextual-orchestrator" / "provider_policy.py"
_SPEC = spec_from_file_location("lineageweave_provider_policy", _PATH)
assert _SPEC and _SPEC.loader
_MODULE = module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)


def test_local_mlx_compatibility_is_not_enabled_for_external_gateway() -> None:
    assert _MODULE.is_local_mlx_provider("http://host.docker.internal:8080/v1")
    assert not _MODULE.is_local_mlx_provider("https://llm-gateway.example/v1")
    assert not _MODULE.is_local_mlx_provider("http://host.docker.internal:18000/v1")
