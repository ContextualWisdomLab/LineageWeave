"""Contract tests for adaptive contextual-orchestrator consumer defaults."""

from __future__ import annotations

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
AUTO_CLIENTS = (
    "lineageweave/post_summary.py",
    "lineageweave/post_evaluation.py",
    "lineageweave/keyman_extraction.py",
    "lineageweave/commitment_extraction.py",
    "lineageweave/entity_relationship_classification.py",
)
VERIFY_CLIENTS = (
    "lineageweave/post_chat.py",
    "lineageweave/adjudication_client.py",
)
_ROUTE_MARKERS = (
    '"mode": "route"',
    'mode="route"',
    'mode: str = "route"',
)


def _source(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


class AdaptiveOrchestratorDefaultTest(unittest.TestCase):
    """Protect production clients from regressing to forced one-model routing."""

    def test_auto_clients_request_auto_and_never_force_route(self) -> None:
        for relative in AUTO_CLIENTS:
            source = _source(relative)
            with self.subTest(path=relative):
                for marker in _ROUTE_MARKERS:
                    self.assertNotIn(marker, source)
                if relative.endswith("post_evaluation.py"):
                    self.assertIn('"mode": mode', source)
                    self.assertIn('mode: str = "auto"', source)
                    continue
                self.assertIn(
                    '"mode": "auto"',
                    source,
                    f"{relative} must send a payload-level mode=auto literal",
                )

    def test_verify_clients_keep_checked_judgment_and_never_force_route(self) -> None:
        for relative in VERIFY_CLIENTS:
            source = _source(relative)
            with self.subTest(path=relative):
                for marker in _ROUTE_MARKERS:
                    self.assertNotIn(marker, source)
                self.assertIn(
                    '"mode": "verify"',
                    source,
                    f"{relative} must send a payload-level mode=verify literal",
                )
                self.assertNotIn(
                    '"mode": "auto"',
                    source,
                    f"{relative} must send verify, not a payload-level auto default",
                )


if __name__ == "__main__":
    unittest.main()
