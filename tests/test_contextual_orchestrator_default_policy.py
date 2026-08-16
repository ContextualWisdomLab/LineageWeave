"""Contract tests for adaptive contextual-orchestrator consumer defaults."""
from __future__ import annotations

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
ACTIVE_CLIENTS = (
    "lineageweave/post_summary.py",
    "lineageweave/post_evaluation.py",
    "lineageweave/keyman_extraction.py",
    "lineageweave/commitment_extraction.py",
    "lineageweave/post_chat.py",
    "lineageweave/entity_relationship_classification.py",
)


class AdaptiveOrchestratorDefaultTest(unittest.TestCase):
    """Protect production clients from regressing to forced one-model routing."""

    def test_active_clients_use_auto_and_never_force_route(self) -> None:
        for relative in ACTIVE_CLIENTS:
            source = (ROOT / relative).read_text(encoding="utf-8")
            with self.subTest(path=relative):
                self.assertNotIn('"mode": "route"', source)
                self.assertNotIn('mode="route"', source)
                self.assertNotIn('mode: str = "route"', source)
                self.assertTrue(
                    '"mode": "auto"' in source
                    or 'mode="auto"' in source
                    or 'mode: str = "auto"' in source
                )

    def test_high_stakes_adjudication_retains_explicit_checked_override(self) -> None:
        source = (ROOT / "lineageweave/adjudication_client.py").read_text(encoding="utf-8")
        self.assertIn('"mode": "verify"', source)


if __name__ == "__main__":
    unittest.main()
