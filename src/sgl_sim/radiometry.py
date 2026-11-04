"""
Photon budget for imaging an extended exoplanet with the solar gravitational lens.

This replaces the earlier, unit-less SNR estimate (docs/auditoria-fisica.md,
finding C1) with a first-principles model of the three terms that matter in the
SGL literature (Turyshev & Toth 2020, "Image formation for extended sources
with the SGL"; Toth & Turyshev 2021, "Image recovery with the SGL"):

1. **Blur.** A telescope of diameter ``d`` anywhere inside the image of a
   uniform planetary disk of diameter ``D`` receives light from the *whole*
   disk through the slowly decaying tails of the PSF,
   ``mu(rho) = mu_0 J_0^2(k theta_E rho) ~ mu_0 / (pi k theta_E rho)``.
   Integrating over the disk gives an intensity ``I = 4 F b / D`` and a power

       P_blur = pi * F * b * d^2 / D,

   where ``F`` is the planet's photon flux without the lens and
   ``b = sqrt(2 R_s z)`` is the Einstein-ring radius.
2. **Signal.** The pixel the telescope sits in (a square of side ``D/N``)
   contributes ``~1/N`` of that. In kernel units the pixel value is
   ``P_unit = F b d^2 / (D N)``.
3. **Corona.** The telescope sees the Einstein ring at ``r = b/R_sun`` from
   the centre of the occulted Sun. It integrates the solar corona over an annulus
   one resolution element wide, ``Omega = 2 pi theta_E (lambda/d)``. The
   corona is the dominant noise for realistic targets, and no coronagraph can
   remove it because it overlaps the ring.

Shot noise of blur and corona sets the per-pixel noise. Deconvolving the 1/rho
blur kernel on an ``N x N`` grid leaves the per-pixel SNR

    SNR = sqrt(6) * P_unit * t / sqrt((P_blur + P_corona) * t)

The factor ``sqrt(6)`` comes from inverting the 2D Fourier transform of a 1/rho
kernel (``~1/|q|``). The integration time per pixel for a target SNR is then

    t_pix = SNR^2 * (P_blur + P_corona) / (6 * P_unit^2)

**Validation.** For an Earth twin at 30 pc, a 1 m telescope, 650 AU, N = 1000
and SNR 7, this gives 1.8e7 s per pixel. Toth & Turyshev (2021) quote 1.33e7 s
for that case (``tests/test_radiometry.py`` keeps the two within 2x). Other
published figures (e.g. Proxima b at 1000 x 1000 in ~14 months, MNRAS 2022)
use assumptions not reproduced here and still need to be checked against the
papers.

**Not included (yet).**
- light leaking from the host star's own image;
- the F-corona;
- detector noise;
- the planet's phase, rotation and orbital motion (findings C3, C4);
- the J2 caustic's change of the PSF.

Treat the results as order-of-magnitude, optimistic for close-in planets.
"""

from __future__ import annotations

from typing import Dict, Tuple, Union

import numpy as np
from astropy import units as u

from sgl_sim.relativity import AU_SI, M_SUN_SI, PC_SI, R_SUN_SI, _to_si_value, schwarzschild_radius

__all__ = [
    "solar_photon_flux",
    "sgl_photon_budget",
    "integration_time_for_snr",
    "SOLAR_CONSTANT_W_M2",
    "EARTH_RADIUS_M",
    "EARTH_GEOMETRIC_ALBEDO",
]

SOLAR_CONSTANT_W_M2 = 1361.0
T_SUN_K = 5772.0
EARTH_RADIUS_M = 6.371e6
EARTH_GEOMETRIC_ALBEDO = 0.367
DECONVOLUTION_GAIN = np.sqrt(6.0)

_H = 6.62607015e-34
_C = 299792458.0
_KB = 1.380649e-23


def solar_photon_flux(band_um: Tuple[float, float] = (0.4, 1.0), n: int = 400) -> Dict[str, float]:
    """
    Solar photon flux at 1 AU in a wavelength band.

    The spectrum is a 5772 K blackbody scaled to the solar constant
    (1361 W/m^2).

    Returns
    -------
    dict
        - 'photons_m2_s': photons / s / m^2 at 1 AU in the band
        - 'energy_fraction': fraction of the solar constant in the band
        - 'mean_wavelength_m': photon-weighted mean wavelength
    """
    lo, hi = (float(band_um[0]) * 1e-6, float(band_um[1]) * 1e-6)
    lam_all = np.geomspace(0.05e-6, 100e-6, 4000)
    lam = np.linspace(lo, hi, n)

    def planck(l):
        return (2 * _H * _C**2 / l**5) / np.expm1(_H * _C / (l * _KB * T_SUN_K))

    total = np.trapezoid(planck(lam_all), lam_all)
    scale = SOLAR_CONSTANT_W_M2 / total
    e_band = np.trapezoid(planck(lam), lam) * scale
    n_band = np.trapezoid(planck(lam) * scale * lam / (_H * _C), lam)
    mean_lam = np.trapezoid(planck(lam) * lam * lam / (_H * _C), lam) / np.trapezoid(planck(lam) * lam / (_H * _C), lam)
    return {
        "photons_m2_s": float(n_band),
        "energy_fraction": float(e_band / SOLAR_CONSTANT_W_M2),
        "mean_wavelength_m": float(mean_lam),
    }


