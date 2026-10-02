"""End-to-end HTTP smoke test: the demo server must serve the reconstructed
graph and the static viewer."""

from __future__ import annotations

import json
import threading
import urllib.request
from pathlib import Path

import lineageweave.server as server_module

# Synthetic unit-test fusion weights injected so this smoke test runs
# without fast-mlsirm (org policy allows synthetic data in unit tests);
# the demo binary itself estimates its weights and refuses to start
# otherwise (ADR 0145, second amendment).
_SYNTHETIC_WEIGHTS = {"temporal": 0.5, "secondary_key": 0.34, "text": 0.16}


def test_lineage_endpoint_serves_the_reconstructed_graph_with_a_branch_point() -> None:
    server = server_module.build_server(port=0, weights=_SYNTHETIC_WEIGHTS)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    port = server.server_address[1]

    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/lineage", timeout=5) as response:
            status = response.status
            body = json.loads(response.read().decode("utf-8"))
    finally:
        server.shutdown()
        thread.join(timeout=5)

    assert status == 200
    assert len(body["nodes"]) > 0
    assert len(body["edges"]) > 0
    assert any(node["is_branch_point"] for node in body["nodes"])


def test_health_endpoint_returns_liveness_json() -> None:
    server = server_module.build_server(port=0, weights=_SYNTHETIC_WEIGHTS)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    port = server.server_address[1]

    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/healthz", timeout=5) as response:
            status = response.status
            body = json.loads(response.read().decode("utf-8"))
    finally:
        server.shutdown()
        thread.join(timeout=5)

    assert status == 200
    assert body == {"status": "ok"}


def test_health_and_lineage_routes_ignore_query_parameters() -> None:
    server = server_module.build_server(port=0, weights=_SYNTHETIC_WEIGHTS)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    port = server.server_address[1]

    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/healthz?probe=1", timeout=5) as health:
            health_body = json.loads(health.read().decode("utf-8"))
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/lineage?view=graph", timeout=5) as lineage:
            lineage_body = json.loads(lineage.read().decode("utf-8"))
    finally:
        server.shutdown()
        thread.join(timeout=5)

    assert health_body == {"status": "ok"}
    assert lineage_body["nodes"]


def test_unknown_api_endpoint_returns_not_found() -> None:
    server = server_module.build_server(port=0, weights=_SYNTHETIC_WEIGHTS)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    port = server.server_address[1]

    try:
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/api/unknown", timeout=5)
            raised = False
        except urllib.error.HTTPError as exc:
            raised = exc.code == 404
    finally:
        server.shutdown()
        thread.join(timeout=5)

    assert raised


def test_root_serves_the_static_viewer() -> None:
    server = server_module.build_server(port=0, weights=_SYNTHETIC_WEIGHTS)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    port = server.server_address[1]

    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=5) as response:
            status = response.status
            body = response.read().decode("utf-8")
    finally:
        server.shutdown()
        thread.join(timeout=5)

    assert status == 200
    assert "LineageWeave" in body


def test_root_route_ignores_query_parameters() -> None:
    server = server_module.build_server(port=0, weights=_SYNTHETIC_WEIGHTS)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    port = server.server_address[1]

    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/?cache=1", timeout=5) as response:
            status = response.status
            body = response.read().decode("utf-8")
    finally:
        server.shutdown()
        thread.join(timeout=5)

    assert status == 200
    assert "LineageWeave" in body


def test_path_traversal_is_rejected() -> None:
    server = server_module.build_server(port=0, weights=_SYNTHETIC_WEIGHTS)
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
        thread.join(timeout=5)

    assert raised


def test_sibling_prefix_path_is_not_inside_web_root(tmp_path, monkeypatch) -> None:
    web_root = tmp_path / "web"
    sibling_root = tmp_path / "web-secret"
    web_root.mkdir()
    sibling_root.mkdir()
    (sibling_root / "index.html").write_text("not public", encoding="utf-8")
    monkeypatch.setattr(server_module, "_WEB_DIR", str(web_root))

    server = server_module.build_server(port=0, weights=_SYNTHETIC_WEIGHTS)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    port = server.server_address[1]

    try:
        try:
            urllib.request.urlopen(
                f"http://127.0.0.1:{port}/../web-secret/index.html", timeout=5
            )
            raised = False
        except urllib.error.HTTPError as exc:
            raised = exc.code == 404
    finally:
        server.shutdown()
        thread.join(timeout=5)

    assert raised


def test_static_viewer_has_loading_empty_and_error_states() -> None:
    html = (Path(__file__).parents[1] / "web" / "index.html").read_text(encoding="utf-8")

    assert 'id="status"' in html
    assert "Loading reconstructed lineage" in html
    assert "if (!r.ok)" in html
    assert "No reconstructed lineage is available yet." in html
    assert "Lineage is temporarily unavailable. Refresh to try again." in html
    assert 'g.setAttribute("tabindex", "0")' in html
    assert 'g.setAttribute("role", "img")' in html
    assert 'g.setAttribute("aria-label"' in html
    assert 'document.createElementNS(svgNS, "title")' in html
    assert 'g.addEventListener("focus"' in html
    assert 'g.addEventListener("blur"' in html
