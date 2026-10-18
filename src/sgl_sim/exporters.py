"""
Astronomical Data Exporters: Multi-Extension FITS, CSV, and JSON.

This module uses astropy.io.fits to create compliant multi-extension FITS files
containing simulation metadata, 2D caustic maps, raw detector images, deconvolved
exoplanet images, and binary table radial PSF profiles. It also provides CSV
and JSON serialization for orbital trajectories and ephemerides.
"""

from typing import Dict, Any, Optional, Union, List
import io
import json
import numpy as np
from astropy.io import fits
from astropy.table import Table

from sgl_sim.relativity import AU_SI, PC_SI, M_SUN_SI, R_SUN_SI


def build_simulation_fits_hdulist(
    sim_data: Dict[str, Any],
) -> fits.HDUList:
    """
    Construct a NASA-standard multi-extension FITS HDUList containing:
    1. PrimaryHDU: metadata in standard 8-character uppercase FITS header keywords.
    2. ImageHDU ('CAUSTIC_MAP'): 2D transverse astroid caustic intensity map.
    3. ImageHDU ('RAW_DETECTOR'): 2D convolved + noisy detector image.
    4. ImageHDU ('DECONV_EXO'): 2D Wiener-deconvolved exoplanet albedo image.
    5. BinTableHDU ('PSF_PROFILE'): Radial PSF profile (RHO_M, INTENSITY, J0_SQUARED).

    Parameters
    ----------
    sim_data : dict
        Simulation output dictionary containing metadata, 2D maps, and PSF profile.

    Returns
    -------
    astropy.io.fits.HDUList
        Multi-extension FITS object.
    """
    # 1. Primary HDU with metadata
    pri_hdr = fits.Header()
    pri_hdr["CREATOR"] = ("sgl-sim v0.1.0", "Software package")
    pri_hdr["TELESCOP"] = ("SGL_FOCAL_LINE", "Gravitational Lens Telescope")
    pri_hdr["MASS_SOL"] = (float(sim_data.get("mass_solar", 1.0)), "Lens mass in solar masses")
    pri_hdr["Z_REC_AU"] = (float(sim_data.get("z_rec_au", 650.0)), "Receiver focal distance in AU")
    pri_hdr["J2_QUAD"] = (float(sim_data.get("j2", 2.2e-7)), "Stellar quadrupole moment J2")
    pri_hdr["WAVELEN"] = (float(sim_data.get("wavelength_m", 1.0e-6)), "Wavelength in meters")
    pri_hdr["SNR_VAL"] = (float(sim_data.get("snr", 15.0)), "Per-pixel Signal to Noise Ratio")
    pri_hdr["APERT_M"] = (float(sim_data.get("aperture_m", 1.0)), "Telescope aperture in meters")
    pri_hdr["T_INT_S"] = (float(sim_data.get("t_int_s", 86400.0)), "Integration time per pixel (s)")
    pri_hdr["EXO_DIST"] = (float(sim_data.get("distance_source_pc", 1.3)), "Exoplanet distance in pc")
    pri_hdr["RMSE_REC"] = (float(sim_data.get("rmse_deconvolved", 0.05)), "Wiener reconstruction RMSE")
    pri_hdr["SSIM_REC"] = (float(sim_data.get("ssim_deconvolved", 0.92)), "Wiener reconstruction SSIM")

    pri_hdu = fits.PrimaryHDU(header=pri_hdr)

    # 2. ImageHDU: Caustic Map
    caustic_map = sim_data.get("caustic_map")
    if caustic_map is None:
        caustic_map = np.zeros((32, 32), dtype=np.float32)
    else:
        caustic_map = np.asarray(caustic_map, dtype=np.float32)
    caustic_hdu = fits.ImageHDU(data=caustic_map, name="CAUSTIC_MAP")
    caustic_hdu.header["BUNIT"] = ("RELATIVE_INTENSITY", "Caustic field intensity")

    # 3. ImageHDU: Raw Detector Image
    raw_det = sim_data.get("convolved_noisy")
    if raw_det is None:
        raw_det = np.zeros((32, 32), dtype=np.float32)
    else:
        raw_det = np.asarray(raw_det, dtype=np.float32)
    raw_hdu = fits.ImageHDU(data=raw_det, name="RAW_DETECTOR")
    raw_hdu.header["BUNIT"] = ("NORMALIZED_FLUX", "Convolved noisy detector flux")

    # 4. ImageHDU: Deconvolved Exoplanet Image
    deconv = sim_data.get("deconvolved")
    if deconv is None:
        deconv = np.zeros((32, 32), dtype=np.float32)
    else:
        deconv = np.asarray(deconv, dtype=np.float32)
    deconv_hdu = fits.ImageHDU(data=deconv, name="DECONV_EXO")
    deconv_hdu.header["BUNIT"] = ("ALBEDO", "Reconstructed planetary albedo")

    # 5. BinTableHDU: Radial PSF Profile
    rho_m = sim_data.get("psf_rho_m")
    intens = sim_data.get("psf_intensity")
    j0_sq = sim_data.get("psf_j0_sq")

    if rho_m is None or intens is None:
        rho_m = np.linspace(0.0, 50.0, 100, dtype=np.float64)
        j0_sq = np.ones(100, dtype=np.float64)
        intens = j0_sq * float(sim_data.get("mu_max", 1e11))
    else:
        rho_m = np.asarray(rho_m, dtype=np.float64)
        intens = np.asarray(intens, dtype=np.float64)
        if j0_sq is None:
            j0_sq = intens / max(float(np.max(intens)), 1e-12)
        else:
            j0_sq = np.asarray(j0_sq, dtype=np.float64)

    col1 = fits.Column(name="RHO_M", format="D", unit="m", array=rho_m)
    col2 = fits.Column(name="INTENSITY", format="D", unit="dimensionless", array=intens)
    col3 = fits.Column(name="J0_SQUARED", format="D", unit="dimensionless", array=j0_sq)

    psf_table_hdu = fits.BinTableHDU.from_columns([col1, col2, col3], name="PSF_PROFILE")

    return fits.HDUList([pri_hdu, caustic_hdu, raw_hdu, deconv_hdu, psf_table_hdu])


