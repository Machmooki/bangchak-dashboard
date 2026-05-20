from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from app.services.xlsx_summary import DashboardDataError, SheetGrid, column_to_number, load_summary_sheet


DIVISION_ORDER = ["FCD", "CID", "LCD", "AVD", "MRD", "ASD", "LBD", "ILD"]
SUMMARY_SHEET_NAME = "Summary (Re-cal)"
FALLBACK_SUMMARY_SHEET_NAME = "Summary"
SHEET7_NAME = "Sheet7"


def _number(value: Any) -> float:
    if value in (None, ""):
        return 0.0
    if isinstance(value, bool):
        return float(int(value))
    if isinstance(value, (int, float)):
        return float(value)

    text = str(value).strip().replace(",", "")
    if text.endswith("%"):
        try:
            return float(text[:-1]) / 100
        except ValueError:
            return 0.0
    try:
        return float(text)
    except ValueError:
        return 0.0


def _int(value: Any) -> int:
    return int(round(_number(value)))


def _ratio(part: Any, total: Any) -> float:
    denominator = _number(total)
    if denominator <= 0:
        return 0.0
    return _number(part) / denominator


def _text(value: Any, fallback: str = "") -> str:
    if value in (None, ""):
        return fallback
    return str(value).strip()


def _sum(items: list[dict[str, Any]], key: str) -> int:
    return sum(_int(item.get(key)) for item in items)


