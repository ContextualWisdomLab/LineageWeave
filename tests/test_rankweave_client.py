"""Fail-closed RankWeave ranking port.

RankWeave is an in-process weighted-RRF library. LineageWeave fuses
only visible posts. A hidden post is omitted from every channel. The
client never invents a fused score or a theta.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from lineageweave.rankweave_client import (
    LibraryRankWeaveTransport,
    RankWeaveClient,
    RankWeaveNotAvailable,
    build_rankweave_client,
    project_ranking_list,
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
        def weighted_reciprocal_rank_fuse(*_args: object, **_kwargs: object) -> list:
            raise RuntimeError("duplicate identifiers")

    monkeypatch.setattr(
        "lineageweave.rankweave_client._import_rankweave", lambda: FakeRw
    )
    client = RankWeaveClient(transport=LibraryRankWeaveTransport())
    with pytest.raises(RankWeaveNotAvailable, match="rankweave_not_available"):
        client.fuse_rankings(
            {"temporal": ["post-1"], "lexical": ["post-1"]},
            {"post-1": "Public post"},
        )


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
        },
        {
            "post_id": "post-1",
            "post_title": "Public post",
            "fused_rank": 2,
        },
    ]


def test_library_transport_projects_monkeypatched_rrf(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    class FakeRw:
        @staticmethod
        def weighted_reciprocal_rank_fuse(
            channels: dict[str, list[str]],
            weights: dict[str, float],
            limit: int = 20,
            rank_constant_eta: int = 60,
        ) -> list:
            captured["channels"] = channels
            captured["weights"] = weights
            captured["limit"] = limit
            captured["eta"] = rank_constant_eta
            return [
                SimpleNamespace(item_id="post-2"),
                SimpleNamespace(item_id="post-1"),
            ]

    monkeypatch.setattr(
        "lineageweave.rankweave_client._import_rankweave", lambda: FakeRw
    )
    payload = RankWeaveClient(transport=LibraryRankWeaveTransport()).as_api_payload(
        [PUBLIC, QUOTE],
        can_see_post=lambda _row: True,
    )

    assert captured["eta"] == 60
    assert captured["weights"]["lexical"] == 0.75
    assert payload["rankings"][0]["post_title"] == (
        "Pricing renegotiation: revised quote sent"
    )
    assert payload["rankings"][0]["fused_rank"] == 1


def test_hidden_post_is_omitted_from_every_channel() -> None:
    channels = ranking_channels_from_rows(
        [PUBLIC, QUOTE, HIDDEN],
        can_see_post=lambda row: str(row["post_id"]) != "hidden-parent",
    )

    assert "hidden-parent" not in channels["temporal"]
    assert "hidden-parent" not in channels["lexical"]
    assert channels["temporal"][0] == "post-2"
    assert channels["lexical"][0] == "post-2"


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


def test_unknown_hit_id_is_dropped_not_repaired() -> None:
    ranking = project_ranking_list(
        [{"item_id": "invented"}, {"item_id": "post-2"}],
        {"post-2": "Pricing renegotiation: revised quote sent"},
    )
    assert [item.post_id for item in ranking.items] == ["post-2"]
    assert all(item.post_id != "invented" for item in ranking.items)
    assert ranking.items[0].fused_rank == 1
