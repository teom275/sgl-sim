"""
Physical image simulation for the solar gravitational lens (SGL).

This replaces the 1 m-pixel Wiener pipeline (docs/auditoria-fisica.md, findings
C2 and C3) with a forward model that follows Toth & Turyshev (2021, "Image
recovery with the SGL") and Toth & Turyshev (2023, "Imaging rotating and
orbiting exoplanets with the SGL").

**Geometry.** The planet's image in the focal region is a disk of diameter
``D = 2 R z / d``, split into ``N x N`` pixels of side ``D/N``. That is 0.1–1 km
for the targets here, against a 5 cm PSF core. A telescope parked on pixel
``i`` receives light from every source pixel ``j`` through the PSF tail
``mu ~ mu_0 / (pi k theta_E rho)``. In pixel units the blur matrix is

    K_ij = 1 / |r_i - r_j|          (i != j)
    K_ii = 4 ln(1 + sqrt 2) = 3.525  (the 1/r kernel integrated over its own pixel)

and the expected photon rate is
``P_unit * sum_j K_ij a_j / A_g + P_corona``, where ``P_unit`` and ``P_corona``
come from :func:`sgl_sim.radiometry.sgl_photon_budget`.

**Time.** Telescopes visit the disk pixels in raster order. ``n_telescopes``
craft share them, each spending ``t_pix`` per pixel. Meanwhile the planet
rotates with period ``P_rot``. A tidally locked planet still rotates, once per
orbit, relative to a distant observer. Each measurement therefore sees the
disk averaged over its own time window. Reconstruction assumes a static
image, so rotation during the scan smears the result. The blur stays below
about one pixel when the total scan time is under ``P_rot / (pi N)``.

**Reconstruction.** The model solves ``K a = y`` directly. Photon noise is
Gaussian with variance equal to the expected count.

**Not modelled yet.** Orbital phase (illumination), clouds, the host star's
light, the motion of the image across the focal plane (finding C4) and the
change in z while the spacecraft recedes.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Dict, Optional, Union

import numpy as np
from astropy import units as u

from sgl_sim.relativity import AU_SI, PC_SI, _to_si_value
from sgl_sim.radiometry import EARTH_RADIUS_M, integration_time_for_snr
from sgl_sim.reference_bodies import GLOBAL_MAPS, render_global_map
from sgl_sim.deconvolution import compute_rmse, compute_ssim

__all__ = [
    "SELF_KERNEL",
    "disk_pixels",
    "sgl_blur_matrix",
    "max_scan_time_for_sharp_image",
    "required_telescopes",
    "sharp_imaging_requirements",
    "simulate_sgl_observation",
]

#: Integral of 1/r over a unit square centred on the origin: 4 ln(1 + sqrt 2).
SELF_KERNEL = 4.0 * np.log(1.0 + np.sqrt(2.0))
_DISK_RADIUS = 0.95


@lru_cache(maxsize=8)
def disk_pixels(n: int):
    """Row/column indices of the pixels inside the planet disk (raster order)."""
    c = (np.arange(n) + 0.5) / n * 2.0 - 1.0
    xx, yy = np.meshgrid(c, -c)
    inside = np.hypot(xx, yy) <= _DISK_RADIUS
    rows, cols = np.nonzero(inside)
    return rows, cols


@lru_cache(maxsize=8)
def sgl_blur_matrix(n: int) -> np.ndarray:
    """SGL blur matrix ``K`` (n_disk x n_disk) for an ``n x n`` image, in pixel units."""
    rows, cols = disk_pixels(n)
    dr = rows[:, None] - rows[None, :]
    dc = cols[:, None] - cols[None, :]
    dist = np.hypot(dr, dc).astype(float)
    with np.errstate(divide="ignore"):
        k = 1.0 / dist
    np.fill_diagonal(k, SELF_KERNEL)
    return k


def max_scan_time_for_sharp_image(rot_period_hours: float, n_pixels: int) -> float:
    """Longest scan (hours) before rotation smears the equator by about one pixel: P_rot / (pi N)."""
    return float(rot_period_hours) / (np.pi * int(n_pixels))


def required_telescopes(per_pixel_s: float, n_pixels: int, rot_period_hours: float) -> int:
    """Telescopes needed to finish an ``N x N`` scan within ``P_rot / (pi N)``."""
    n_disk = len(disk_pixels(int(n_pixels))[0])
    t_max_s = max_scan_time_for_sharp_image(rot_period_hours, n_pixels) * 3600.0
    # Each telescope does a whole number of pixels: it fits floor(t_max / t_pix) of them.
    per_scope = int(np.floor(t_max_s / float(per_pixel_s)))
    if per_scope < 1:
        return n_disk  # even one pixel each is too slow; the aperture must grow
    return int(max(1, np.ceil(n_disk / per_scope)))


def sharp_imaging_requirements(per_pixel_s: float, n_pixels: int, rot_period_hours: float,
                               aperture_m: float = 1.0) -> Dict[str, float]:
    """
    What it takes to image an ``N x N`` rotating planet without smear.

    The swarm must finish within ``P_rot / (pi N)``. Each pixel's own
    integration must also fit inside that window: if ``t_pix`` exceeds it, no
    number of telescopes helps and the aperture must grow. In the
    corona-dominated regime ``t_pix ~ d^-3``, so the minimum aperture is
    ``d * (t_pix / t_max)^(1/3)``.
    """
    t_max_s = max_scan_time_for_sharp_image(rot_period_hours, n_pixels) * 3600.0
    possible = float(per_pixel_s) <= t_max_s
    return {
        "telescopes_needed": required_telescopes(per_pixel_s, n_pixels, rot_period_hours),
        "sharp_possible": bool(possible),
        "residual_smear": float(max(0.0, float(per_pixel_s) / t_max_s)),
        "min_aperture_m": float(aperture_m) * max(1.0, float(per_pixel_s) / t_max_s) ** (1.0 / 3.0),
    }


def _disk_average(global_map: np.ndarray, n: int, t0_s: float, dt_s: float, p_rot_s: float,
                  max_sub: int = 12, oversample: int = 2) -> np.ndarray:
    """Disk image averaged over [t0, t0 + dt] while the body turns with period p_rot."""
    turns = dt_s / p_rot_s
    if turns >= 1.0:
        # A full turn or more: the average over the window is the same as over one turn
        # plus the leftover fraction; use evenly spread phases.
        n_sub = max_sub
    else:
        n_sub = int(np.clip(np.ceil(turns * 360.0 / 5.0), 1, max_sub))  # one sample per ~5 deg
    phases = (t0_s + (np.arange(n_sub) + 0.5) / n_sub * dt_s) / p_rot_s * 360.0
    img = np.zeros((n, n))
    for ph in phases:
        img += render_global_map(global_map, n, sub_lon_deg=-ph, oversample=oversample)
    return img / n_sub


def simulate_sgl_observation(
    surface: Union[str, np.ndarray] = "planet",
    n_pixels: int = 32,
    z_rec: Union[float, u.Quantity] = 650.0 * AU_SI,
    aperture_m: float = 1.0,
    distance_source: Union[float, u.Quantity] = 1.3 * PC_SI,
    planet_radius: Union[float, u.Quantity] = EARTH_RADIUS_M,
    insolation_earth: float = 1.0,
    geometric_albedo: Optional[float] = None,
    rot_period_hours: Optional[float] = 24.0,
    n_telescopes: int = 1,
    target_snr: float = 7.0,
    per_pixel_s: Optional[float] = None,
    seed: int = 7,
) -> Dict[str, object]:
    """
    Simulate an SGL image of a rotating planet, including blur, corona noise and reconstruction.

    Parameters
    ----------
    surface : {"planet", "earth", "moon"} or ndarray
        A built-in global map, or any 180 x 360 latitude/longitude albedo map
        (values are albedos in [0, 1]).
    n_pixels : int
        Image resolution N.
    z_rec, aperture_m, distance_source, planet_radius, insolation_earth
        Passed to :func:`sgl_sim.radiometry.sgl_photon_budget`.
    geometric_albedo : float, optional
        Disk-average albedo used for the photon budget. Default: the mean of
        the visible face of ``surface``, so ``target_snr`` refers to that
        surface's mean brightness.
    rot_period_hours : float or None
        Rotation period seen by the observer. For tidally locked planets this is
        the orbital period. ``None`` means a non-rotating body.
    n_telescopes : int
        Telescopes scanning in parallel.
    target_snr : float
        Per-pixel SNR that sets the integration time (unless ``per_pixel_s``).
    per_pixel_s : float, optional
        Integration time per pixel; overrides ``target_snr``.
    seed : int
        Seed for the photon noise.

    Returns
    -------
    dict
        - 'truth': the disk at the start of the scan (N x N);
        - 'measured': the blurred, noisy, corona-subtracted measurements (N x N);
        - 'reconstructed': the reconstructed image (N x N);
        - 'rmse' and 'ssim': reconstruction against the truth;
        - 'rmse_static' and 'ssim_static': the same scan of a non-rotating planet
          (photon noise only), to separate noise from rotation smear;
        - timing: 'per_pixel_s', 'scan_hours', 'max_sharp_scan_hours',
          'smear_factor' (scan / max sharp scan), 'telescopes_needed',
          'sharp_possible' (False if even one pixel takes longer than the
          sharp-scan window) and 'min_aperture_m';
        - photon budget: 'blur_rate', 'pixel_rate', 'corona_rate'.
    """
    n = int(n_pixels)
    n_tel = max(1, int(n_telescopes))
    gmap = GLOBAL_MAPS[surface]() if isinstance(surface, str) else np.asarray(surface, dtype=float)

    rows, cols = disk_pixels(n)
    face = render_global_map(gmap, n, 0.0)
    if geometric_albedo is None:
        geometric_albedo = float(face[rows, cols].mean())

    budget_kwargs = dict(
        z_rec=z_rec, aperture_m=aperture_m, distance_source=distance_source,
        planet_radius=planet_radius, n_pixels=n, insolation_earth=insolation_earth,
        geometric_albedo=geometric_albedo,
    )
    tb = integration_time_for_snr(target_snr, **budget_kwargs)
    t_pix = float(per_pixel_s) if per_pixel_s is not None else tb["per_pixel_s"]
    p_unit, p_cor = tb["pixel"], tb["corona"]

    n_disk = len(rows)
    kmat = sgl_blur_matrix(n)
    scale = 1.0  # albedos are used as given

    rng = np.random.RandomState(seed)
    n_steps = int(np.ceil(n_disk / n_tel))
    scan_s = n_steps * t_pix
    rotating = rot_period_hours is not None and rot_period_hours > 0
    p_rot_s = float(rot_period_hours) * 3600.0 if rotating else np.inf

    def measure(static: bool) -> np.ndarray:
        y = np.zeros(n_disk)
        a_static = (face * scale)[rows, cols]
        for step in range(n_steps):
            idx = np.arange(step * n_tel, min((step + 1) * n_tel, n_disk))
            if static or not rotating:
                a = a_static
            else:
                a = (_disk_average(gmap, n, step * t_pix, t_pix, p_rot_s) * scale)[rows, cols]
            expected = t_pix * (p_unit * (kmat[idx] @ a) / geometric_albedo + p_cor)
            counts = expected + rng.normal(size=idx.size) * np.sqrt(expected)
            # Subtract the (known) mean corona and convert back to albedo units.
            y[idx] = (counts / t_pix - p_cor) * geometric_albedo / p_unit
        return y

    def to_image(vec: np.ndarray) -> np.ndarray:
        img = np.zeros((n, n))
        img[rows, cols] = vec
        return img

    truth = face * scale
    results = {}
    for label, static in (("", False), ("_static", True)):
        y = measure(static)
        a_hat = np.linalg.solve(kmat, y)
        rec = to_image(np.clip(a_hat, 0.0, 1.0))
        results[label] = (y, rec)
    y, rec = results[""]
    _, rec_static = results["_static"]

    t_sharp_h = max_scan_time_for_sharp_image(rot_period_hours, n) if rotating else float("inf")
    return {
        "truth": truth,
        "measured": to_image(y / SELF_KERNEL),
        "reconstructed": rec,
        "rmse": float(compute_rmse(truth, rec)),
        "ssim": float(compute_ssim(truth, rec)),
        "rmse_static": float(compute_rmse(truth, rec_static)),
        "ssim_static": float(compute_ssim(truth, rec_static)),
        "per_pixel_s": t_pix,
        "scan_hours": float(scan_s / 3600.0),
        "max_sharp_scan_hours": float(t_sharp_h),
        "smear_factor": float(scan_s / 3600.0 / t_sharp_h) if rotating else 0.0,
        "telescopes_needed": required_telescopes(t_pix, n, rot_period_hours) if rotating else 1,
        "sharp_possible": sharp_imaging_requirements(t_pix, n, rot_period_hours, aperture_m)["sharp_possible"] if rotating else True,
        "min_aperture_m": sharp_imaging_requirements(t_pix, n, rot_period_hours, aperture_m)["min_aperture_m"] if rotating else float(aperture_m),
        "n_telescopes": n_tel,
        "n_pixels": n,
        "blur_rate": float(tb["blur"]),
        "pixel_rate": float(p_unit),
        "corona_rate": float(p_cor),
        "image_diameter_m": float(tb["image_diameter_m"]),
    }
