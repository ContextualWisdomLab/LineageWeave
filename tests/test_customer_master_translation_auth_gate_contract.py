"""Executable guard for Customer Master's auth-bound translation admission."""

from pathlib import Path


APP_SOURCE = Path("frontend/src/App.tsx")


def _customer_master_panel_source() -> str:
    """Return only the Customer Master component so unrelated UI cannot satisfy the contract."""
    source = APP_SOURCE.read_text(encoding="utf-8")
    start = source.index("function CustomerMasterPanel(")
    end = source.index("\nexport function AskAgentPanel(", start)
    return source[start:end]


def test_customer_master_translation_ready_is_bound_to_current_access_token() -> None:
    """Changing auth identity must invalidate translated-copy readiness before data admission."""
    panel = _customer_master_panel_source()

    assert "const [copyAccessToken, setCopyAccessToken] = useState<string | null>(null);" in panel
    assert "setCopyAccessToken(null);" in panel
    assert "setCopyAccessToken(accessToken);" in panel
    assert "copyAccessToken !== accessToken" in panel


def test_customer_master_data_effect_requires_auth_bound_copy() -> None:
    """The Customer Master request effect must fail closed on stale-token copy."""
    panel = _customer_master_panel_source()
    effect_start = panel.index('if (copyState !== "ready"')
    effect_end = panel.index("\n  useEffect(() => {", effect_start + 1)
    data_effect = panel[effect_start:effect_end]

    assert "copyLocale !== locale" in data_effect
    assert "copyAccessToken !== accessToken" in data_effect
    assert "void loadMaster();" in data_effect


def test_customer_master_render_gate_rejects_stale_token_copy() -> None:
    """Stale-token translations must not unlock the Customer Master surface."""
    panel = _customer_master_panel_source()
    render_gate_start = panel.index('if (copyState === "loading"')
    render_gate_end = panel.index("\n  return (", render_gate_start)
    render_gate = panel[render_gate_start:render_gate_end]

    assert "copyAccessToken !== accessToken" in render_gate
