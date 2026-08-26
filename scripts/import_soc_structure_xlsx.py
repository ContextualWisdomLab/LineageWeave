#!/usr/bin/env python3
"""Normalize the pinned official 2018 SOC XLSX without spreadsheet dependencies."""

from __future__ import annotations

import argparse
import csv
import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree

XML_NAMESPACE = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
LEVELS = (
    "major_group",
    "minor_group",
    "broad_occupation",
    "detailed_occupation",
)
EXPECTED_COUNTS = (23, 98, 459, 867)
CODE_PATTERN = re.compile(r"^\d{2}-\d{4}$")


def extract_rows(source: Path) -> list[tuple[str, str, str, str]]:
    """Extract code, title, source-column level, and preceding source parent."""
    namespace = {"x": XML_NAMESPACE}
    with zipfile.ZipFile(source) as workbook:
        shared_root = ElementTree.fromstring(
            workbook.read("xl/sharedStrings.xml")
        )
        strings = [
            "".join(
                node.text or ""
                for node in item.iter(f"{{{XML_NAMESPACE}}}t")
            )
            for item in shared_root.findall("x:si", namespace)
        ]
        sheet = ElementTree.fromstring(
            workbook.read("xl/worksheets/sheet1.xml")
        )

    rows: list[tuple[str, str, str, str]] = []
    ancestors: list[str | None] = [None] * len(LEVELS)
    for row in sheet.findall(".//x:sheetData/x:row", namespace):
        values: dict[str, str] = {}
        for cell in row.findall("x:c", namespace):
            value = cell.find("x:v", namespace)
            if value is None or value.text is None:
                continue
            column = re.match(r"[A-Z]+", cell.attrib["r"])
            if column is None:
                raise ValueError(f"invalid XLSX cell reference {cell.attrib['r']!r}")
            values[column.group()] = (
                strings[int(value.text)]
                if cell.attrib.get("t") == "s"
                else value.text
            )
        codes = [values.get(column) for column in "ABCD"]
        code = next((value for value in codes if value), None)
        title = values.get("E")
        if code is None or title is None or CODE_PATTERN.fullmatch(code) is None:
            continue
        level_index = codes.index(code)
        parent = ancestors[level_index - 1] if level_index else None
        if level_index and parent is None:
            raise ValueError(f"SOC row {code} has no preceding source parent")
        rows.append((code, title, LEVELS[level_index], parent or ""))
        ancestors[level_index] = code
        ancestors[level_index + 1 :] = [None] * (len(LEVELS) - level_index - 1)
    return rows


def write_normalized(source: Path, output: Path) -> None:
    """Validate the pinned release shape and atomically write normalized CSV."""
    rows = extract_rows(source)
    counts = tuple(sum(row[2] == level for row in rows) for level in LEVELS)
    if counts != EXPECTED_COUNTS or len({row[0] for row in rows}) != len(rows):
        raise ValueError(f"unexpected 2018 SOC workbook shape: {counts}")
    temporary = output.with_suffix(output.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(
            ("soc_code", "preferred_title", "classification_level", "broader_soc_code")
        )
        writer.writerows(rows)
    temporary.replace(output)


def main() -> int:
    """Normalize one official workbook from command-line paths."""
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    write_normalized(args.source, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
