"""
Unit tests for exoplanet target resolver and 3D heliocentric telemetry.
"""

import pytest
import numpy as np
import astropy.units as u

from sgl_sim.targets import (
    TOP_15_SGL_TARGETS,
    list_curated_targets,
    resolve_exoplanet,
    compute_sgl_deployment_vector,
)
from sgl_sim.web.app import app


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as test_client:
        yield test_client


def test_curated_targets_catalog():
    """Verify curated catalog has top 15 prime SGL exoplanets with complete metadata."""
    targets = list_curated_targets()
    assert len(targets) == 15
    assert len(TOP_15_SGL_TARGETS) == 15

    # Check key targets exist
    names = [t["name"] for t in targets]
    assert "Proxima Centauri b" in names
    assert "TRAPPIST-1 e" in names
    assert "TRAPPIST-1 d" in names
    assert "TRAPPIST-1 f" in names
    assert "LHS 1140 b" in names
    assert "Tau Ceti e" in names
    assert "Teegarden's Star b" in names
    assert "Ross 128 b" in names
    assert "Gliese 667 Cc" in names
    assert "Epsilon Eridani b" in names


def test_resolve_exoplanet_curated_and_aliases():
    """Verify name matching and alias resolution for curated targets."""
    # Exact name
    prox = resolve_exoplanet("Proxima Centauri b")
    assert prox["name"] == "Proxima Centauri b"
    assert prox["hostname"] == "Proxima Centauri"
    assert prox["constellation"] == "Centaurus"
    assert pytest.approx(217.4289, abs=0.01) == prox["ra_deg"]
    assert pytest.approx(-62.6795, abs=0.01) == prox["dec_deg"]
    assert pytest.approx(1.30, abs=0.05) == prox["distance_pc"]

    # Alias matching
    alias1 = resolve_exoplanet("proxima cen b")
    assert alias1["name"] == "Proxima Centauri b"

    alias2 = resolve_exoplanet("trappist-1 e")
    assert alias2["name"] == "TRAPPIST-1 e"
    assert alias2["constellation"] == "Aquarius"


def test_resolve_custom_coordinates_and_dict():
    """Verify parsing numeric string coordinates and dictionary inputs."""
    # String coordinates 'RA, Dec'
    custom = resolve_exoplanet("217.42, -62.68")
    assert pytest.approx(217.42, abs=0.01) == custom["ra_deg"]
    assert pytest.approx(-62.68, abs=0.01) == custom["dec_deg"]
    assert custom["constellation"] == "Centaurus"
    assert custom["source"] == "Custom Input"

    # Dictionary input
    dict_target = resolve_exoplanet({
        "name": "Synthetic Target",
        "ra_deg": 180.0,
        "dec_deg": 45.0,
        "distance_pc": 5.0,
    })
    assert dict_target["name"] == "Synthetic Target"
    assert dict_target["ra_deg"] == 180.0
    assert dict_target["dec_deg"] == 45.0
    assert dict_target["distance_pc"] == 5.0


def test_resolve_invalid_target_raises_value_error():
    """Verify that unresolvable targets raise ValueError with helpful message."""
    with pytest.raises(ValueError, match="Unable to resolve exoplanet"):
        resolve_exoplanet("NonExistentPlanet_XYZ99999_Unknown")


