"""
Wave Optics and Focal Line Properties for Gravitational Lens Telescopes.

This module models the minimum focal distance z_min, the Einstein ring angular radius
theta_E, peak on-axis wave-optics magnification mu_max, and the diffraction-limited
Bessel J_0^2 point spread function (PSF).
"""

from typing import Dict, Any, Tuple, Optional, Union
import numpy as np
from scipy.special import jv
from astropy import constants as const
from astropy import units as u

from sgl_sim.relativity import (
    schwarzschild_radius,
    critical_impact_parameter,
    _to_si_value,
    M_SUN_SI,
    R_SUN_SI,
    AU_SI,
)


def minimum_focal_distance(
    mass: Union[float, u.Quantity] = M_SUN_SI,
    radius: Optional[Union[float, u.Quantity]] = R_SUN_SI,
    is_black_hole: bool = False,
) -> Dict[str, float]:
    """
    Calculate the minimum focal distance z_min of the gravitational lens.

    For a star of physical radius R_star:
        z_min = R_star^2 / (2 * R_s)
    For 1 M_sun and 1 R_sun, this evaluates to ≈ 547.8 AU.

    For a black hole, the minimum focal distance for uncaptured rays (b > b_c):
        b_c = (3*sqrt(3)/2) * R_s
        z_min_bh ≈ b_c^2 / (2 * R_s) = (27/8) * R_s = 3.375 * R_s

    Parameters
    ----------
    mass : float or astropy.units.Quantity, optional
        Lens mass (default: 1 solar mass).
    radius : float or astropy.units.Quantity, optional
        Physical radius of the star in meters (default: 1 solar radius).
    is_black_hole : bool, optional
        Whether the lens is a black hole without a stellar surface.

    Returns
    -------
    dict
        Dictionary containing:
        - 'z_min_m': minimum focal distance in meters
        - 'z_min_au': minimum focal distance in AU
        - 'b_min_m': minimum unocculted impact parameter in meters
    """
    rs = schwarzschild_radius(mass)

    if is_black_hole or radius is None:
        bc = critical_impact_parameter(mass)
        z_min_m = (bc**2) / (2.0 * rs)
        b_min_m = bc
    else:
        if isinstance(radius, u.Quantity):
            r_val = radius.to(u.m).value
        else:
            r_val = float(radius)
        z_min_m = (r_val**2) / (2.0 * rs)
        b_min_m = r_val

    z_min_au = z_min_m / AU_SI
    return {
        "z_min_m": float(z_min_m),
        "z_min_au": float(z_min_au),
        "b_min_m": float(b_min_m),
    }


def einstein_ring_properties(
    z_rec: Union[float, u.Quantity],
    mass: Union[float, u.Quantity] = M_SUN_SI,
) -> Dict[str, float]:
    """
    Compute the Einstein ring radius and angular radius at receiver distance z_rec.

        b_ring = sqrt(2 * R_s * z_rec)
        theta_E = sqrt(2 * R_s / z_rec) = b_ring / z_rec

    Parameters
    ----------
    z_rec : float or astropy.units.Quantity
        Heliocentric / receiver distance along optical axis. If float, meters.
    mass : float or astropy.units.Quantity, optional
        Lens mass (default: 1 solar mass).

    Returns
    -------
    dict
        Dictionary containing:
        - 'b_ring_m': impact parameter of the Einstein ring in meters
        - 'b_ring_r_sun': impact parameter in units of solar radii
        - 'theta_E_rad': angular Einstein radius in radians
        - 'theta_E_arcsec': angular Einstein radius in arcseconds
        - 'theta_E_mas': angular Einstein radius in milliarcseconds
    """
    if isinstance(z_rec, u.Quantity):
        z_m = z_rec.to(u.m).value
    else:
        z_m = float(z_rec)

    rs = schwarzschild_radius(mass)
    b_ring = np.sqrt(2.0 * rs * z_m)
    theta_E = np.sqrt(2.0 * rs / z_m)

    theta_E_arcsec = np.degrees(theta_E) * 3600.0
    theta_E_mas = theta_E_arcsec * 1000.0

    return {
        "b_ring_m": float(b_ring),
        "b_ring_r_sun": float(b_ring / R_SUN_SI),
        "theta_E_rad": float(theta_E),
        "theta_E_arcsec": float(theta_E_arcsec),
        "theta_E_mas": float(theta_E_mas),
    }


