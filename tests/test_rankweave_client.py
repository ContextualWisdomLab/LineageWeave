"""Fail-closed RankWeave ranking port.

RankWeave owns classic and convex-weighted RRF calculation. LineageWeave sends
only visible posts and projects the owner's contributions from owned channel
inputs. The client never invents a fused score or a theta.
"""

from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace

import pytest

from backend.app.ranking_ingestion import (
    load_ranking_context_choices,
    load_selected_ranking_rows,
)

from lineageweave.rankweave_client import (
    LibraryRankWeaveTransport,
    RankWeaveClient,
    RankWeaveNotAvailable,
    build_rankweave_client,
    project_ranking_list,
    ranking_channel_evidence,
    ranking_channels_from_rows,
)


PUBLIC = {
    "post_id": "post-1",
    "post_title": "Public post",
    "created_at": "2026-01-05T00:00:00Z",
}
QUOTE = {
    "post_id": "post-2",
    "post_title": "Pricing renegotiation: revised quote sent",
    "created_at": "2026-01-09T00:00:00Z",
}
HIDDEN = {
    "post_id": "hidden-parent",
    "post_title": "Private parent",
    "created_at": "2026-01-10T00:00:00Z",
}


class _CaptureConnection:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[object, ...]]] = []

    async def fetch(self, sql: str, *args: object) -> list[dict[str, object]]:
        self.calls.append((sql, args))
        return []


def test_context_choice_abac_is_bound_inside_sql() -> None:
    conn = _CaptureConnection()
    asyncio.run(load_ranking_context_choices(conn, ["entity-1"], ["unit-1"]))
    sql, args = conn.calls[0]
    assert "post.visibility_code = 'public'" in sql
    assert "post.corporate_entity_id::text = any($1::text[])" in sql
    assert args == (["entity-1"], ["unit-1"])


def test_selected_population_abac_precedes_projection() -> None:
    conn = _CaptureConnection()
    selection = {
        "topic_model_run_id": "run-1",
        "influence_run_id": "influence-1",
        "topic_index": 2,
        "dimension": "team",
        "context": "context-1",
    }
    asyncio.run(load_selected_ranking_rows(conn, selection, ["entity-1"], []))
    sql, args = conn.calls[0]
    assert "post.process_unit_id::text = any($2::text[])" in sql
    assert "influence.topic_model_run_id = $3::uuid" in sql
    assert args == (["entity-1"], [], "run-1", "influence-1", 2, "team", "context-1")


def _lexical_then_temporal(post_id: str, channel_rank: int) -> list[dict[str, object]]:
    # Parameter-free classic RRF (Cormack et al., 2009): every channel
    # weighs 1.0 -- no hand-picked weight exists (ADR 0200 point 1).
    lexical = 1.0 / (60 + channel_rank)
    temporal = 1.0 / (60 + channel_rank)
    return [
        {
            "signal_code": "lexical",
            "signal_label": "Title overlap",
            "channel_rank": channel_rank,
            "weight": 1.0,
            "contribution": lexical,
            "rank": 1,
        },
        {
            "signal_code": "temporal",
            "signal_label": "Newest first",
            "channel_rank": channel_rank,
            "weight": 1.0,
            "contribution": temporal,
            "rank": 2,
        },
    ]


def test_default_transport_fails_closed() -> None:
    client = RankWeaveClient()
    with pytest.raises(RankWeaveNotAvailable, match="rankweave_not_available"):
        client.fuse_rankings(
            {"temporal": ["post-1"], "lexical": ["post-1"]},
            {"post-1": "Public post"},
        )


def test_default_payload_never_invents_a_fused_score() -> None:
    payload = RankWeaveClient().as_api_payload(
        [PUBLIC, QUOTE],
        can_see_post=lambda _row: True,
    )

    assert payload == {
        "port": "rankweave",
        "status": "unavailable",
        "status_reason": "rankweave_not_available",
        "rankings": [],
    }
    assert "theta" not in json.dumps(payload)


