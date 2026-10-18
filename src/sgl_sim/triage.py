"""
SGL Exoplanet Feasibility Classifier, Sky Efficiency Map & Rotational Motion-Blur Swarm Analyzer.

Provides:
1. compute_motion_blur: Single-craft vs. swarm scan time, fuel Delta-V, and rotational motion-blur modeling.
2. score_exoplanet_candidate: Universal SGL feasibility index (0-100), sub-scores, and Tier classification.
3. get_ranked_catalog: Ranked exoplanet catalog evaluated across SGL mission parameters.
4. generate_sky_efficiency_map: Full-sky grid of Solar Lens efficiency (ecliptic belt & galactic plane avoidance).
5. check_mission_coalignment: Checks if a target can be co-observed by an existing SGL trajectory corridor.
"""

from typing import Dict, Any, List, Optional, Union
import numpy as np

import astropy.units as u
from astropy.coordinates import SkyCoord, HeliocentricTrueEcliptic
from astropy.constants import c as C_ASTROPY

from sgl_sim.relativity import AU_SI, PC_SI, C_SI, _to_si_value
from sgl_sim.orbital import image_cylinder_diameter
from sgl_sim.deconvolution import (
    generate_exoplanet_map,
    wiener_deconvolution,
    compute_rmse,
    compute_ssim,
)
from sgl_sim.optics import generate_2d_psf

# Earth radius in meters
R_EARTH_SI = 6.371e6

