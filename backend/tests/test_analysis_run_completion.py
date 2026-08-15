"""Repository input guards for analysis-run completion."""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any

import pytest

from backend.app.analysis_run_ingestion import complete_analysis_run
from lineageweave.analysis_run import AnalysisRunContractError


class RejectTransactionConnection:
    """Fail if invalid completion input reaches the database boundary."""

    transaction_requested = False

    def transaction(self) -> Any:
        self.transaction_requested = True
        raise AssertionError("invalid completion must not open a transaction")


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"analysis_run_id": " "}, "analysis_run_id"),
        ({"actor_account_id": " "}, "actor_account_id"),
        ({"succeeded": 1}, "succeeded"),
        ({"completed_at": datetime(2026, 8, 15)}, "completed_at"),
    ],
)
def test_invalid_completion_fails_before_database_access(
    changes: dict[str, object], message: str
) -> None:
    values: dict[str, object] = {
        "analysis_run_id": "run-id",
        "actor_account_id": "account-id",
        "succeeded": True,
        "completed_at": datetime.fromisoformat("2026-08-15T02:00:00+00:00"),
    }
    values.update(changes)
    connection = RejectTransactionConnection()
    with pytest.raises(AnalysisRunContractError, match=message):
        asyncio.run(
            complete_analysis_run(
                connection,  # type: ignore[arg-type]
                **values,  # type: ignore[arg-type]
            )
        )
    assert connection.transaction_requested is False
