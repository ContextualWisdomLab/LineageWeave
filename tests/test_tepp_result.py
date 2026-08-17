"""Persistable TEPP envelopes succeed; accepted acks and thetas do not."""

from datetime import datetime, timezone

from lineageweave.tepp_result import (
    parse_persistable_tepp_result,
    persistable_tepp_seed_envelope,
)


def test_persistable_time_multilevel_envelope_is_accepted() -> None:
    """A time / multilevel / multi-affiliation result is persistable."""
    parsed = parse_persistable_tepp_result(persistable_tepp_seed_envelope())
    assert parsed is not None
    assert parsed.contract_version == 1
    assert parsed.result_kind == "time_multilevel_multi_affiliation"
    assert parsed.measured_at == datetime(2026, 1, 12, 12, 45, tzinfo=timezone.utc)
    assert parsed.interval_count == 2
    assert parsed.level_count == 3
    assert parsed.affiliation_count == 2
    assert len(parsed.result_sha256()) == 64
    assert "theta" not in parsed.result_sha256()


def test_accepted_ack_is_not_persistable() -> None:
    """A mere accepted envelope is not a measurement this product can store."""
    assert parse_persistable_tepp_result({"status": "accepted"}) is None
    assert parse_persistable_tepp_result({"contract_version": 1, "status": "accepted"}) is None


def test_theta_and_irt_payloads_are_not_persistable() -> None:
    """Never treat a theta or IRT item parameter as a persistable TEPP result."""
    base = persistable_tepp_seed_envelope()
    assert parse_persistable_tepp_result({**base, "theta": 0.42}) is None
    assert parse_persistable_tepp_result({**base, "item_parameters": [1.0]}) is None
    assert parse_persistable_tepp_result({**base, "nested": {"mean_theta": 1.2}}) is None


def test_topic_and_alr_payloads_are_not_persistable() -> None:
    """Topic and ALR stay in TEPP; this product does not store them."""
    base = persistable_tepp_seed_envelope()
    assert parse_persistable_tepp_result({**base, "topic": "pricing"}) is None
    assert parse_persistable_tepp_result({**base, "alr": [0.1, 0.9]}) is None
    assert parse_persistable_tepp_result({**base, "extras": [{"topic_label": "x"}]}) is None


def test_missing_or_negative_aggregates_are_not_persistable() -> None:
    """Counts must be present non-negative integers; clocks must parse."""
    base = persistable_tepp_seed_envelope()
    missing = dict(base)
    del missing["affiliation_count"]
    assert parse_persistable_tepp_result(missing) is None
    assert parse_persistable_tepp_result({**base, "affiliation_count": -1}) is None
    assert parse_persistable_tepp_result({**base, "interval_count": True}) is None
    assert parse_persistable_tepp_result({**base, "measured_at": "not-a-clock"}) is None
    assert parse_persistable_tepp_result("accepted") is None
