"""Normalize and execute the temporary PR 343 repair script."""

from __future__ import annotations

import runpy
from pathlib import Path


SCRIPT_PATH = Path(__file__).with_name("repair_pr_343_contract_integrity.py")


def _replace_once(text: str, old: str, new: str, label: str) -> str:
    """Replace one temporary-script fragment or fail closed."""

    if text.count(old) != 1:
        raise SystemExit(f"refusing unknown {label} repair-script shape")
    return text.replace(old, new, 1)


def main() -> None:
    """Tighten ambiguous source anchors, then execute the reviewed repair."""

    text = SCRIPT_PATH.read_text(encoding="utf-8")

    old = '''        ''' + '"""' + '''    contract_version: str
    analysis_id: str
    analysis_scope_code: AnalysisScopeCode
''' + '"""' + ''',
        ''' + '"""' + '''    contract_version: str
    analysis_id: str
    authorization_scope_ref: str
    analysis_scope_code: AnalysisScopeCode
''' + '"""' + ''',
        label="request authorization field",
'''
    new = '''        ''' + '"""' + '''    contract_version: str
    analysis_id: str
    analysis_scope_code: AnalysisScopeCode
    knowledge_cutoff: datetime | None
    policy: LineageAnalysisPolicy
''' + '"""' + ''',
        ''' + '"""' + '''    contract_version: str
    analysis_id: str
    authorization_scope_ref: str
    analysis_scope_code: AnalysisScopeCode
    knowledge_cutoff: datetime | None
    policy: LineageAnalysisPolicy
''' + '"""' + ''',
        label="request authorization field",
'''
    text = _replace_once(text, old, new, "request dataclass")

    old = '''        ''' + '"""' + '''                "contract_version",
                "analysis_id",
                "analysis_scope_code",
''' + '"""' + ''',
        ''' + '"""' + '''                "contract_version",
                "analysis_id",
                "authorization_scope_ref",
                "analysis_scope_code",
''' + '"""' + ''',
        label="allowed authorization field",
'''
    new = '''        ''' + '"""' + '''                "contract_version",
                "analysis_id",
                "analysis_scope_code",
                "knowledge_cutoff",
''' + '"""' + ''',
        ''' + '"""' + '''                "contract_version",
                "analysis_id",
                "authorization_scope_ref",
                "analysis_scope_code",
                "knowledge_cutoff",
''' + '"""' + ''',
        label="allowed authorization field",
'''
    text = _replace_once(text, old, new, "allowed field")

    old = '''        ''' + '"""' + '''        "contract_version": request.contract_version,
        "analysis_id": request.analysis_id,
        "analysis_scope_code": request.analysis_scope_code,
''' + '"""' + ''',
        ''' + '"""' + '''        "contract_version": request.contract_version,
        "analysis_id": request.analysis_id,
        "authorization_scope_ref": request.authorization_scope_ref,
        "analysis_scope_code": request.analysis_scope_code,
''' + '"""' + ''',
        label="authorization serializer",
'''
    new = '''        ''' + '"""' + '''        "contract_version": request.contract_version,
        "analysis_id": request.analysis_id,
        "analysis_scope_code": request.analysis_scope_code,
        "knowledge_cutoff": _time_text(request.knowledge_cutoff),
        "policy": {
''' + '"""' + ''',
        ''' + '"""' + '''        "contract_version": request.contract_version,
        "analysis_id": request.analysis_id,
        "authorization_scope_ref": request.authorization_scope_ref,
        "analysis_scope_code": request.analysis_scope_code,
        "knowledge_cutoff": _time_text(request.knowledge_cutoff),
        "policy": {
''' + '"""' + ''',
        label="authorization serializer",
'''
    text = _replace_once(text, old, new, "request serializer")

    SCRIPT_PATH.write_text(text, encoding="utf-8")
    runpy.run_path(str(SCRIPT_PATH), run_name="__main__")


if __name__ == "__main__":
    main()
