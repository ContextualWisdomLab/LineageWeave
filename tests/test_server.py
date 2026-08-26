"""End-to-end HTTP smoke test: the demo server must serve the reconstructed
graph and the static viewer."""

from __future__ import annotations

import json
import threading
import urllib.request

from lineageweave.server import build_server

# Synthetic unit-test fusion weights injected so this smoke test runs
# without fast-mlsirm (org policy allows synthetic data in unit tests);
# the demo binary itself estimates its weights and refuses to start
# otherwise (ADR 0145, second amendment).
_SYNTHETIC_WEIGHTS = {"temporal": 0.5, "secondary_key": 0.34, "text": 0.16}


def test_lineage_endpoint_serves_the_reconstructed_graph_with_a_branch_point() -> None:
    server = build_server(port=0, weights=_SYNTHETIC_WEIGHTS)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    port = server.server_address[1]

    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/lineage", timeout=5) as response:
            status = response.status
            body = json.loads(response.read().decode("utf-8"))
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    assert status == 200
    assert len(body["nodes"]) > 0
    assert len(body["edges"]) > 0
    assert any(node["is_branch_point"] for node in body["nodes"])


def test_root_serves_the_static_viewer() -> None:
    server = build_server(port=0, weights=_SYNTHETIC_WEIGHTS)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    port = server.server_address[1]

    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=5) as response:
            status = response.status
            body = response.read().decode("utf-8")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    assert status == 200
    assert "LineageWeave" in body


def test_path_traversal_is_rejected() -> None:
    server = build_server(port=0, weights=_SYNTHETIC_WEIGHTS)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    port = server.server_address[1]

    try:
        req = urllib.request.Request(f"http://127.0.0.1:{port}/../pyproject.toml")
        try:
            urllib.request.urlopen(req, timeout=5)
            raised = False
        except urllib.error.HTTPError as exc:
            raised = exc.code == 404
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    assert raised
