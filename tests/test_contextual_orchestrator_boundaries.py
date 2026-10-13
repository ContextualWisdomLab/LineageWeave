"""Synthetic Compose/bootstrap contracts, no private env read."""
import importlib.util
import os
from pathlib import Path
import subprocess
import json
import pytest
ROOT=Path(__file__).parents[1]

def test_bootstrap_threat_boundary_is_not_erasure():
    source=(ROOT/'docker/contextual-orchestrator/start.py').read_text()
    assert 'initial process environment' in source
    assert 'Docker container configuration' in source

def test_compose_loopback_no_public_dev_token_or_allowlist_override():
    text=(ROOT/'docker-compose.yml').read_text()
    section=text.split('  orchestrator:\n')[1].split('  backend:\n')[0]
    assert '127.0.0.1:${ORCHESTRATOR_PORT:-18000}:8000' in section
    assert 'lineageweave-orchestrator-dev-only' not in section
    assert 'CONTEXTUAL_ORCHESTRATOR_ALLOWED_PROVIDER_HOSTS:' not in section

def test_known_public_token_rejected_before_runtime_import(monkeypatch):
    path=ROOT/'docker/contextual-orchestrator/start.py'
    spec=importlib.util.spec_from_file_location('test_lw_start',path); module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    monkeypatch.setenv('LLM_GATEWAY_API_KEY','synthetic-only')
    monkeypatch.setenv('CONTEXTUAL_ORCHESTRATOR_TOKEN','lineageweave-orchestrator-dev-only')
    with pytest.raises(SystemExit,match='nondefault'):module.main()
