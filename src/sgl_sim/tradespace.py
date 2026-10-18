"""
Trade-Space Exploration and Design Matrix Analysis for SGL Spacecraft Missions.

This module evaluates 2D mission tradespace matrices over receiver distance z_rec
(550 AU to 950 AU) and telescope aperture (0.5 m to 5.0 m), calculating expected SNR
and required per-pixel integration time to reach a target science threshold.
"""

from typing import Dict, Any, List, Optional
import numpy as np

from sgl_sim.relativity import AU_SI, PC_SI, M_SUN_SI
from sgl_sim.deconvolution import calculate_snr


def evaluate_tradespace(
    z_min_au: float = 550.0,
    z_max_au: float = 950.0,
    n_z: int = 15,
    aperture_min_m: float = 0.5,
    aperture_max_m: float = 5.0,
    n_aperture: int = 15,
    ref_integration_time_s: float = 86400.0,
    target_snr: float = 10.0,
    distance_source: float = 1.3 * PC_SI,
    exoplanet_radius: float = 6.371e6,
    wavelength: float = 1.0e-6,
    mass: float = M_SUN_SI,
) -> Dict[str, Any]:
    """
    Compute a 2D mission tradespace design matrix over (z_rec, aperture_m).

    Parameters
    ----------
    z_min_au : float, optional
        Minimum receiver distance in AU (default: 550 AU).
    z_max_au : float, optional
        Maximum receiver distance in AU (default: 950 AU).
    n_z : int, optional
        Number of grid points in distance.
    aperture_min_m : float, optional
        Minimum telescope aperture in meters (default: 0.5 m).
    aperture_max_m : float, optional
        Maximum telescope aperture in meters (default: 5.0 m).
    n_aperture : int, optional
        Number of grid points in aperture.
    ref_integration_time_s : float, optional
        Reference integration time per pixel in seconds (default: 1 day = 86400 s).
    target_snr : float, optional
        Target SNR threshold for integration time calculations (default: 10.0).
    distance_source : float, optional
        Distance to exoplanet host in meters.
    exoplanet_radius : float, optional
        Exoplanet physical radius in meters.
    wavelength : float, optional
        Observation wavelength in meters.
    mass : float, optional
        Lens mass in kg.

    Returns
    -------
    dict
        Dictionary containing:
        - 'z_au_grid': 1D array of z_rec in AU
        - 'aperture_m_grid': 1D array of apertures in meters
        - 'snr_matrix': 2D array of shape (n_z, n_aperture) with SNR values
        - 't_req_hours_matrix': 2D array of hours to achieve target_snr
        - 'target_snr': target SNR value
    """
    z_au_arr = np.linspace(z_min_au, z_max_au, n_z)
    aperture_arr = np.linspace(aperture_min_m, aperture_max_m, n_aperture)

    snr_matrix = np.zeros((n_z, n_aperture), dtype=float)
    t_req_hours_matrix = np.zeros((n_z, n_aperture), dtype=float)

    for i, z_au in enumerate(z_au_arr):
        z_m = z_au * AU_SI
        for j, ap_m in enumerate(aperture_arr):
            res = calculate_snr(
                z_rec=z_m,
                aperture_m=ap_m,
                integration_time_s=ref_integration_time_s,
                distance_source=distance_source,
                exoplanet_radius=exoplanet_radius,
                wavelength=wavelength,
                mass=mass,
            )
            snr_val = res["snr"]
            snr_matrix[i, j] = snr_val

            # In shot/background noise limited regime: SNR ∝ sqrt(t_int)
            # t_req = t_ref * (SNR_target / SNR_ref)^2
            if snr_val > 0:
                t_req_s = ref_integration_time_s * ((target_snr / snr_val) ** 2)
            else:
                t_req_s = 1e9
            t_req_hours_matrix[i, j] = float(t_req_s / 3600.0)

    return {
        "z_au_grid": z_au_arr,
        "aperture_m_grid": aperture_arr,
        "snr_matrix": snr_matrix,
        "t_req_hours_matrix": t_req_hours_matrix,
        "target_snr": float(target_snr),
    }