# 12 Curated Exoplanet Candidates for Triage & Ranking
CATALOG_12_CANDIDATES: List[Dict[str, Any]] = [
    {
        "name": "TRAPPIST-1 e",
        "ra_deg": 346.6224,
        "dec_deg": -5.0414,
        "dist_pc": 12.43,
        "radius_earth": 0.920,
        "rot_period_hrs": 146.4,
        "tidally_locked": True,
        "host_star_mag": 18.8,
        "proper_motion_mas_yr": 1005.0,
        "description": "Temperate Earth-sized planet in the TRAPPIST-1 habitable zone; near-ecliptic plane.",
    },
    {
        "name": "Ross 128 b",
        "ra_deg": 176.9350,
        "dec_deg": 0.8045,
        "dist_pc": 3.37,
        "radius_earth": 1.11,
        "rot_period_hrs": 237.6,
        "tidally_locked": True,
        "host_star_mag": 11.1,
        "proper_motion_mas_yr": 1362.0,
        "description": "Nearby temperate world around quiet M dwarf; directly on the celestial equator/ecliptic.",
    },
    {
        "name": "TRAPPIST-1 d",
        "ra_deg": 346.6224,
        "dec_deg": -5.0414,
        "dist_pc": 12.43,
        "radius_earth": 0.788,
        "rot_period_hrs": 97.2,
        "tidally_locked": True,
        "host_star_mag": 18.8,
        "proper_motion_mas_yr": 1005.0,
        "description": "Inner habitable zone planet in the TRAPPIST-1 multi-planet corridor.",
    },
    {
        "name": "TRAPPIST-1 f",
        "ra_deg": 346.6224,
        "dec_deg": -5.0414,
        "dist_pc": 12.43,
        "radius_earth": 1.045,
        "rot_period_hrs": 220.8,
        "tidally_locked": True,
        "host_star_mag": 18.8,
        "proper_motion_mas_yr": 1005.0,
        "description": "Outer habitable zone volatile-rich candidate in the TRAPPIST-1 corridor.",
    },
    {
        "name": "Proxima Centauri b",
        "ra_deg": 217.4289,
        "dec_deg": -62.6795,
        "dist_pc": 1.301,
        "radius_earth": 1.03,
        "rot_period_hrs": 268.3,
        "tidally_locked": True,
        "host_star_mag": 11.1,
        "proper_motion_mas_yr": 3859.0,
        "description": "Closest known exoplanet; maximum optical photon flux, high ecliptic inclination.",
    },
    {
        "name": "Wolf 1061 c",
        "ra_deg": 247.5833,
        "dec_deg": -12.6639,
        "dist_pc": 4.31,
        "radius_earth": 1.66,
        "rot_period_hrs": 429.6,
        "tidally_locked": True,
        "host_star_mag": 10.1,
        "proper_motion_mas_yr": 1157.0,
        "description": "Nearby super-Earth in the habitable zone at moderate ecliptic inclination.",
    },
    {
        "name": "LHS 1140 b",
        "ra_deg": 11.2475,
        "dec_deg": -15.2705,
        "dist_pc": 14.99,
        "radius_earth": 1.73,
        "rot_period_hrs": 314.4,
        "tidally_locked": True,
        "host_star_mag": 14.1,
        "proper_motion_mas_yr": 676.0,
        "description": "Dense super-Earth around inactive M dwarf; high atmospheric retention.",
    },
    {
        "name": "Teegarden's Star b",
        "ra_deg": 43.2758,
        "dec_deg": 16.8647,
        "dist_pc": 3.83,
        "radius_earth": 1.05,
        "rot_period_hrs": 117.6,
        "tidally_locked": True,
        "host_star_mag": 15.1,
        "proper_motion_mas_yr": 6312.0,
        "description": "Very high Earth similarity index (ESI=0.95); large proper-motion lateral drift.",
    },
    {
        "name": "Tau Ceti e",
        "ra_deg": 26.0170,
        "dec_deg": -15.9375,
        "dist_pc": 3.65,
        "radius_earth": 1.80,
        "rot_period_hrs": 35.0,
        "tidally_locked": False,
        "host_star_mag": 3.5,
        "proper_motion_mas_yr": 1920.0,
        "description": "Candidate around solar analog G-dwarf; rotating non-locked world requiring swarm.",
    },
    {
        "name": "Luyten b",
        "ra_deg": 111.8542,
        "dec_deg": 5.2250,
        "dist_pc": 3.80,
        "radius_earth": 1.18,
        "rot_period_hrs": 446.4,
        "tidally_locked": True,
        "host_star_mag": 9.9,
        "proper_motion_mas_yr": 3737.0,
        "description": "Temperate super-Earth (1.35 M_earth) around GJ 273 near the ecliptic.",
    },
    {
        "name": "TOI-700 d",
        "ra_deg": 97.4371,
        "dec_deg": -65.6744,
        "dist_pc": 31.13,
        "radius_earth": 1.14,
        "rot_period_hrs": 897.6,
        "tidally_locked": True,
        "host_star_mag": 13.1,
        "proper_motion_mas_yr": 153.0,
        "description": "NASA TESS discovered habitable-zone planet; highly inclined ecliptic polar trajectory.",
    },
    {
        "name": "Kepler-186 f",
        "ra_deg": 298.6500,
        "dec_deg": 44.1500,
        "dist_pc": 178.5,
        "radius_earth": 1.17,
        "rot_period_hrs": 312.0,
        "tidally_locked": True,
        "host_star_mag": 14.6,
        "proper_motion_mas_yr": 12.0,
        "description": "Historic first Earth-sized planet in habitable zone; distant target with low photon flux.",
    },
]


def _apply_rotational_blur_kernel(img: np.ndarray, eta_blur: float) -> np.ndarray:
    """
    Apply longitudinal (East-West) rotational motion-blur smearing along latitude lines.

    Parameters
    ----------
    img : np.ndarray
        2D image matrix of shape (N, N).
    eta_blur : float
        Motion blur smearing factor. If <= 1.0, no blur is applied.

    Returns
    -------
    np.ndarray
        Blurred 2D matrix.
    """
    if eta_blur <= 1.0:
        return img.copy()

    n = img.shape[0]
    k_max = min(n, max(2, int(np.ceil(eta_blur))))
    out = np.zeros_like(img, dtype=float)

    for r in range(n):
        # Normalized latitude from -1 (south pole) to +1 (north pole)
        y = (r - (n - 1) / 2.0) / max(1.0, ((n - 1) / 2.0))
        cos_lat = np.sqrt(max(0.0, 1.0 - y**2))
        kr = max(1, int(round(k_max * cos_lat)))

        if kr <= 1:
            out[r, :] = img[r, :]
        else:
            kernel = np.ones(kr, dtype=float) / float(kr)
            padded = np.pad(img[r, :], kr, mode="wrap")
            conv = np.convolve(padded, kernel, mode="same")
            out[r, :] = conv[kr:-kr]

    return out


