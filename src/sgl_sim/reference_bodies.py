"""
Reference bodies for judging image quality: the Earth and the Moon.

These albedo maps use the same layout as
:func:`sgl_sim.deconvolution.generate_exoplanet_map` (an ``N x N`` array, a disk
of radius 0.95 on a ``[-1, 1]`` grid, 0 outside). Any imaging or motion-blur
routine can take them as ``ground_truth``, so a mission profile can show what
a familiar world would look like through the same lens, noise and scan.

* **Earth:** cloud-free visible albedo in an orthographic view. Oceans, land,
  the major deserts, and ice on Antarctica, Greenland and the high Arctic are
  included. The coastlines come from a 1-degree land mask derived from the
  NOAA GLOBE digital elevation model (public domain), via the
  ``global-land-mask`` package (MIT). The mask is stored below, so no extra
  dependency is needed.
* **Moon:** the near side, with highlands and the principal maria drawn as
  circles and ellipses at their published positions and sizes, plus the
  bright crater Tycho. It is a schematic map, not a photometric one.

Row 0 is the northern edge of the disk, so images display with north up.
"""

from __future__ import annotations

import base64
import zlib
from typing import Dict, Tuple

import numpy as np

__all__ = [
    "earth_albedo_map", "moon_albedo_map", "reference_body_map", "REFERENCE_BODIES",
    "earth_global_map", "moon_global_map", "synthetic_global_map", "render_global_map", "GLOBAL_MAPS",
]

# 1-degree land mask, 180 rows (latitude 89.5 .. -89.5) x 360 columns
# (longitude -179.5 .. 179.5), bit-packed, zlib-compressed, base64-encoded.
_LAND_MASK_1DEG_B64 = (
    "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"
)

_DISK_RADIUS = 0.95


def _land_mask() -> np.ndarray:
    raw = zlib.decompress(base64.b64decode(_LAND_MASK_1DEG_B64))
    bits = np.unpackbits(np.frombuffer(raw, dtype=np.uint8))[: 180 * 360]
    return bits.reshape(180, 360).astype(bool)


def _orthographic_latlon(grid_size: int, lat0_deg: float, lon0_deg: float, oversample: int):
    """Latitude/longitude (deg) of sub-pixel samples on a disk; NaN off the disk."""
    n = grid_size * oversample
    # Sample centres of an n x n grid spanning [-1, 1]; row 0 is north (+y).
    c = (np.arange(n) + 0.5) / n * 2.0 - 1.0
    xx, yy = np.meshgrid(c, -c)
    x = xx / _DISK_RADIUS
    y = yy / _DISK_RADIUS
    rho = np.hypot(x, y)
    on_disk = rho <= 1.0
    rho_c = np.clip(rho, 1e-12, 1.0)
    cang = np.arcsin(rho_c)
    phi0 = np.radians(lat0_deg)
    lam0 = np.radians(lon0_deg)
    with np.errstate(invalid="ignore"):
        lat = np.arcsin(np.cos(cang) * np.sin(phi0) + y * np.sin(cang) * np.cos(phi0) / rho_c)
        lon = lam0 + np.arctan2(x * np.sin(cang), rho_c * np.cos(cang) * np.cos(phi0) - y * np.sin(cang) * np.sin(phi0))
    lat = np.degrees(lat)
    lon = (np.degrees(lon) + 180.0) % 360.0 - 180.0
    lat[~on_disk] = np.nan
    lon[~on_disk] = np.nan
    return lat, lon, on_disk


def _downsample(fine: np.ndarray, grid_size: int, oversample: int) -> np.ndarray:
    return fine.reshape(grid_size, oversample, grid_size, oversample).mean(axis=(1, 3))


def _in_box(lat, lon, lat_lo, lat_hi, lon_lo, lon_hi):
    return (lat >= lat_lo) & (lat <= lat_hi) & (lon >= lon_lo) & (lon <= lon_hi)


# Approximate extents of the large hot and cold deserts (deg).
_EARTH_DESERTS = (
    (15.0, 32.0, -17.0, 35.0),    # Sahara
    (15.0, 31.0, 35.0, 58.0),     # Arabian
    (24.0, 38.0, 58.0, 72.0),     # Iranian plateau, Thar margin
    (37.0, 46.0, 75.0, 112.0),    # Taklamakan, Gobi
    (-32.0, -19.0, 118.0, 142.0), # Australian interior
    (-29.0, -17.0, 13.0, 25.0),   # Namib, Kalahari
    (28.0, 38.0, -118.0, -104.0), # North American southwest
    (-28.0, -18.0, -71.0, -66.0), # Atacama
)

EARTH_ALBEDO = {"ocean": 0.06, "land": 0.17, "desert": 0.36, "ice": 0.80}


