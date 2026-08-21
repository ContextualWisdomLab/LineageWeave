"""Minimal HTTP server: serves the reconstructed lineage graph as JSON and
the static DAG viewer. Stdlib-only, mirroring contextual-orchestrator's own
server style so this repo has no required runtime dependency beyond
ThreadWeave and RankWeave.
"""

from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .fixtures import sample_records
from .models import Tree
from .reconstruct import reconstruct

_WEB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "web")


def trees_to_graph(trees: list[Tree]) -> dict:
    """Flatten reconstructed trees into a ``{nodes, edges}`` shape for the UI."""
    nodes = []
    edges = []
    for tree in trees:
        for record_id, record in tree.records.items():
            nodes.append(
                {
                    "id": record_id,
                    "group": tree.group_key,
                    "label": record.label,
                    "occurred_at": record.occurred_at.isoformat(),
                    "is_root": record_id in tree.roots,
                    "is_branch_point": record_id in tree.children_of and len(tree.children_of[record_id]) >= 2,
                }
            )
        for edge in tree.edges:
            edges.append(
                {
                    "source": edge.parent_id,
                    "target": edge.child_id,
                    "fused_score": edge.fused_score,
                    "channel_scores": edge.channel_scores,
                }
            )
    return {"nodes": nodes, "edges": edges}


def build_server(host: str = "127.0.0.1", port: int = 8420) -> ThreadingHTTPServer:
    """Build, but do not start, the demo server."""

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            """Handle a GET request using the server's health endpoint contract."""
            if self.path == "/api/lineage":
                trees = reconstruct(sample_records())
                self._send_json(trees_to_graph(trees))
                return
            self._send_static()

        def _send_json(self, payload: dict) -> None:
            """Implement the _send_json operation for this channel."""
            body = json.dumps(payload).encode("utf-8")
            self.send_response(200)
            self.send_header("content-type", "application/json")
            self.send_header("content-length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _send_static(self) -> None:
            """Implement the _send_static operation for this channel."""
            relative = "index.html" if self.path in ("/", "") else self.path.lstrip("/")
            file_path = os.path.normpath(os.path.join(_WEB_DIR, relative))
            if not file_path.startswith(_WEB_DIR) or not os.path.isfile(file_path):
                self.send_response(404)
                self.end_headers()
                return
            with open(file_path, "rb") as f:
                body = f.read()
            content_type = "text/html; charset=utf-8" if file_path.endswith(".html") else "application/octet-stream"
            self.send_response(200)
            self.send_header("content-type", content_type)
            self.send_header("content-length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format: str, *args) -> None:  # noqa: A002 - stdlib signature
            """Suppress the standard library request log for this service."""
            pass  # quiet by default; rely on the caller's own logging if needed

    return ThreadingHTTPServer((host, port), Handler)


def serve(host: str = "127.0.0.1", port: int = 8420) -> None:
    """Run the local HTTP server until it is stopped."""
    server = build_server(host, port)
    print(f"LineageWeave demo listening on http://{host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    serve()
