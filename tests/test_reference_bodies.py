"""Tests for the Earth and Moon reference albedo maps."""

import numpy as np
import pytest

from sgl_sim import compute_motion_blur, earth_albedo_map, moon_albedo_map, reference_body_map
from sgl_sim.reference_bodies import EARTH_ALBEDO, _land_mask


def test_land_mask_has_the_right_geography():
    mask = _land_mask()
    assert mask.shape == (180, 360)
    land_fraction = mask.mean()
    assert 0.28 < land_fraction < 0.36  # ~29 % land plus rounding at 1 deg
    cell = lambda lat, lon: mask[int(round(89.5 - lat)), int(round(lon + 179.5))]
    assert cell(23.5, 10.5)        # Sahara
    assert cell(-10.5, -55.5)      # Brazil
    assert cell(-80.5, 0.5)        # Antarctica
    assert not cell(0.5, -30.5)    # Atlantic
    assert not cell(0.5, -150.5)   # Pacific


@pytest.mark.parametrize("fn", [earth_albedo_map, moon_albedo_map])
def test_maps_match_the_exoplanet_map_layout(fn):
    m = fn(32)
    assert m.shape == (32, 32)
    assert m.min() >= 0.0 and m.max() <= 1.0
    assert m[0, 0] == 0.0 and m[-1, -1] == 0.0  # space outside the disk
    assert m[16, 16] > 0.0


def test_earth_shows_africa_and_bright_deserts():
    m = earth_albedo_map(64)
    disk = m > 0
    # The centre (10 N, 15 E) is in the Sahel/Sahara belt: brighter than ocean.
    assert m[28:36, 28:36].mean() > EARTH_ALBEDO["ocean"] * 2
    # Most of the visible disk is still ocean.
    assert np.median(m[disk]) < EARTH_ALBEDO["land"]


def test_moon_maria_are_darker_than_highlands():
    m = moon_albedo_map(64)
    north_west = m[12:24, 12:24].mean()   # Imbrium / Procellarum
    south_central = m[44:52, 28:36].mean()  # southern highlands
    assert north_west < south_central


def test_reference_body_map_lookup_and_pipeline():
    assert np.array_equal(reference_body_map("Earth"), earth_albedo_map())
    with pytest.raises(ValueError):
        reference_body_map("Mars")
    res = compute_motion_blur(image_diameter_km=10.0, ground_truth=reference_body_map("moon"))
    assert np.allclose(res["ground_truth"], moon_albedo_map())
