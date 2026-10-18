"""
Orbital Mechanics and Focal-Line Navigation for Gravitational Lens Telescopes.

This module computes Keplerian orbital velocities, periods, black hole ISCO checks,
projected exoplanet image cylinder dimensions, and annual station-keeping delta-V.
"""

from typing import Dict, Any, Optional, Union
import numpy as np
from astropy import constants as const
from astropy import units as u

from sgl_sim.relativity import (
    schwarzschild_radius,
    G_SI,
    M_SUN_SI,
    AU_SI,
    PC_SI,
)

# Standard seconds in one Julian year
SECONDS_PER_YEAR = 365.25 * 86400.0


def orbital_velocity(
    z_rec: Union[float, u.Quantity],
    mass: Union[float, u.Quantity] = M_SUN_SI,
) -> float:
    """
    Compute circular Keplerian orbital velocity at heliocentric distance z_rec:

        v_orb = sqrt(G * M / z_rec)

    Parameters
    ----------
    z_rec : float or astropy.units.Quantity
        Heliocentric distance (meters if float).
    mass : float or astropy.units.Quantity, optional
        Lens mass (default: 1 solar mass).

    Returns
    -------
    float
        Orbital velocity in m/s.
    """
    if isinstance(z_rec, u.Quantity):
        z_m = z_rec.to(u.m).value
    else:
        z_m = float(z_rec)

    if isinstance(mass, u.Quantity):
        m_kg = mass.to(u.kg).value
    else:
        m_kg = float(mass)

    return float(np.sqrt(G_SI * m_kg / z_m))


def orbital_period(
    z_rec: Union[float, u.Quantity],
    mass: Union[float, u.Quantity] = M_SUN_SI,
) -> Dict[str, float]:
    """
    Compute Keplerian orbital period: T = 2 * pi * sqrt(z_rec^3 / (G * M)).

    Parameters
    ----------
    z_rec : float or astropy.units.Quantity
        Heliocentric distance (meters if float).
    mass : float or astropy.units.Quantity, optional
        Lens mass (default: 1 solar mass).

    Returns
    -------
    dict
        Dictionary containing 'period_s', 'period_days', and 'period_years'.
    """
    if isinstance(z_rec, u.Quantity):
        z_m = z_rec.to(u.m).value
    else:
        z_m = float(z_rec)

    if isinstance(mass, u.Quantity):
        m_kg = mass.to(u.kg).value
    else:
        m_kg = float(mass)

    period_s = 2.0 * np.pi * np.sqrt((z_m**3) / (G_SI * m_kg))
    period_days = period_s / 86400.0
    period_years = period_s / SECONDS_PER_YEAR

    return {
        "period_s": float(period_s),
        "period_days": float(period_days),
        "period_years": float(period_years),
    }


def isco_radius(mass: Union[float, u.Quantity]) -> float:
    """
    Calculate the Innermost Stable Circular Orbit (ISCO) radius for a Schwarzschild black hole:

        r_ISCO = 3 * R_s = 6 * G * M / c^2

    Parameters
    ----------
    mass : float or astropy.units.Quantity
        Black hole mass (kg if float).

    Returns
    -------
    float
        ISCO radius in meters.
    """
    rs = schwarzschild_radius(mass)
    return float(3.0 * rs)


def check_isco(
    z_rec: Union[float, u.Quantity],
    mass: Union[float, u.Quantity],
) -> Dict[str, Any]:
    """
    Check if a receiver distance z_rec is outside the black hole ISCO radius.

    Parameters
    ----------
    z_rec : float or astropy.units.Quantity
        Distance in meters.
    mass : float or astropy.units.Quantity
        Black hole mass.

    Returns
    -------
    dict
        Dictionary containing 'r_isco_m', 'z_rec_m', and 'is_stable' (bool).
    """
    if isinstance(z_rec, u.Quantity):
        z_m = z_rec.to(u.m).value
    else:
        z_m = float(z_rec)

    r_isco = isco_radius(mass)
    is_stable = z_m > r_isco

    return {
        "r_isco_m": float(r_isco),
        "z_rec_m": float(z_m),
        "is_stable": bool(is_stable),
    }


