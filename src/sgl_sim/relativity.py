"""
Relativistic Geodesics and Lensing Geometry in Schwarzschild Spacetime.

This module computes Schwarzschild radii, critical photon capture parameters,
weak-field deflection angles, focal line crossing distances, and strong-field
numerical null geodesics using astropy constants and units.
"""

from typing import Dict, Any, Tuple, Optional, Union
import numpy as np
from scipy.integrate import solve_ivp
from astropy import constants as const
from astropy import units as u

# Standard physical constants in SI
G_SI = const.G.value
C_SI = const.c.value
M_SUN_SI = const.M_sun.value
R_SUN_SI = const.R_sun.value
AU_SI = const.au.value
PC_SI = const.pc.value


def schwarzschild_radius(mass: Union[float, u.Quantity]) -> float:
    """
    Calculate the Schwarzschild radius of a spherically symmetric body.

    R_s = 2 * G * M / c^2

    Parameters
    ----------
    mass : float or astropy.units.Quantity
        Mass of the gravitating body. If float, assumed in kg.

    Returns
    -------
    float
        Schwarzschild radius in meters.
    """
    if isinstance(mass, u.Quantity):
        m_val = mass.to(u.kg).value
    else:
        m_val = float(mass)
    return float(2.0 * G_SI * m_val / (C_SI**2))


def photon_sphere_radius(mass: Union[float, u.Quantity]) -> float:
    """
    Calculate the photon sphere radius (unstable circular photon orbit).

    r_ph = 1.5 * R_s = 3 * G * M / c^2

    Parameters
    ----------
    mass : float or astropy.units.Quantity
        Mass of the gravitating body. If float, assumed in kg.

    Returns
    -------
    float
        Photon sphere radius in meters.
    """
    return 1.5 * schwarzschild_radius(mass)


def critical_impact_parameter(mass: Union[float, u.Quantity]) -> float:
    """
    Calculate the critical impact parameter for photon capture in Schwarzschild spacetime.

    b_c = (3 * sqrt(3) / 2) * R_s ≈ 2.59807621135 * R_s

    Parameters
    ----------
    mass : float or astropy.units.Quantity
        Mass of the gravitating body. If float, assumed in kg.

    Returns
    -------
    float
        Critical impact parameter in meters.
    """
    rs = schwarzschild_radius(mass)
    return float((3.0 * np.sqrt(3.0) / 2.0) * rs)


def weak_deflection_angle(
    impact_param: Union[float, np.ndarray, u.Quantity],
    mass: Union[float, u.Quantity] = M_SUN_SI,
) -> Union[float, np.ndarray]:
    """
    Compute the Einstein weak-field deflection angle: alpha(b) = 2 * R_s / b.

    Parameters
    ----------
    impact_param : float, np.ndarray, or astropy.units.Quantity
        Impact parameter(s) b in meters.
    mass : float or astropy.units.Quantity, optional
        Lens mass in kg (default: 1 solar mass).

    Returns
    -------
    float or np.ndarray
        Deflection angle in radians.
    """
    if isinstance(impact_param, u.Quantity):
        b_val = impact_param.to(u.m).value
    else:
        b_val = np.asarray(impact_param, dtype=float)

    rs = schwarzschild_radius(mass)
    alpha = (2.0 * rs) / b_val
    if np.ndim(alpha) == 0:
        return float(alpha)
    return alpha


def focal_distance(
    impact_param: Union[float, np.ndarray, u.Quantity],
    mass: Union[float, u.Quantity] = M_SUN_SI,
    star_radius: Optional[Union[float, u.Quantity]] = R_SUN_SI,
) -> Dict[str, Any]:
    """
    Compute the axial focal crossing distance z(b) = b^2 / (2 * R_s).

    Rays with impact parameter b < star_radius are flagged as 'blocked_by_star'.

    Parameters
    ----------
    impact_param : float, np.ndarray, or astropy.units.Quantity
        Impact parameter(s) in meters.
    mass : float or astropy.units.Quantity, optional
        Lens mass in kg (default: 1 solar mass).
    star_radius : float or astropy.units.Quantity, optional
        Physical radius of the star in meters. If None, no blocking check.

    Returns
    -------
    dict
        Dictionary containing:
        - 'z_m': focal distance(s) in meters
        - 'z_au': focal distance(s) in Astronomical Units (AU)
        - 'blocked': boolean or boolean array indicating if ray is blocked
        - 'status': list or string of status tags ('ok' or 'blocked_by_star')
    """
    if isinstance(impact_param, u.Quantity):
        b = impact_param.to(u.m).value
    else:
        b = np.asarray(impact_param, dtype=float)

    if star_radius is not None:
        if isinstance(star_radius, u.Quantity):
            r_star = star_radius.to(u.m).value
        else:
            r_star = float(star_radius)
    else:
        r_star = 0.0

    rs = schwarzschild_radius(mass)
    z_m = (b**2) / (2.0 * rs)
    z_au = z_m / AU_SI
    blocked = b < r_star

    if np.ndim(b) == 0:
        status = "blocked_by_star" if bool(blocked) else "ok"
        return {
            "z_m": float(z_m),
            "z_au": float(z_au),
            "blocked": bool(blocked),
            "status": status,
        }
    else:
        status_list = ["blocked_by_star" if blk else "ok" for blk in blocked]
        return {
            "z_m": z_m,
            "z_au": z_au,
            "blocked": blocked,
            "status": status_list,
        }


