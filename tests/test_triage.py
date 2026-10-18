"""
Unit tests for SGL exoplanet triage classifier, sky efficiency map,
and rotational motion-blur swarm analyzer.
"""

import pytest
import numpy as np
import astropy.units as u

from sgl_sim.triage import (
    compute_motion_blur,
    score_exoplanet_candidate,
    get_ranked_catalog,
    generate_sky_efficiency_map,
    check_mission_coalignment,
    CATALOG_12_CANDIDATES,
)
from sgl_sim.web.app import app


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as test_client:
        yield test_client


def test_catalog_12_candidates_completeness():
    """Verify the 12 curated triage candidates exist with valid physical parameters."""
    assert len(CATALOG_12_CANDIDATES) == 12
    required_keys = {
        "name", "ra_deg", "dec_deg", "dist_pc", "radius_earth",
        "rot_period_hrs", "tidally_locked", "host_star_mag", "proper_motion_mas_yr"
    }
    for cand in CATALOG_12_CANDIDATES:
        assert required_keys.issubset(cand.keys())
        assert cand["dist_pc"] > 0
        assert 0 <= cand["ra_deg"] <= 360
        assert -90 <= cand["dec_deg"] <= 90


def test_score_exoplanet_candidate_ecliptic_access():
    """
    Verify ecliptic proximity scoring: targets near the ecliptic plane
    (TRAPPIST-1 e and Ross 128 b) score higher in ecliptic_access_score
    than high-inclination targets (Proxima Centauri b).
    """
    trap = score_exoplanet_candidate(
        name="TRAPPIST-1 e",
        ra_deg=346.6224,
        dec_deg=-5.0414,
        dist_pc=12.43,
        radius_earth=0.92,
        rot_period_hrs=146.4,
        tidally_locked=True,
    )
    ross = score_exoplanet_candidate(
        name="Ross 128 b",
        ra_deg=176.9350,
        dec_deg=0.8045,
        dist_pc=3.37,
        radius_earth=1.11,
        rot_period_hrs=237.6,
        tidally_locked=True,
    )
    prox = score_exoplanet_candidate(
        name="Proxima Centauri b",
        ra_deg=217.4289,
        dec_deg=-62.6795,
        dist_pc=1.301,
        radius_earth=1.03,
        rot_period_hrs=268.3,
        tidally_locked=True,
    )

    # TRAPPIST-1 e and Ross 128 b have near-zero ecliptic latitude |beta| < 5 deg
    assert abs(trap["ecliptic_lat_deg"]) < 5.0
    assert abs(ross["ecliptic_lat_deg"]) < 5.0
    assert trap["ecliptic_access_score"] > 0.95
    assert ross["ecliptic_access_score"] > 0.95

    # Proxima Centauri b is far out of the ecliptic (|beta| ~ 44.8 deg)
    assert abs(prox["ecliptic_lat_deg"]) > 40.0
    assert prox["ecliptic_access_score"] < 0.60
    assert trap["ecliptic_access_score"] > prox["ecliptic_access_score"]


def test_score_exoplanet_candidate_bounds_and_tiers():
    """Verify sub-score normalization [0, 1], composite score [0, 100], and tier logic."""
    res = score_exoplanet_candidate(
        name="Test Planet",
        ra_deg=180.0,
        dec_deg=0.0,
        dist_pc=5.0,
        radius_earth=1.0,
        rot_period_hrs=24.0,
        tidally_locked=False,
    )

    assert 0.0 <= res["snr_score"] <= 1.0
    assert 0.0 <= res["scan_logistics_score"] <= 1.0
    assert 0.0 <= res["ecliptic_access_score"] <= 1.0
    assert 0.0 <= res["blur_immunity_score"] <= 1.0
    assert 0.0 <= res["sgl_score"] <= 100.0

    assert "telescope_ra_deg" in res
    assert "telescope_dec_deg" in res
    assert "tier" in res
    assert any(res["tier"].startswith(prefix) for prefix in ["Tier 1", "Tier 2", "Tier 3", "Inviable"])


def test_ranked_catalog_ordering():
    """Verify get_ranked_catalog returns candidates sorted by sgl_score descending."""
    ranked = get_ranked_catalog(z_rec_au=650.0)
    assert len(ranked) == 12
    scores = [r["sgl_score"] for r in ranked]
    assert scores == sorted(scores, reverse=True)

    # Top candidates should have high scores (> 70)
    assert ranked[0]["sgl_score"] >= 70.0


def test_compute_motion_blur_single_vs_swarm_scaling():
    """
    Verify rotational motion blur scaling:
    On a rotating planet (P_rot = 24h) with long dwell, scaling N_sat = 1 -> 8:
    1. strictly decreases eta_blur by factor of ~8
    2. strictly reduces image reconstruction RMSE
    3. increases SSIM towards 1.0
    """
    single = compute_motion_blur(
        image_diameter_km=5.0,
        grid_pixels=32,
        planet_rot_period_hours=24.0,
        tidally_locked=False,
        num_satellites=1,
        integration_time_per_pixel_s=10.0,
    )

    swarm = compute_motion_blur(
        image_diameter_km=5.0,
        grid_pixels=32,
        planet_rot_period_hours=24.0,
        tidally_locked=False,
        num_satellites=8,
        integration_time_per_pixel_s=10.0,
    )

    # Blur smearing factor should drop by 8x
    assert pytest.approx(single["eta_blur"] / 8.0, rel=0.01) == swarm["eta_blur"]
    assert single["eta_blur"] > 1.0
    assert single["is_blurred"] is True

    # Swarm should strictly reduce RMSE and improve SSIM
    assert swarm["rmse"] < single["rmse"]
    assert swarm["ssim"] > single["ssim"]

    # Scan duration drops by 8x
    assert pytest.approx(single["scan_time_days"] / 8.0, rel=0.01) == swarm["scan_time_days"]