def test_disabled_factory_fails_closed() -> None:
    client = build_rankweave_client(disabled=True)
    payload = client.as_api_payload([PUBLIC], can_see_post=lambda _row: True)
    assert payload["status"] == "unavailable"
    assert payload["rankings"] == []


def test_library_transport_fails_closed_when_rankweave_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def boom() -> object:
        raise ImportError("No module named 'rankweave'")

    monkeypatch.setattr("lineageweave.rankweave_client._import_rankweave", boom)
    client = RankWeaveClient(transport=LibraryRankWeaveTransport())
    with pytest.raises(RankWeaveNotAvailable, match="rankweave_not_available"):
        client.fuse_rankings(
            {"temporal": ["post-1"], "lexical": ["post-1"]},
            {"post-1": "Public post"},
        )
    assert (
        client.as_api_payload([PUBLIC], can_see_post=lambda _row: True)["rankings"]
        == []
    )


def test_library_transport_fails_closed_when_fuse_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeRw:
        @staticmethod
        def reciprocal_rank_fuse(*_args: object, **_kwargs: object) -> list:
            raise RuntimeError("duplicate identifiers")

    monkeypatch.setattr(
        "lineageweave.rankweave_client._import_rankweave", lambda: FakeRw
    )
    client = RankWeaveClient(transport=LibraryRankWeaveTransport())
    with pytest.raises(RankWeaveNotAvailable) as error:
        client.fuse_rankings(
            {"temporal": ["post-1"], "lexical": ["post-1"]},
            {"post-1": "Public post"},
        )
    assert "rankweave_not_available" in str(error.value)
    assert "duplicate identifiers" not in str(error.value)


def test_injected_transport_returns_accepted_hits() -> None:
    def fake_transport(
        _channels: dict[str, list[str]],
        _weights: dict[str, float],
    ) -> list[dict]:
        return [{"item_id": "post-2"}, {"item_id": "post-1"}]

    payload = RankWeaveClient(transport=fake_transport).as_api_payload(
        [PUBLIC, QUOTE],
        can_see_post=lambda _row: True,
    )

    assert payload["status"] == "accepted"
    assert payload["status_reason"] is None
    assert payload["rankings"] == [
        {
            "post_id": "post-2",
            "post_title": "Pricing renegotiation: revised quote sent",
            "fused_rank": 1,
            "channel_evidence": [],
        },
        {
            "post_id": "post-1",
            "post_title": "Public post",
            "fused_rank": 2,
            "channel_evidence": [],
        },
    ]
    serialized = json.dumps(payload)
    assert "theta" not in serialized
    assert "fused_score" not in serialized


def test_library_transport_uses_classic_rrf_without_convex_weights() -> None:
    payload = build_rankweave_client().as_api_payload(
        [PUBLIC, QUOTE],
        can_see_post=lambda _row: True,
    )

    assert payload["status"] == "accepted"
    assert payload["rankings"][0]["channel_evidence"] == _lexical_then_temporal(
        "post-2", 1
    )


def test_explicit_empty_weight_vector_fails_before_transport() -> None:
    def transport(*_args: object) -> object:
        pytest.fail("invalid explicit weights must not cross the transport boundary")

    with pytest.raises(RankWeaveNotAvailable, match="rankweave_not_available"):
        RankWeaveClient(transport=transport).fuse_rankings(
            {"temporal": ["post-1"], "lexical": ["post-1"]},
            {"post-1": "Public post"},
            weights={},
        )


