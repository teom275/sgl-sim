"""
Unit tests for astroid caustics, coronal noise, Wiener deconvolution, and orbital mechanics.
"""

import pytest
import numpy as np
from astropy import units as u

from sgl_sim.relativity import AU_SI, PC_SI, M_SUN_SI, R_SUN_SI
from sgl_sim.caustics import (
    astroid_caustic_semi_width,
    parametric_astroid,
    check_caustic_regime,
    solve_quadrupole_images,
    generate_caustic_map_2d,
    J2_SUN,
)
from sgl_sim.deconvolution import (
    baumbach_allen_coronal_brightness,
    calculate_snr,
    generate_exoplanet_map,
    compute_ssim,
    compute_rmse,
    wiener_deconvolution,
)
from sgl_sim.optics import generate_2d_psf
from sgl_sim.orbital import (
    orbital_velocity,
    orbital_period,
    isco_radius,
    check_isco,
    image_cylinder_diameter,
    station_keeping_delta_v,
)
from sgl_sim.tradespace import evaluate_tradespace


def test_astroid_caustic_semi_width():
    """Astroid caustic size matches Turyshev & Toth (2021): 287.39 m at 650 AU for J2 = 2.25e-7."""
    from sgl_sim.caustics import solar_axis_sin2_beta

    ref = astroid_caustic_semi_width(z_rec=650.0 * AU_SI, j2=2.25e-7)["a_caustic_m"]
    assert ref == pytest.approx(287.39, rel=2e-3)
    # Shrinks as 1/sqrt(z): smaller further out, not larger.
    far = astroid_caustic_semi_width(z_rec=4 * 650.0 * AU_SI, j2=2.25e-7)["a_caustic_m"]
    assert far == pytest.approx(ref / 2.0, rel=1e-9)
    # Linear in J2 and in sin^2(beta_s).
    assert astroid_caustic_semi_width(650.0 * AU_SI, j2=4.5e-7)["a_caustic_m"] == pytest.approx(2 * ref)
    assert astroid_caustic_semi_width(650.0 * AU_SI, j2=2.25e-7, sin2_beta_s=0.25)["a_caustic_m"] == pytest.approx(ref / 4)
    # Orientation factor: zero along the solar spin axis, one in the solar equator.
    assert solar_axis_sin2_beta(286.13, 63.87) == pytest.approx(0.0, abs=1e-12)
    assert solar_axis_sin2_beta(286.13 + 180.0, -63.87) == pytest.approx(0.0, abs=1e-12)
    assert solar_axis_sin2_beta(286.13, 63.87 - 90.0) == pytest.approx(1.0)


def test_parametric_astroid_geometry():
    """Verify astroid parametric coordinates satisfy x^(2/3) + y^(2/3) == a^(2/3)."""
    a_val = 15.0
    astroid = parametric_astroid(a_caustic=a_val, num_points=100)
    x = astroid["x"]
    y = astroid["y"]
    assert len(x) == 100
    assert len(y) == 100

    # Test algebraic relation (x/a)^(2/3) + (y/a)^(2/3) = 1
    # Avoid zero singularity at axes by testing intermediate points
    u = np.abs(x[10:40]) / a_val
    v = np.abs(y[10:40]) / a_val
    lhs = (u ** (2.0 / 3.0)) + (v ** (2.0 / 3.0))
    assert np.allclose(lhs, 1.0, atol=1e-5)


def test_caustic_regime_and_quadrupole_solver():
    """Verify image count: 4 images inside astroid (Einstein Cross), 2 images outside."""
    z_rec_m = 650.0 * AU_SI
    caustic_info = astroid_caustic_semi_width(z_rec=z_rec_m, mass=M_SUN_SI, star_radius=R_SUN_SI, j2=J2_SUN)
    a = caustic_info["a_caustic_m"]

    # 1. Receiver at center (0, 0) -> Inside astroid -> 4 images (Einstein Cross)
    sol_center = solve_quadrupole_images(x0=0.0, y0=0.0, z_rec=z_rec_m)
    assert sol_center["regime"] == "inside"
    assert sol_center["num_images"] == 4
    assert len(sol_center["image_angles_rad"]) == 4

    # 2. Receiver far outside (2.5 * a, 2.5 * a) -> Outside astroid -> 2 images
    sol_outside = solve_quadrupole_images(x0=2.5 * a, y0=2.5 * a, z_rec=z_rec_m)
    assert sol_outside["regime"] == "outside"
    assert sol_outside["num_images"] == 2

    # 3. 360-degree ring profile is computed
    assert len(sol_center["ring_profile"]) == 720
    assert np.max(sol_center["ring_profile"]) == pytest.approx(1.0, rel=1e-4)


def test_solve_quadrupole_images_quantity_equivalence():
    """Verify that passing Quantity objects produces identical image solutions to raw floats."""
    sol_q = solve_quadrupole_images(
        x0=5.0 * u.m,
        y0=-2.0 * u.m,
        z_rec=650.0 * u.AU,
        mass=1.0 * u.M_sun,
        star_radius=1.0 * u.R_sun,
        wavelength=1.0 * u.micron,
    )
    sol_f = solve_quadrupole_images(
        x0=5.0,
        y0=-2.0,
        z_rec=650.0 * AU_SI,
        mass=M_SUN_SI,
        star_radius=R_SUN_SI,
        wavelength=1.0e-6,
    )

    assert sol_q["regime"] == sol_f["regime"]
    assert sol_q["num_images"] == sol_f["num_images"]
    assert np.allclose(sol_q["image_angles_rad"], sol_f["image_angles_rad"], rtol=1e-5)
    assert np.allclose(sol_q["ring_profile"], sol_f["ring_profile"], rtol=1e-5)
    assert pytest.approx(sol_q["a_caustic"], rel=1e-5) == sol_f["a_caustic"]


