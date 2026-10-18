"""
Unit tests for relativistic geodesics and wave optics modules.
"""

import pytest
import numpy as np
from astropy import units as u
from astropy import constants as const

from sgl_sim.relativity import (
    schwarzschild_radius,
    photon_sphere_radius,
    critical_impact_parameter,
    weak_deflection_angle,
    focal_distance,
    integrate_strong_geodesic,
    M_SUN_SI,
    R_SUN_SI,
    AU_SI,
)
from sgl_sim.optics import (
    minimum_focal_distance,
    einstein_ring_properties,
    peak_magnification,
    psf_intensity,
    generate_2d_psf,
)


def test_schwarzschild_and_critical_thresholds():
    """Verify Schwarzschild radius, photon sphere, and critical impact parameter."""
    rs = schwarzschild_radius(M_SUN_SI)
    assert pytest.approx(2953.25, rel=1e-3) == rs

    r_ph = photon_sphere_radius(M_SUN_SI)
    assert pytest.approx(1.5 * rs, rel=1e-6) == r_ph

    bc = critical_impact_parameter(M_SUN_SI)
    expected_bc = (3.0 * np.sqrt(3.0) / 2.0) * rs
    assert pytest.approx(expected_bc, rel=1e-6) == bc
    assert pytest.approx(2.59807621135 * rs, rel=1e-6) == bc


def test_astropy_units_support():
    """Verify that public API functions accept astropy Quantity objects."""
    mass_q = 1.0 * u.M_sun
    radius_q = 1.0 * u.R_sun
    rs = schwarzschild_radius(mass_q)
    assert pytest.approx(2953.25, rel=1e-3) == rs

    z_min_dict = minimum_focal_distance(mass=mass_q, radius=radius_q)
    assert pytest.approx(547.8, rel=2e-3) == z_min_dict["z_min_au"]

    alpha = weak_deflection_angle(impact_param=1.0 * u.R_sun, mass=mass_q)
    assert pytest.approx(4.0 * const.G.value * const.M_sun.value / (const.c.value**2 * const.R_sun.value), rel=1e-5) == alpha


def test_minimum_focal_distance_solar():
    """Verify that for 1 M_sun and 1 R_sun, z_min evaluates to ≈ 547.8 AU."""
    res = minimum_focal_distance(mass=M_SUN_SI, radius=R_SUN_SI)
    z_min_au = res["z_min_au"]
    assert 547.0 < z_min_au < 548.5
    assert pytest.approx(547.76, rel=2e-3) == z_min_au


def test_minimum_focal_distance_black_hole():
    """Verify that for a black hole, z_min starts beyond the photon sphere shadow."""
    res = minimum_focal_distance(mass=M_SUN_SI, is_black_hole=True)
    rs = schwarzschild_radius(M_SUN_SI)
    bc = critical_impact_parameter(M_SUN_SI)
    expected_z = (bc**2) / (2.0 * rs)
    assert pytest.approx(expected_z, rel=1e-5) == res["z_min_m"]


def test_focal_distance_and_blocking():
    """Verify focal crossing distance and stellar disk blocking."""
    # Ray at b = 0.5 R_sun should be blocked
    b_blocked = 0.5 * R_SUN_SI
    res_blocked = focal_distance(impact_param=b_blocked, star_radius=R_SUN_SI)
    assert res_blocked["blocked"] is True
    assert res_blocked["status"] == "blocked_by_star"

    # Ray at b = 1.2 R_sun should not be blocked
    b_free = 1.2 * R_SUN_SI
    res_free = focal_distance(impact_param=b_free, star_radius=R_SUN_SI)
    assert res_free["blocked"] is False
    assert res_free["status"] == "ok"
    assert res_free["z_au"] > 547.8