def _coronal_brightness(r_sun: float) -> float:
    # Local import avoids a circular import with sgl_sim.deconvolution.
    from sgl_sim.deconvolution import baumbach_allen_coronal_brightness

    return float(baumbach_allen_coronal_brightness(r_sun))


def sgl_photon_budget(
    z_rec: Union[float, u.Quantity] = 650.0 * AU_SI,
    aperture_m: Union[float, u.Quantity] = 1.0,
    distance_source: Union[float, u.Quantity] = 1.3 * PC_SI,
    planet_radius: Union[float, u.Quantity] = EARTH_RADIUS_M,
    n_pixels: int = 32,
    insolation_earth: float = 1.0,
    geometric_albedo: float = EARTH_GEOMETRIC_ALBEDO,
    band_um: Tuple[float, float] = (0.4, 1.0),
    throughput: float = 1.0,
    mass: Union[float, u.Quantity] = M_SUN_SI,
    star_radius: Union[float, u.Quantity] = R_SUN_SI,
    annulus_width_lambda_over_d: float = 1.0,
) -> Dict[str, float]:
    """
    Photon rates for one telescope inside the SGL image of an exoplanet.

    Parameters
    ----------
    z_rec : float or Quantity
        Heliocentric distance of the telescope (m if float).
    aperture_m : float or Quantity
        Telescope diameter (m).
    distance_source : float or Quantity
        Distance to the planet (m if float).
    planet_radius : float or Quantity
        Planet radius (m if float).
    n_pixels : int
        Image resolution N (the image is N x N pixels across the disk).
    insolation_earth : float
        Stellar flux at the planet in units of the solar constant.
    geometric_albedo : float
        Geometric albedo (Earth ~0.37). The planet is assumed at full phase.
    band_um : (float, float)
        Observing band in micrometres (the star is approximated as Sun-like).
    throughput : float
        End-to-end optical and detector efficiency.
    mass, star_radius
        Lens mass and radius (default: the Sun).
    annulus_width_lambda_over_d : float
        Width of the coronal annulus in units of lambda/d.

    Returns
    -------
    dict
        Photon rates (photons/s) 'blur', 'pixel' (P_unit) and 'corona'; the
        planet flux 'planet_flux_m2_s'; the geometry 'b_ring_m', 'theta_E_rad',
        'r_ring_rsun' and 'image_diameter_m'; and 'snr_per_sqrt_s', the
        deconvolved per-pixel SNR after 1 s.
    """
    z = _to_si_value(z_rec, u.m)
    d = _to_si_value(aperture_m, u.m)
    dist = _to_si_value(distance_source, u.m)
    r_p = _to_si_value(planet_radius, u.m)
    m = _to_si_value(mass, u.kg)
    r_star = _to_si_value(star_radius, u.m)
    n = max(1, int(n_pixels))

    sun = solar_photon_flux(band_um)
    rs = schwarzschild_radius(m)
    b = np.sqrt(2.0 * rs * z)
    theta_e = b / z
    d_img = 2.0 * r_p * z / dist

    # Planet: reflected starlight at full phase, F = Phi_sun * S * A_g * (R_p / d)^2.
    f_planet = sun["photons_m2_s"] * insolation_earth * geometric_albedo * (r_p / dist) ** 2

    p_blur = np.pi * f_planet * b * d**2 / d_img * throughput
    p_pixel = f_planet * b * d**2 / (d_img * n) * throughput

    # Corona: mean solar-disk radiance times the Baumbach ratio, over an annulus of width lambda/d.
    omega_sun = np.pi * (r_star / AU_SI) ** 2
    radiance_sun = sun["photons_m2_s"] / omega_sun
    r_ring = b / r_star
    omega_annulus = 2.0 * np.pi * theta_e * annulus_width_lambda_over_d * sun["mean_wavelength_m"] / d
    p_corona = _coronal_brightness(r_ring) * radiance_sun * omega_annulus * (np.pi * d**2 / 4.0) * throughput

    snr_1s = DECONVOLUTION_GAIN * p_pixel / np.sqrt(p_blur + p_corona)
    return {
        "blur": float(p_blur),
        "pixel": float(p_pixel),
        "corona": float(p_corona),
        "planet_flux_m2_s": float(f_planet),
        "b_ring_m": float(b),
        "theta_E_rad": float(theta_e),
        "r_ring_rsun": float(r_ring),
        "image_diameter_m": float(d_img),
        "n_pixels": n,
        "snr_per_sqrt_s": float(snr_1s),
    }


def integration_time_for_snr(target_snr: float = 7.0, n_telescopes: int = 1, **budget_kwargs) -> Dict[str, float]:
    """
    Integration time needed to reach a deconvolved per-pixel SNR.

    ``budget_kwargs`` are passed to :func:`sgl_photon_budget`. With
    ``n_telescopes`` identical telescopes sampling different pixels in
    parallel, the total time is ``N^2 * t_pix / n_telescopes``.

    Returns
    -------
    dict
        'per_pixel_s', 'total_s', 'total_years', plus the photon budget.
    """
    bud = sgl_photon_budget(**budget_kwargs)
    t_pix = (float(target_snr) / bud["snr_per_sqrt_s"]) ** 2
    total = t_pix * bud["n_pixels"] ** 2 / max(1, int(n_telescopes))
    return {
        "per_pixel_s": float(t_pix),
        "total_s": float(total),
        "total_years": float(total / (365.25 * 86400.0)),
        "target_snr": float(target_snr),
        "n_telescopes": int(n_telescopes),
        **bud,
    }