def compute_motion_blur(
    image_diameter_km: float,
    grid_pixels: int = 32,
    planet_rot_period_hours: float = 24.0,
    tidally_locked: bool = False,
    num_satellites: int = 1,
    integration_time_per_pixel_s: float = 10.0,
    max_lateral_accel_m_s2: float = 1e-4,
    v_drift_m_s: float = 0.0,
    ground_truth: Optional[np.ndarray] = None,
    snr: float = 25.0,
) -> Dict[str, Any]:
    """
    Analyze rotational motion blur and compute scan time & Delta-V for a single craft vs. swarm.

    Parameters
    ----------
    image_diameter_km : float
        Projected exoplanet image cylinder diameter at receiver distance z_rec.
    grid_pixels : int, optional
        Image grid dimension (default: 32 for 32x32).
    planet_rot_period_hours : float, optional
        Planet rotation period in hours (default: 24.0 h).
    tidally_locked : bool, optional
        Whether the planet is tidally locked (default: False).
    num_satellites : int, optional
        Number of optical receiver spacecraft in the fleet (default: 1).
    integration_time_per_pixel_s : float, optional
        Integration dwell time per pixel in seconds (default: 10.0 s).
    max_lateral_accel_m_s2 : float, optional
        Maximum lateral spacecraft thruster acceleration (default: 1e-4 m/s²).
    v_drift_m_s : float, optional
        Focal-line lateral drift velocity from target proper motion (m/s).
    ground_truth : np.ndarray, optional
        Optional ground truth albedo map. If None, generated automatically.
    snr : float, optional
        Signal-to-noise ratio for Wiener reconstruction (default: 25.0).

    Returns
    -------
    dict
        Dictionary containing scan duration, blur metrics (eta_blur), fuel Delta-V,
        RMSE, SSIM, and 2D reconstructed matrices.
    """
    n_pix = max(8, int(grid_pixels))
    n_sat = max(1, int(num_satellites))
    t_int_s = max(1.0, float(integration_time_per_pixel_s))
    p_rot_h = max(0.5, float(planet_rot_period_hours))
    d_img_m = max(100.0, float(image_diameter_km) * 1000.0)

    # 1. Image Resolution & Scan Duration
    total_pixels = n_pix * n_pix
    pixels_per_sat = total_pixels / float(n_sat)
    total_scan_s = pixels_per_sat * t_int_s
    total_scan_hours = total_scan_s / 3600.0
    total_scan_days = total_scan_s / 86400.0

    # 2. Maximum allowable dwell time before rotational blur exceeds 1 pixel
    # t_max_blur = P_rot / (pi * N_pix)
    t_max_blur_hours = p_rot_h / (np.pi * float(n_pix))
    t_max_blur_s = t_max_blur_hours * 3600.0

    # 3. Motion Blur Smearing Factor (eta_blur)
    if tidally_locked:
        # Minimal atmospheric circulation / cloud motion blur
        eta_blur = 0.05
    else:
        # Scan duration divided by blur threshold
        eta_blur = float(total_scan_hours / max(1e-4, t_max_blur_hours))

    # 4. Spacecraft Delta-V Fuel Budget per satellite
    # Lateral raster/spiral repositioning across footprint:
    pixel_width_m = d_img_m / float(n_pix)
    # Travel length per satellite across footprint
    travel_length_m = (d_img_m * float(n_pix)) / float(n_sat)
    v_reposition_m_s = travel_length_m / max(1.0, total_scan_s)
    # Lateral impulses for start/stop raster steps
    delta_v_reposition = float(2.0 * pixels_per_sat * v_reposition_m_s * 0.01)

    # Station-keeping against proper-motion lateral drift (v_drift_m_s)
    # Delta-v = v_drift * (total_scan_s / 1 year)
    yr_sec = 365.25 * 86400.0
    delta_v_drift = float(v_drift_m_s * (total_scan_s / yr_sec))
    total_delta_v_m_s = float(delta_v_reposition + delta_v_drift)

    # 5. Image Reconstruction with Motion Blur
    if ground_truth is None or ground_truth.shape != (n_pix, n_pix):
        gt = generate_exoplanet_map(grid_size=n_pix, seed=42)
    else:
        gt = np.asarray(ground_truth, dtype=float)

    # Base SGL Wiener deconvolution
    psf_kernel = generate_2d_psf(grid_size=n_pix, pixel_scale_m=1.0, z_rec=650.0 * AU_SI)
    deconv_base = wiener_deconvolution(ground_truth=gt, psf_kernel=psf_kernel, snr=snr)
    reconstructed_base = deconv_base["deconvolved"]

    # Apply rotational blur kernel if eta_blur > 1.0
    if eta_blur > 1.0:
        reconstructed = _apply_rotational_blur_kernel(reconstructed_base, eta_blur)
    else:
        reconstructed = reconstructed_base.copy()

    rmse = compute_rmse(gt, reconstructed)
    ssim = compute_ssim(gt, reconstructed)

    return {
        "num_satellites": n_sat,
        "grid_pixels": n_pix,
        "image_diameter_km": float(image_diameter_km),
        "planet_rot_period_hours": p_rot_h,
        "tidally_locked": bool(tidally_locked),
        "scan_time_seconds": float(total_scan_s),
        "scan_time_hours": float(total_scan_hours),
        "scan_time_days": float(total_scan_days),
        "t_max_blur_hours": float(t_max_blur_hours),
        "eta_blur": float(eta_blur),
        "is_blurred": bool(eta_blur > 1.0),
        "delta_v_reposition_m_s": float(delta_v_reposition),
        "delta_v_drift_m_s": float(delta_v_drift),
        "total_delta_v_m_s": float(total_delta_v_m_s),
        "rmse": float(rmse),
        "ssim": float(ssim),
        "reconstructed_image": reconstructed.tolist(),
        "ground_truth": gt.tolist(),
    }