def test_baumbach_allen_coronal_brightness():
    """Verify Baumbach-Allen solar coronal brightness power-law drop."""
    # At solar surface (r = 1.0)
    b_1 = baumbach_allen_coronal_brightness(1.0)
    # At r = 1.5 solar radii
    b_1_5 = baumbach_allen_coronal_brightness(1.5)
    # At r = 2.5 solar radii
    b_2_5 = baumbach_allen_coronal_brightness(2.5)

    # Brightness should drop steeply
    assert b_1 > 5.0 * b_1_5
    assert b_1 > 20.0 * b_2_5
    assert b_1 > 0.0
    # Classic Baumbach values (Allen's Astrophysical Quantities).
    assert b_1 == pytest.approx(4.0432e-6, rel=1e-4)
    assert baumbach_allen_coronal_brightness(1.09) == pytest.approx(1.415e-6, rel=5e-3)
    assert b_2_5 == pytest.approx(1e-6 * (0.0532 / 2.5**2.5 + 1.425 / 2.5**7 + 2.565 / 2.5**17))


def test_calculate_snr():
    """Verify SNR calculation and sensitivity to aperture and integration time."""
    z_rec_m = 650.0 * AU_SI

    # Baseline 1m telescope, 1 day
    snr_1m = calculate_snr(z_rec=z_rec_m, aperture_m=1.0, integration_time_s=86400.0)
    assert snr_1m["snr"] > 0.0

    # 2m telescope (4x collecting area) should yield strictly higher SNR
    snr_2m = calculate_snr(z_rec=z_rec_m, aperture_m=2.0, integration_time_s=86400.0)
    assert snr_2m["snr"] > snr_1m["snr"]


def test_exoplanet_wiener_deconvolution_rmse_reduction():
    """Verify that Wiener deconvolution achieves significant RMSE reduction on blurred+noisy image."""
    z_rec_m = 650.0 * AU_SI
    gt = generate_exoplanet_map(grid_size=32, seed=42)
    assert gt.shape == (32, 32)
    assert 0.0 <= np.min(gt) and np.max(gt) <= 1.0

    psf_kernel = generate_2d_psf(grid_size=32, pixel_scale_m=1.0, z_rec=z_rec_m, normalize_sum=True)

    # Run deconvolution with moderate SNR (e.g. 20)
    res = wiener_deconvolution(ground_truth=gt, psf_kernel=psf_kernel, snr=20.0, seed=42)

    # Check output images
    assert res["ground_truth"].shape == (32, 32)
    assert res["convolved_noisy"].shape == (32, 32)
    assert res["deconvolved"].shape == (32, 32)

    # Core scientific requirement: Wiener reconstruction RMSE must be lower than noisy image RMSE!
    assert res["rmse_deconvolved"] < res["rmse_noisy"]
    # Structural similarity SSIM should be significantly improved
    assert res["ssim_deconvolved"] > res["ssim_noisy"]


def test_orbital_mechanics_and_isco():
    """Verify Keplerian orbital velocity, periods, ISCO, and station-keeping."""
    z_rec_m = 650.0 * AU_SI

    v_orb = orbital_velocity(z_rec=z_rec_m, mass=M_SUN_SI)
    assert 1000.0 < v_orb < 1500.0  # ~1.16 km/s

    period_info = orbital_period(z_rec=z_rec_m, mass=M_SUN_SI)
    assert 15000.0 < period_info["period_years"] < 18000.0

    # ISCO check for black hole
    bh_mass = 10.0 * M_SUN_SI
    r_isco = isco_radius(bh_mass)
    assert check_isco(z_rec=z_rec_m, mass=bh_mass)["is_stable"] is True
    assert check_isco(z_rec=0.5 * r_isco, mass=bh_mass)["is_stable"] is False

    # Image cylinder diameter for Earth at 1.3 pc
    cyl = image_cylinder_diameter(z_rec=z_rec_m, distance_source=1.3 * PC_SI)
    assert 20.0 < cyl["d_img_km"] < 40.0

    # Annual station-keeping delta-V
    sk = station_keeping_delta_v(z_rec=z_rec_m, mass=M_SUN_SI)
    assert 0.1 < sk["delta_v_hover_annual_m_s"] < 2.0


def test_evaluate_tradespace_grid():
    """Verify 2D mission tradespace matrix calculation."""
    res = evaluate_tradespace(
        z_min_au=550.0,
        z_max_au=750.0,
        n_z=5,
        aperture_min_m=0.5,
        aperture_max_m=2.5,
        n_aperture=5,
    )
    assert res["snr_matrix"].shape == (5, 5)
    assert res["t_req_hours_matrix"].shape == (5, 5)
    assert np.all(res["snr_matrix"] > 0)
