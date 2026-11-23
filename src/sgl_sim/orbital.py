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


def solar_oberth_trajectory(
    r_perihelion: Union[float, u.Quantity] = 0.05 * AU_SI,
    delta_v_burn: Union[float, u.Quantity] = 5000.0,
    target_z_rec: Union[float, u.Quantity] = 650.0 * AU_SI,
    mass: Union[float, u.Quantity] = M_SUN_SI,
) -> Dict[str, float]:
    """
    Model a Solar Oberth maneuver for high-speed heliocentric escape to the SGL focal line.

    The spacecraft approaches the Sun along a high-eccentricity inward leg, reaching
    perihelion at r_p, where an impulsive delta-V burn (or concentrated solar photon boost)
    is applied to maximize the hyperbolic asymptotic excess velocity v_inf:

        v_p = sqrt(2 * G * M / r_p)
        v_post = v_p + delta_v
        v_inf = sqrt(v_post^2 - 2 * G * M / r_p)

    Parameters
    ----------
    r_perihelion : float or astropy.units.Quantity, optional
        Perihelion distance in meters (default: 0.05 AU ≈ 10.75 R_sun).
    delta_v_burn : float or astropy.units.Quantity, optional
        Impulsive burn velocity increment in m/s (default: 5000 m/s = 5 km/s).
    target_z_rec : float or astropy.units.Quantity, optional
        Target focal distance in meters (default: 650 AU).
    mass : float or astropy.units.Quantity, optional
        Central lens mass in kg (default: 1 M_sun).

    Returns
    -------
    dict
        Dictionary containing:
        - 'r_perihelion_au': perihelion distance in AU
        - 'v_perihelion_km_s': perihelion pre-burn velocity in km/s
        - 'delta_v_burn_km_s': applied burn in km/s
        - 'v_post_burn_km_s': velocity immediately post-burn in km/s
        - 'v_inf_km_s': asymptotic hyperbolic escape velocity in km/s
        - 'v_inf_au_yr': escape velocity in AU/year
        - 'cruise_time_years': approximate time of flight from 1 AU to target_z_rec
        - 'amplification_factor': Oberth velocity amplification (v_inf / delta_v)
    """
    if isinstance(r_perihelion, u.Quantity):
        r_p_m = r_perihelion.to(u.m).value
    else:
        r_p_m = float(r_perihelion)

    if isinstance(delta_v_burn, u.Quantity):
        dv_m_s = delta_v_burn.to(u.m / u.s).value
    else:
        dv_m_s = float(delta_v_burn)

    if isinstance(target_z_rec, u.Quantity):
        z_target_m = target_z_rec.to(u.m).value
    else:
        z_target_m = float(target_z_rec)

    if isinstance(mass, u.Quantity):
        m_kg = mass.to(u.kg).value
    else:
        m_kg = float(mass)

    mu = G_SI * m_kg
    v_p = np.sqrt(2.0 * mu / r_p_m)
    v_post = v_p + dv_m_s

    # Hyperbolic excess velocity
    v_esc_sq = 2.0 * mu / r_p_m
    v_inf_sq = max(v_post**2 - v_esc_sq, 0.0)
    v_inf = np.sqrt(v_inf_sq)

    # Conversion to AU/year
    # 1 AU/year in m/s: AU_SI / SECONDS_PER_YEAR ≈ 4740.4 m/s
    v_inf_au_yr = (v_inf * SECONDS_PER_YEAR) / AU_SI

    # Approximate cruise time (outer leg dominant: z_target / v_inf)
    if v_inf > 0.0:
        cruise_time_years = (z_target_m / v_inf) / SECONDS_PER_YEAR
        amp_factor = v_inf / max(dv_m_s, 1e-6)
    else:
        cruise_time_years = float("inf")
        amp_factor = 0.0

    return {
        "r_perihelion_au": float(r_p_m / AU_SI),
        "v_perihelion_km_s": float(v_p / 1000.0),
        "delta_v_burn_km_s": float(dv_m_s / 1000.0),
        "v_post_burn_km_s": float(v_post / 1000.0),
        "v_inf_km_s": float(v_inf / 1000.0),
        "v_inf_au_yr": float(v_inf_au_yr),
        "cruise_time_years": float(cruise_time_years),
        "amplification_factor": float(amp_factor),
    }


