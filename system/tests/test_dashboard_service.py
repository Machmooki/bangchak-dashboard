from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SYSTEM_DIR = PROJECT_ROOT / "system"
if str(SYSTEM_DIR) not in sys.path:
    sys.path.insert(0, str(SYSTEM_DIR))

from app.services.dashboard_service import DashboardService


class DashboardServiceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.service = DashboardService(PROJECT_ROOT / "excel" / "00_Prospecting assign lot1_as of 17 Apr.xlsx")

    def test_snapshot_uses_final_recal_summary(self) -> None:
        snapshot = self.service.load_snapshot()
        data = snapshot["data"]

        self.assertEqual(snapshot["meta"]["sheet"], "Summary (Re-cal)")
        self.assertEqual(data["summary"]["total_leads"], 8039)
        self.assertEqual(data["summary"]["processed"], 2776)
        self.assertEqual(data["summary"]["not_processed"], 5263)
        self.assertEqual(data["overview"]["lead_flow"][0]["value"], 378)
        self.assertEqual(data["overview"]["lead_flow"][1]["value"], 1154)
        self.assertEqual(data["overview"]["lead_flow"][2]["value"], 5263)
        self.assertEqual(data["overview"]["lead_flow"][3]["value"], 1244)

    def test_detail_cards_are_driven_by_excel(self) -> None:
        data = self.service.load_snapshot()["data"]

        connected = data["details"]["connected"]["items"]
        reconnect = data["details"]["reconnect"]["items"]
        not_called = data["details"]["not_called"]["items"]
        closed = data["details"]["business_closed"]["items"]

        self.assertEqual(connected[0]["label"], "Fleet Card")
        self.assertEqual(connected[0]["value"], 372)
        self.assertEqual(reconnect[0]["value"], 1054)
        self.assertEqual(reconnect[1]["value"], 9)
        self.assertEqual(reconnect[2]["value"], 91)
        self.assertEqual(not_called[0]["value"], 5263)
        self.assertEqual(len(not_called), 1)
        self.assertEqual(closed[0]["value"], 1237)
        self.assertEqual(closed[1]["value"], 7)

    def test_division_performance_comes_from_sheet7(self) -> None:
        divisions = self.service.load_snapshot()["data"]["divisions"]
        first = divisions[0]

        self.assertEqual(len(divisions), 8)
        self.assertEqual(first["division"], "FCD")
        self.assertEqual(first["total_leads"], 1133)
        self.assertEqual(first["connected"], 151)
        self.assertEqual(first["reconnect"], 312)
        self.assertEqual(first["unable_to_find_contact_number"], 381)
        self.assertEqual(first["not_processed"], 306)
        self.assertEqual(first["not_called"], 286)


if __name__ == "__main__":
    unittest.main()