def peak_magnification(
    wavelength: Union[float, u.Quantity] = 1.0e-6,
    mass: Union[float, u.Quantity] = M_SUN_SI,
) -> float:
    """
    Compute peak on-axis wave-optics magnification: mu_max = 4 * pi^2 * R_s / lambda.

    Parameters
    ----------
    wavelength : float or astropy.units.Quantity, optional
        Observation wavelength in meters (default: 1.0 um).
    mass : float or astropy.units.Quantity, optional
        Lens mass (default: 1 solar mass).

    Returns
    -------
    float
        Peak magnification (dimensionless).
    """
    if isinstance(wavelength, u.Quantity):
        lam = wavelength.to(u.m).value
    else:
        lam = float(wavelength)

    rs = schwarzschild_radius(mass)
    return float((4.0 * (np.pi**2) * rs) / lam)


def psf_intensity(
    rho: Union[float, np.ndarray, u.Quantity],
    z_rec: Union[float, u.Quantity],
    wavelength: Union[float, u.Quantity] = 1.0e-6,
    mass: Union[float, u.Quantity] = M_SUN_SI,
    normalize: bool = False,
) -> Union[float, np.ndarray]:
    """
    Compute the wave-optics Point Spread Function (PSF) intensity at transverse offset rho:

        I(rho) = mu_max * [ J_0( (2 * pi / lambda) * sqrt(2 * R_s / z_rec) * rho ) ]^2

    Parameters
    ----------
    rho : float, np.ndarray, or astropy.units.Quantity
        Transverse displacement from optical axis in meters.
    z_rec : float or astropy.units.Quantity
        Receiver distance along optical axis. If float, meters.
    wavelength : float or astropy.units.Quantity, optional
        Wavelength in meters (default: 1.0 um).
    mass : float or astropy.units.Quantity, optional
        Lens mass (default: 1 solar mass).
    normalize : bool, optional
        If True, normalizes peak intensity to 1.0.

    Returns
    -------
    float or np.ndarray
        PSF intensity value(s).
    """
    if isinstance(rho, u.Quantity):
        rho_m = rho.to(u.m).value
    else:
        rho_m = np.asarray(rho, dtype=float)

    if isinstance(z_rec, u.Quantity):
        z_m = z_rec.to(u.m).value
    else:
        z_m = float(z_rec)

    if isinstance(wavelength, u.Quantity):
        lam = wavelength.to(u.m).value
    else:
        lam = float(wavelength)

    rs = schwarzschild_radius(mass)
    theta_E = np.sqrt(2.0 * rs / z_m)
    k = 2.0 * np.pi / lam
    arg = k * theta_E * rho_m

    j0_val = jv(0, arg)
    j0_sq = j0_val**2

    if normalize:
        res = j0_sq
    else:
        mu_max = (4.0 * (np.pi**2) * rs) / lam
        res = mu_max * j0_sq

    if np.ndim(res) == 0:
        return float(res)
    return res


def generate_2d_psf(
    grid_size: int,
    pixel_scale_m: Union[float, u.Quantity],
    z_rec: Union[float, u.Quantity],
    wavelength: Union[float, u.Quantity] = 1.0e-6,
    mass: Union[float, u.Quantity] = M_SUN_SI,
    normalize_sum: bool = True,
) -> np.ndarray:
    """
    Generate a 2D Bessel J_0^2 PSF kernel on an N x N Cartesian grid.

    Parameters
    ----------
    grid_size : int
        Number of pixels along each side (e.g. 32).
    pixel_scale_m : float or astropy.units.Quantity
        Physical width of each pixel (in meters if float).
    z_rec : float or astropy.units.Quantity
        Receiver distance (in meters if float).
    wavelength : float or astropy.units.Quantity, optional
        Wavelength in meters (default: 1.0 um).
    mass : float or astropy.units.Quantity, optional
        Lens mass in kg (default: 1 solar mass).
    normalize_sum : bool, optional
        If True, normalizes the array such that sum(kernel) == 1.0.

    Returns
    -------
    np.ndarray
        2D array of shape (grid_size, grid_size).
    """
    pix_scale = _to_si_value(pixel_scale_m, u.m)
    z_val = _to_si_value(z_rec, u.m)
    lam_val = _to_si_value(wavelength, u.m)
    m_val = _to_si_value(mass, u.kg)

    coords = (np.arange(grid_size) - (grid_size - 1) / 2.0) * pix_scale
    xx, yy = np.meshgrid(coords, coords)
    rho_grid = np.sqrt(xx**2 + yy**2)

    psf_2d = psf_intensity(
        rho=rho_grid,
        z_rec=z_val,
        wavelength=lam_val,
        mass=m_val,
        normalize=True,
    )

    if normalize_sum:
        total = np.sum(psf_2d)
        if total > 0:
            psf_2d = psf_2d / total

    return psf_2d