def test_library_transport_projects_monkeypatched_rrf(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    class FakeRw:
        @staticmethod
        def reciprocal_rank_fuse(
            channels: dict[str, list[str]],
            limit: int = 20,
            rank_constant_eta: int = 60,
        ) -> list:
            captured["calls"] = int(captured.get("calls", 0)) + 1
            captured["channels"] = channels
            captured["limit"] = limit
            captured["eta"] = rank_constant_eta
            return [
                SimpleNamespace(
                    item_id="post-2",
                    fused_score=0.99,
                    theta=1.2,
                    channel_contributions=(
                        SimpleNamespace(
                            channel_name="lexical",
                            rank=1,
                            weight=1.0,
                            contribution=1.0 / 61,
                        ),
                        SimpleNamespace(
                            channel_name="temporal",
                            rank=1,
                            weight=1.0,
                            contribution=1.0 / 61,
                        ),
                    ),
                ),
                SimpleNamespace(
                    item_id="post-1",
                    channel_contributions=(
                        SimpleNamespace(
                            channel_name="lexical",
                            rank=2,
                            weight=1.0,
                            contribution=1.0 / 62,
                        ),
                        SimpleNamespace(
                            channel_name="temporal",
                            rank=2,
                            weight=1.0,
                            contribution=1.0 / 62,
                        ),
                    ),
                ),
            ]

    monkeypatch.setattr(
        "lineageweave.rankweave_client._import_rankweave", lambda: FakeRw
    )
    payload = RankWeaveClient(transport=LibraryRankWeaveTransport()).as_api_payload(
        [PUBLIC, QUOTE],
        can_see_post=lambda _row: True,
    )

    assert captured["eta"] == 60
    assert captured["calls"] == 1
    assert payload["rankings"][0]["post_title"] == (
        "Pricing renegotiation: revised quote sent"
    )
    assert payload["rankings"][0]["fused_rank"] == 1
    assert payload["rankings"][0]["channel_evidence"] == _lexical_then_temporal(
        "post-2", 1
    )
    serialized = json.dumps(payload)
    assert "theta" not in serialized
    assert "fused_score" not in serialized


def test_hidden_post_is_omitted_from_every_channel() -> None:
    channels = ranking_channels_from_rows(
        [PUBLIC, QUOTE, HIDDEN],
        can_see_post=lambda row: str(row["post_id"]) != "hidden-parent",
    )

    assert "hidden-parent" not in channels["temporal"]
    assert "hidden-parent" not in channels["lexical"]
    assert channels["temporal"][0] == "post-2"
    assert channels["lexical"][0] == "post-2"


def test_selected_rows_use_exact_lazy_influence_and_temporal_population(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Selected Rankings delegates exact bounded fusion and preserves evidence."""
    captured: dict[str, object] = {}

    class FakeRw:
        @staticmethod
        def lazy_reciprocal_rank_fuse(channels, resolver, **kwargs):
            captured.update(channels=channels, kwargs=kwargs)
            assert set(channels["influence"]) == set(channels["temporal"])
            assert "lexical" not in channels
            assert resolver("post-2") == (0, {"influence": 1, "temporal": 2})
            return [
                SimpleNamespace(
                    item_id="post-2",
                    channel_contributions=(
                        SimpleNamespace(
                            channel_name="influence",
                            rank=1,
                            weight=1.0,
                            contribution=1 / 61,
                        ),
                        SimpleNamespace(
                            channel_name="temporal",
                            rank=2,
                            weight=1.0,
                            contribution=1 / 62,
                        ),
                    ),
                )
            ]

    monkeypatch.setattr(
        "lineageweave.rankweave_client._import_rankweave", lambda: FakeRw
    )
    rows = [
        {
            "post_id": "post-2", "post_title": "Older influence",
            "event_time": "2026-01-01T00:00:00Z", "influence_value": 4.0,
            "uncertainty_method_code": "bootstrap", "uncertainty_lower_value": 3.0,
            "uncertainty_upper_value": 5.0, "evidence_sha256": "a" * 64,
            "provenance_assertion_id": "assertion-2",
        },
        {
            "post_id": "post-1", "post_title": "Newer post",
            "event_time": "2026-01-02T00:00:00Z", "influence_value": 2.0,
            "uncertainty_method_code": "bootstrap", "uncertainty_lower_value": 1.0,
            "uncertainty_upper_value": 3.0, "evidence_sha256": "b" * 64,
            "provenance_assertion_id": "assertion-1",
        },
    ]

    item = RankWeaveClient().fuse_selected_rows(rows).to_json()[0]

    assert captured["kwargs"] == {"limit": 20, "rank_constant_eta": 60}
    assert item["evidence"] == {
        "influence_value": 4.0,
        "uncertainty_method_code": "bootstrap",
        "uncertainty_lower_value": 3.0,
        "uncertainty_upper_value": 5.0,
        "membership_evidence_sha256": "a" * 64,
        "provenance_assertion_id": "assertion-2",
    }


def test_lexical_channel_ranks_quote_ahead_of_generic_title() -> None:
    channels = ranking_channels_from_rows(
        [PUBLIC, QUOTE],
        can_see_post=lambda _row: True,
        query="pricing quote delivery",
    )
    assert channels["lexical"][0] == "post-2"


def test_unknown_envelope_fails_closed() -> None:
    with pytest.raises(RankWeaveNotAvailable, match="rankweave_not_available"):
        project_ranking_list({"hits": [{"item_id": "spoofed"}]}, {"spoofed": "x"})


def test_empty_transport_result_does_not_start_an_owner_calculation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "lineageweave.rankweave_client._import_rankweave",
        lambda: pytest.fail("empty projection must not call RankWeave"),
    )
    assert project_ranking_list([], {}).items == ()


def test_unknown_hit_id_is_dropped_not_repaired() -> None:
    ranking = project_ranking_list(
        [{"item_id": "invented"}, {"item_id": "post-2"}],
        {"post-2": "Pricing renegotiation: revised quote sent"},
    )
    assert [item.post_id for item in ranking.items] == ["post-2"]
    assert all(item.post_id != "invented" for item in ranking.items)
    assert ranking.items[0].fused_rank == 1
    assert ranking.items[0].channel_evidence == ()


def test_ranking_channel_evidence_uses_cormack_weighted_rrf() -> None:
    evidence = ranking_channel_evidence(
        "post-1",
        {"temporal": ["post-1"], "lexical": ["post-1"]},
        {"temporal": 0.5, "lexical": 0.5},
        eta=60,
    )
    by_code = {item.signal_code: item for item in evidence}
    assert by_code["lexical"].contribution == 0.5 / 61
    assert by_code["temporal"].contribution == 0.5 / 61
    assert by_code["lexical"].channel_rank == 1
    assert by_code["temporal"].channel_rank == 1
    assert by_code["lexical"].rank == 1
    assert by_code["temporal"].rank == 2
    assert [item.signal_code for item in evidence] == ["lexical", "temporal"]


def test_ranking_channel_evidence_skips_missing_and_zero_weight_channels() -> None:
    evidence = ranking_channel_evidence(
        "post-1",
        {"temporal": ["post-1"], "lexical": ["post-2"], "unused": ["post-1"]},
        {"temporal": 0.25, "lexical": 0.75, "unused": 0.0},
    )
    assert [item.signal_code for item in evidence] == ["temporal"]
    assert evidence[0].contribution == 0.25 / 61
    assert evidence[0].channel_rank == 1


def test_ranking_channel_evidence_tie_breaks_by_signal_code() -> None:
    evidence = ranking_channel_evidence(
        "post-1",
        {"temporal": ["post-1"], "lexical": ["post-1"]},
        {"temporal": 0.5, "lexical": 0.5},
    )
    assert [item.signal_code for item in evidence] == ["lexical", "temporal"]
    assert evidence[0].contribution == evidence[1].contribution == 0.5 / 61


def test_project_ranking_list_does_not_refuse_legacy_transport_for_evidence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "lineageweave.rankweave_client._owner_channel_evidence",
        lambda *_args, **_kwargs: pytest.fail("legacy ordering must not be re-fused"),
    )
    ranking = project_ranking_list(
        [
            {
                "item_id": "post-1",
                "theta": 1.7,
                "channel_evidence": [{"signal_code": "invented", "rank": 1}],
            }
        ],
        {"post-1": "Public post"},
        channels={"temporal": ["post-1"], "lexical": ["post-2"]},
        weights={"temporal": 0.5, "lexical": 0.5},
    )
    payload = ranking.to_json()
    assert payload[0]["channel_evidence"] == []
    serialized = json.dumps(payload)
    assert "theta" not in serialized
    assert "invented" not in serialized
