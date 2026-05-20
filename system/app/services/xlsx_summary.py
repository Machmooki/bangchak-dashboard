from __future__ import annotations

import re
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET


MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
WORKBOOK_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
CELL_RE = re.compile(r"([A-Z]+)(\d+)")


class DashboardDataError(RuntimeError):
    """Raised when the Summary sheet cannot be parsed as expected."""


def _xml_tag(namespace: str, name: str) -> str:
    return f"{{{namespace}}}{name}"


def column_to_number(column: str) -> int:
    result = 0
    for char in column:
        result = (result * 26) + (ord(char.upper()) - 64)
    return result


def coerce_scalar(value: str | None) -> Any:
    if value is None:
        return None

    text = str(value).strip()
    if not text:
        return ""

    lowered = text.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False

    try:
        number = float(text)
    except ValueError:
        return text

    if number.is_integer():
        return int(number)
    return number


@dataclass(slots=True)
class SheetGrid:
    rows: dict[int, dict[str, Any]]

    def find_row(self, label: str) -> int:
        for row_number in sorted(self.rows):
            if self.rows[row_number].get("A") == label:
                return row_number
        raise DashboardDataError(f"Could not find row label: {label}")

    def pair(self, header_row: int, value_row: int) -> dict[str, Any]:
        headers = self.rows.get(header_row, {})
        values = self.rows.get(value_row, {})
        ordered_columns = sorted(headers, key=column_to_number)
        result: dict[str, Any] = {}
        for column in ordered_columns:
            header = headers.get(column)
            if header in (None, ""):
                continue
            result[str(header)] = values.get(column)
        return result

    def table(self, header_row: int, start_row: int, end_row: int) -> list[dict[str, Any]]:
        headers = self.rows.get(header_row, {})
        ordered_columns = [
            column
            for column in sorted(headers, key=column_to_number)
            if headers.get(column) not in (None, "")
        ]
        if not ordered_columns:
            raise DashboardDataError(f"Header row {header_row} is empty.")

        records: list[dict[str, Any]] = []
        for row_number in range(start_row, end_row + 1):
            row = self.rows.get(row_number, {})
            if not row or row.get("A") in (None, ""):
                continue
            record: dict[str, Any] = {}
            has_value = False
            for column in ordered_columns:
                header = str(headers[column])
                value = row.get(column)
                if value not in (None, ""):
                    has_value = True
                record[header] = value
            if has_value:
                records.append(record)
        return records


def _load_shared_strings(zip_file: zipfile.ZipFile) -> list[str]:
    path = "xl/sharedStrings.xml"
    if path not in zip_file.namelist():
        return []

    root = ET.fromstring(zip_file.read(path))
    shared_strings: list[str] = []
    for item in root.findall(_xml_tag(MAIN_NS, "si")):
        text = "".join(node.text or "" for node in item.iter(_xml_tag(MAIN_NS, "t")))
        shared_strings.append(text)
    return shared_strings


def _resolve_sheet_target(zip_file: zipfile.ZipFile, sheet_name: str) -> str:
    workbook = ET.fromstring(zip_file.read("xl/workbook.xml"))
    rels = ET.fromstring(zip_file.read("xl/_rels/workbook.xml.rels"))

    relation_map = {
        node.attrib["Id"]: node.attrib["Target"]
        for node in rels.findall(_xml_tag(WORKBOOK_REL_NS, "Relationship"))
    }

    sheets_node = workbook.find(_xml_tag(MAIN_NS, "sheets"))
    if sheets_node is None:
        raise DashboardDataError("Workbook does not contain any sheets.")

    for sheet in sheets_node.findall(_xml_tag(MAIN_NS, "sheet")):
        if sheet.attrib.get("name") != sheet_name:
            continue
        relation_id = sheet.attrib.get(f"{{{REL_NS}}}id")
        if not relation_id or relation_id not in relation_map:
            raise DashboardDataError(f"Missing relationship for sheet: {sheet_name}")
        return f"xl/{relation_map[relation_id]}"

    raise DashboardDataError(f"Sheet not found: {sheet_name}")


def _read_cell_value(cell: ET.Element, shared_strings: list[str]) -> Any:
    cell_type = cell.attrib.get("t")

    inline = cell.find(_xml_tag(MAIN_NS, "is"))
    if inline is not None:
        text = "".join(node.text or "" for node in inline.iter(_xml_tag(MAIN_NS, "t")))
        return coerce_scalar(text)

    value_node = cell.find(_xml_tag(MAIN_NS, "v"))
    if value_node is None:
        return None

    raw_value = value_node.text
    if cell_type == "s" and raw_value is not None:
        try:
            return coerce_scalar(shared_strings[int(raw_value)])
        except (IndexError, ValueError):
            return raw_value

    return coerce_scalar(raw_value)


def load_summary_sheet(excel_path: Path, sheet_name: str = "Summary") -> SheetGrid:
    excel_path = excel_path.resolve()
    if not excel_path.exists():
        raise FileNotFoundError(f"Excel file not found: {excel_path}")

    with zipfile.ZipFile(excel_path) as zip_file:
        shared_strings = _load_shared_strings(zip_file)
        sheet_target = _resolve_sheet_target(zip_file, sheet_name)
        root = ET.fromstring(zip_file.read(sheet_target))

    rows: dict[int, dict[str, Any]] = {}
    for cell in root.iter(_xml_tag(MAIN_NS, "c")):
        reference = cell.attrib.get("r", "")
        match = CELL_RE.match(reference)
        if not match:
            continue
        column, row_str = match.groups()
        row_number = int(row_str)
        value = _read_cell_value(cell, shared_strings)
        if value in (None, ""):
            continue
        rows.setdefault(row_number, {})[column] = value

    if not rows:
        raise DashboardDataError("Summary sheet is empty.")

    return SheetGrid(rows=rows)