def generate_swarm_formation(
    pattern: str = "concentric",
    num_satellites: int = 6,
    radius_km: Union[float, u.Quantity] = 10.0,
) -> Dict[str, Any]:
    """
    Generate spatial coordinate positions and geometry for a satellite swarm
    operating in the transverse focal plane of the Solar System (at z_rec ~ 650 AU).

    Supported patterns:
    - 'concentric': Center craft surrounded by concentric ring(s)
    - 'hexagonal': Hexagonal close-packed grid (optimal area subdivision)
    - 'spiral': Golden-angle Fermat spiral (uniform UV-plane coverage)
    - 'linear_rake': Equispaced parallel linear rake for parallel pushbroom scans

    Parameters
    ----------
    pattern : str, optional
        Formation pattern geometry ('concentric', 'hexagonal', 'spiral', 'linear_rake').
    num_satellites : int, optional
        Total number of spacecraft in the swarm (default: 6).
    radius_km : float or astropy.units.Quantity, optional
        Outer radius of the formation in kilometers (default: 10.0 km).

    Returns
    -------
    dict
        Dictionary containing:
        - 'pattern': selected pattern
        - 'num_satellites': satellite count
        - 'radius_km': envelope radius
        - 'positions': list of dicts with 'id', 'x_km', 'y_km', 'r_km', 'theta_deg'
        - 'max_baseline_km': maximum inter-satellite separation distance
        - 'mean_separation_km': average distance between neighboring satellites
    """
    if isinstance(radius_km, u.Quantity):
        r_max = float(radius_km.to(u.km).value)
    else:
        r_max = float(radius_km)

    n = max(1, int(num_satellites))
    pat = pattern.lower().strip()
    positions = []

    if n == 1:
        positions.append({"id": 1, "x_km": 0.0, "y_km": 0.0, "r_km": 0.0, "theta_deg": 0.0})

    elif pat == "hexagonal":
        # Hexagonal grid: 1 at center (if odd/>=7), remaining on hexagon vertices/rings
        if n == 7:
            positions.append({"id": 1, "x_km": 0.0, "y_km": 0.0, "r_km": 0.0, "theta_deg": 0.0})
            hex_angles = np.linspace(0, 2.0 * np.pi, 6, endpoint=False)
            for i, ang in enumerate(hex_angles, start=2):
                x = r_max * np.cos(ang)
                y = r_max * np.sin(ang)
                positions.append({
                    "id": i,
                    "x_km": float(round(x, 4)),
                    "y_km": float(round(y, 4)),
                    "r_km": float(round(r_max, 4)),
                    "theta_deg": float(round(np.degrees(ang), 2)),
                })
        else:
            # General regular polygon
            angles = np.linspace(0, 2.0 * np.pi, n, endpoint=False)
            for i, ang in enumerate(angles, start=1):
                x = r_max * np.cos(ang)
                y = r_max * np.sin(ang)
                positions.append({
                    "id": i,
                    "x_km": float(round(x, 4)),
                    "y_km": float(round(y, 4)),
                    "r_km": float(round(r_max, 4)),
                    "theta_deg": float(round(np.degrees(ang), 2)),
                })

    elif pat == "spiral":
        # Golden-angle Fermat spiral (sunflower distribution)
        golden_angle_rad = np.pi * (3.0 - np.sqrt(5.0))  # ≈ 137.508°
        for i in range(n):
            if i == 0:
                r_i = 0.0
                theta_i = 0.0
            else:
                r_i = r_max * np.sqrt(float(i) / float(n - 1))
                theta_i = (i * golden_angle_rad) % (2.0 * np.pi)
            x = r_i * np.cos(theta_i)
            y = r_i * np.sin(theta_i)
            positions.append({
                "id": i + 1,
                "x_km": float(round(x, 4)),
                "y_km": float(round(y, 4)),
                "r_km": float(round(r_i, 4)),
                "theta_deg": float(round(np.degrees(theta_i), 2)),
            })

    elif pat == "linear_rake":
        # Linear rake distributed along X with Y=0
        xs = np.linspace(-r_max, r_max, n)
        for i, x in enumerate(xs, start=1):
            positions.append({
                "id": i,
                "x_km": float(round(x, 4)),
                "y_km": 0.0,
                "r_km": float(round(abs(x), 4)),
                "theta_deg": 0.0 if x >= 0 else 180.0,
            })

    else:
        # Default 'concentric': 1 center craft + regular ring, or dual rings
        if n >= 6 and n % 2 == 0:
            # Dual concentric rings (inner at 0.5 * r_max, outer at r_max)
            n_inner = n // 3
            n_outer = n - n_inner
            ang_inner = np.linspace(0, 2.0 * np.pi, n_inner, endpoint=False)
            ang_outer = np.linspace(0, 2.0 * np.pi, n_outer, endpoint=False) + (np.pi / n_outer)

            pid = 1
            for ang in ang_inner:
                x = 0.5 * r_max * np.cos(ang)
                y = 0.5 * r_max * np.sin(ang)
                positions.append({
                    "id": pid,
                    "x_km": float(round(x, 4)),
                    "y_km": float(round(y, 4)),
                    "r_km": float(round(0.5 * r_max, 4)),
                    "theta_deg": float(round(np.degrees(ang), 2)),
                })
                pid += 1

            for ang in ang_outer:
                x = r_max * np.cos(ang)
                y = r_max * np.sin(ang)
                positions.append({
                    "id": pid,
                    "x_km": float(round(x, 4)),
                    "y_km": float(round(y, 4)),
                    "r_km": float(round(r_max, 4)),
                    "theta_deg": float(round(np.degrees(ang), 2)),
                })
                pid += 1
        else:
            # Single ring with optional center craft
            has_center = (n % 2 == 1 and n >= 3)
            pid = 1
            if has_center:
                positions.append({"id": pid, "x_km": 0.0, "y_km": 0.0, "r_km": 0.0, "theta_deg": 0.0})
                pid += 1
                ring_n = n - 1
            else:
                ring_n = n

            angles = np.linspace(0, 2.0 * np.pi, ring_n, endpoint=False)
            for ang in angles:
                x = r_max * np.cos(ang)
                y = r_max * np.sin(ang)
                positions.append({
                    "id": pid,
                    "x_km": float(round(x, 4)),
                    "y_km": float(round(y, 4)),
                    "r_km": float(round(r_max, 4)),
                    "theta_deg": float(round(np.degrees(ang), 2)),
                })
                pid += 1

    # Compute baselines between pairs
    all_x = [p["x_km"] for p in positions]
    all_y = [p["y_km"] for p in positions]
    dists = []
    for i in range(n):
        for j in range(i + 1, n):
            d = np.hypot(all_x[i] - all_x[j], all_y[i] - all_y[j])
            dists.append(d)

    max_baseline = float(max(dists)) if dists else 0.0
    mean_sep = float(np.mean(dists)) if dists else 0.0

    return {
        "pattern": pat,
        "num_satellites": n,
        "radius_km": float(r_max),
        "positions": positions,
        "max_baseline_km": float(round(max_baseline, 4)),
        "mean_separation_km": float(round(mean_sep, 4)),
    }
