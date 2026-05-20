from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RuntimeLayout:
    app_home: Path
    project_root: Path
    system_dir: Path
    static_dir: Path
    excel_dir: Path


def resolve_project_root(app_home: Path) -> Path:
    candidates = []
    env_home = os.environ.get("DASHBOARD_HOME")
    if env_home:
        candidates.append(Path(env_home).expanduser())
    candidates.extend([app_home, app_home.parent])

    seen: set[str] = set()
    for candidate in candidates:
        resolved = candidate.resolve()
        key = str(resolved)
        if key in seen:
            continue
        seen.add(key)
        if (resolved / "excel").exists():
            return resolved

    return candidates[0].resolve() if candidates else app_home.resolve()


def resolve_runtime_layout() -> RuntimeLayout:
    if getattr(sys, "frozen", False):
        app_home = Path(sys.executable).resolve().parent
        system_dir = Path(getattr(sys, "_MEIPASS", app_home))
    else:
        system_dir = Path(__file__).resolve().parents[1]
        app_home = system_dir

    project_root = resolve_project_root(app_home)
    return RuntimeLayout(
        app_home=app_home,
        project_root=project_root,
        system_dir=system_dir,
        static_dir=system_dir / "app" / "static",
        excel_dir=project_root / "excel",
    )
