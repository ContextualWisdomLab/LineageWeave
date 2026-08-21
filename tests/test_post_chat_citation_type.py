"""Citation indices must be JSON integers, never booleans."""

from lineageweave.post_chat import ChatSourceDocument, parse_chat_response


def test_post_chat_rejects_boolean_source_numbers() -> None:
    """JSON ``true`` must not alias source number one through Python's bool/int relation."""
    sources = [ChatSourceDocument("post-1", "Evidence", "source")]
    answer = parse_chat_response(
        '{"answer_text":"Grounded","cited_source_numbers":[true,1]}',
        sources,
    )
    assert answer is not None
    assert answer.cited_post_ids == ("post-1",)