def score_exoplanet_candidate(
    name: str,
    ra_deg: float,
    dec_deg: float,
    dist_pc: float,
    radius_earth: float = 1.0,
    rot_period_hrs: float = 24.0,
    tidally_locked: bool = False,
    host_star_mag: float = 11.0,
    proper_motion_mas_yr: float = 100.0,
    z_rec_au: float = 650.0,
) -> Dict[str, Any]:
    """
    Compute the universal SGL Feasibility Index (0-100) and mission Tier classification.

    Parameters
    ----------
    name : str
        Target exoplanet name.
    ra_deg : float
        Right Ascension in degrees (ICRS).
    dec_deg : float
        Declination in degrees (ICRS).
    dist_pc : float
        Distance in parsecs.
    radius_earth : float, optional
        Planet radius in Earth radii (default: 1.0).
    rot_period_hrs : float, optional
        Rotation period in hours (default: 24.0).
    tidally_locked : bool, optional
        Whether target is tidally locked (default: False).
    host_star_mag : float, optional
        Host star apparent magnitude (default: 11.0).
    proper_motion_mas_yr : float, optional
        Total proper motion in mas/yr (default: 100.0).
    z_rec_au : float, optional
        Receiver focal distance in AU (default: 650.0).

    Returns
    -------
    dict
        Feasibility scores, antipodal coordinates, logistics, and mission tier.
    """
    ra = float(ra_deg) % 360.0
    dec = float(dec_deg)
    dist = max(0.5, float(dist_pc))
    r_exo = max(0.2, float(radius_earth))
    p_rot = max(0.5, float(rot_period_hrs))
    pm = max(0.0, float(proper_motion_mas_yr))
    z_au = float(z_rec_au)

    # 1. Transform to Telescope Deployment Antipode
    tel_ra = float((ra + 180.0) % 360.0)
    tel_dec = float(-dec)

    tel_coord = SkyCoord(
        ra=tel_ra * u.deg,
        dec=tel_dec * u.deg,
        distance=z_au * u.AU,
        frame="icrs",
    )
    constellation = tel_coord.get_constellation()

    # Heliocentric True Ecliptic coordinates
    ecl = tel_coord.transform_to(HeliocentricTrueEcliptic())
    beta_ecl = float(ecl.lat.deg)
    lambda_ecl = float(ecl.lon.deg)

    # Galactic coordinates
    gal = tel_coord.galactic
    b_gal = float(gal.b.deg)
    l_gal = float(gal.l.deg)

    # 2. Sub-Score 1: SNR Score (30%)
    # Planetary photon flux scales as (R_exo / 1.0)^2 / (dist_pc / 1.3)^2
    s_rel = (r_exo**2) / max(1e-4, (dist / 1.3)**2)
    snr_score = float(np.clip((np.log10(s_rel) + 3.0) / 3.0, 0.05, 1.0))

    # 3. Sub-Score 2: Scan Logistics Score (25%)
    # Optimal when 1.5 km <= D_img <= 15 km and v_drift < 35 m/s
    d_img_km = 2.0 * (r_exo * 6371.0) * (z_au * AU_SI) / (dist * PC_SI)

    mu_rad_s = pm * (np.pi / (180.0 * 3600.0 * 1000.0)) / (365.25 * 86400.0)
    v_drift_m_s = (z_au * AU_SI) * mu_rad_s

    # Image diameter sizing score
    if 1.5 <= d_img_km <= 15.0:
        s_dimg = 1.0
    elif d_img_km < 1.5:
        s_dimg = max(0.15, d_img_km / 1.5)
    else:
        s_dimg = max(0.1, 1.0 - (d_img_km - 15.0) / 45.0)

    # Proper motion drift score
    if v_drift_m_s <= 35.0:
        s_drift = 1.0 - 0.25 * (v_drift_m_s / 35.0)
    else:
        s_drift = max(0.1, 0.75 - 0.65 * ((v_drift_m_s - 35.0) / 100.0))

    scan_logistics_score = float(np.clip(0.6 * s_dimg + 0.4 * s_drift, 0.05, 1.0))

    # 4. Sub-Score 3: Ecliptic Access Score (25%)
    # cos^2(beta_ecl), rewarding low-inclination ecliptic targets (Jupiter / Solar Oberth assist)
    ecliptic_access_score = float(np.cos(np.radians(beta_ecl))**2)

    # 5. Sub-Score 4: Rotational Blur Immunity Score (20%)
    if tidally_locked:
        blur_immunity_score = 0.98
    else:
        # Based on rotation period compared to nominal 24h
        if p_rot >= 24.0:
            blur_immunity_score = float(np.clip(0.75 + 0.25 * min(1.0, p_rot / 100.0), 0.75, 1.0))
        else:
            blur_immunity_score = float(np.clip(max(0.15, 0.75 * (p_rot / 24.0)), 0.15, 0.75))

    # 6. Composite SGL Feasibility Index (0 - 100)
    sgl_score = float(
        100.0 * (
            0.30 * snr_score
            + 0.25 * scan_logistics_score
            + 0.25 * ecliptic_access_score
            + 0.20 * blur_immunity_score
        )
    )

    # 7. Mission Tier Classification
    if sgl_score >= 72.0:
        tier = "Tier 1: Prime Swarm/Single Target"
    elif abs(beta_ecl) > 30.0:
        tier = "Tier 3: High Launch Delta-V (Out of Ecliptic)"
    elif (not tidally_locked and p_rot < 24.0) or d_img_km > 15.0:
        tier = "Tier 2: Swarm Required (Fast Rotator / Large Image)"
    elif sgl_score >= 50.0:
        tier = "Tier 2: Swarm Required (Fast Rotator / Large Image)"
    else:
        tier = "Inviable"

    return {
        "name": str(name),
        "ra_deg": float(ra),
        "dec_deg": float(dec),
        "dist_pc": float(dist),
        "dist_ly": float(dist * 3.26156),
        "radius_earth": float(r_exo),
        "rot_period_hrs": float(p_rot),
        "tidally_locked": bool(tidally_locked),
        "proper_motion_mas_yr": float(pm),
        
        # Antipodal Coordinates
        "telescope_ra_deg": float(tel_ra),
        "telescope_dec_deg": float(tel_dec),
        "telescope_constellation": constellation,
        "ecliptic_lon_deg": float(lambda_ecl),
        "ecliptic_lat_deg": float(beta_ecl),
        "galactic_l_deg": float(l_gal),
        "galactic_b_deg": float(b_gal),

        # Logistics
        "image_diameter_km": float(d_img_km),
        "v_drift_m_s": float(v_drift_m_s),

        # 4 Sub-Scores
        "snr_score": float(snr_score),
        "scan_logistics_score": float(scan_logistics_score),
        "ecliptic_access_score": float(ecliptic_access_score),
        "blur_immunity_score": float(blur_immunity_score),

        # Composite & Tier
        "sgl_score": float(round(sgl_score, 1)),
        "tier": tier,
    }


