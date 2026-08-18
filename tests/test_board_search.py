"""게시판 search binds ontology / catalog terms. Never title-keyword only."""

from lineageweave.board_search import (
    SEARCH_EMPTY_NEXT_ACTION,
    classify_board_query,
    post_matches_bind,
)


def test_unbound_query_is_not_a_title_keyword_hit() -> None:
    assert classify_board_query("Invent a leftover theta") is None
    assert classify_board_query("Public post") is None


def test_catalog_person_bind_is_exact() -> None:
    bind = classify_board_query("Ada West", person_names=["Ada West"])
    assert bind is not None
    assert bind["kind"] == "person"
    assert post_matches_bind(
        bind,
        voc_type_code="voc",
        person_names=["Ada West"],
        organization_names=[],
        team_names=[],
        relationship_codes=[],
        has_keyman=True,
    )
    assert not post_matches_bind(
        bind,
        voc_type_code="voc",
        person_names=["Priya Nair"],
        organization_names=[],
        team_names=[],
        relationship_codes=[],
        has_keyman=True,
    )


def test_voc_alias_binds_the_ontology_relationship() -> None:
    bind = classify_board_query("Voice of Customer")
    assert bind is not None
    assert bind["lookup_code"] == "rel_voc"
    assert SEARCH_EMPTY_NEXT_ACTION.startswith("이 검색")
