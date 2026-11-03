"""The web simulator's target table must match the Python ranking."""

import json
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_site_targets_json_is_up_to_date():
    spec = importlib.util.spec_from_file_location("export_site_targets", ROOT / "scripts" / "export_site_targets.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    published = json.loads((ROOT / "docs" / "sim" / "targets.json").read_text(encoding="utf-8"))
    assert published == mod.build(), "Run: python scripts/export_site_targets.py"
