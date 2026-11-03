"""
Unit tests for the Flask web application and API endpoints.
"""

import pytest
from sgl_sim.web.app import app


@pytest.fixture
def client():
    """Create Flask test client."""
    app.config["TESTING"] = True
    with app.test_client() as test_client:
        yield test_client


def test_index_route(client):
    """Verify that root index renders the HTML dashboard."""
    resp = client.get("/")
    assert resp.status_code == 200
    assert b"sgl-sim" in resp.data
    assert b"Relativistic ray tracing" in resp.data
    assert b"dashboard.js" in resp.data


def test_api_simulate_endpoint(client):
    """Verify /api/simulate returns full simulation JSON."""
    payload = {
      "lens_type": "star",
      "mass_solar": 1.0,
      "z_rec_au": 650.0,
      "j2": 2.2e-7,
      "wavelength_um": 1.0,
      "aperture_m": 1.0,
      "t_int_days": 1.0,
      "distance_source_pc": 1.3,
      "x0_m": 0.0,
      "y0_m": 0.0,
    }
    resp = client.post("/api/simulate", json=payload)
    assert resp.status_code == 200
    data = resp.get_json()

    assert "z_min_au" in data
    assert pytest.approx(547.8, rel=2e-3) == data["z_min_au"]
    assert "a_caustic_m" in data
    assert "convolved_noisy" in data
    assert "deconvolved" in data
    assert "rmse_noisy" in data
    assert "rmse_deconvolved" in data
    assert data["rmse_deconvolved"] < data["rmse_noisy"]


def test_api_research_analysis_endpoint(client):
    """Verify /api/research_analysis tradespace matrix endpoint."""
    resp = client.get("/api/research_analysis?target_snr=10.0&distance_source_pc=1.3")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "snr_matrix" in data
    assert "t_req_hours_matrix" in data
    assert len(data["snr_matrix"]) > 0


def test_api_export_fits_endpoint(client):
    """Verify /api/export_fits returns a valid downloadable FITS binary."""
    resp = client.get("/api/export_fits?lens_type=star&mass_solar=1.0&z_rec_au=650.0")
    assert resp.status_code == 200
    assert resp.mimetype == "image/fits"
    assert resp.data.startswith(b"SIMPLE")


def test_api_export_csv_and_json_endpoints(client):
    """Verify /api/export_csv and /api/export_json endpoints."""
    resp_csv = client.get("/api/export_csv?z_rec_au=650.0")
    assert resp_csv.status_code == 200
    assert resp_csv.mimetype == "text/csv"
    assert b"rho_m" in resp_csv.data

    resp_json = client.get("/api/export_json?mass_solar=1.0")
    assert resp_json.status_code == 200
    assert resp_json.mimetype == "application/json"
    assert b"z_min_au" in resp_json.data


def test_api_simulate_black_hole_without_oblateness_is_valid_json(client):
    """J2 = 0 (black-hole preset) must not emit NaN, which browsers cannot parse."""
    import json

    resp = client.post("/api/simulate", json={"lens_type": "black_hole", "mass_solar": 5.0, "j2": 0.0})
    assert resp.status_code == 200
    data = json.loads(resp.get_data(as_text=True), parse_constant=lambda c: pytest.fail(f"non-JSON constant {c}"))
    assert len(data["ray_bundle"]) > 0


def test_api_simulate_psf_samples_the_core(client):
    """The radial PSF grid must resolve the centimetre-scale core."""
    data = client.post("/api/simulate", json={"z_rec_au": 650.0, "wavelength_um": 1.0}).get_json()
    assert data["psf_core_m"] == pytest.approx(0.0491, rel=1e-2)
    assert data["psf_rho_m"][-1] == pytest.approx(8 * data["psf_core_m"])
    assert min(data["psf_j0_sq"]) < 1e-3  # first dark ring is inside the grid
