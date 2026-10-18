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
    Compute the solar K-corona surface brightness relative to mean solar disk brightness B_sun
    using the classical Baumbach-Allen model:

        B_cor(r) / B_sun = (2.56e-6 / r^6) + (1.42e-6 / r^2.5) + (2.26e-8 / r^1.5)

    where r is the heliocentric radial distance in units of solar radii (r >= 1.0).

    Parameters
    ----------
    r_sun : float or np.ndarray
        Radial impact parameter / coronal distance in solar radii (b / R_sun).

    Returns
    -------
    float or np.ndarray
        Coronal brightness relative to mean solar disk (dimensionless ratio).
    """
    r = np.asarray(r_sun, dtype=float)
    # Baumbach-Allen empirical coefficients
    b_cor = (2.56e-6 / (r**6)) + (1.42e-6 / (r**2.5)) + (2.26e-8 / (r**1.5))
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
    coronagraph_suppression: float = 1.0e-6,
    optical_throughput: float = 0.35,
) -> Dict[str, float]:
    """
    Calculate the per-pixel Signal-to-Noise Ratio (SNR) for an exoplanet surface element
    observed through the Gravitational Lens.

    Parameters
    ----------
    z_rec : float or astropy.units.Quantity
        Receiver distance in meters (or AU if Quantity).
    aperture_m : float or astropy.units.Quantity, optional
        Telescope primary mirror diameter in meters (default: 1.0 m).
    integration_time_s : float or astropy.units.Quantity, optional
        Integration time per pixel in seconds (default: 1 day = 86400 s).
    distance_source : float or astropy.units.Quantity, optional
        Distance to exoplanet host system in meters (default: 1.3 pc ≈ Proxima Cen).
    exoplanet_radius : float or astropy.units.Quantity, optional
        Radius of exoplanet in meters (default: Earth radius = 6371 km).
    wavelength : float or astropy.units.Quantity, optional
        Observation wavelength in meters.
    mass : float or astropy.units.Quantity, optional
        Lens mass in kg.
    coronagraph_suppression : float, optional
        Effective coronagraph / occulter suppression factor of solar corona.
    optical_throughput : float, optional
        End-to-end instrument throughput efficiency.

    Returns
    -------
    dict
        Dictionary containing 'snr', 'signal_photons', 'coronal_photons',
        'noise_photons', and 'r_sun_impact'.
    """
    if isinstance(z_rec, u.Quantity):
        z_m = z_rec.to(u.m).value
    else:
        z_m = float(z_rec)

    if isinstance(aperture_m, u.Quantity):
        d_tel = aperture_m.to(u.m).value
    else:
        d_tel = float(aperture_m)

    if isinstance(integration_time_s, u.Quantity):
        t_int = integration_time_s.to(u.s).value
    else:
        t_int = float(integration_time_s)

    if isinstance(distance_source, u.Quantity):
        d_src = distance_source.to(u.m).value
    else:
        d_src = float(distance_source)

    if isinstance(exoplanet_radius, u.Quantity):
        r_exo = exoplanet_radius.to(u.m).value
    else:
        r_exo = float(exoplanet_radius)

    if isinstance(wavelength, u.Quantity):
        lam = wavelength.to(u.m).value
    else:
        lam = float(wavelength)

    rs = schwarzschild_radius(mass)
    b_ring = np.sqrt(2.0 * rs * z_m)
    r_sun_impact = b_ring / R_SUN_SI

    # Solar irradiance at 1 AU (approx 1361 W/m^2, ~ 1.5e21 photons/s/m^2)
    # Earth-like exoplanet at d_src reflected flux
    tel_area = np.pi * (d_tel / 2.0) ** 2
    mu_eff = peak_magnification(wavelength=lam, mass=mass) * 1.5e-3

    # Scaled photon flux from exoplanet pixel (finite disk averaged)
    # Turyshev NIAC Phase III: effective magnification over resolved patch is ~1e6
    mu_eff = (4.0 * np.pi * rs / lam)  # effective disk-averaged geometric factor
    photon_flux_base = (
        1.5e-3
        * (1.3 * PC_SI / d_src) ** 2
        * (r_exo / 6.371e6) ** 2
        * (1.0e-6 / lam)
    )
    signal_photons = photon_flux_base * mu_eff * tel_area * t_int * optical_throughput

    # Coronal background photon flux per pixel
    cor_ratio = baumbach_allen_coronal_brightness(r_sun_impact)
    # Solar flux at 650 AU ~ 3.2 W/m^2; coronagraph suppresses by factor ~ 1e-6
    coronal_flux = 8.5e6 * cor_ratio * coronagraph_suppression * (1.0e-6 / lam)
    coronal_photons = coronal_flux * tel_area * t_int * optical_throughput

    # Detector read/dark noise floor (e.g. 5 e- RMS per pixel)
    read_noise_sq = 25.0

    # Total noise variance (Poisson shot noise of signal + corona + read noise)
    noise_variance = signal_photons + coronal_photons + read_noise_sq
    noise_photons = np.sqrt(max(noise_variance, 1.0))

    snr = signal_photons / noise_photons

    return {
        "snr": float(max(snr, 0.1)),
        "signal_photons": float(signal_photons),
        "coronal_photons": float(coronal_photons),
        "noise_photons": float(noise_photons),
        "r_sun_impact": float(r_sun_impact),
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
