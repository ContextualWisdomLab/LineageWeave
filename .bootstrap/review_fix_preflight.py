from pathlib import Path

path = Path(".bootstrap/review_fix_support.py")
text = path.read_text()
import_anchor = "from textwrap import dedent\n"
helper = (
    "from textwrap import dedent, indent\n\n\n"
    "def dedent_four(value: str) -> str:\n"
    "    return indent(dedent(value), '    ')\n"
)
if text.count(import_anchor) != 1:
    raise SystemExit("support-script textwrap import anchor is missing")
text = text.replace(import_anchor, helper, 1)
replacements = {
    "old = dedent(\n    '''\n        if relation_kind": "old = dedent_four(\n    '''\n        if relation_kind",
    "new = dedent(\n    '''\n        if relation_kind": "new = dedent_four(\n    '''\n        if relation_kind",
    "old = dedent(\n    '''\n        fields: dict[str, list[str]]": "old = dedent_four(\n    '''\n        fields: dict[str, list[str]]",
    "new = dedent(\n    '''\n        fields: dict[str, list[str]]": "new = dedent_four(\n    '''\n        fields: dict[str, list[str]]",
}
for old, new in replacements.items():
    if text.count(old) != 1:
        raise SystemExit(f"expected one support-script anchor: {old!r}")
    text = text.replace(old, new, 1)
path.write_text(text)