class DashboardService:
    def __init__(self, excel_path: Path) -> None:
        self.excel_path = excel_path.resolve()

    def load_snapshot(self) -> dict[str, Any]:
        try:
            summary = load_summary_sheet(self.excel_path, sheet_name=SUMMARY_SHEET_NAME)
            summary_sheet_name = SUMMARY_SHEET_NAME
        except DashboardDataError:
            summary = load_summary_sheet(self.excel_path, sheet_name=FALLBACK_SUMMARY_SHEET_NAME)
            summary_sheet_name = FALLBACK_SUMMARY_SHEET_NAME

        try:
            sheet7 = load_summary_sheet(self.excel_path, sheet_name=SHEET7_NAME)
        except DashboardDataError:
            sheet7 = None

        built = self._build_dashboard_payload(summary, sheet7)
        stats = self.excel_path.stat()
        return {
            "meta": {
                "title": "Lead-to-Prospect Dashboard",
                "sheet": summary_sheet_name,
                "source_file": self.excel_path.name,
                "source_path": str(self.excel_path),
                "file_modified_at": datetime.fromtimestamp(stats.st_mtime).isoformat(),
                "refreshed_at": datetime.now().isoformat(),
            },
            "data": built,
        }

    def _build_dashboard_payload(self, summary: SheetGrid, sheet7: SheetGrid | None) -> dict[str, Any]:
        uses_recal_layout = self._is_recal_summary(summary)
        if uses_recal_layout:
            summary_row = self._record(summary, header_row=3, value_row=4)
            flow_row = self._record(summary, header_row=5, value_row=6)
            reconnect_row = self._record(summary, header_row=7, value_row=8)
            closed_row = self._record(summary, header_row=9, value_row=10)
            product_row = self._record(summary, header_row=13, value_row=14)
        else:
            summary_row = summary.pair(10, 11)
            flow_row = {}
            reconnect_row = summary.pair(13, 14)
            closed_row = summary.pair(15, 16)
            product_row = summary.pair(18, 19)

        if sheet7 is not None:
            division_status_rows = self._table(sheet7, header_row=2, start_row=3, end_row=10)
            division_proceeded_rows = self._table(sheet7, header_row=13, start_row=14, end_row=21)
            bu_status_rows = self._table(sheet7, header_row=25, start_row=26, end_row=28)
            bu_proceeded_rows = self._table(sheet7, header_row=30, start_row=31, end_row=33)

            business_units = self._build_business_units(bu_status_rows, bu_proceeded_rows)
            divisions = self._build_divisions(division_status_rows, division_proceeded_rows)
        elif uses_recal_layout:
            business_units = self._build_business_units_from_status(
                self._table(summary, header_row=17, start_row=18, end_row=20)
            )
            divisions = self._build_divisions_from_status(
                self._table(summary, header_row=24, start_row=25, end_row=32)
            )
        else:
            raise DashboardDataError("Sheet7 is required for the legacy Summary layout.")

        total_leads = _int(summary_row.get("Total Leads"))

        business_total = {
            "name": "TOTAL",
            "total_leads": _sum(business_units, "total_leads"),
            "processed": _sum(business_units, "processed"),
            "not_processed": _sum(business_units, "not_processed"),
            "not_called": _sum(business_units, "not_called"),
            "connected": _sum(business_units, "connected"),
            "reconnect": _sum(business_units, "reconnect"),
            "unable_to_find_contact_number": _sum(business_units, "unable_to_find_contact_number"),
            "closed_business": _sum(business_units, "closed_business"),
        }

        processed = _int(summary_row.get("Processed")) or business_total["processed"]
        not_processed = business_total["not_processed"] or _int(summary_row.get("Not Processed"))
        not_called = _int(flow_row.get("Not Called")) or business_total["not_called"] or not_processed
        connected = _int(flow_row.get("Called (Connected)")) or business_total["connected"] or _int(
            summary_row.get("Called (Connected)")
        )
        reconnect = _int(flow_row.get("Reconnect")) or business_total["reconnect"] or _int(summary_row.get("Reconnect"))
        closed_summary_total = _int(closed_row.get("Closed"))
        unable_to_find = _int(closed_row.get("Unable To Find Contact Number")) or business_total[
            "unable_to_find_contact_number"
        ]
        closed_business = _int(closed_row.get("Business Closed")) or business_total["closed_business"]
        closed_total = _int(flow_row.get("Closed")) or closed_summary_total or (unable_to_find + closed_business)

        products = [
            {
                "key": "fleet_card",
                "label": "Fleet Card",
                "value": _int(product_row.get("Fleet Card")),
                "tone": "fleet",
            },
            {
                "key": "clean_oil",
                "label": "Clean Oil (Bulk)",
                "source_label": "Clean Oil (Bulk)",
                "value": _int(product_row.get("Clean Oil (Bulk)")),
                "tone": "bulk",
            },
            {
                "key": "lube",
                "label": "Lube",
                "value": _int(product_row.get("Lube")),
                "tone": "lube",
            },
            {
                "key": "marine",
                "label": "Asphalt/Aviation/Marine",
                "source_label": "Asphalt/Aviation/Marine",
                "value": _int(product_row.get("Asphalt/Aviation/Marine")),
                "tone": "marine",
            },
        ]

        details = {
            "connected": {
                "title": "Detail Called (Connected): PRODUCT OPPORTUNITY ANALYSIS",
                "items": products,
            },
            "reconnect": {
                "title": "Detail Called (Reconnect):",
                "items": [
                    {
                        "key": "contact_number_unreachable",
                        "label": "Contact Number Unreachable",
                        "value": _int(reconnect_row.get("Contact Number Unreachable")),
                        "tone": "yellow",
                    },
                    {
                        "key": "unable_to_reach_coordinator",
                        "label": "Unable To Reach The Coordinator",
                        "value": _int(reconnect_row.get("Unable To Reach The Coordinator")),
                        "tone": "blue",
                    },
                    {
                        "key": "customer_not_interested",
                        "label": "Customer Not Interested",
                        "value": _int(reconnect_row.get("Customer Not Interested")),
                        "tone": "orange",
                    },
                ],
            },
            "not_called": {
                "title": "Detail Not Called:",
                "items": [
                    {
                        "key": "not_processed",
                        "label": "Not Processed",
                        "value": not_called,
                        "tone": "green",
                    }
                ],
            },
            "business_closed": {
                "title": "Detail Closed:",
                "items": [
                    {
                        "key": "unable_to_find_contact_number",
                        "label": "Unable To Find Contact Number",
                        "value": unable_to_find,
                        "tone": "orange",
                    },
                    {
                        "key": "business_closed",
                        "label": "Business Closed",
                        "value": closed_business,
                        "tone": "blue",
                    },
                ],
            },
        }

        lead_flow = [
            {"key": "connected", "label": "Called (Connected)", "value": connected, "tone": "positive"},
            {"key": "reconnect", "label": "Called (Reconnect)", "value": reconnect, "tone": "reconnect"},
            {"key": "not_called", "label": "Not Called", "value": not_called, "tone": "warning"},
            {"key": "business_closed", "label": "Closed", "value": closed_total, "tone": "closed"},
        ]

        return {
            "overview": {
                "headline_cards": [
                    {"label": "Total Leads", "value": total_leads},
                    {"label": "Processed", "value": processed, "subvalue": _ratio(processed, total_leads), "kind": "percent"},
                    {"label": "Not Processed", "value": not_processed, "subvalue": _ratio(not_processed, total_leads), "kind": "percent"},
                    {"label": "Called (Connected)", "value": connected},
                    {"label": "Called (Reconnect)", "value": reconnect},
                    {"label": "Not Called", "value": not_called},
                    {"label": "Closed", "value": closed_total},
                ],
                "lead_flow_root": {"label": "Total Leads", "value": total_leads},
                "lead_flow": lead_flow,
                "status_breakdown": [{"label": item["label"], "value": item["value"]} for item in lead_flow],
                "quality_flags": [],
            },
            "summary": {
                "total_leads": total_leads,
                "processed": processed,
                "not_processed": _int(summary_row.get("Not Processed")) or not_processed,
                "processed_rate": _ratio(processed, total_leads),
                "not_processed_rate": _ratio(_int(summary_row.get("Not Processed")) or not_processed, total_leads),
            },
            "details": details,
            "business_units": {"items": business_units, "total": business_total},
            "divisions": divisions,
            "products": {
                "coverage": [
                    {"product": item["label"], "has_data_count": item["value"], "share_of_total": _ratio(item["value"], total_leads)}
                    for item in products
                ],
                "coverage_total": {"label": "TOTAL OPPORTUNITIES", "value": sum(item["value"] for item in products)},
                "by_sub_team": [
                    {
                        "sub_team": "TOTAL",
                        "fleet_card": products[0]["value"],
                        "clean_oil": products[1]["value"],
                        "lube": products[2]["value"],
                        "asphalt_marine": products[3]["value"],
                        "total_opportunities": sum(item["value"] for item in products),
                    }
                ],
            },
            "analysis": self._build_analysis(
                total_leads=total_leads,
                processed=processed,
                not_processed=not_processed,
                divisions=divisions,
                products=products,
            ),
        }

    def _is_recal_summary(self, grid: SheetGrid) -> bool:
        row = grid.rows.get(3, {})
        return row.get("A") == "Total Leads" and row.get("B") == "Processed"

    def _record(self, grid: SheetGrid, *, header_row: int, value_row: int) -> dict[str, Any]:
        headers = grid.rows.get(header_row, {})
        values = grid.rows.get(value_row, {})
        record: dict[str, Any] = {}
        for column in sorted(headers, key=column_to_number):
            header = headers.get(column)
            if header in (None, ""):
                continue
            record[str(header)] = values.get(column)
        return record

    def _table(self, grid: SheetGrid, *, header_row: int, start_row: int, end_row: int) -> list[dict[str, Any]]:
        headers = grid.rows.get(header_row, {})
        columns = [
            column
            for column in sorted(headers, key=column_to_number)
            if headers.get(column) not in (None, "")
        ]
        if not columns:
            raise DashboardDataError(f"Header row {header_row} is empty.")

        records: list[dict[str, Any]] = []
        for row_number in range(start_row, end_row + 1):
            row = grid.rows.get(row_number, {})
            if not row:
                continue
            if not any(row.get(column) not in (None, "") for column in columns):
                continue
            records.append({str(headers[column]): row.get(column) for column in columns})
        return records

    def _build_business_units_from_status(self, status_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        for row in status_rows:
            name = _text(row.get("BU"), "Unknown")
            total = _int(row.get("Total Leads"))
            not_called = _int(row.get("Not Processed"))
            not_processed = not_called
            processed = max(total - not_processed, 0)
            connected = _int(row.get("Called (Connected)"))
            reconnect = _int(row.get("Reconnect"))
            unable = _int(row.get("Unable To Find Contact Number"))
            closed = _int(row.get("Business closed"))
            items.append(
                {
                    "name": name,
                    "total_leads": total,
                    "processed": processed,
                    "not_processed": not_processed,
                    "connected": connected,
                    "reconnect": reconnect,
                    "no_answer": reconnect,
                    "not_called": not_called,
                    "unable_to_find_contact_number": unable,
                    "closed_business": closed,
                    "process_rate": _ratio(processed, total),
                    "connect_rate": _ratio(connected, processed),
                }
            )
        return items

    def _build_divisions_from_status(self, status_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        rows_by_division = {_text(row.get("DIVISION")): row for row in status_rows}
        divisions: list[dict[str, Any]] = []

        for division_name in DIVISION_ORDER:
            row = rows_by_division.get(division_name)
            if row is None:
                continue
            total = _int(row.get("Total Leads"))
            not_called = _int(row.get("Not Processed"))
            not_processed = not_called
            processed = max(total - not_processed, 0)
            connected = _int(row.get("Called (Connected)"))
            reconnect = _int(row.get("Reconnect"))
            unable = _int(row.get("Unable To Find Contact Number"))
            closed = _int(row.get("Business closed"))
            divisions.append(
                {
                    "division": division_name,
                    "total_leads": total,
                    "processed": processed,
                    "not_processed": not_processed,
                    "connected": connected,
                    "reconnect": reconnect,
                    "no_answer": reconnect,
                    "not_called": not_called,
                    "unable_to_find_contact_number": unable,
                    "closed_business": closed,
                    "process_rate": _ratio(processed, total),
                    "connect_rate": _ratio(connected, processed),
                }
            )
        return divisions

    def _build_business_units(
        self,
        status_rows: list[dict[str, Any]],
        proceeded_rows: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        proceeded_map = {_text(row.get("BU")): row for row in proceeded_rows}
        items: list[dict[str, Any]] = []
        for row in status_rows:
            name = _text(row.get("BU"), "Unknown")
            proceeded = proceeded_map.get(name, {})
            processed = _int(proceeded.get("Proceeded"))
            not_processed = _int(proceeded.get("Not Proceeded") or row.get("Not Processed"))
            not_called = _int(row.get("Not Processed") or not_processed)
            total = _int(row.get("Total Leads") or processed + not_processed)
            connected = _int(row.get("Called (Connected)"))
            reconnect = _int(row.get("Reconnect"))
            unable = _int(row.get("Unable To Find Contact Number"))
            closed = _int(row.get("Business closed"))
            items.append(
                {
                    "name": name,
                    "total_leads": total,
                    "processed": processed,
                    "not_processed": not_processed,
                    "connected": connected,
                    "reconnect": reconnect,
                    "no_answer": reconnect,
                    "not_called": not_called,
                    "unable_to_find_contact_number": unable,
                    "closed_business": closed,
                    "process_rate": _ratio(processed, total),
                    "connect_rate": _ratio(connected, processed),
                }
            )
        return items

    def _build_divisions(
        self,
        status_rows: list[dict[str, Any]],
        proceeded_rows: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        proceeded_map = {_text(row.get("DIVISION")): row for row in proceeded_rows}
        rows_by_division = {_text(row.get("DIVISION")): row for row in status_rows}
        divisions: list[dict[str, Any]] = []

        for division_name in DIVISION_ORDER:
            row = rows_by_division.get(division_name)
            if row is None:
                continue
            proceeded = proceeded_map.get(division_name, {})
            processed = _int(proceeded.get("Proceeded"))
            not_processed = _int(proceeded.get("Not Proceeded") or row.get("Not Processed"))
            not_called = _int(row.get("Not Processed") or not_processed)
            total = _int(row.get("Total Leads") or processed + not_processed)
            connected = _int(row.get("Called (Connected)"))
            reconnect = _int(row.get("Reconnect"))
            unable = _int(row.get("Unable To Find Contact Number"))
            closed = _int(row.get("Business closed"))
            divisions.append(
                {
                    "division": division_name,
                    "total_leads": total,
                    "processed": processed,
                    "not_processed": not_processed,
                    "connected": connected,
                    "reconnect": reconnect,
                    "no_answer": reconnect,
                    "not_called": not_called,
                    "unable_to_find_contact_number": unable,
                    "closed_business": closed,
                    "process_rate": _ratio(processed, total),
                    "connect_rate": _ratio(connected, processed),
                }
            )
        return divisions

    def _build_analysis(
        self,
        *,
        total_leads: int,
        processed: int,
        not_processed: int,
        divisions: list[dict[str, Any]],
        products: list[dict[str, Any]],
    ) -> dict[str, Any]:
        largest_backlog = max(divisions, key=lambda item: item["not_processed"]) if divisions else None
        top_connected = max(divisions, key=lambda item: item["connected"]) if divisions else None
        top_product = max(products, key=lambda item: item["value"]) if products else None
        return {
            "highlights": [
                {
                    "title": "Processed Rate",
                    "value": processed,
                    "share": _ratio(processed, total_leads),
                },
                {
                    "title": "Not Processed Backlog",
                    "value": not_processed,
                    "share": _ratio(not_processed, total_leads),
                },
                {
                    "title": "Largest Division Backlog",
                    "value": largest_backlog["division"] if largest_backlog else "-",
                    "supporting": largest_backlog["not_processed"] if largest_backlog else 0,
                },
                {
                    "title": "Top Connected Division",
                    "value": top_connected["division"] if top_connected else "-",
                    "supporting": top_connected["connected"] if top_connected else 0,
                },
                {
                    "title": "Largest Product Opportunity",
                    "value": top_product["label"] if top_product else "-",
                    "supporting": top_product["value"] if top_product else 0,
                },
            ]
        }