def export_fits(
    sim_data: Dict[str, Any],
    output_path: Optional[str] = None,
) -> Union[bytes, str]:
    """
    Export simulation data to a multi-extension FITS file on disk or bytes.

    Parameters
    ----------
    sim_data : dict
        Simulation results dictionary.
    output_path : str, optional
        Path to save the .fits file. If None, returns bytes.

    Returns
    -------
    bytes or str
        File contents as bytes (if output_path is None) or output_path string.
    """
    hdul = build_simulation_fits_hdulist(sim_data)
    if output_path is not None:
        hdul.writeto(output_path, overwrite=True)
        hdul.close()
        return output_path
    else:
        buf = io.BytesIO()
        hdul.writeto(buf)
        hdul.close()
        return buf.getvalue()


def export_csv(
    data: Dict[str, Union[np.ndarray, List[float]]],
    output_path: Optional[str] = None,
) -> str:
    """
    Export columnar numerical arrays (e.g. PSF profile or ray trajectories) to CSV.

    Parameters
    ----------
    data : dict
        Dictionary of column names to 1D numpy arrays or lists.
    output_path : str, optional
        Path to save the .csv file. If None, returns CSV string.

    Returns
    -------
    str
        CSV string content or saved file path.
    """
    table = Table()
    for col_name, col_data in data.items():
        table[col_name] = np.asarray(col_data)

    if output_path is not None:
        table.write(output_path, format="ascii.csv", overwrite=True)
        return output_path
    else:
        buf = io.StringIO()
        table.write(buf, format="ascii.csv")
        return buf.getvalue()


def export_json(
    data: Dict[str, Any],
    output_path: Optional[str] = None,
    indent: int = 2,
) -> str:
    """
    Serialize simulation parameters and results into valid JSON.

    Handles conversion of numpy arrays and floats into serializable types.

    Parameters
    ----------
    data : dict
        Dictionary of simulation data.
    output_path : str, optional
        Path to save .json file.
    indent : int, optional
        JSON indentation level.

    Returns
    -------
    str
        JSON string or saved file path.
    """
    class NumpyEncoder(json.JSONEncoder):
        def default(self, obj):
            if isinstance(obj, np.ndarray):
                return obj.tolist()
            if isinstance(obj, (np.float32, np.float64, np.floating)):
                return float(obj)
            if isinstance(obj, (np.int32, np.int64, np.integer)):
                return int(obj)
            if isinstance(obj, (np.bool_, bool)):
                return bool(obj)
            return super().default(obj)

    json_str = json.dumps(data, cls=NumpyEncoder, indent=indent)
    if output_path is not None:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(json_str)
        return output_path
    return json_str
