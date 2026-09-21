"""Authorization regression for grouping-comparison leftover-map coverage."""

from __future__ import annotations

import pytest

from backend.app import main
from backend.app.auth import CurrentAccount


class _Acquire:
    """Return one inert connection through an async pool context."""

    async def __aenter__(self) -> object:
        return object()

    async def __aexit__(self, *_args: object) -> bool:
        return False


class _Pool:
    """Provide the minimal pool protocol used by the compare handler."""

    def acquire(self) -> _Acquire:
        return _Acquire()


def _account() -> CurrentAccount:
    """Authorize one private entity/process-unit scope and report reads."""
    return CurrentAccount(
        "account-1",
        "subject-1",
        "Analyst",
        None,
        frozenset({"entity-visible"}),
        frozenset({"unit-visible"}),
        frozenset({"post_read"}),
    )


@pytest.mark.anyio
async def test_compare_omits_full_group_coverage_when_population_is_partly_hidden(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Never disclose persisted coverage denominators computed with inaccessible members."""

    async def _fetch_period_comparison(_conn: object, _period_code: str) -> list[dict[str, object]]:
        return [
            {
                "grouping_kind": "corporate_entity",
                "grouping_key": "group-1",
                "grouping_label": "Group 1",
                "mean_theta": 0.25,
                "post_count": 2,
                "link_method": "anchor",
                "members": [
                    {
                        "visibility_code": "private",
                        "corporate_entity_id": "entity-visible",
                        "process_unit_id": "unit-visible",
                        "has_real_source_context": True,
                    },
                    {
                        "visibility_code": "private",
                        "corporate_entity_id": "entity-hidden",
                        "process_unit_id": "unit-hidden",
                        "has_real_source_context": True,
                    },
                ],
                "leftover_pairs": [],
                "leftover_map_coverage": {
                    "map_post_count": 2,
                    "scored_post_count": 2,
                    "map_item_count": 3,
                    "scored_item_count": 3,
                    "incomplete_post_count": 0,
                    "incomplete_item_count": 0,
                },
            }
        ]

    async def _has_real_source_context(_conn: object, _entity_ids: list[str]) -> bool:
        return False

    monkeypatch.setattr(main, "fetch_period_comparison", _fetch_period_comparison)
    monkeypatch.setattr(main, "has_real_source_context", _has_real_source_context)

    result = await main.compare_period_groupings("2026-W35", _account(), _Pool())

    assert len(result["groupings"]) == 1
    grouping = result["groupings"][0]
    assert grouping["post_count"] == 1
    assert grouping["leftover_map_coverage"] is None
