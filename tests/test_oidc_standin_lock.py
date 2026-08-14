"""Verify the Compose worker never becomes a Keyverse-shaped OIDC process."""

from __future__ import annotations

import importlib
import json
import runpy
import threading
import urllib.error
import urllib.request

from tests._contract_utils import assert_http_error_contract, find_contract_route, load_contract


_ROUTE_CONTRACT_NAME = "compose_oidc_worker_route_contract.json"
_COMPOSE_BOUNDARY_GUARD = importlib.import_module("scripts.check_compose_identity_boundary")


def _load_worker():
    """Load the worker from the current checkout."""
    return importlib.reload(importlib.import_module("compose.http_standin"))


def test_compose_worker_does_not_ship_local_keyverse_oidc() -> None:
    """The retained audit artifact must not be imported or packaged by the worker."""
    worker_src = _COMPOSE_BOUNDARY_GUARD.WORKER_PATH.read_text(encoding="utf-8")
    dockerfile = _COMPOSE_BOUNDARY_GUARD.WORKER_DOCKERFILE_PATH.read_text(encoding="utf-8")
    assert _COMPOSE_BOUNDARY_GUARD.COMPOSE_ROOT.joinpath("compose/keyverse_oidc.py").exists()
    assert "keyverse_oidc" not in worker_src
    assert "keyverse_oidc.py" not in dockerfile


def test_compose_worker_rejects_oidc_routes() -> None:
    """Discovery, authorization, token, and introspection are Keyverse-owned."""
    worker = _load_worker()
    route_contract = load_contract(_ROUTE_CONTRACT_NAME)
    httpd = worker.ThreadingHTTPServer(("127.0.0.1", 0), worker.StandinHandler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    origin = f"http://127.0.0.1:{httpd.server_address[1]}"
    try:
        for route in route_contract["routes"]:
            path = route["path"]
            method = route["method"]
            data = b"{}" if method == "POST" else None
            request = urllib.request.Request(
                origin + path,
                data=data,
                method=method,
            )
            try:
                urllib.request.urlopen(request, timeout=5)
                raise AssertionError(f"identity route unexpectedly served: {path}")
            except urllib.error.HTTPError as error:
                route_schema = find_contract_route(route_contract, path, method)
                assert_http_error_contract(
                    error.code,
                    json.loads(error.read()),
                    route_schema,
                )
    finally:
        httpd.shutdown()
        httpd.server_close()


def test_keyverse_oidc_module_is_not_runnable_as_compose_service() -> None:
    """Guardrail: the retained OIDC utility must not be launched in runtime mode."""
    try:
        runpy.run_path("compose/keyverse_oidc.py")
    except RuntimeError as error:
        assert str(error) == "compose_keyverse_oidc_module_is_not_runnable_in_compose"
    else:
        raise AssertionError("compose/keyverse_oidc.py must fail when executed as __main__")
