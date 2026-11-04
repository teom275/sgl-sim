"""Tests for the SGL photon budget (sgl_sim.radiometry)."""

import pytest

from sgl_sim import calculate_snr
from sgl_sim.radiometry import integration_time_for_snr, sgl_photon_budget, solar_photon_flux
from sgl_sim.relativity import AU_SI, PC_SI


def test_solar_band_photons():
    sun = solar_photon_flux((0.4, 1.0))
    assert 0.5 < sun["energy_fraction"] < 0.7          # ~60 % of 1361 W/m^2
    assert sun["photons_m2_s"] == pytest.approx(2.7e21, rel=0.1)


def test_reproduces_toth_turyshev_reference_case():
    """Earth twin at 30 pc, 1 m telescope, 650 AU, N = 1000, SNR 7: ~1.33e7 s per pixel (Toth & Turyshev 2021)."""
    r = integration_time_for_snr(7.0, distance_source=30 * PC_SI, aperture_m=1.0, n_pixels=1000)
    assert r["image_diameter_m"] == pytest.approx(1.3e3, rel=0.05)  # 1.3 km image, as published
    assert 1.33e7 / 2 < r["per_pixel_s"] < 1.33e7 * 2
    # The corona dominates the noise budget, as in the literature.
    assert r["corona"] > 1e3 * r["blur"]


def test_scalings():
    base = dict(distance_source=10 * PC_SI, aperture_m=1.0, n_pixels=100)
    t0 = integration_time_for_snr(7.0, **base)["per_pixel_s"]
    # Per-pixel time grows as N^2 (pixel signal ~ 1/N).
    assert integration_time_for_snr(7.0, **{**base, "n_pixels": 200})["per_pixel_s"] == pytest.approx(4 * t0, rel=1e-9)
    # Corona-dominated: signal ~ d^2, corona ~ d, so t ~ d^-3.
    assert integration_time_for_snr(7.0, **{**base, "aperture_m": 2.0})["per_pixel_s"] == pytest.approx(t0 / 8, rel=0.02)
    # SNR target enters squared; telescopes in parallel divide the total.
    r = integration_time_for_snr(14.0, n_telescopes=4, **base)
    assert r["per_pixel_s"] == pytest.approx(4 * t0, rel=1e-9)
    assert r["total_s"] == pytest.approx(4 * t0 * 100**2 / 4, rel=1e-9)


def test_calculate_snr_wraps_budget_and_is_physical():
    one_day = calculate_snr(z_rec=650 * AU_SI, aperture_m=1.0, integration_time_s=86400.0,
                            distance_source=30 * PC_SI, n_pixels=1000)
    # ~0.5 per day per pixel for a megapixel Earth at 30 pc: nothing like the old ~1e6.
    assert 0.1 < one_day["snr"] < 2.0
    four_days = calculate_snr(z_rec=650 * AU_SI, aperture_m=1.0, integration_time_s=4 * 86400.0,
                              distance_source=30 * PC_SI, n_pixels=1000)
    assert four_days["snr"] == pytest.approx(2 * one_day["snr"], rel=1e-9)
    bud = sgl_photon_budget(distance_source=30 * PC_SI, n_pixels=1000)
    assert one_day["coronal_photons"] == pytest.approx(bud["corona"] * 86400.0)
