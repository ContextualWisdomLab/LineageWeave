"""Request-size checks for the two reader-facing chat boundaries."""

import pytest
from pydantic import ValidationError

from backend.app.main import ChatRequest, GlobalAskRequest


@pytest.mark.parametrize("request_type", [ChatRequest, GlobalAskRequest])
def test_chat_questions_are_bounded_before_retrieval_or_persistence(request_type) -> None:
    """Reject a question before it can consume retrieval, LLM, or database capacity."""
    assert len(request_type(question="x" * 4000).question) == 4000
    with pytest.raises(ValidationError):
        request_type(question="x" * 4001)