def test_strong_field_geodesic_capture_and_escape():
    """Verify that rays with b <= b_c are captured, and b > b_c escape."""
    rs = schwarzschild_radius(M_SUN_SI)
    bc = critical_impact_parameter(M_SUN_SI)

    # Ray with b < bc (captured by black hole)
    res_captured = integrate_strong_geodesic(impact_param=0.8 * bc, mass=M_SUN_SI)
    assert res_captured["status"] == "captured_by_bh"

    # Ray with b > bc (escapes)
    res_escaped = integrate_strong_geodesic(impact_param=1.5 * bc, mass=M_SUN_SI)
    assert res_escaped["status"] == "escaped"
    assert len(res_escaped["x"]) > 10
    assert len(res_escaped["y"]) > 10
    assert res_escaped["r_min"] > 1.5 * rs  # Turning point outside photon sphere


def test_optics_einstein_ring_and_magnification():
    """Verify Einstein ring properties and peak magnification."""
    z_rec_m = 650.0 * AU_SI
    ring = einstein_ring_properties(z_rec=z_rec_m, mass=M_SUN_SI)
    assert ring["b_ring_m"] > R_SUN_SI
    assert ring["theta_E_arcsec"] > 0.0

    # Peak magnification at 1 micron
    lam = 1.0e-6
    mu = peak_magnification(wavelength=lam, mass=M_SUN_SI)
    rs = schwarzschild_radius(M_SUN_SI)
    expected_mu = 4.0 * (np.pi**2) * rs / lam
    assert pytest.approx(expected_mu, rel=1e-6) == mu
    assert mu > 1e11


def test_optics_psf_profile_and_2d_kernel():
    """Verify wave-optics Bessel J_0^2 PSF shape and 2D kernel."""
    z_rec_m = 650.0 * AU_SI
    lam = 1.0e-6

    # On-axis peak
    i_0 = psf_intensity(rho=0.0, z_rec=z_rec_m, wavelength=lam, mass=M_SUN_SI, normalize=True)
    assert pytest.approx(1.0, rel=1e-5) == i_0

    # Off-axis decay
    i_off = psf_intensity(rho=15.0, z_rec=z_rec_m, wavelength=lam, mass=M_SUN_SI, normalize=True)
    assert 0.0 <= i_off < 1.0

    # 2D Kernel sum normalization
    kernel = generate_2d_psf(grid_size=32, pixel_scale_m=1.0, z_rec=z_rec_m, wavelength=lam, normalize_sum=True)
    assert kernel.shape == (32, 32)
    assert pytest.approx(1.0, rel=1e-4) == np.sum(kernel)


def test_generate_2d_psf_quantity_equivalence():
    """Verify that passing astropy.units.Quantity vs float produces identical kernels."""
    z_rec_q = 650.0 * u.AU
    z_rec_m = (650.0 * u.AU).to(u.m).value
    pix_scale_q = 1.5 * u.m
    pix_scale_m = 1.5
    lam_q = 1.2 * u.micron
    lam_m = 1.2e-6
    mass_q = 1.0 * u.M_sun
    mass_kg = const.M_sun.value

    kernel_quantities = generate_2d_psf(
        grid_size=16,
        pixel_scale_m=pix_scale_q,
        z_rec=z_rec_q,
        wavelength=lam_q,
        mass=mass_q,
        normalize_sum=True,
    )

    kernel_floats = generate_2d_psf(
        grid_size=16,
        pixel_scale_m=pix_scale_m,
        z_rec=z_rec_m,
        wavelength=lam_m,
        mass=mass_kg,
        normalize_sum=True,
    )

    assert np.allclose(kernel_quantities, kernel_floats, rtol=1e-7, atol=1e-10)


def test_strong_geodesic_with_quantity():
    """Verify that integrate_strong_geodesic accepts Quantity objects."""
    bc = critical_impact_parameter(1.0 * u.M_sun)
    res_q = integrate_strong_geodesic(impact_param=1.5 * bc * u.m, mass=1.0 * u.M_sun)
    assert res_q["status"] == "escaped"