def earth_albedo_map(grid_size: int = 32, center_lat_deg: float = 10.0, center_lon_deg: float = 15.0,
                     oversample: int = 4) -> np.ndarray:
    """
    Cloud-free Earth albedo map seen from space.

    Parameters
    ----------
    grid_size : int, optional
        Output dimensions (default: 32 x 32, matching the imaging pipeline).
    center_lat_deg, center_lon_deg : float, optional
        Sub-observer point. The default (10 N, 15 E) faces Africa and Europe.
    oversample : int, optional
        Sub-samples per pixel along each axis, for anti-aliased coastlines.

    Returns
    -------
    np.ndarray
        ``(grid_size, grid_size)`` albedo in ``[0, 1]``, 0 outside the disk.
    """
    lat, lon, on_disk = _orthographic_latlon(grid_size, center_lat_deg, center_lon_deg, oversample)
    mask = _land_mask()
    i = np.clip(np.round(89.5 - np.nan_to_num(lat)).astype(int), 0, 179)
    j = np.clip(np.round(np.nan_to_num(lon) + 179.5).astype(int), 0, 359)
    land = mask[i, j] & on_disk

    alb = np.full(lat.shape, EARTH_ALBEDO["ocean"])
    alb[land] = EARTH_ALBEDO["land"]
    desert = np.zeros_like(land)
    for box in _EARTH_DESERTS:
        desert |= _in_box(lat, lon, *box)
    alb[land & desert] = EARTH_ALBEDO["desert"]
    ice = (land & (lat < -60.0)) | (land & (lat > 60.0) & (lon > -75.0) & (lon < -10.0)) | (land & (lat > 75.0))
    ice |= on_disk & (lat > 82.0)  # Arctic sea ice
    alb[ice] = EARTH_ALBEDO["ice"]
    alb[~on_disk] = 0.0
    return np.clip(_downsample(alb, grid_size, oversample), 0.0, 1.0)


# (name, centre lat, centre lon, semi-axis in latitude, semi-axis in longitude), degrees.
_MOON_MARIA: Tuple[Tuple[str, float, float, float, float], ...] = (
    ("Oceanus Procellarum", 18.0, -57.0, 22.0, 17.0),
    ("Oceanus Procellarum (south)", -2.0, -45.0, 12.0, 12.0),
    ("Mare Imbrium", 32.8, -15.6, 17.0, 18.0),
    ("Mare Serenitatis", 28.0, 17.5, 10.0, 10.0),
    ("Mare Tranquillitatis", 8.5, 31.4, 11.0, 13.0),
    ("Mare Crisium", 17.0, 59.1, 8.0, 9.0),
    ("Mare Fecunditatis", -7.8, 51.3, 11.0, 8.0),
    ("Mare Nectaris", -15.2, 35.5, 5.5, 5.5),
    ("Mare Nubium", -21.3, -16.6, 10.0, 11.0),
    ("Mare Cognitum", -10.0, -23.0, 5.0, 6.0),
    ("Mare Humorum", -24.4, -38.6, 6.0, 6.0),
    ("Mare Vaporum", 13.3, 3.6, 4.0, 4.0),
    ("Mare Frigoris", 56.0, 1.4, 4.0, 40.0),
)
MOON_ALBEDO = {"highland": 0.55, "mare": 0.26, "bright_crater": 0.85}


def moon_albedo_map(grid_size: int = 32, oversample: int = 4) -> np.ndarray:
    """
    Schematic albedo map of the Moon's near side (highlands, maria, Tycho).

    Parameters
    ----------
    grid_size : int, optional
        Output dimensions (default: 32 x 32).
    oversample : int, optional
        Sub-samples per pixel along each axis.

    Returns
    -------
    np.ndarray
        ``(grid_size, grid_size)`` albedo in ``[0, 1]``, 0 outside the disk.
    """
    lat, lon, on_disk = _orthographic_latlon(grid_size, 0.0, 0.0, oversample)
    la = np.nan_to_num(lat)
    lo = np.nan_to_num(lon)
    alb = np.full(lat.shape, MOON_ALBEDO["highland"])
    for _, clat, clon, a_lat, a_lon in _MOON_MARIA:
        inside = ((la - clat) / a_lat) ** 2 + ((lo - clon) * np.cos(np.radians(la)) / (a_lon * np.cos(np.radians(clat)))) ** 2 <= 1.0
        alb[inside] = MOON_ALBEDO["mare"]
    tycho = ((la + 43.3) ** 2 + ((lo + 11.4) * np.cos(np.radians(la))) ** 2) <= 3.5 ** 2
    alb[tycho] = MOON_ALBEDO["bright_crater"]
    alb[~on_disk] = 0.0
    return np.clip(_downsample(alb, grid_size, oversample), 0.0, 1.0)


REFERENCE_BODIES: Dict[str, str] = {
    "earth": "Earth, cloud-free, facing Africa and Europe",
    "moon": "Moon, near side (schematic maria)",
}


