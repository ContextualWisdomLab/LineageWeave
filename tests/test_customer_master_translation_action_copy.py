"""Buyer-language contract for Customer Master hint resolution copy."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_CUSTOMER_MASTER_SEED = ROOT / "migrations" / "0248_customer_master_translation_draft.sql"

_RESOLVE_ROW = (
    "    ('Resolve', '조직 식별', 'Resolve', '組織を特定', '识别组织', "
    "'Xác minh tổ chức', 'Identificar organización', 'Organisation identifizieren', "
    "'Identifier l’organisation'),"
)
_RESOLVING_ROW = (
    "    ('Resolving...', '조직 식별 중...', 'Resolving...', '組織を特定中...', "
    "'正在识别组织...', 'Đang xác minh tổ chức...', 'Identificando organización...', "
    "'Organisation wird identifiziert...', 'Identification de l’organisation en cours...'),"
)


def test_customer_master_hint_resolution_copy_names_the_action() -> None:
    """Locale copy must describe organization identification, not generic solving/finalization."""
    seed = _CUSTOMER_MASTER_SEED.read_text(encoding="utf-8")

    assert _RESOLVE_ROW in seed
    assert _RESOLVING_ROW in seed
