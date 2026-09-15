"""Executable translation contract for comparison-graphic tick accessibility copy."""

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
I18N_SOURCE = ROOT / "frontend" / "src" / "i18n.ts"

TEMPLATES = {
    "leftover map comparison graphic leftover-map axis {axis} tick {value}": ("axis", "value"),
    "leftover map comparison graphic leftover-map axis {axis} tick {value} {share}%": ("axis", "value", "share"),
    "leftover map comparison graphic leftover-map axis {axis} tick {value} σ {singular}": ("axis", "value", "singular"),
    "leftover map comparison graphic leftover-map axis {axis} tick {value} σ {singular} {share}%": ("axis", "value", "singular", "share"),
    "leftover map comparison graphic leftover-map axis {axis} origin tick {value}": ("axis", "value"),
    "leftover map comparison graphic leftover-map axis {axis} origin tick {value} {share}%": ("axis", "value", "share"),
    "leftover map comparison graphic leftover-map axis {axis} origin tick {value} σ {singular}": ("axis", "value", "singular"),
    "leftover map comparison graphic leftover-map axis {axis} origin tick {value} σ {singular} {share}%": ("axis", "value", "singular", "share"),
}


def test_comparison_tick_accessibility_templates_are_translated_for_each_catalog_locale() -> None:
    """Every non-English catalog must translate every tick template without dropping placeholders."""
    source = I18N_SOURCE.read_text(encoding="utf-8")

    for template, placeholders in TEMPLATES.items():
        entries = re.findall(
            rf'{re.escape(chr(34) + template + chr(34))}\s*:\s*"([^"]*)"',
            source,
        )
        assert len(entries) == 4, f"expected ko/zh/ja/vi translations for {template!r}"
        for translated in entries:
            for placeholder in placeholders:
                assert f"{{{placeholder}}}" in translated, (
                    f"translation for {template!r} dropped {{{placeholder}}}: {translated!r}"
                )