def image_cylinder_diameter(
    z_rec: Union[float, u.Quantity],
    distance_source: Union[float, u.Quantity] = 1.3 * PC_SI,
    exoplanet_radius: Union[float, u.Quantity] = 6.371e6,
) -> Dict[str, float]:
    """
    Calculate projected exoplanet image cylinder diameter at focal line distance z_rec:

        D_img = 2 * R_exo * (z_rec / d_source)

    Parameters
    ----------
    z_rec : float or astropy.units.Quantity
        Receiver distance along the optical axis (meters if float).
    distance_source : float or astropy.units.Quantity, optional
        Distance to exoplanet host star (default: 1.3 pc ≈ Proxima Cen).
    exoplanet_radius : float or astropy.units.Quantity, optional
        Exoplanet physical radius (default: Earth radius = 6371 km).

    Returns
    -------
    dict
        Dictionary containing 'd_img_m', 'd_img_km', and 'theta_exo_rad'.
    """
    if isinstance(z_rec, u.Quantity):
        z_m = z_rec.to(u.m).value
    else:
        z_m = float(z_rec)

    if isinstance(distance_source, u.Quantity):
        d_src = distance_source.to(u.m).value
    else:
        d_src = float(distance_source)

    if isinstance(exoplanet_radius, u.Quantity):
        r_exo = exoplanet_radius.to(u.m).value
    else:
        r_exo = float(exoplanet_radius)

    theta_exo = (2.0 * r_exo) / d_src
    d_img_m = 2.0 * r_exo * (z_m / d_src)

    return {
        "d_img_m": float(d_img_m),
        "d_img_km": float(d_img_m / 1000.0),
        "theta_exo_rad": float(theta_exo),
    }


def station_keeping_delta_v(
    z_rec: Union[float, u.Quantity],
    mass: Union[float, u.Quantity] = M_SUN_SI,
    distance_source: Union[float, u.Quantity] = 1.3 * PC_SI,
    exoplanet_radius: Union[float, u.Quantity] = 6.371e6,
    scan_duration_years: float = 1.0,
) -> Dict[str, float]:
    """
    Calculate annual station-keeping delta-V (m/s/year) required to:
    1. Hover at fixed focal line position counteracting solar gravity.
    2. Scan across the exoplanet image cylinder diameter D_img.

    Parameters
    ----------
    z_rec : float or astropy.units.Quantity
        Receiver distance in meters.
    mass : float or astropy.units.Quantity, optional
        Lens mass (default: 1 solar mass).
    distance_source : float or astropy.units.Quantity, optional
        Distance to exoplanet in meters.
    exoplanet_radius : float or astropy.units.Quantity, optional
        Exoplanet radius in meters.
    scan_duration_years : float, optional
        Time allotted to scan across the image cylinder.

    Returns
    -------
    dict
        Dictionary containing:
        - 'a_grav_m_s2': gravitational acceleration in m/s^2
        - 'delta_v_hover_annual_m_s': delta-V to hover for 1 year in m/s
        - 'delta_v_scan_m_s': delta-V to scan across image cylinder in m/s
        - 'total_annual_budget_m_s': sum of annual hover and scan delta-V
    """
    if isinstance(z_rec, u.Quantity):
        z_m = z_rec.to(u.m).value
    else:
        z_m = float(z_rec)

    if isinstance(mass, u.Quantity):
        m_kg = mass.to(u.kg).value
    else:
        m_kg = float(mass)

    a_grav = (G_SI * m_kg) / (z_m**2)
    delta_v_hover = a_grav * SECONDS_PER_YEAR

    img_info = image_cylinder_diameter(
        z_rec=z_m,
        distance_source=distance_source,
        exoplanet_radius=exoplanet_radius,
    )
    d_img = img_info["d_img_m"]

    # Continuous slow scanning across cylinder: v_scan = D_img / scan_time
    scan_time_s = max(scan_duration_years * SECONDS_PER_YEAR, 86400.0)
    v_scan = d_img / scan_time_s
    # Total scan delta-V involves accelerations and raster turns (~4x v_scan)
    delta_v_scan = 4.0 * v_scan

    total_budget = delta_v_hover + delta_v_scan

    return {
        "a_grav_m_s2": float(a_grav),
        "delta_v_hover_annual_m_s": float(delta_v_hover),
        "delta_v_scan_m_s": float(delta_v_scan),
        "total_annual_budget_m_s": float(total_budget),
    }
