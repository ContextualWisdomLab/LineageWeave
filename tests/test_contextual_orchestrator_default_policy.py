"""Contract tests for adaptive contextual-orchestrator consumer defaults.

These scans walk the AST of each production client. A class docstring
that mentions ``mode="auto"`` or quotes ``{"mode": "auto"}`` is not a
payload. Beginners can read this file as: "the live request body must
name auto or verify in executable code, not in the comment that
describes the client."
"""

from __future__ import annotations

import ast
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
AUTO_CLIENTS = (
    "lineageweave/post_summary.py",
    "lineageweave/post_evaluation.py",
    "lineageweave/keyman_extraction.py",
    "lineageweave/commitment_extraction.py",
    "lineageweave/entity_relationship_classification.py",
    "lineageweave/image_content.py",
)
VERIFY_CLIENTS = (
    "lineageweave/post_chat.py",
    "lineageweave/adjudication_client.py",
)
# Typed ``complete(..., mode="auto")`` forwards the name into the body.
_FORWARDED_AUTO_CLIENTS = frozenset({"lineageweave/post_evaluation.py"})
# Generic OpenAI-compat vision omits ``mode`` so unknown-field gateways
# do not 400. The orchestrator factory must pass ``mode="auto"``.
_FACTORY_AUTO_CLIENTS = frozenset({"lineageweave/image_content.py"})


def _source(relative: str) -> str:
    """Read one repository file as UTF-8 text."""

    return (ROOT / relative).read_text(encoding="utf-8")


def _dict_mode_values(source: str) -> list[ast.expr]:
    """Return every ``{"mode": ...}`` value that appears in executable code.

    Comments and docstrings are invisible to the AST, so a prose mention
    of ``mode="auto"`` or a docstring JSON fragment cannot appear here.
    """

    values: list[ast.expr] = []
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.Dict):
            continue
        for key, value in zip(node.keys, node.values, strict=False):
            if value is None or key is None:
                continue
            if isinstance(key, ast.Constant) and key.value == "mode":
                values.append(value)
    return values


def _literal_modes(source: str) -> set[str]:
    """Return string literals used as dict ``mode`` values in *source*."""

    found: set[str] = set()
    for value in _dict_mode_values(source):
        if isinstance(value, ast.Constant) and isinstance(value.value, str):
            found.add(value.value)
    return found


def _forwards_mode_name(source: str) -> bool:
    """True when a request dict sets ``"mode": mode`` (typed default)."""

    return any(isinstance(value, ast.Name) and value.id == "mode" for value in _dict_mode_values(source))


def _is_auto_constant(node: ast.expr | None) -> bool:
    """True when *node* is the string literal ``auto``."""

    return isinstance(node, ast.Constant) and node.value == "auto"


def _typed_auto_default(source: str) -> bool:
    """True when a parameter or annotated assignment defaults ``mode`` to auto."""

    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.AnnAssign):
            target = node.target
            if isinstance(target, ast.Name) and target.id == "mode" and _is_auto_constant(node.value):
                return True
            continue
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        args = node.args
        if args.defaults:
            named = args.args[-len(args.defaults) :]
            for arg, default in zip(named, args.defaults, strict=True):
                if arg.arg == "mode" and _is_auto_constant(default):
                    return True
        for arg, default in zip(args.kwonlyargs, args.kw_defaults, strict=True):
            if arg.arg == "mode" and _is_auto_constant(default):
                return True
    return False


def _call_kwarg_mode_auto(source: str) -> bool:
    """True when some call passes ``mode="auto"`` (factory / constructor)."""

    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.Call):
            continue
        for keyword in node.keywords:
            if keyword.arg != "mode":
                continue
            if isinstance(keyword.value, ast.Constant) and keyword.value.value == "auto":
                return True
    return False


def _assigns_payload_mode(source: str) -> bool:
    """True when executable code writes ``payload["mode"] = ...``."""

    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if not isinstance(target, ast.Subscript):
                continue
            if isinstance(target.slice, ast.Constant) and target.slice.value == "mode":
                return True
    return False


def _assert_auto_client(source: str, relative: str) -> None:
    """Fail unless *source* is an executable auto-mode consumer.

    Docstrings, comments, and quoted JSON fragments do not count.
    """

    modes = _literal_modes(source)
    if "route" in modes:
        raise AssertionError(f"{relative} must not send a payload-level mode=route literal")
    if relative in _FORWARDED_AUTO_CLIENTS:
        if not _forwards_mode_name(source):
            raise AssertionError(f"{relative} must forward mode into the request body")
        if not _typed_auto_default(source):
            raise AssertionError(f"{relative} must default the forwarded mode to auto")
        return
    if relative in _FACTORY_AUTO_CLIENTS:
        if not _call_kwarg_mode_auto(source):
            raise AssertionError(f"{relative} must pass mode=auto from the orchestrator factory")
        if not _assigns_payload_mode(source):
            raise AssertionError(f"{relative} must write mode onto the outbound payload")
        return
    if "auto" not in modes:
        raise AssertionError(f"{relative} must send a payload-level mode=auto literal")


def _assert_verify_client(source: str, relative: str) -> None:
    """Fail unless *source* is an executable verify-mode consumer."""

    modes = _literal_modes(source)
    if "route" in modes:
        raise AssertionError(f"{relative} must not send a payload-level mode=route literal")
    if "auto" in modes:
        raise AssertionError(f"{relative} must send verify, not a payload-level auto default")
    if "verify" not in modes:
        raise AssertionError(f"{relative} must send a payload-level mode=verify literal")


class AdaptiveOrchestratorDefaultTest(unittest.TestCase):
    """Protect production clients from regressing to forced one-model routing."""

    def test_auto_clients_request_auto_and_never_force_route(self) -> None:
        for relative in AUTO_CLIENTS:
            source = _source(relative)
            with self.subTest(path=relative):
                _assert_auto_client(source, relative)

    def test_verify_clients_keep_checked_judgment_and_never_force_route(self) -> None:
        for relative in VERIFY_CLIENTS:
            source = _source(relative)
            with self.subTest(path=relative):
                _assert_verify_client(source, relative)

    def test_docstring_mode_mention_is_not_a_payload_literal(self) -> None:
        """The same helpers used on production clients must reject prose-only mode."""

        source = (
            '"""Calls the orchestrator with mode="auto", not mode="verify".\n'
            'Also quotes {"mode": "auto"} and {"mode": "verify"} as prose.\n'
            '"""\n'
            'body = {"messages": []}\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "docstring_only_client.py"
            path.write_text(source, encoding="utf-8")
            loaded = path.read_text(encoding="utf-8")
        with self.assertRaises(AssertionError):
            _assert_auto_client(loaded, "lineageweave/docstring_only_client.py")
        with self.assertRaises(AssertionError):
            _assert_verify_client(loaded, "lineageweave/docstring_only_client.py")
        self.assertEqual(_literal_modes(loaded), set())
        self.assertIn('mode="auto"', loaded)
        self.assertIn('"mode": "auto"', loaded)

    def test_scan_accepts_an_executable_auto_payload(self) -> None:
        """A real request dict is what the auto scan is looking for."""

        _assert_auto_client(
            'body = {"messages": [], "mode": "auto"}\n',
            "lineageweave/real_auto_client.py",
        )


if __name__ == "__main__":
    unittest.main()
