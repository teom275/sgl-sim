"""Tests for the physical SGL image simulator (sgl_sim.imaging)."""

import numpy as np
import pytest

from sgl_sim.imaging import (
    SELF_KERNEL,
    disk_pixels,
    max_scan_time_for_sharp_image,
    required_telescopes,
    sgl_blur_matrix,
    simulate_sgl_observation,
)
from sgl_sim.reference_bodies import GLOBAL_MAPS, earth_albedo_map, earth_global_map, render_global_map
from sgl_sim.relativity import PC_SI


def test_blur_matrix_is_the_sgl_1_over_r_kernel():
    k = sgl_blur_matrix(16)
    rows, cols = disk_pixels(16)
    assert k.shape == (len(rows), len(rows))
    assert np.allclose(k, k.T)
    assert np.allclose(np.diag(k), SELF_KERNEL)
    assert SELF_KERNEL == pytest.approx(3.5255, rel=1e-4)
    # Neighbouring pixel weighs 1, two pixels away 1/2.
    i = np.nonzero((rows == 8) & (cols == 8))[0][0]  # centre of the disk
    j = np.nonzero((rows == 8) & (cols == 10))[0][0]
    assert k[i, j] == pytest.approx(0.5)


def test_global_maps_render_like_the_static_maps():
    assert set(GLOBAL_MAPS) == {"planet", "earth", "moon"}
    for make in GLOBAL_MAPS.values():
        g = make()
        assert g.shape == (180, 360) and 0.0 <= g.min() and g.max() <= 1.0
    # Same projection as earth_albedo_map.
    assert np.allclose(render_global_map(earth_global_map(), 32, 15.0, 10.0), earth_albedo_map(32, 10.0, 15.0, 2))
    # Rotating by 180 degrees shows a different face.
    a, b = (render_global_map(earth_global_map(), 32, lon) for lon in (0.0, 180.0))
    assert np.abs(a - b).mean() > 0.01


def test_reconstruction_noise_matches_the_photon_budget():
    """With a uniform, non-rotating surface the deconvolved noise is ~albedo / SNR (validates radiometry's sqrt(6) law)."""
    rows, cols = disk_pixels(24)
    errs = []
    for seed in range(4):
        r = simulate_sgl_observation(np.full((180, 360), 0.3), 24, distance_source=10 * PC_SI,
                                     rot_period_hours=None, target_snr=7.0, seed=seed)
        errs.append((r["reconstructed"] - r["truth"])[rows, cols].std())
    assert np.mean(errs) == pytest.approx(0.3 / 7.0, rel=0.15)


def test_rotation_smears_and_a_swarm_fixes_it():
    kw = dict(surface="earth", n_pixels=24, distance_source=1.3 * PC_SI, rot_period_hours=60.0)
    one = simulate_sgl_observation(n_telescopes=1, **kw)
    assert one["smear_factor"] > 1.0
    need = one["telescopes_needed"]
    swarm = simulate_sgl_observation(n_telescopes=need, **kw)
    assert swarm["smear_factor"] <= 1.0
    assert swarm["ssim"] > one["ssim"] + 0.05
    # A non-rotating planet is limited only by photon noise.
    assert one["ssim_static"] > one["ssim"]


def test_tidally_locked_planets_still_rotate():
    """Synchronous rotation is one turn per orbit, not zero: a long scan smears too."""
    r = simulate_sgl_observation("planet", 24, distance_source=12.43 * PC_SI, planet_radius=0.92 * 6.371e6,
                                 insolation_earth=0.66, rot_period_hours=146.4)
    assert r["smear_factor"] > 10.0
    assert r["telescopes_needed"] > 10


def test_swarm_sizing_formula():
    assert max_scan_time_for_sharp_image(24.0, 32) == pytest.approx(24.0 / (np.pi * 32))
    n_disk = len(disk_pixels(32)[0])
    t_max = 24.0 / (np.pi * 32) * 3600.0
    n_tel = required_telescopes(10.0, 32, 24.0)
    assert int(np.ceil(n_disk / n_tel)) * 10.0 <= t_max            # this many finish in time
    assert int(np.ceil(n_disk / (n_tel - 1))) * 10.0 > t_max       # one fewer does not


def test_when_one_pixel_is_too_slow_only_a_bigger_aperture_helps():
    from sgl_sim.imaging import sharp_imaging_requirements

    ok = sharp_imaging_requirements(per_pixel_s=60.0, n_pixels=32, rot_period_hours=24.0)
    assert ok["sharp_possible"] and ok["min_aperture_m"] == pytest.approx(1.0)
    t_max = 24.0 / (np.pi * 32) * 3600.0
    bad = sharp_imaging_requirements(per_pixel_s=8 * t_max, n_pixels=32, rot_period_hours=24.0)
    assert not bad["sharp_possible"]
    assert bad["min_aperture_m"] == pytest.approx(2.0)  # t ~ d^-3


def test_truth_keeps_physical_albedos():
    r = simulate_sgl_observation("planet", 24, distance_source=1.3 * PC_SI, rot_period_hours=None)
    assert 0.0 <= r["truth"].min() and r["truth"].max() <= 1.0
    assert r["ssim"] > 0.85  # SNR 7, no rotation: limited by photon noise only