def integrate_strong_geodesic(
    impact_param: float,
    mass: float = M_SUN_SI,
    x_start: float = -50.0,
    max_tau: float = 3.0 * np.pi,
    num_points: int = 400,
) -> Dict[str, Any]:
    """
    Integrate the exact null geodesic differential equation in Schwarzschild spacetime:
        d^2u/dphi^2 + u = (3/2) * R_s * u^2

    where u = 1/r. Uses scipy.integrate.solve_ivp (RK45).

    Flags rays with b <= b_c as 'captured_by_bh'. Returns 2D Cartesian
    trajectories (x, y) in units of meters and in normalized R_s units.

    Parameters
    ----------
    impact_param : float
        Impact parameter b in meters.
    mass : float, optional
        Black hole mass in kg (default: 1 solar mass).
    x_start : float, optional
        Starting x-coordinate in units of impact_param (negative, e.g. -50.0).
    max_tau : float, optional
        Maximum integration span in angular coordinate tau.
    num_points : int, optional
        Number of output trajectory sample points.

    Returns
    -------
    dict
        Dictionary containing:
        - 'status': 'captured_by_bh' or 'escaped'
        - 'b': impact parameter in meters
        - 'b_c': critical impact parameter in meters
        - 'x': array of x coordinates in meters
        - 'y': array of y coordinates in meters
        - 'x_rs': array of x coordinates in units of R_s
        - 'y_rs': array of y coordinates in units of R_s
        - 'r_min': closest approach distance in meters
    """
    rs = schwarzschild_radius(mass)
    bc = critical_impact_parameter(mass)
    b = float(impact_param)

    # Initial position in Cartesian coordinates
    # Start at x0 < 0, y0 = b
    x0 = x_start * abs(b)
    y0 = b
    r0 = np.sqrt(x0**2 + y0**2)
    phi0 = np.arctan2(y0, x0)  # in (0, pi]
    u0 = 1.0 / r0

    # Initial derivative with respect to tau = phi0 - phi
    # Since du/dtau = -du/dphi, and (du/dphi)^2 = 1/b^2 - u^2 + rs * u^3
    energy_term = (1.0 / (b**2)) - (u0**2) + (rs * (u0**3))
    v0 = np.sqrt(max(energy_term, 0.0))

    if b <= bc:
        is_captured = True
    else:
        is_captured = False

    # ODE system: y_vec = [u, v], with tau as independent variable
    # du/dtau = v
    # dv/dtau = (3/2) * rs * u^2 - u
    def ode_system(t, y_vec):
        u_val, v_val = y_vec
        du_dt = v_val
        dv_dt = 1.5 * rs * (u_val**2) - u_val
        return [du_dt, dv_dt]

    # Event 1: Photon captured inside event horizon (r <= 1.05 * R_s => u >= 1 / (1.05 * R_s))
    def event_capture(t, y_vec):
        return (1.0 / (1.05 * rs)) - y_vec[0]

    event_capture.terminal = True
    event_capture.direction = -1

    # Event 2: Photon escapes to infinity (r >= 2 * r0 => u <= 0.5 * u0)
    def event_escape(t, y_vec):
        # Only escape if past turning point (v_val < 0)
        if y_vec[1] < -1e-12:
            return y_vec[0] - (0.3 * u0)
        return 1.0

    event_escape.terminal = True
    event_escape.direction = -1

    t_eval = np.linspace(0.0, max_tau, num_points)

    sol = solve_ivp(
        ode_system,
        t_span=(0.0, max_tau),
        y0=[u0, v0],
        method="RK45",
        t_eval=None,
        events=[event_capture, event_escape],
        rtol=1e-8,
        atol=1e-10,
        max_step=0.05,
    )

    tau_arr = sol.t
    u_arr = sol.y[0]
    phi_arr = phi0 - tau_arr

    # Prevent division by zero
    u_clipped = np.clip(u_arr, 1e-18, 1.0 / (0.95 * rs))
    r_arr = 1.0 / u_clipped
    x_arr = r_arr * np.cos(phi_arr)
    y_arr = r_arr * np.sin(phi_arr)

    # Determine status
    if b <= bc or (len(sol.t_events[0]) > 0 and sol.t_events[0].size > 0):
        status = "captured_by_bh"
    else:
        status = "escaped"

    r_min = float(np.min(r_arr))

    return {
        "status": status,
        "b": b,
        "b_c": bc,
        "x": x_arr,
        "y": y_arr,
        "x_rs": x_arr / rs,
        "y_rs": y_arr / rs,
        "r_min": r_min,
    }
