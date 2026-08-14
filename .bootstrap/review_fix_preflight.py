from pathlib import Path


def add_dedent_four(source_path: str, replacements: dict[str, str]) -> None:
    path = Path(source_path)
    text = path.read_text()
    import_anchor = "from textwrap import dedent\n"
    helper = (
        "from textwrap import dedent, indent\n\n\n"
        "def dedent_four(value: str) -> str:\n"
        "    return indent(dedent(value), '    ')\n"
    )
    if text.count(import_anchor) != 1:
        raise SystemExit(f"{source_path}: textwrap import anchor is missing")
    text = text.replace(import_anchor, helper, 1)
    for old, new in replacements.items():
        if text.count(old) != 1:
            raise SystemExit(f"{source_path}: expected one anchor: {old!r}")
        text = text.replace(old, new, 1)
    path.write_text(text)


add_dedent_four(
    ".bootstrap/review_fix_core.py",
    {
        "replacement = dedent(\n    '''\n            resolved_names": (
            "replacement = dedent_four(\n    '''\n            resolved_names"
        ),
        "replacement = dedent(\n    '''\n        context_text": (
            "replacement = dedent_four(\n    '''\n        context_text"
        ),
    },
)

add_dedent_four(
    ".bootstrap/review_fix_support.py",
    {
        "old = dedent(\n    '''\n        if relation_kind": (
            "old = dedent_four(\n    '''\n        if relation_kind"
        ),
        "new = dedent(\n    '''\n        if relation_kind": (
            "new = dedent_four(\n    '''\n        if relation_kind"
        ),
        "old = dedent(\n    '''\n        fields: dict[str, list[str]]": (
            "old = dedent_four(\n    '''\n        fields: dict[str, list[str]]"
        ),
        "new = dedent(\n    '''\n        fields: dict[str, list[str]]": (
            "new = dedent_four(\n    '''\n        fields: dict[str, list[str]]"
        ),
    },
)

support_path = Path(".bootstrap/review_fix_support.py")
support_text = support_path.read_text()
return_anchor = "        return old;\n    end;\n"
return_contract = (
    "        if tg_op = 'UPDATE' then\n"
    "            return new;\n"
    "        end if;\n"
    "        return old;\n"
    "    end;\n"
)
if support_text.count(return_anchor) != 1:
    raise SystemExit("support-script trigger return anchor is missing")
support_text = support_text.replace(return_anchor, return_contract, 1)

# A polymorphic trigger record cannot reference a table-specific field even
# when the other side of an AND is false. JSON extraction keeps the shared
# trigger fail-closed without touching a field absent from the current table.
for old, new, expected in (
    (
        "old.resource_id",
        "(to_jsonb(old)->>'resource_id')::uuid",
        2,
    ),
    (
        "old.literal_id",
        "(to_jsonb(old)->>'literal_id')::uuid",
        1,
    ),
):
    if support_text.count(old) != expected:
        raise SystemExit(f"support-script expected {expected} occurrences of {old}")
    support_text = support_text.replace(old, new)

# The added regressions use helpers already imported by their target modules.
support_text = support_text.replace(
    "parsed = image_content._parse_description(",
    "parsed = _parse_description(",
    1,
)
support_text = support_text.replace(
    "graph = _load_graph()",
    "graph = load_ontology()",
    1,
)
support_path.write_text(support_text)
