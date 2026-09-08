"""Naming contract for the deterministic ontology-site builder."""

from __future__ import annotations

import ast
from pathlib import Path


SCRIPT_PATH = Path(__file__).parents[1] / "scripts" / "build_ontology_site.py"


def test_ontology_site_builder_uses_semantic_owned_identifiers() -> None:
    """Keep ontology, serialization, manifest, and CLI names specific."""
    script_source = SCRIPT_PATH.read_text(encoding="utf-8")
    syntax_tree = ast.parse(script_source)
    owned_identifiers = {
        syntax_node.id
        for syntax_node in ast.walk(syntax_tree)
        if isinstance(syntax_node, ast.Name)
    }
    owned_identifiers.update(
        syntax_node.arg
        for syntax_node in ast.walk(syntax_tree)
        if isinstance(syntax_node, ast.arg)
    )

    assert owned_identifiers.isdisjoint(
        {
            "args",
            "comment",
            "counted",
            "graph",
            "heading",
            "item",
            "key",
            "label",
            "output",
            "parser",
            "payload",
            "predicate",
            "root",
            "rows",
            "sections",
            "source",
            "subject",
            "terms",
            "value",
        }
    )
    assert {
        "command_arguments",
        "documented_ontology_subjects",
        "json_item",
        "json_key",
        "json_value",
        "literal_value",
        "manifest_payload",
        "ontology_graph",
        "ontology_resource",
        "ontology_source_path",
        "publication_output_dir",
        "relation_rows",
        "repository_root_path",
        "site_build_parser",
    } <= owned_identifiers

    owned_function_names = {
        syntax_node.name
        for syntax_node in ast.walk(syntax_tree)
        if isinstance(syntax_node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    assert {"_fragment", "_parse_args", "_sha256"}.isdisjoint(owned_function_names)
    assert {
        "_file_sha256",
        "_ontology_fragment",
        "_parse_site_build_arguments",
    } <= owned_function_names


def test_ontology_site_builder_preserves_publication_contracts() -> None:
    """Keep public URLs, CLI flags, formats, and manifest keys stable."""
    script_source = SCRIPT_PATH.read_text(encoding="utf-8")

    for contract_literal in (
        '"--repository-root"',
        '"--output-dir"',
        '"documentation_url"',
        '"generated_artifacts"',
        '"ontology_triple_count"',
        '"ontology_unique_term_count"',
        '"source_sha256"',
        'format="json-ld"',
        'format="nt"',
        'format="turtle"',
    ):
        assert contract_literal in script_source