def test_compute_sgl_deployment_vector_proxima_centauri_b():
    """
    Verify core benchmarks for Proxima Centauri b:
    - Target: RA ≈ 217.42°, Dec ≈ -62.68°
    - Antipode: RA ≈ 37.42°, Dec ≈ +62.68°
    - Heliocentric Cartesian 3D vector norm equals z_rec_au
    - Light-travel time at 550 AU is ≈ 3.17 - 3.18 days
    - Constellation is Cassiopeia
    - Cruise time at 20 AU/yr is 27.5 years
    """
    prox = resolve_exoplanet("Proxima Centauri b")

    # Compute deployment vector at z_rec = 550 AU without space motion
    res = compute_sgl_deployment_vector(
        target_data=prox,
        z_rec_au=550.0,
        arrival_year=None,
        cruise_vel_au_yr=20.0,
    )

    # 1. Target RA/Dec check
    assert pytest.approx(217.42, abs=0.05) == res["target_ra_deg"]
    assert pytest.approx(-62.68, abs=0.05) == res["target_dec_deg"]
    assert res["target_constellation"] == "Centaurus"

    # 2. Celestial Antipode: RA ≈ 37.42°, Dec ≈ +62.68°
    assert pytest.approx(37.42, abs=0.05) == res["telescope_ra_deg"]
    assert pytest.approx(62.68, abs=0.05) == res["telescope_dec_deg"]
    assert res["telescope_constellation"] == "Cassiopeia"

    # 3. 3D Heliocentric Cartesian vector norm equals z_rec_au
    norm = np.sqrt(res["x_au"]**2 + res["y_au"]**2 + res["z_au"]**2)
    assert pytest.approx(550.0, rel=1e-6) == norm
    assert pytest.approx(550.0, rel=1e-6) == res["vector_norm_au"]

    # 4. Light-travel communication delay at 550 AU is ≈ 3.17 - 3.18 days
    assert pytest.approx(3.1765, rel=1e-3) == res["light_delay_days"]
    assert pytest.approx(3.17, abs=0.02) == res["light_delay_days"]
    assert pytest.approx(76.24, rel=1e-2) == res["light_delay_hours"]

    # 5. Cruise transit time at 20 AU/yr
    assert pytest.approx(27.5, rel=1e-3) == res["cruise_time_years"]

    # 6. Ecliptic inclination angle
    assert res["ecliptic_inclination_deg"] > 40.0

    # 7. Projected image cylinder diameter (Earth-sized planet at 1.30 pc)
    assert 20.0 < res["image_diameter_km"] < 35.0


def test_space_motion_propagation_to_arrival_year_2048():
    """Verify that applying proper motion propagates target coordinates to arrival year."""
    prox = resolve_exoplanet("Proxima Centauri b")

    res_j2000 = compute_sgl_deployment_vector(prox, z_rec_au=650.0, arrival_year=None)
    res_2048 = compute_sgl_deployment_vector(prox, z_rec_au=650.0, arrival_year=2048.0)

    # Coordinates should differ due to Proxima's large proper motion (~3.8 arcsec/yr)
    assert res_j2000["target_ra_deg"] != res_2048["target_ra_deg"]
    assert res_j2000["target_dec_deg"] != res_2048["target_dec_deg"]

    # Proper motion shift over 48 years: ~180 arcsec ≈ 0.05 deg
    ra_diff = abs(res_j2000["target_ra_deg"] - res_2048["target_ra_deg"])
    assert 0.02 < ra_diff < 0.20

    # Lateral drift velocity at 650 AU
    assert res_2048["proper_motion_drift_m_s"] > 10.0


def test_quantity_input_equivalence():
    """Verify that passing astropy.units.Quantity objects yields identical results to raw floats."""
    prox = resolve_exoplanet("Proxima Centauri b")

    res_float = compute_sgl_deployment_vector(prox, z_rec_au=650.0, arrival_year=2048.0)
    res_qty = compute_sgl_deployment_vector(prox, z_rec_au=650.0 * u.AU, arrival_year=2048.0)

    assert pytest.approx(res_float["vector_norm_au"], rel=1e-7) == res_qty["vector_norm_au"]
    assert pytest.approx(res_float["x_au"], rel=1e-7) == res_qty["x_au"]
    assert pytest.approx(res_float["y_au"], rel=1e-7) == res_qty["y_au"]
    assert pytest.approx(res_float["z_au"], rel=1e-7) == res_qty["z_au"]
    assert pytest.approx(res_float["light_delay_days"], rel=1e-7) == res_qty["light_delay_days"]


def test_api_targets_endpoint(client):
    """Verify GET /api/targets returns HTTP 200 with all 15 curated targets."""
    resp = client.get("/api/targets")
    assert resp.status_code == 200
    data = resp.get_json()
    assert isinstance(data, list)
    assert len(data) == 15
    assert any(t["name"] == "Proxima Centauri b" for t in data)


def test_api_target_ephemeris_endpoint(client):
    """Verify POST /api/target_ephemeris returns accurate telemetry."""
    payload = {
        "target": "Proxima Centauri b",
        "z_rec_au": 550.0,
        "arrival_year": 2048,
        "cruise_velocity_au_yr": 20.0,
    }
    resp = client.post("/api/target_ephemeris", json=payload)
    assert resp.status_code == 200
    res = resp.get_json()
    assert res["status"] == "success"
    d = res["data"]
    assert d["target_name"] == "Proxima Centauri b"
    assert d["telescope_constellation"] == "Cassiopeia"
    assert pytest.approx(550.0, rel=1e-6) == d["vector_norm_au"]
    assert pytest.approx(3.17, abs=0.02) == d["light_delay_days"]
