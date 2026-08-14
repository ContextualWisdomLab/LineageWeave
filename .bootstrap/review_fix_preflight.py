from pathlib import Path

path = Path('.bootstrap/review_fix_support.py')
text = path.read_text()
replacements = {
    "old = dedent(\n    '''\n        if relation_kind": "old = (\n    '''\n        if relation_kind",
    "new = dedent(\n    '''\n        if relation_kind": "new = (\n    '''\n        if relation_kind",
    "old = dedent(\n    '''\n        fields: dict[str, list[str]]": "old = (\n    '''\n        fields: dict[str, list[str]]",
    "new = dedent(\n    '''\n        fields: dict[str, list[str]]": "new = (\n    '''\n        fields: dict[str, list[str]]",
}
for old, new in replacements.items():
    if text.count(old) != 1:
        raise SystemExit(f'expected one support-script anchor: {old!r}')
    text = text.replace(old, new, 1)
path.write_text(text)