def get_ranked_catalog(z_rec_au: float = 650.0) -> List[Dict[str, Any]]:
    """
    Evaluate and rank the 12 curated exoplanet candidates sorted by SGL Feasibility Score.

    Parameters
    ----------
    z_rec_au : float, optional
        Focal receiver distance in AU (default: 650.0).

    Returns
    -------
    list
        Ranked list of evaluated candidates sorted by sgl_score descending.
    """
    ranked = []
    for cand in CATALOG_12_CANDIDATES:
        res = score_exoplanet_candidate(
            name=cand["name"],
            ra_deg=cand["ra_deg"],
            dec_deg=cand["dec_deg"],
            dist_pc=cand["dist_pc"],
            radius_earth=cand["radius_earth"],
            rot_period_hrs=cand["rot_period_hrs"],
            tidally_locked=cand["tidally_locked"],
            host_star_mag=cand["host_star_mag"],
            proper_motion_mas_yr=cand["proper_motion_mas_yr"],
            z_rec_au=z_rec_au,
        )
        res["description"] = cand.get("description", "")
        ranked.append(res)

    ranked.sort(key=lambda x: x["sgl_score"], reverse=True)
    return ranked


def generate_sky_efficiency_map(n_ra: int = 72, n_dec: int = 36) -> Dict[str, Any]:
    """
    Generate a full-sky grid of Solar Lens efficiency combining Ecliptic proximity
    and Galactic plane avoidance.

    Parameters
    ----------
    n_ra : int, optional
        Number of Right Ascension grid points (default: 72, step = 5 deg).
    n_dec : int, optional
        Number of Declination grid points (default: 36, step = 5 deg).

    Returns
    -------
    dict
        Dictionary containing 'ra_grid', 'dec_grid', 'efficiency_matrix', and 'candidates'.
    """
    ra_1d = np.linspace(0.0, 360.0, n_ra, endpoint=False)
    dec_1d = np.linspace(-90.0, 90.0, n_dec)
    ra_grid, dec_grid = np.meshgrid(ra_1d, dec_1d)

    tel_ra = (ra_grid + 180.0) % 360.0
    tel_dec = -dec_grid

    # Vectorized celestial coordinate conversion
    coords = SkyCoord(
        ra=tel_ra.ravel() * u.deg,
        dec=tel_dec.ravel() * u.deg,
        distance=650.0 * u.AU,
        frame="icrs",
    )
    ecl = coords.transform_to(HeliocentricTrueEcliptic())
    beta_ecl = ecl.lat.deg.reshape(n_dec, n_ra)
    ecl_score = np.cos(np.radians(beta_ecl))**2

    gal = coords.galactic
    b_gal = gal.b.deg.reshape(n_dec, n_ra)
    gal_factor = np.where(np.abs(b_gal) < 10.0, 0.4 + 0.6 * (np.abs(b_gal) / 10.0), 1.0)

    efficiency = np.clip(ecl_score * gal_factor, 0.0, 1.0)

    # Add antipodal coordinates of the 12 candidates for map overlay
    candidate_markers = []
    for cand in CATALOG_12_CANDIDATES:
        cand_tel_ra = float((cand["ra_deg"] + 180.0) % 360.0)
        cand_tel_dec = float(-cand["dec_deg"])
        candidate_markers.append({
            "name": cand["name"],
            "target_ra": cand["ra_deg"],
            "target_dec": cand["dec_deg"],
            "tel_ra": cand_tel_ra,
            "tel_dec": cand_tel_dec,
            "dist_pc": cand["dist_pc"],
        })

    return {
        "n_ra": n_ra,
        "n_dec": n_dec,
        "ra_grid": ra_1d.tolist(),
        "dec_grid": dec_1d.tolist(),
        "efficiency_matrix": efficiency.tolist(),
        "candidates": candidate_markers,
    }


