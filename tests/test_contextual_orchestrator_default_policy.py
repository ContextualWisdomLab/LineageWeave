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
_PAYLOAD_AUTO = '"mode": "auto"'
_PAYLOAD_VERIFY = '"mode": "verify"'
_TYPED_AUTO_DEFAULT = 'mode: str = "auto"'
_FORWARDED_MODE = '"mode": mode'


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
                    self.assertIn(_FORWARDED_MODE, source)
                    self.assertIn(_TYPED_AUTO_DEFAULT, source)
                    continue
                self.assertIn(
                    _PAYLOAD_AUTO,
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
                    _PAYLOAD_VERIFY,
                    source,
                    f"{relative} must send a payload-level mode=verify literal",
                )
                self.assertNotIn(
                    _PAYLOAD_AUTO,
                    source,
                    f"{relative} must send verify, not a payload-level auto default",
                )

    def test_docstring_mode_mention_is_not_a_payload_literal(self) -> None:
        """A class docstring contrast must not satisfy the auto/verify scan."""

        source = (
            '"""Calls the orchestrator with mode="auto", not mode="verify"."""\n'
            "body = {\"messages\": [], \"mode\": \"route\"}\n"
        )
        self.assertNotIn(_PAYLOAD_AUTO, source)
        self.assertNotIn(_PAYLOAD_VERIFY, source)
        self.assertIn('mode="auto"', source)
        self.assertIn('mode="verify"', source)


if __name__ == "__main__":
    unittest.main()
