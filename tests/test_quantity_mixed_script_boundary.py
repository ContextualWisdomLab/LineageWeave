"""Regression coverage for ADR 0165 mixed-script caret exponents."""

from lineageweave.chunking import normalize_script_text


def test_mixed_script_numeric_exponents_remain_literal() -> None:
    """Do not superscript any ASCII prefix or strip braces from unsupported digits."""
    for text in ("x^123\u0664", "x^123.\u0664", "x^{\u0661}", "x^{12\u0664}"):
        assert normalize_script_text(text) == text
