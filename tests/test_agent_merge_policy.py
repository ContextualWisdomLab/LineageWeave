"""Executable guard for the repository agent merge-policy boundary."""

from pathlib import Path


_ROOT = Path(__file__).resolve().parents[1]
_AGENTS = _ROOT / "AGENTS.md"
_SECTION = "## Agent loop discipline for PRs and Issues"


def _agent_loop_section() -> str:
    text = _AGENTS.read_text(encoding="utf-8")
    _, marker, tail = text.partition(_SECTION)
    assert marker, "AGENTS.md must retain the agent loop discipline section"
    return tail


def test_agent_loop_policy_keeps_normal_merge_as_default() -> None:
    """Do not turn infrastructure failures into standing protection bypasses."""
    section = _agent_loop_section()
    assert "Normal merge is the default" in section
    assert "may bypass-merge" not in section


def test_exceptional_bypass_requires_exact_current_authority() -> None:
    """Exceptional bypass needs explicit authority scoped to the exact PR head."""
    section = _agent_loop_section().lower()
    assert "explicit current" in section
    assert "exact pr/head" in section
    assert "fail-closed" in section
