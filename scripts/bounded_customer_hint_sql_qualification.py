"""Temporary bounded fix for source-customer join column qualification."""

from pathlib import Path

path = Path("backend/app/main.py")
text = path.read_text(encoding="utf-8")
old = '''                 where (nullif(btrim(source_customer_code), '') is not null
                        or nullif(btrim(source_customer_name), '') is not null)
'''
new = '''                 where (nullif(btrim(source_post.source_customer_code), '') is not null
                        or nullif(btrim(source_post.source_customer_name), '') is not null)
'''
if text.count(old) != 1:
    raise SystemExit(f"expected one source-customer WHERE anchor, found {text.count(old)}")
path.write_text(text.replace(old, new, 1), encoding="utf-8")
