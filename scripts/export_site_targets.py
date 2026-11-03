"""
Export the ranked SGL target catalogue for the static web simulator.

    python scripts/export_site_targets.py

Writes docs/sim/targets.json from sgl_sim.triage.get_ranked_catalog. Re-run it
whenever the catalogue or the scoring changes; tests/test_site_targets.py
fails if the published file is out of date.
"""

import json
from pathlib import Path

from sgl_sim import get_ranked_catalog

Z_REC_AU = 650.0
FIELDS = (
    "name", "dist_pc", "radius_earth", "rot_period_hrs", "tidally_locked", "ra_deg", "dec_deg",
    "ecliptic_lat_deg", "telescope_constellation", "image_diameter_km", "v_drift_m_s",
    "snr_score", "scan_logistics_score", "ecliptic_access_score", "blur_immunity_score",
    "sgl_score", "tier", "description",
)
OUT = Path(__file__).resolve().parents[1] / "docs" / "sim" / "targets.json"


def build() -> dict:
    rows = [{k: r[k] for k in FIELDS} for r in get_ranked_catalog(z_rec_au=Z_REC_AU)]
    for r in rows:
        for k, v in r.items():
            if isinstance(v, float):
                r[k] = round(v, 4)
    return {"z_rec_au": Z_REC_AU, "targets": rows}


if __name__ == "__main__":
    OUT.write_text(json.dumps(build(), indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {OUT}")
