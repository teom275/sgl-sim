"""
Unit tests for NASA-standard multi-extension FITS, CSV, and JSON exporters.
"""

import os
import json
import tempfile
import pytest
import numpy as np
from astropy.io import fits

from sgl_sim.exporters import (
    build_simulation_fits_hdulist,
    export_fits,
    export_csv,
    export_json,
)


@pytest.fixture
def sample_sim_data():
    """Generate dummy simulation output dictionary for exporter tests."""
    return {
        "mass_solar": 1.0,
        "z_rec_au": 650.0,
        "j2": 2.2e-7,
        "wavelength_m": 1.0e-6,
        "snr": 18.5,
        "aperture_m": 1.0,
        "t_int_s": 86400.0,
        "distance_source_pc": 1.3,
        "rmse_deconvolved": 0.045,
        "ssim_deconvolved": 0.925,
        "caustic_map": np.ones((32, 32), dtype=np.float32) * 0.5,
        "convolved_noisy": np.ones((32, 32), dtype=np.float32) * 0.3,
        "deconvolved": np.ones((32, 32), dtype=np.float32) * 0.8,
        "psf_rho_m": np.linspace(0.0, 50.0, 60),
        "psf_intensity": np.exp(-np.linspace(0.0, 50.0, 60)),
        "psf_j0_sq": np.exp(-np.linspace(0.0, 50.0, 60)),
    }


def test_build_fits_hdulist_structure(sample_sim_data):
    """Verify multi-extension FITS HDUList structure and standard 8-character headers."""
    hdul = build_simulation_fits_hdulist(sample_sim_data)
    assert len(hdul) == 5

    # Extension 0: PrimaryHDU
    pri_hdr = hdul[0].header
    assert pri_hdr["TELESCOP"] == "SGL_FOCAL_LINE"
    assert pri_hdr["MASS_SOL"] == 1.0
    assert pri_hdr["Z_REC_AU"] == 650.0
    assert pri_hdr["J2_QUAD"] == 2.2e-7
    assert pri_hdr["WAVELEN"] == 1.0e-6
    assert pri_hdr["SNR_VAL"] == 18.5
    assert pri_hdr["APERT_M"] == 1.0
    assert pri_hdr["T_INT_S"] == 86400.0
    assert pri_hdr["EXO_DIST"] == 1.3
    assert pri_hdr["RMSE_REC"] == 0.045
    assert pri_hdr["SSIM_REC"] == 0.925

    # Extension 1: CAUSTIC_MAP ImageHDU
    assert isinstance(hdul[1], fits.ImageHDU)
    assert hdul[1].name == "CAUSTIC_MAP"
    assert hdul[1].data.shape == (32, 32)

    # Extension 2: RAW_DETECTOR ImageHDU
    assert isinstance(hdul[2], fits.ImageHDU)
    assert hdul[2].name == "RAW_DETECTOR"
    assert hdul[2].data.shape == (32, 32)

    # Extension 3: DECONV_EXO ImageHDU
    assert isinstance(hdul[3], fits.ImageHDU)
    assert hdul[3].name == "DECONV_EXO"
    assert hdul[3].data.shape == (32, 32)

    # Extension 4: PSF_PROFILE BinTableHDU
    assert isinstance(hdul[4], fits.BinTableHDU)
    assert hdul[4].name == "PSF_PROFILE"
    assert "RHO_M" in hdul[4].columns.names
    assert "INTENSITY" in hdul[4].columns.names
    assert "J0_SQUARED" in hdul[4].columns.names


def test_export_fits_file_roundtrip(sample_sim_data):
    """Verify writing FITS to disk and reading back with astropy.io.fits."""
    with tempfile.TemporaryDirectory() as tmpdir:
        fits_path = os.path.join(tmpdir, "test_output.fits")
        res_path = export_fits(sample_sim_data, output_path=fits_path)
        assert os.path.exists(res_path)

        with fits.open(fits_path) as roundtrip_hdul:
            assert len(roundtrip_hdul) == 5
            assert roundtrip_hdul[0].header["SNR_VAL"] == 18.5
            assert roundtrip_hdul["DECONV_EXO"].data.shape == (32, 32)
            assert len(roundtrip_hdul["PSF_PROFILE"].data) == 60


def test_export_fits_in_memory_bytes(sample_sim_data):
    """Verify export_fits returns valid FITS bytes when output_path is None."""
    fits_bytes = export_fits(sample_sim_data, output_path=None)
    assert isinstance(fits_bytes, bytes)
    assert len(fits_bytes) > 2880  # Standard FITS block multiple
    assert fits_bytes[:6] == b"SIMPLE"


def test_export_csv_and_json():
    """Verify CSV and JSON serialization utilities."""
    table_data = {
        "x": [1.0, 2.0, 3.0],
        "y": [10.0, 20.0, 30.0],
    }
    csv_str = export_csv(table_data)
    assert "x,y" in csv_str
    assert "1.0,10.0" in csv_str

    json_dict = {
        "mass": 1.0,
        "array": np.array([1, 2, 3]),
        "status": "ok",
    }
    json_str = export_json(json_dict)
    loaded = json.loads(json_str)
    assert loaded["mass"] == 1.0
    assert loaded["array"] == [1, 2, 3]
