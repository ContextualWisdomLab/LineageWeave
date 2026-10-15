"""Runtime must install the pinned upstream's actual locked/native contract."""
from pathlib import Path

def test_runtime_builds_locked_upstream_dependencies_and_native_extensions():
    source = (Path(__file__).parents[1] / "docker/contextual-orchestrator/Dockerfile").read_text()
    assert "8e1f1a8bf3e96e56dc8fcc90ec777883a1d56ce6" in source
    assert "--require-hashes" in source
    assert "requirements.lock" in source
    assert "maturin==1.15.0" in source
    assert "--locked" in source
    assert "rust/token_counter/Cargo.toml" in source
    assert "rust/decision_receipt/Cargo.toml" in source
    assert "sha256:" in source
    assert "register_credential" not in source
