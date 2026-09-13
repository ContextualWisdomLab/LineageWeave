"""Temporary bounded strengthening for Customer Master resolver input isolation."""

from pathlib import Path

path = Path("backend/tests/test_api.py")
text = path.read_text(encoding="utf-8")
old = '''            def resolve(self, hint_code: str, context_text: str) -> str | None:
                assert hint_code == "HINT-CODE-001"
                assert "own" in context_text.lower() or context_text
                return "Northridge Grid"
'''
new = '''            def resolve(self, hint_code: str, context_text: str) -> str | None:
                assert hint_code == "HINT-CODE-001"
                assert "Own-corp private post" in context_text
                assert "Other-corp private post" not in context_text
                return "Northridge Grid"
'''
if text.count(old) != 1:
    raise SystemExit(f"expected one resolver assertion anchor, found {text.count(old)}")
path.write_text(text.replace(old, new, 1), encoding="utf-8")
