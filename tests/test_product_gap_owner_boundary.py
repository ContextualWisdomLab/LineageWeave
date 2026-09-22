"""Executable ownership checks for live product-gap and evidence contracts."""

from pathlib import Path


_ROOT = Path(__file__).resolve().parents[1]
_PRODUCT_GAP_BASELINE = _ROOT / "docs" / "product-technical-gap-baseline.md"
_TRANSLATION_LEDGER_RUNNER_RECEIPT = (
    _ROOT / "docs" / "doctoring" / "translation-ledger-hosted-runner-provenance.md"
)
_LATEST_VALIDATION_MARKER = "> Exact-head validation overlay:"


def _latest_validation_overlay() -> str:
    """Return only the newest validation overlay, leaving older snapshots immutable."""
    baseline = _PRODUCT_GAP_BASELINE.read_text(encoding="utf-8")
    _, separator, tail = baseline.partition(_LATEST_VALIDATION_MARKER)
    assert separator, "product-gap baseline must publish a validation overlay"
    return separator + tail.split("\n> Exact-head validation overlay:", 1)[0]


def test_latest_validation_overlay_records_released_orchestrator_consumer_gap() -> None:
    """A local CO wire client cannot be promoted while the owner has no release."""
    overlay = _latest_validation_overlay().replace("\n> ", " ")

    assert "`c10b6545520afb342e68d01ea4bcfce75a6e5bab`" in overlay
    assert "contextual-orchestrator#1083" in overlay
    assert "Releases API" in overlay and "`[]`" in overlay
    assert "/v1/chat/completions" in overlay
    assert "`180.0s`" in overlay
    assert "released API/client/schema" in overlay
    assert "bind to mutable `main`" in overlay


def test_latest_validation_overlay_records_current_owner_and_voice_heads() -> None:
    """The mutable overlay must bind owner and Voice evidence to exact heads."""
    overlay = _latest_validation_overlay().replace("\n> ", " ")

    assert "`33c14c4b05a6fff6c11800b60184d2bdd3eb01db`" in overlay
    assert "`8f5c2659d2471aee9ab6b9c35c2bed5651f7d97c`" in overlay
    assert "fast-mlsirm 0.11.3" in overlay
    assert "locked 0.11.4" in overlay
    assert "twelve atomic Voices" in overlay
    assert "adds no fixed Voice combination" in overlay


def test_latest_validation_overlay_keeps_browser_and_load_evidence_bounded() -> None:
    """Candidate browser proof must not promote a failed load admission to acceptance."""
    overlay = _latest_validation_overlay().replace("\n> ", " ")

    assert "all 538 frontend tests" in overlay
    assert "Four authenticated Playwright scenarios passed" in overlay
    assert "`/api/me` returned successfully" in overlay
    assert "not protected-main delivery" in overlay
    assert "no admitted `lineageweave-test-automation` client" in overlay
    assert "No concurrency, latency, error-rate, throughput" in overlay
    assert "not an observed product bottleneck" in overlay


def test_latest_validation_overlay_does_not_promote_partial_codeql_admission() -> None:
    """A successful CodeQL detector must not be described as successful CodeQL."""
    overlay = _latest_validation_overlay().replace("\n> ", " ")

    assert "CodeQL language detection succeeded" in overlay
    assert "CodeQL compatibility/dispatch settlement" in overlay
    assert "primary CodeQL successful" not in overlay


def test_translation_ledger_hosted_failure_keeps_runner_provenance() -> None:
    """The #929 hosted RED must retain its runner-provenance classification."""
    receipt = _TRANSLATION_LEDGER_RUNNER_RECEIPT.read_text(encoding="utf-8")

    assert "#929" in receipt
    assert "`d4f42f579663e88a0c9af0cc492aa6ff7cae96ee`" in receipt
    assert "`35236145547`" in receipt
    assert "`105252445377`" in receipt
    assert "file or directory not found: tests" in receipt
    assert "collected 0 items" in receipt
    assert "workspace/config-provenance" in receipt
    assert ".github#712" in receipt
    assert "not an i18n/product assertion failure" in receipt
    assert "blind rerun" in receipt
