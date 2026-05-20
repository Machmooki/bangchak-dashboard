from __future__ import annotations

import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from app.project_paths import resolve_project_root


class ProjectPathsTest(unittest.TestCase):
    def test_resolve_project_root_prefers_parent_with_excel(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source_home = root / "src"
            source_home.mkdir()
            (root / "excel").mkdir()

            previous_home = os.environ.pop("DASHBOARD_HOME", None)
            try:
                self.assertEqual(resolve_project_root(source_home), root.resolve())
            finally:
                if previous_home is not None:
                    os.environ["DASHBOARD_HOME"] = previous_home

    def test_resolve_project_root_prefers_dashboard_home_env(self) -> None:
        with TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            source_home = workspace / "src"
            source_home.mkdir()
            external_root = workspace / "shared-dashboard"
            external_root.mkdir()
            (external_root / "excel").mkdir()

            previous_home = os.environ.get("DASHBOARD_HOME")
            os.environ["DASHBOARD_HOME"] = str(external_root)
            try:
                self.assertEqual(resolve_project_root(source_home), external_root.resolve())
            finally:
                if previous_home is None:
                    os.environ.pop("DASHBOARD_HOME", None)
                else:
                    os.environ["DASHBOARD_HOME"] = previous_home
