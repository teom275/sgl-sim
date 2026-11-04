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
* a physical image simulation (sgl_sim.imaging.simulate_sgl_observation)
  for one telescope and for the swarm that keeps the image sharp. It uses the
  photon budget, the SGL blur matrix, corona noise and the planet's rotation,
  and is run for three surfaces: a synthetic planet, the Earth and the Moon,
  all with the target's distance, size, insolation and rotation.

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
    compute_sgl_deployment_vector,
    generate_sky_efficiency_map,
    get_ranked_catalog,
    resolve_exoplanet,
)
from sgl_sim.imaging import sharp_imaging_requirements, simulate_sgl_observation
from sgl_sim.radiometry import EARTH_GEOMETRIC_ALBEDO, integration_time_for_snr
from sgl_sim.relativity import AU_SI, PC_SI
from sgl_sim.targets import _find_in_curated_catalog

Z_REC_AU = 650.0
ARRIVAL_YEAR = 2048
CRUISE_AU_YR = 20.0
GRID = 32
TARGET_SNR = 7.0
APERTURE_M = 1.0
SURFACES = ("planet", "earth", "moon")
OUT = Path(__file__).resolve().parents[1] / "docs" / "sim" / "targets.json"

RANK_FIELDS = (
    "name", "dist_pc", "radius_earth", "rot_period_hrs", "tidally_locked", "ra_deg", "dec_deg",
    "ecliptic_lat_deg", "ecliptic_lon_deg", "telescope_constellation", "telescope_ra_deg", "telescope_dec_deg",
    "image_diameter_km", "v_drift_m_s", "proper_motion_mas_yr",
    "snr_score", "scan_logistics_score", "ecliptic_access_score", "blur_immunity_score",
    "sgl_score", "tier", "description", "radius_measured", "confirmed", "insolation_earth",
)
DEPLOY_FIELDS = (
    "x_au", "y_au", "z_au", "ecliptic_inclination_deg", "light_delay_days", "light_delay_hours",
    "cruise_time_years", "image_diameter_km", "proper_motion_drift_m_s", "annual_lateral_drift_km",
    "telescope_ra_deg", "telescope_dec_deg", "telescope_constellation", "target_constellation", "hostname",
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


def imaging_profile(cand: dict) -> dict:
    """One telescope vs. the swarm that keeps a GRID x GRID image sharp, for each surface."""
    kw = dict(
        n_pixels=GRID, z_rec=Z_REC_AU * AU_SI, aperture_m=APERTURE_M,
        distance_source=cand["dist_pc"] * PC_SI, planet_radius=cand["radius_earth"] * 6.371e6,
        insolation_earth=cand.get("insolation_earth", 1.0), rot_period_hours=cand["rot_period_hrs"],
        target_snr=TARGET_SNR, geometric_albedo=EARTH_GEOMETRIC_ALBEDO,
    )
    first = simulate_sgl_observation("planet", n_telescopes=1, **kw)
    swarm_n = first["telescopes_needed"]
    out = {
        "per_pixel_s": first["per_pixel_s"],
        "scan_hours_one": first["scan_hours"],
        "max_sharp_scan_hours": first["max_sharp_scan_hours"],
        "smear_one": first["smear_factor"],
        "telescopes_needed": swarm_n,
        "sharp_possible": first["sharp_possible"],
        "min_aperture_m": first["min_aperture_m"],
        "residual_smear": sharp_imaging_requirements(first["per_pixel_s"], GRID, cand["rot_period_hrs"], APERTURE_M)["residual_smear"],
        "corona_to_blur": first["corona_rate"] / first["blur_rate"],
        "surfaces": {},
    }
    # Telescopes for a sharper 64 x 64 image (time per pixel grows as N^2).
    t64 = integration_time_for_snr(TARGET_SNR, **{k: v for k, v in kw.items()
                                                  if k not in ("rot_period_hours", "target_snr")} | {"n_pixels": 64})
    req64 = sharp_imaging_requirements(t64["per_pixel_s"], 64, cand["rot_period_hrs"], APERTURE_M)
    out["telescopes_needed_64"] = req64["telescopes_needed"]
    out["sharp_possible_64"] = req64["sharp_possible"]
    out["min_aperture_m_64"] = req64["min_aperture_m"]
    for surface in SURFACES:
        one = first if surface == "planet" else simulate_sgl_observation(surface, n_telescopes=1, **kw)
        many = simulate_sgl_observation(surface, n_telescopes=swarm_n, **kw)
        out["surfaces"][surface] = {
            "one": {"rmse": one["rmse"], "ssim": one["ssim"], "image": _encode_image(one["reconstructed"])},
            "swarm": {"rmse": many["rmse"], "ssim": many["ssim"], "scan_hours": many["scan_hours"],
                      "image": _encode_image(many["reconstructed"])},
        }
    return out


def mission_profile(rank_row: dict, cand: dict) -> dict:
    deploy = compute_sgl_deployment_vector(
        target_data=_target_record(cand), z_rec_au=Z_REC_AU,
        arrival_year=ARRIVAL_YEAR, cruise_vel_au_yr=CRUISE_AU_YR,
    )
    imaging = imaging_profile(cand)
    coal = check_mission_coalignment(CATALOG_12_CANDIDATES, cand["ra_deg"], cand["dec_deg"])
    companions = [
        {"name": m["target_name"], "separation_deg": m["separation_deg"]}
        for m in coal["matching_missions"]
        if m["target_name"] != cand["name"] and m["deflection_feasible"]
    ]
    return {
        "deployment": {k: deploy[k] for k in DEPLOY_FIELDS},
        "imaging": imaging,
        "coaligned_with": companions,
    }


def _truth(surface: str):
    """The face each surface shows at the start of the scan (as the simulator normalises it)."""
    return simulate_sgl_observation(surface, n_pixels=GRID, distance_source=10 * PC_SI,
                                    rot_period_hours=None, target_snr=TARGET_SNR)["truth"]


def build() -> dict:
    by_name = {c["name"]: c for c in CATALOG_12_CANDIDATES}
    rows = []
    for r in get_ranked_catalog(z_rec_au=Z_REC_AU):
        row = {k: r[k] for k in RANK_FIELDS}
        row["mission"] = mission_profile(r, by_name[r["name"]])
        rows.append(row)
    sky = generate_sky_efficiency_map(n_ra=72, n_dec=36)
    return _round({
        "z_rec_au": Z_REC_AU,
        "arrival_year": ARRIVAL_YEAR,
        "cruise_velocity_au_yr": CRUISE_AU_YR,
        "grid": GRID,
        "target_snr": TARGET_SNR,
        "aperture_m": APERTURE_M,
        "surfaces": {name: _encode_image(_truth(name)) for name in SURFACES},
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
