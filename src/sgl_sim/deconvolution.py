"""
Coronal Noise Modeling, Signal-to-Noise Ratio (SNR), and 2D Wiener Deconvolution.

This module models the Baumbach-Allen solar K-corona background, calculates per-pixel
SNR for focal-line imaging of an exoplanet, generates synthetic exoplanet albedo maps,
and performs 2D Fourier-space Wiener deconvolution with RMSE and SSIM evaluation.
"""

from typing import Dict, Any, Tuple, Optional, Union
import numpy as np
from astropy import constants as const
from astropy import units as u

from sgl_sim.relativity import (
    _to_si_value,
    schwarzschild_radius,
    M_SUN_SI,
    R_SUN_SI,
    AU_SI,
    PC_SI,
)
from sgl_sim.optics import (
    einstein_ring_properties,
    peak_magnification,
    generate_2d_psf,
)


def baumbach_allen_coronal_brightness(r_sun: Union[float, np.ndarray]) -> Union[float, np.ndarray]:
    """
    Solar K-corona surface brightness relative to the mean solar disk, Baumbach (1937)
    as given in Allen's Astrophysical Quantities:

        B_cor(r) / B_sun = 1e-6 * (0.0532 / r^2.5 + 1.425 / r^7 + 2.565 / r^17)

    where r is the heliocentric distance in solar radii (r >= 1). At the Einstein
    ring of a receiver at 650 AU (r = 1.09) this is 1.4e-6.

    Earlier versions paired these coefficients with the wrong exponents
    (2.56/r^6 + 1.42/r^2.5 + 0.0226/r^1.5), overestimating the outer corona by up
    to ~24x at 3 R_sun; see docs/auditoria-fisica.md (finding M1). The F-corona is
    not included, so this is a lower bound on the background.

    Parameters
    ----------
    r_sun : float or np.ndarray
        Radial distance in solar radii (b / R_sun).

    Returns
    -------
    float or np.ndarray
        Coronal brightness relative to the mean solar disk (dimensionless).
    """
    r = np.asarray(r_sun, dtype=float)
    b_cor = 1.0e-6 * (0.0532 / r**2.5 + 1.425 / r**7 + 2.565 / r**17)
    if np.ndim(b_cor) == 0:
        return float(b_cor)
    return b_cor


def calculate_snr(
    z_rec: Union[float, u.Quantity],
    aperture_m: Union[float, u.Quantity] = 1.0,
    integration_time_s: Union[float, u.Quantity] = 86400.0,
    distance_source: Union[float, u.Quantity] = 1.3 * PC_SI,
    exoplanet_radius: Union[float, u.Quantity] = 6.371e6,
    wavelength: Union[float, u.Quantity] = 1.0e-6,
    mass: Union[float, u.Quantity] = M_SUN_SI,
    coronagraph_suppression: Optional[float] = None,
    optical_throughput: float = 1.0,
    n_pixels: int = 32,
    insolation_earth: float = 1.0,
    geometric_albedo: float = 0.367,
) -> Dict[str, float]:
    """
    Deconvolved per-pixel SNR for an N x N image of an exoplanet through the SGL.

    Wraps :func:`sgl_sim.radiometry.sgl_photon_budget`. That model accounts for
    the direct pixel signal, the blur from the rest of the disk, and the solar
    corona inside the Einstein-ring annulus. The earlier version of this function
    used unit-less constants and a 1e-6 "coronagraph" factor on the corona, and
    overestimated the SNR by ~1e10 (docs/auditoria-fisica.md, finding C1).

    Parameters
    ----------
    z_rec : float or Quantity
        Receiver distance (m if float).
    aperture_m : float or Quantity
        Telescope diameter (m).
    integration_time_s : float or Quantity
        Integration time per pixel (s).
    distance_source : float or Quantity
        Distance to the exoplanet (m if float).
    exoplanet_radius : float or Quantity
        Planet radius (m if float).
    wavelength : float or Quantity
        Kept for compatibility. The band is 0.4-1.0 um; for the PSF use
        :func:`sgl_sim.optics.psf_intensity`.
    mass : float or Quantity
        Lens mass (kg if float).
    coronagraph_suppression : float, optional
        Ignored. The corona overlaps the Einstein ring and cannot be suppressed.
    optical_throughput : float
        End-to-end efficiency (default 1, ideal).
    n_pixels : int
        Image resolution N (default 32, matching the imaging pipeline).
    insolation_earth : float
        Stellar flux at the planet in solar-constant units.
    geometric_albedo : float
        Planet geometric albedo.

    Returns
    -------
    dict
        'snr', 'signal_photons' (pixel term), 'blur_photons', 'coronal_photons',
        'noise_photons', 'r_sun_impact', 'image_diameter_m' and 'n_pixels',
        all for the given integration time.
    """
    from sgl_sim.radiometry import sgl_photon_budget

    t_int = _to_si_value(integration_time_s, u.s)
    bud = sgl_photon_budget(
        z_rec=z_rec,
        aperture_m=aperture_m,
        distance_source=distance_source,
        planet_radius=exoplanet_radius,
        n_pixels=n_pixels,
        insolation_earth=insolation_earth,
        geometric_albedo=geometric_albedo,
        throughput=optical_throughput,
        mass=mass,
    )
    noise = np.sqrt((bud["blur"] + bud["corona"]) * t_int)
    return {
        "snr": float(bud["snr_per_sqrt_s"] * np.sqrt(t_int)),
        "signal_photons": float(bud["pixel"] * t_int),
        "blur_photons": float(bud["blur"] * t_int),
        "coronal_photons": float(bud["corona"] * t_int),
        "noise_photons": float(noise),
        "r_sun_impact": float(bud["r_ring_rsun"]),
        "image_diameter_m": float(bud["image_diameter_m"]),
        "n_pixels": int(bud["n_pixels"]),
    }


