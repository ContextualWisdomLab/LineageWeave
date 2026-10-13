"""Synthetic seed helpers preserve explicit generation scope at every writer call."""
import ast
from pathlib import Path


def test_every_seed_chat_writer_supplies_generation_account_scope():
    """No fixture may fall back to author ownership or an omitted generation receipt."""
    tree = ast.parse(Path('scripts/seed_demo_data.py').read_text())
    calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == '_write_post_chat']
    assert len(calls) == 2
    assert all(len(call.args) == 5 for call in calls)
    seed_call = next(node for node in ast.walk(tree) if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == '_seed_fixture_chats')
    assert len(seed_call.args) == 2
    assert isinstance(seed_call.args[1], ast.Subscript)
    assert seed_call.args[1].slice.value == 'demo.analyst'


def test_api_fixture_chat_supplies_the_authenticated_generation_account():
    """The API fixture passes its authenticated reader, not the source author."""
    tree = ast.parse(Path('backend/tests/test_api.py').read_text())
    calls = [node for node in ast.walk(tree)
             if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
             and node.func.id == '_seed_fixture_chats']
    assert len(calls) == 1
    assert len(calls[0].args) == 2
    assert isinstance(calls[0].args[1], ast.Subscript)
    assert calls[0].args[1].value.id == 'seeded_db'
    assert calls[0].args[1].slice.value == 'account_id'
