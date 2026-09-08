"""Regression coverage for ADR 0165 mixed-script caret exponents."""

from lineageweave.chunking import normalize_script_text


def test_mixed_script_numeric_exponents_remain_literal() -> None:
    """Do not superscript any ASCII prefix or strip braces from unsupported digits."""
    for text in ("x^123٤", "x^123.٤", "x^{١}", "x^{12٤}"):
        assert normalize_script_text(text) == text
