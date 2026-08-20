"""Run the PR #282 implementation with the exact current client import anchor."""

from __future__ import annotations

import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).with_name("implement_282_tepp_project_history.py")
SPEC = importlib.util.spec_from_file_location("implement_282", SCRIPT)
if SPEC is None or SPEC.loader is None:
    raise SystemExit("could not load implementation module")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def patch_client() -> None:
    """Align the strict client with TEPP's lower-snake-case code contract."""
    path = "lineageweave/tepp_project_history.py"
    source = MODULE.read(path)
    source = MODULE.replace_once(
        source,
        "from dataclasses import dataclass\n",
        "import re\n\nfrom dataclasses import dataclass\n",
        label="client regex import",
    )
    anchor = "_MAX_IDENTITY_TEXT = 256\n"
    source = MODULE.replace_once(
        source,
        anchor,
        anchor + "_CODE_PATTERN = re.compile(r\"^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$\")\n",
        label="client code pattern",
    )
    helper_anchor = "def _parse_utc_timestamp(value: Any, *, name: str) -> datetime:\n"
    helper = '''def _require_code(value: Any, *, name: str, maximum: int = 128) -> str:\n    """Return one closed lower-snake-case code."""\n    code = _require_text(value, name=name, maximum=maximum)\n    if _CODE_PATTERN.fullmatch(code) is None:\n        raise TeppProjectHistoryUnavailable(f"{name} must be lower snake_case")\n    return code\n\n\n'''
    if helper not in source:
        source = MODULE.replace_once(
            source,
            helper_anchor,
            helper + helper_anchor,
            label="client code validator",
        )
    source = source.replace(
        '''"event_type_code": _require_text(\n                self.event_type_code, name="event_type_code", maximum=96\n            ),''',
        '''"event_type_code": _require_code(\n                self.event_type_code, name="event_type_code", maximum=96\n            ),''',
    )
    source = source.replace(
        '''"availability_basis": _require_text(\n                self.availability_basis, name="availability_basis", maximum=128\n            ),''',
        '''"availability_basis": _require_code(\n                self.availability_basis, name="availability_basis", maximum=128\n            ),''',
    )
    source = source.replace(
        '''event_type_code=_require_text(\n                payload.get("event_type_code"), name="event_type_code", maximum=96\n            ),''',
        '''event_type_code=_require_code(\n                payload.get("event_type_code"), name="event_type_code", maximum=96\n            ),''',
    )
    source = source.replace(
        '''availability_basis=_require_text(\n                payload.get("availability_basis"), name="availability_basis", maximum=128\n            ),''',
        '''availability_basis=_require_code(\n                payload.get("availability_basis"), name="availability_basis", maximum=128\n            ),''',
    )
    MODULE.write(path, source)


MODULE.patch_client = patch_client
MODULE.main()