def reference_body_map(name: str, grid_size: int = 32) -> np.ndarray:
    """Albedo map of a reference body by name: ``"earth"`` or ``"moon"``."""
    key = name.strip().lower()
    if key == "earth":
        return earth_albedo_map(grid_size=grid_size)
    if key == "moon":
        return moon_albedo_map(grid_size=grid_size)
    raise ValueError(f"Unknown reference body {name!r}; choose from {sorted(REFERENCE_BODIES)}")


# ---------------------------------------------------------------------------
# Global (latitude x longitude) maps, so a body can be rotated.
# ---------------------------------------------------------------------------

_GLOBAL_LAT = np.arange(89.5, -90.0, -1.0)    # 180 rows, north first
_GLOBAL_LON = np.arange(-179.5, 180.0, 1.0)   # 360 columns


def earth_global_map() -> np.ndarray:
    """Cloud-free Earth albedo on a 1-degree latitude/longitude grid (180 x 360)."""
    lat, lon = np.meshgrid(_GLOBAL_LAT, _GLOBAL_LON, indexing="ij")
    land = _land_mask()
    alb = np.where(land, EARTH_ALBEDO["land"], EARTH_ALBEDO["ocean"])
    desert = np.zeros_like(land)
    for box in _EARTH_DESERTS:
        desert |= _in_box(lat, lon, *box)
    alb = np.where(land & desert, EARTH_ALBEDO["desert"], alb)
    ice = (land & (lat < -60.0)) | (land & (lat > 60.0) & (lon > -75.0) & (lon < -10.0)) | (land & (lat > 75.0)) | (lat > 82.0)
    return np.where(ice, EARTH_ALBEDO["ice"], alb)


def moon_global_map() -> np.ndarray:
    """Schematic lunar albedo on a 1-degree grid; maria on the near side, highlands elsewhere."""
    la, lo = np.meshgrid(_GLOBAL_LAT, _GLOBAL_LON, indexing="ij")
    alb = np.full(la.shape, MOON_ALBEDO["highland"])
    for _, clat, clon, a_lat, a_lon in _MOON_MARIA:
        inside = ((la - clat) / a_lat) ** 2 + ((lo - clon) * np.cos(np.radians(la)) / (a_lon * np.cos(np.radians(clat)))) ** 2 <= 1.0
        alb[inside] = MOON_ALBEDO["mare"]
    tycho = ((la + 43.3) ** 2 + ((lo + 11.4) * np.cos(np.radians(la))) ** 2) <= 3.5 ** 2
    alb[tycho] = MOON_ALBEDO["bright_crater"]
    return alb


def synthetic_global_map(seed: int = 42) -> np.ndarray:
    """
    Synthetic ocean world with continents and polar caps on a 1-degree grid.

    Continents are blobs at random positions on the sphere (reproducible for a
    given seed), so the planet looks different as it rotates.
    """
    rng = np.random.RandomState(seed)
    la, lo = np.meshgrid(np.radians(_GLOBAL_LAT), np.radians(_GLOBAL_LON), indexing="ij")
    xyz = np.stack([np.cos(la) * np.cos(lo), np.cos(la) * np.sin(lo), np.sin(la)], axis=-1)
    field = np.zeros(la.shape)
    for _ in range(14):
        c_lat = np.arcsin(rng.uniform(-0.8, 0.8))
        c_lon = rng.uniform(-np.pi, np.pi)
        c = np.array([np.cos(c_lat) * np.cos(c_lon), np.cos(c_lat) * np.sin(c_lon), np.sin(c_lat)])
        width = rng.uniform(0.3, 0.55)
        ang = np.arccos(np.clip(xyz @ c, -1.0, 1.0))
        field += np.exp(-(ang / width) ** 2)
    land = field > 0.55
    alb = np.where(land, 0.30 + 0.06 * np.sin(5 * lo) * np.cos(3 * la), 0.06)
    alb = np.where(np.abs(np.degrees(la)) > 66.0, 0.80, alb)
    return np.clip(alb, 0.0, 1.0)


GLOBAL_MAPS = {
    "planet": synthetic_global_map,
    "earth": earth_global_map,
    "moon": moon_global_map,
}


def render_global_map(global_map: np.ndarray, grid_size: int = 32, sub_lon_deg: float = 0.0,
                      sub_lat_deg: float = 0.0, oversample: int = 2) -> np.ndarray:
    """
    Orthographic view of a 180 x 360 global map, centred on (sub_lat, sub_lon).

    Same layout as the other maps in this module: ``grid_size x grid_size``,
    disk radius 0.95, zero outside, row 0 north.
    """
    lat, lon, on_disk = _orthographic_latlon(grid_size, sub_lat_deg, sub_lon_deg, oversample)
    i = np.clip(np.round(89.5 - np.nan_to_num(lat)).astype(int), 0, 179)
    j = np.clip(np.round(np.nan_to_num(lon) + 179.5).astype(int), 0, 359)
    fine = np.where(on_disk, global_map[i, j], 0.0)
    return _downsample(fine, grid_size, oversample)
