"""Replay adversaries at the real receipt/serialization repository boundary."""
import asyncio
import pytest
from backend.app.post_chat_ingestion import fetch_persisted_chat, fetch_persisted_chats
from backend.app.post_chat_replay_policy import PostChatAuthorizationScope


class _Connection:
    def __init__(self, *, sources=('focal', 'evidence'), citations=('evidence',), corporate=('corp-a',), processes=('pu-a',), limited=True, visible=None):
        self.sources = sources
        self.citations = citations
        self.corporate = corporate
        self.processes = processes
        self.limited = limited
        self.visible = sources if visible is None else visible
        self.serialized = False

    def transaction(self):
        return self

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_exc):
        return False

    async def fetchrow(self, query, *_args):
        if 'post_chat_authorization_receipt' in query:
            return self.limited if isinstance(self.limited, dict) else {'process_scope_limited': self.limited}
        self.serialized = True
        return {'question_text': 'Question', 'answer_text': 'Synthetic derived answer'}

    async def fetch(self, query, *_args):
        if 'question_norm from post_chat_result' in query:
            return [{'question_norm': 'question'}]
        if 'post_chat_corporate_entity_scope' in query:
            return [{'corporate_entity_id': value} for value in self.corporate]
        if 'post_chat_process_unit_scope' in query:
            return [{'process_unit_id': value} for value in self.processes]
        if 'from post_chat_source' in query:
            return [{'source_post_id': value} for value in self.sources]
        if 'from source_post' in query and 'for share' in query:
            return [{'post_id': value} for value in self.visible]
        return [{'cited_post_id': value, 'post_title': 'Synthetic evidence'} for value in self.citations]


def _scope():
    return PostChatAuthorizationScope.captured(corporate_entity_ids={'corp-a'}, process_unit_ids={'pu-a'})


@pytest.mark.parametrize('kwargs', [
    {'sources': ('evidence',)},
    {'sources': ('focal', 'evidence', 'evidence')},
    {'sources': ('focal', None)},
    {'sources': ('focal', '')},
    {'citations': ('foreign-uncaptured',)},
])
def test_malformed_source_receipt_rejects_derived_text_on_both_replay_paths(kwargs):
    """A focal authorization cannot repair malformed captured evidence or citations."""
    conn = _Connection(**kwargs)
    assert asyncio.run(fetch_persisted_chat(conn, 'focal', 'question', _scope())) is None
    assert asyncio.run(fetch_persisted_chats(conn, 'focal', _scope())) == []


@pytest.mark.parametrize('kwargs', [
    {'limited': True, 'processes': ()},
    {'limited': False},
    {'limited': None},
    {'limited': {}},
    {'corporate': (None,)},
    {'corporate': ('',)},
    {'visible': ('focal',)},
    {'corporate': ('corp-a', 'corp-b')},
    {'processes': ('pu-a', 'pu-b')},
])
def test_invalid_or_contracted_receipt_never_serializes_answer(kwargs):
    """Malformed policy or narrower current authorization is not safe replay evidence."""
    conn = _Connection(**kwargs)
    assert asyncio.run(fetch_persisted_chat(conn, 'focal', 'question', _scope())) is None
    assert conn.serialized is False


def test_matching_scope_and_all_sources_replay_real_serialized_answer():
    """The adversarial guard must retain a complete authorized persisted exchange."""
    conn = _Connection()
    payload = asyncio.run(fetch_persisted_chat(conn, 'focal', 'question', _scope()))
    assert payload['answer_text'] == 'Synthetic derived answer'
    assert payload['_source_post_ids'] == ['focal', 'evidence']
    assert len(asyncio.run(fetch_persisted_chats(conn, 'focal', _scope()))) == 1


@pytest.mark.parametrize(('sources', 'citations'), [
    ([], []), (["evidence"], ["evidence"]), (["focal"], ["uncaptured"]),
])
def test_persistence_rejects_invalid_capture_before_any_write(sources, citations):
    """The replay invariant is also enforced before replacement deletes stored rows."""
    from backend.app.post_chat_ingestion import persist_post_chat

    class NoWriteConnection:
        async def execute(self, *_args):
            raise AssertionError("invalid capture must not mutate storage")

    with pytest.raises(ValueError):
        asyncio.run(persist_post_chat(
            NoWriteConnection(), "focal", "question", "Synthetic answer",
            citations, _scope(), sources,
        ))
