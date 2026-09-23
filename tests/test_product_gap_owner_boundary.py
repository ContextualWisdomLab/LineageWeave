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


def test_latest_validation_overlay_keeps_voice_adr_authority_exact() -> None:
    """Voice composition must not absorb the unrelated ADR 0251 FJA authority."""
    overlay = _latest_validation_overlay().replace("\n> ", " ")
    _, voice_marker, voice_tail = overlay.partition("Voice-of-X candidate #1121")

    assert voice_marker, "latest overlay must include the current Voice candidate"
    voice_contract = voice_tail.split("This baseline PR was inspected", 1)[0]
    assert "ADRs 0246" in voice_contract
    assert "0252" in voice_contract
    assert "0256" in voice_contract
    assert "0251" not in voice_contract


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

    assert "CodeQL language detection" in overlay
    assert "remain queued" in overlay
    assert "CodeQL compatibility/dispatch settlement" in overlay
    assert "primary CodeQL successful" not in overlay


def test_latest_validation_overlay_pins_current_global_ask_candidate() -> None:
    """Global Ask evidence names its reviewed head without promoting delivery."""
    overlay = _latest_validation_overlay().replace("\n> ", " ")

    assert "2026-09-23T15:22:05Z" in overlay
    assert "`2cbc64bbf436d63e7851f8f977872683c0a40d9d`" in overlay
    assert "two-session PostgreSQL serialization" in overlay
    assert "k6 burst" in overlay
    assert "evidence remains unavailable" in overlay
    assert "unavailable capacity default" in overlay


def test_latest_validation_overlay_pins_similar_voc_retry_acceptance_boundary() -> None:
    """Similar VOC recovery keeps exact-head UI proof below runtime acceptance."""
    overlay = _latest_validation_overlay().replace("\n> ", " ")

    assert "2026-09-23T15:22:05Z" in overlay
    assert "`1515b872d32b7e943c6c09b0f7da2806fe1224ac`" in overlay
    assert "all 533 frontend tests" in overlay
    assert "`RetainedEvidenceRetry`" in overlay
    assert "`EmptyNextPageRetry`" in overlay
    assert "authenticated PostgreSQL/API acceptance" in overlay
    assert "no qualifying independent approval exists" in overlay


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
