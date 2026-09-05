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


def test_customer_master_auth_transition_clears_data_before_copy_can_unlock() -> None:
    """Token/locale transitions must invalidate customer data before replacement copy is fetched."""
    panel = _customer_master_panel_source()
    translation_fetch = panel.index('fetchTranslationScreen(accessToken, "customer-master", locale)')
    effect_start = panel.rfind("  useEffect(() => {", 0, translation_fetch)
    transition_prefix = panel[effect_start:translation_fetch]

    assert "setMaster(null);" in transition_prefix


def test_customer_master_fetch_completion_is_not_admitted_by_unscoped_then_setter() -> None:
    """A request started under an old auth identity must not publish after identity changes."""
    panel = _customer_master_panel_source()
    callback_start = panel.index("  const loadMaster = useCallback(() => {")
    callback_end = panel.index("\n  useEffect(() => {", callback_start)
    load_master = panel[callback_start:callback_end]

    assert ".then(setMaster)" not in load_master
    assert "masterRequestGeneration" in panel


def test_customer_master_render_gate_rejects_stale_token_copy() -> None:
    """Stale-token translations must not unlock the Customer Master surface."""
    panel = _customer_master_panel_source()
    render_gate_start = panel.index('if (copyState === "loading"')
    render_gate_end = panel.index("\n  return (", render_gate_start)
    render_gate = panel[render_gate_start:render_gate_end]

    assert "copyAccessToken !== accessToken" in render_gate


def test_customer_master_auth_transition_invalidates_secondary_authorization_projections() -> None:
    """Related data, post detail, and privileges from the old token must be discarded on transition."""
    panel = _customer_master_panel_source()
    fetch_me = panel.index("fetchMe(accessToken)")
    effect_start = panel.rfind("  useEffect(() => {", 0, fetch_me)
    effect_end = panel.index("\n  }, [accessToken]);", fetch_me)
    auth_effect = panel[effect_start:effect_end]

    for statement in (
        "setCanResolveHints(false);",
        "setRelatedByEntity({});",
        "setExpandedEntityId(null);",
        "setRelatedLoading(null);",
        "setSelectedPostId(null);",
        "setSelectedPostGraph(null);",
        "setResolvingHint(null);",
        "setResolveError(null);",
    ):
        assert statement in auth_effect


def test_customer_master_secondary_async_completions_are_bound_to_current_auth_identity() -> None:
    """Old-token async continuations must not repopulate Customer Master secondary projections."""
    panel = _customer_master_panel_source()

    assert "const currentAccessTokenRef = useRef(accessToken);" in panel
    assert "currentAccessTokenRef.current = accessToken;" in panel

    load_start = panel.index("  const loadMaster = useCallback(() => {")
    load_end = panel.index("\n  useEffect(() => {", load_start)
    load_master = panel[load_start:load_end]
    assert "requestAccessToken === currentAccessTokenRef.current" in load_master

    resolve_start = panel.index("  async function handleResolveHint(")
    resolve_end = panel.index("\n  async function toggleEntity(", resolve_start)
    resolve_hint = panel[resolve_start:resolve_end]
    assert "requestAccessToken === currentAccessTokenRef.current" in resolve_hint

    toggle_start = panel.index("  async function toggleEntity(")
    toggle_end = panel.index('\n  if (copyState === "retry")', toggle_start)
    toggle_entity = panel[toggle_start:toggle_end]
    assert "requestAccessToken === currentAccessTokenRef.current" in toggle_entity