def generate_exoplanet_map(grid_size: int = 32, seed: int = 42) -> np.ndarray:
    """
    Generate a synthetic N x N exoplanet albedo map containing oceans,
    continents, and polar ice caps.

    Parameters
    ----------
    grid_size : int, optional
        Map dimensions (default: 32x32).
    seed : int, optional
        Random seed for reproducible continents.

    Returns
    -------
    np.ndarray
        2D float array of shape (grid_size, grid_size) with albedo values in [0.0, 1.0].
    """
    rng = np.random.RandomState(seed)

    coords = np.linspace(-1.0, 1.0, grid_size)
    xx, yy = np.meshgrid(coords, coords)
    radius_grid = np.sqrt(xx**2 + yy**2)

    # Base ocean albedo
    albedo = np.full((grid_size, grid_size), 0.08, dtype=float)

    # Continents generated via low-frequency harmonic functions
    c1 = np.exp(-((xx - 0.2) ** 2 + (yy - 0.1) ** 2) / 0.18)
    c2 = np.exp(-((xx + 0.35) ** 2 + (yy + 0.25) ** 2) / 0.14)
    c3 = np.exp(-((xx + 0.2) ** 2 + (yy - 0.45) ** 2) / 0.10)
    c4 = np.exp(-((xx - 0.4) ** 2 + (yy - 0.2) ** 2) / 0.12)

    land_mask = (c1 + c2 + c3 + c4) > 0.45
    albedo[land_mask] = 0.38 + 0.08 * rng.randn(np.count_nonzero(land_mask))

    # Polar ice caps (high albedo ~ 0.82)
    polar_mask = np.abs(yy) > 0.72
    albedo[polar_mask] = 0.82 + 0.04 * rng.randn(np.count_nonzero(polar_mask))

    # Moderate coastal greening
    coastal_mask = (c1 + c2) > 0.35
    albedo[coastal_mask & ~land_mask & ~polar_mask] = 0.18

    # Space background outside planet disk
    space_mask = radius_grid > 0.95
    albedo[space_mask] = 0.0

    return np.clip(albedo, 0.0, 1.0)


def compute_ssim(
    img1: np.ndarray,
    img2: np.ndarray,
    data_range: float = 1.0,
    k1: float = 0.01,
    k2: float = 0.03,
) -> float:
    """
    Compute Structural Similarity Index (SSIM) between two 2D images.

    Parameters
    ----------
    img1 : np.ndarray
        Reference image.
    img2 : np.ndarray
        Comparison image.
    data_range : float, optional
        Dynamic range of pixel values (default: 1.0).
    k1, k2 : float, optional
        SSIM stability constants.

    Returns
    -------
    float
        SSIM value between -1.0 and 1.0.
    """
    c1 = (k1 * data_range) ** 2
    c2 = (k2 * data_range) ** 2

    mu1 = np.mean(img1)
    mu2 = np.mean(img2)

    var1 = np.var(img1)
    var2 = np.var(img2)
    covar = np.mean((img1 - mu1) * (img2 - mu2))

    numerator = (2.0 * mu1 * mu2 + c1) * (2.0 * covar + c2)
    denominator = (mu1**2 + mu2**2 + c1) * (var1 + var2 + c2)

    if denominator == 0.0:
        return 1.0
    return float(numerator / denominator)