def test_compute_motion_blur_tidally_locked():
    """Verify tidally locked planets have minimal blur (eta_blur = 0.05)."""
    res = compute_motion_blur(
        image_diameter_km=4.0,
        grid_pixels=32,
        planet_rot_period_hours=100.0,
        tidally_locked=True,
        num_satellites=1,
    )
    assert res["eta_blur"] == 0.05
    assert res["is_blurred"] is False


def test_generate_sky_efficiency_map():
    """Verify all-sky efficiency grid dimensions, values in [0, 1], and candidate overlays."""
    grid_res = generate_sky_efficiency_map(n_ra=36, n_dec=18)
    assert grid_res["n_ra"] == 36
    assert grid_res["n_dec"] == 18

    matrix = np.array(grid_res["efficiency_matrix"])
    assert matrix.shape == (18, 36)
    assert np.all(matrix >= 0.0)
    assert np.all(matrix <= 1.0)
    assert len(grid_res["candidates"]) == 12


def test_check_mission_coalignment():
    """
    Verify co-alignment detector:
    TRAPPIST-1 d, e, f share the same host star and coordinate direction,
    so separation is 0.0 deg <= 3.0 deg.
    """
    trappist_missions = [
        {"name": "TRAPPIST-1 e", "ra_deg": 346.6224, "dec_deg": -5.0414},
        {"name": "Proxima Centauri b", "ra_deg": 217.4289, "dec_deg": -62.6795},
    ]

    # Check TRAPPIST-1 d against active missions
    res_d = check_mission_coalignment(
        active_missions=trappist_missions,
        new_target_ra=346.6224,
        new_target_dec=-5.0414,
        max_deflection_deg=3.0,
    )
    assert res_d["is_coaligned"] is True
    assert res_d["matching_missions"][0]["target_name"] == "TRAPPIST-1 e"
    assert res_d["matching_missions"][0]["separation_deg"] < 0.01

    # Check distant candidate (e.g. LHS 1140 b at RA 00h44m, Dec -15d)
    res_distant = check_mission_coalignment(
        active_missions=trappist_missions,
        new_target_ra=11.23,
        new_target_dec=-15.27,
        max_deflection_deg=3.0,
    )
    assert res_distant["is_coaligned"] is False


def test_api_ranking_endpoint(client):
    """Test GET /api/ranking endpoint."""
    res = client.get("/api/ranking?z_rec_au=650.0")
    assert res.status_code == 200
    json_data = res.get_json()
    assert json_data["status"] == "success"
    assert len(json_data["data"]) == 12
    assert "sgl_score" in json_data["data"][0]


def test_api_evaluate_candidate_endpoint(client):
    """Test POST /api/evaluate_candidate endpoint."""
    payload = {
        "name": "Discovery-X",
        "ra_deg": 346.62,
        "dec_deg": -5.04,
        "dist_pc": 12.4,
        "radius_earth": 1.1,
        "rot_period_hrs": 48.0,
        "tidally_locked": False,
        "proper_motion_mas_yr": 500.0,
        "z_rec_au": 650.0,
    }
    res = client.post("/api/evaluate_candidate", json=payload)
    assert res.status_code == 200
    json_data = res.get_json()
    assert json_data["status"] == "success"
    assert "candidate" in json_data
    assert "coalignment" in json_data
    assert json_data["candidate"]["name"] == "Discovery-X"
    # Should be coaligned with TRAPPIST-1 candidates
    assert json_data["coalignment"]["is_coaligned"] is True


def test_api_swarm_blur_sim_endpoint(client):
    """Test POST /api/swarm_blur_sim endpoint."""
    payload = {
        "image_diameter_km": 4.5,
        "grid_pixels": 16,
        "planet_rot_period_hours": 24.0,
        "tidally_locked": False,
        "num_satellites": 4,
        "integration_time_per_pixel_s": 10.0,
    }
    res = client.post("/api/swarm_blur_sim", json=payload)
    assert res.status_code == 200
    json_data = res.get_json()
    assert json_data["status"] == "success"
    assert "single" in json_data
    assert "swarm" in json_data
    assert json_data["swarm"]["num_satellites"] == 4
    assert json_data["single"]["num_satellites"] == 1
    assert json_data["swarm"]["rmse"] < json_data["single"]["rmse"]


def test_api_sky_efficiency_endpoint(client):
    """Test GET /api/sky_efficiency endpoint."""
    res = client.get("/api/sky_efficiency?n_ra=36&n_dec=18")
    assert res.status_code == 200
    json_data = res.get_json()
    assert json_data["status"] == "success"
    assert json_data["data"]["n_ra"] == 36
    assert json_data["data"]["n_dec"] == 18
    assert len(json_data["data"]["candidates"]) == 12
