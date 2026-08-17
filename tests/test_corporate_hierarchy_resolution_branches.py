"""Branch-complete edge cases for corporate entity resolution."""

from lineageweave.corporate_hierarchy_resolution import (
    RESOLUTION_MISS,
    CorporateEntityCandidate,
    score_corporate_entity,
)


def test_zero_similarity_candidate_remains_a_miss() -> None:
    """A zero score does not enter the tied-candidate set."""
    outcome = score_corporate_entity(
        "aaa",
        [CorporateEntityCandidate("bbb-id", "bbb")],
    )
    assert outcome.kind == RESOLUTION_MISS
    assert outcome.top_score == 0.0
    assert outcome.top_catalog_ids == ()


def test_zero_threshold_without_candidates_is_still_a_miss() -> None:
    """An empty candidate set cannot become a unique zero-score match."""
    outcome = score_corporate_entity(
        "Synthetic Energy",
        [],
        min_similarity=0.0,
    )
    assert outcome.kind == RESOLUTION_MISS
    assert outcome.catalog_id is None