def compute_rmse(img1: np.ndarray, img2: np.ndarray) -> float:
    """Compute Root Mean Square Error (RMSE) between two images."""
    return float(np.sqrt(np.mean((img1 - img2) ** 2)))


def wiener_deconvolution(
    ground_truth: np.ndarray,
    psf_kernel: np.ndarray,
    snr: float,
    seed: int = 101,
) -> Dict[str, Any]:
    """
    Perform 2D convolution with Bessel PSF, inject Poisson/Gaussian coronal noise,
    and reconstruct via regularized Wiener deconvolution in Fourier space:

        O_hat(f) = [ H*(f) / (|H(f)|^2 + 1 / SNR^2) ] * Y(f)

    Parameters
    ----------
    ground_truth : np.ndarray
        2D array of synthetic exoplanet albedo (e.g. 32x32).
    psf_kernel : np.ndarray
        2D Bessel PSF kernel of matching shape, normalized to sum=1.0.
    snr : float
        Per-pixel Signal-to-Noise Ratio.
    seed : int, optional
        Random seed for noise generation.

    Returns
    -------
    dict
        Dictionary containing:
        - 'ground_truth': original 2D array
        - 'convolved_noisy': blurred + noisy 2D detector image
        - 'deconvolved': reconstructed 2D array
        - 'rmse_noisy': RMSE between ground_truth and convolved_noisy
        - 'rmse_deconvolved': RMSE between ground_truth and deconvolved
        - 'ssim_noisy': SSIM between ground_truth and convolved_noisy
        - 'ssim_deconvolved': SSIM between ground_truth and deconvolved
        - 'snr': SNR used
    """
    rng = np.random.RandomState(seed)
    n = ground_truth.shape[0]

    # Center the PSF kernel for FFT
    psf_shifted = np.fft.ifftshift(psf_kernel)
    h_f = np.fft.fft2(psf_shifted)
    o_f = np.fft.fft2(ground_truth)

    # Convolve in Fourier space
    convolved_clean = np.real(np.fft.ifft2(o_f * h_f))

    # Noise model: standard deviation inversely proportional to SNR
    signal_level = np.std(convolved_clean)
    if signal_level <= 0:
        signal_level = np.mean(convolved_clean) + 1e-4

    sigma_noise = max(signal_level / max(snr, 0.5), 1e-4)
    noise = rng.normal(loc=0.0, scale=sigma_noise, size=ground_truth.shape)

    convolved_noisy = convolved_clean + noise
    convolved_noisy = np.clip(convolved_noisy, 0.0, 1.0)

    # Wiener Filter Transfer Function
    # W(f) = H*(f) / (|H(f)|^2 + K)
    # where K = 1 / SNR^2
    k_reg = 1.0 / (max(snr, 1.0) ** 2)
    h_f_conj = np.conj(h_f)
    h_f_mag_sq = np.abs(h_f) ** 2

    w_f = h_f_conj / (h_f_mag_sq + k_reg)

    y_f = np.fft.fft2(convolved_noisy)
    deconvolved_raw = np.real(np.fft.ifft2(y_f * w_f))

    # Mask outside planet disk
    coords = np.linspace(-1.0, 1.0, n)
    xx, yy = np.meshgrid(coords, coords)
    disk_mask = (xx**2 + yy**2) <= 0.98

    deconvolved = np.zeros_like(deconvolved_raw)
    deconvolved[disk_mask] = np.clip(deconvolved_raw[disk_mask], 0.0, 1.0)

    rmse_noisy = compute_rmse(ground_truth, convolved_noisy)
    rmse_deconv = compute_rmse(ground_truth, deconvolved)

    ssim_noisy = compute_ssim(ground_truth, convolved_noisy)
    ssim_deconv = compute_ssim(ground_truth, deconvolved)

    return {
        "ground_truth": ground_truth,
        "convolved_noisy": convolved_noisy,
        "deconvolved": deconvolved,
        "rmse_noisy": rmse_noisy,
        "rmse_deconvolved": rmse_deconv,
        "ssim_noisy": ssim_noisy,
        "ssim_deconvolved": ssim_deconv,
        "snr": float(snr),
    }
