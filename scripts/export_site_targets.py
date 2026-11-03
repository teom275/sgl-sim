"""
Export the SGL mission analysis for the static web simulator.

    python scripts/export_site_targets.py

Writes docs/sim/targets.json from the sgl_sim API:

* the ranked candidate catalogue (sgl_sim.triage.get_ranked_catalog), and for
  every candidate a full mission profile:
  - deployment geometry (sgl_sim.targets.compute_sgl_deployment_vector)
  - rotational motion blur for one spacecraft vs. a swarm
    (sgl_sim.triage.compute_motion_blur)
  - other candidates reachable from the same trajectory
    (sgl_sim.triage.check_mission_coalignment)
* the all-sky efficiency map (sgl_sim.triage.generate_sky_efficiency_map).
* reference surfaces (sgl_sim.reference_bodies): every blur result is also
  computed as if the target had the Earth's or the Moon's surface, keeping
  the target's distance, rotation and noise, to give a feel for image quality.

Images are stored as base64-encoded uint8 arrays (row 0 = north) to keep the
file small.

The site has no server, so everything is precomputed here. Re-run this script
whenever the catalogue or the models change; tests/test_site_targets.py fails
if the published file is out of date.
"""

import base64
import json
from pathlib import Path

import numpy as np

from sgl_sim import (
    CATALOG_12_CANDIDATES,
    check_mission_coalignment,
    compute_motion_blur,
    compute_sgl_deployment_vector,
    generate_sky_efficiency_map,
    get_ranked_catalog,
    generate_exoplanet_map,
    reference_body_map,
    resolve_exoplanet,
)
from sgl_sim.targets import _find_in_curated_catalog

Z_REC_AU = 650.0
ARRIVAL_YEAR = 2048
CRUISE_AU_YR = 20.0
SWARM_SIZE = 8
GRID = 32
SURFACES = {
    "planet": lambda: generate_exoplanet_map(grid_size=GRID, seed=42),
    "earth": lambda: reference_body_map("earth", grid_size=GRID),
    "moon": lambda: reference_body_map("moon", grid_size=GRID),
}
OUT = Path(__file__).resolve().parents[1] / "docs" / "sim" / "targets.json"

RANK_FIELDS = (
    "name", "dist_pc", "radius_earth", "rot_period_hrs", "tidally_locked", "ra_deg", "dec_deg",
    "ecliptic_lat_deg", "ecliptic_lon_deg", "telescope_constellation", "telescope_ra_deg", "telescope_dec_deg",
    "image_diameter_km", "v_drift_m_s", "proper_motion_mas_yr",
    "snr_score", "scan_logistics_score", "ecliptic_access_score", "blur_immunity_score",
    "sgl_score", "tier", "description",
)
DEPLOY_FIELDS = (
    "x_au", "y_au", "z_au", "ecliptic_inclination_deg", "light_delay_days", "light_delay_hours",
    "cruise_time_years", "image_diameter_km", "proper_motion_drift_m_s", "annual_lateral_drift_km",
    "telescope_ra_deg", "telescope_dec_deg", "telescope_constellation", "target_constellation", "hostname",
)
BLUR_FIELDS = (
    "num_satellites", "eta_blur", "is_blurred", "scan_time_hours", "t_max_blur_hours",
    "rmse", "ssim", "total_delta_v_m_s",
)


def _encode_image(img) -> str:
    """Base64 of the image clipped to [0, 1] and quantised to uint8."""
    arr = np.clip(np.asarray(img, dtype=float), 0.0, 1.0)
    return base64.b64encode(np.round(arr * 255).astype(np.uint8).tobytes()).decode("ascii")


def _round(obj, nd=4):
    """Round floats recursively so the JSON stays small and stable."""
    if isinstance(obj, float):
        return round(obj, nd)
    if isinstance(obj, dict):
        return {k: _round(v, nd) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_round(v, nd) for v in obj]
    if hasattr(obj, "tolist"):
        return _round(obj.tolist(), nd)
    return obj


def _target_record(cand: dict) -> dict:
    """Curated catalogue entry when available (it has both proper-motion components)."""
    curated = _find_in_curated_catalog(cand["name"])
    if curated is not None:
        return curated
    return resolve_exoplanet({
        "name": cand["name"],
        "ra_deg": cand["ra_deg"],
        "dec_deg": cand["dec_deg"],
        "distance_pc": cand["dist_pc"],
        "pl_rade": cand["radius_earth"],
        # Only the total proper motion is catalogued; assign it to RA.
        "pmra_mas_yr": cand["proper_motion_mas_yr"],
        "pmdec_mas_yr": 0.0,
    })


def mission_profile(rank_row: dict, cand: dict, surfaces: dict) -> dict:
    deploy = compute_sgl_deployment_vector(
        target_data=_target_record(cand), z_rec_au=Z_REC_AU,
        arrival_year=ARRIVAL_YEAR, cruise_vel_au_yr=CRUISE_AU_YR,
    )
    blur = {}
    for key, n in (("single", 1), ("swarm", SWARM_SIZE)):
        per_surface = {}
        for surface, gt in surfaces.items():
            res = compute_motion_blur(
                image_diameter_km=rank_row["image_diameter_km"],
                grid_pixels=GRID,
                planet_rot_period_hours=cand["rot_period_hrs"],
                tidally_locked=cand["tidally_locked"],
                num_satellites=n,
                v_drift_m_s=rank_row["v_drift_m_s"],
                ground_truth=gt,
            )
            per_surface[surface] = {"rmse": res["rmse"], "ssim": res["ssim"],
                                    "image": _encode_image(res["reconstructed_image"])}
        blur[key] = {k: res[k] for k in BLUR_FIELDS if k not in ("rmse", "ssim")}
        blur[key]["surfaces"] = per_surface
    coal = check_mission_coalignment(CATALOG_12_CANDIDATES, cand["ra_deg"], cand["dec_deg"])
    companions = [
        {"name": m["target_name"], "separation_deg": m["separation_deg"]}
        for m in coal["matching_missions"]
        if m["target_name"] != cand["name"] and m["deflection_feasible"]
    ]
    return {
        "deployment": {k: deploy[k] for k in DEPLOY_FIELDS},
        "blur": blur,
        "coaligned_with": companions,
    }


def build() -> dict:
    by_name = {c["name"]: c for c in CATALOG_12_CANDIDATES}
    surfaces = {name: make() for name, make in SURFACES.items()}
    rows = []
    for r in get_ranked_catalog(z_rec_au=Z_REC_AU):
        row = {k: r[k] for k in RANK_FIELDS}
        row["mission"] = mission_profile(r, by_name[r["name"]], surfaces)
        rows.append(row)
    sky = generate_sky_efficiency_map(n_ra=72, n_dec=36)
    return _round({
        "z_rec_au": Z_REC_AU,
        "arrival_year": ARRIVAL_YEAR,
        "cruise_velocity_au_yr": CRUISE_AU_YR,
        "swarm_size": SWARM_SIZE,
        "grid": GRID,
        "surfaces": {name: _encode_image(img) for name, img in surfaces.items()},
        "targets": rows,
        "sky": {
            "ra_grid": sky["ra_grid"],
            "dec_grid": sky["dec_grid"],
            "efficiency": _round(sky["efficiency_matrix"], 3),
        },
    })


if __name__ == "__main__":
    OUT.write_text(json.dumps(build(), separators=(",", ":"), ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {OUT} ({OUT.stat().st_size / 1024:.0f} KiB)")