def check_mission_coalignment(
    active_missions: List[Dict[str, Any]],
    new_target_ra: float,
    new_target_dec: float,
    max_deflection_deg: float = 3.0,
) -> Dict[str, Any]:
    """
    Check if a newly discovered target or secondary planet falls within the reachable
    lateral deflection corridor of an existing or planned SGL mission.

    Parameters
    ----------
    active_missions : list of dict
        List of deployed or candidate mission trajectories, each having 'name',
        'ra_deg', and 'dec_deg'.
    new_target_ra : float
        Right Ascension of new exoplanet (degrees).
    new_target_dec : float
        Declination of new exoplanet (degrees).
    max_deflection_deg : float, optional
        Maximum allowable angular deflection achievable by solar sail / ion engine (default: 3.0°).

    Returns
    -------
    dict
        Dictionary containing 'is_coaligned', 'matching_missions', and summary message.
    """
    ra_new = float(new_target_ra) % 360.0
    dec_new = float(new_target_dec)
    coord_new = SkyCoord(ra=ra_new * u.deg, dec=dec_new * u.deg, frame="icrs")

    matching = []
    is_coaligned = False

    for m in active_missions:
        m_ra = float(m.get("ra_deg", m.get("ra", 0.0))) % 360.0
        m_dec = float(m.get("dec_deg", m.get("dec", 0.0)))
        m_coord = SkyCoord(ra=m_ra * u.deg, dec=m_dec * u.deg, frame="icrs")

        sep_deg = float(coord_new.separation(m_coord).deg)
        feasible = sep_deg <= float(max_deflection_deg)

        if feasible:
            is_coaligned = True

        matching.append({
            "target_name": m.get("name", "Unknown Mission"),
            "separation_deg": float(round(sep_deg, 3)),
            "deflection_feasible": bool(feasible),
            # Estimated lateral deflection delta-v at 650 AU (~ 1 km/s per 1 degree deflection)
            "deflection_dv_km_s": float(round(sep_deg * 0.85, 2)),
        })

    matching.sort(key=lambda x: x["separation_deg"])

    if is_coaligned:
        top = matching[0]
        msg = (
            f"Co-aligned with {top['target_name']} (Δθ = {top['separation_deg']:.2f}° ≤ {max_deflection_deg}°)! "
            f"A single deployed telescope fleet can survey both targets via minor trajectory deflection."
        )
    else:
        min_sep = matching[0]["separation_deg"] if matching else 999.0
        msg = f"Independent deployment required. Nearest candidate mission is {min_sep:.1f}° away (> {max_deflection_deg}°)."

    return {
        "is_coaligned": bool(is_coaligned),
        "matching_missions": matching,
        "message": msg,
    }
