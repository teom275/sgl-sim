"""
Exoplanet Target Resolver & Heliocentric 3D Telemetry for Gravitational Lens Telescopes.

Integrates with the NASA Exoplanet Archive TAP API, SIMBAD/Astropy coordinates,
and provides a curated offline catalog of prime SGL exoplanet targets (Proxima Cen b,
TRAPPIST-1 d/e/f, LHS 1140 b, Tau Ceti e, Teegarden b, Ross 128 b, etc.).
Computes the exact 3D heliocentric positioning, celestial antipode (RA/Dec),
ecliptic coordinates, proper-motion lateral drift, and communication/cruise logistics.
"""

from typing import Dict, Any, List, Optional, Union
import re
import json
import urllib.request
import urllib.parse
import warnings
import numpy as np

import astropy.units as u
from astropy.constants import c as C_ASTROPY
from astropy.coordinates import SkyCoord, ICRS, HeliocentricTrueEcliptic
from astropy.time import Time

from sgl_sim.relativity import AU_SI, PC_SI, C_SI, _to_si_value
from sgl_sim.orbital import image_cylinder_diameter

# Earth radius in meters
R_EARTH_SI = 6.371e6

# Curated offline catalog of top 15 prime SGL exoplanet targets
TOP_15_SGL_TARGETS: Dict[str, Dict[str, Any]] = {
    "Proxima Centauri b": {
        "name": "Proxima Centauri b",
        "aliases": ["proxima cen b", "proxima b", "alpha cen c b", "gliese 551 b"],
        "hostname": "Proxima Centauri",
        "ra_deg": 217.428938,
        "dec_deg": -62.679492,
        "distance_pc": 1.3012,
        "distance_ly": 4.244,
        "pmra_mas_yr": -3781.74,
        "pmdec_mas_yr": 769.46,
        "pl_rade": 1.03,
        "st_mass_solar": 0.12,
        "constellation": "Centaurus",
        "description": "Closest known exoplanet to Earth; prime candidate for high-resolution multipixel SGL imaging.",
    },
    "TRAPPIST-1 d": {
        "name": "TRAPPIST-1 d",
        "aliases": ["trappist 1 d", "2mass j23062928-0502285 d"],
        "hostname": "TRAPPIST-1",
        "ra_deg": 346.622375,
        "dec_deg": -5.041389,
        "distance_pc": 12.43,
        "distance_ly": 40.54,
        "pmra_mas_yr": 888.66,
        "pmdec_mas_yr": -471.21,
        "pl_rade": 0.788,
        "st_mass_solar": 0.089,
        "constellation": "Aquarius",
        "description": "Ultra-cool dwarf system with 7 temperate rocky planets; inner habitable-zone candidate.",
    },
    "TRAPPIST-1 e": {
        "name": "TRAPPIST-1 e",
        "aliases": ["trappist 1 e", "2mass j23062928-0502285 e"],
        "hostname": "TRAPPIST-1",
        "ra_deg": 346.622375,
        "dec_deg": -5.041389,
        "distance_pc": 12.43,
        "distance_ly": 40.54,
        "pmra_mas_yr": 888.66,
        "pmdec_mas_yr": -471.21,
        "pl_rade": 0.920,
        "st_mass_solar": 0.089,
        "constellation": "Aquarius",
        "description": "Earth-sized planet in the prime habitable zone with high probability of surface liquid water.",
    },
    "TRAPPIST-1 f": {
        "name": "TRAPPIST-1 f",
        "aliases": ["trappist 1 f", "2mass j23062928-0502285 f"],
        "hostname": "TRAPPIST-1",
        "ra_deg": 346.622375,
        "dec_deg": -5.041389,
        "distance_pc": 12.43,
        "distance_ly": 40.54,
        "pmra_mas_yr": 888.66,
        "pmdec_mas_yr": -471.21,
        "pl_rade": 1.045,
        "st_mass_solar": 0.089,
        "constellation": "Aquarius",
        "description": "Outer habitable-zone planet with potential volatile-rich or ice-covered surface.",
    },
    "LHS 1140 b": {
        "name": "LHS 1140 b",
        "aliases": ["lhs1140 b", "gj 3053 b"],
        "hostname": "LHS 1140",
        "ra_deg": 11.2475,
        "dec_deg": -15.2705,
        "distance_pc": 14.99,
        "distance_ly": 48.88,
        "pmra_mas_yr": -317.06,
        "pmdec_mas_yr": -597.43,
        "pl_rade": 1.73,
        "st_mass_solar": 0.19,
        "constellation": "Cetus",
        "description": "Super-Earth in the habitable zone of a quiet M dwarf; excellent candidate for atmospheric characterization.",
    },
    "Tau Ceti e": {
        "name": "Tau Ceti e",
        "aliases": ["tau cet e", "hd 10700 e"],
        "hostname": "Tau Ceti",
        "ra_deg": 26.0170,
        "dec_deg": -15.9375,
        "distance_pc": 3.65,
        "distance_ly": 11.90,
        "pmra_mas_yr": -1721.05,
        "pmdec_mas_yr": 854.16,
        "pl_rade": 1.80,
        "st_mass_solar": 0.78,
        "constellation": "Cetus",
        "description": "Super-Earth candidate around a solar analog (G-dwarf) at only 3.65 pc.",
    },
    "Teegarden's Star b": {
        "name": "Teegarden's Star b",
        "aliases": ["teegarden b", "teegarden star b"],
        "hostname": "Teegarden's Star",
        "ra_deg": 43.2758,
        "dec_deg": 16.8647,
        "distance_pc": 3.83,
        "distance_ly": 12.50,
        "pmra_mas_yr": 5040.85,
        "pmdec_mas_yr": -3799.39,
        "pl_rade": 1.05,
        "st_mass_solar": 0.089,
        "constellation": "Aries",
        "description": "Very nearby Earth-mass planet in the habitable zone with high Earth Similarity Index (ESI = 0.95).",
    },
    "Ross 128 b": {
        "name": "Ross 128 b",
        "aliases": ["ross128 b", "gj 447 b"],
        "hostname": "Ross 128",
        "ra_deg": 176.9350,
        "dec_deg": 0.8045,
        "distance_pc": 3.37,
        "distance_ly": 11.00,
        "pmra_mas_yr": 607.72,
        "pmdec_mas_yr": -1219.28,
        "pl_rade": 1.11,
        "st_mass_solar": 0.17,
        "constellation": "Virgo",
        "description": "Temperate planet around an inactive M dwarf; benign stellar environment.",
    },
    "Gliese 667 Cc": {
        "name": "Gliese 667 Cc",
        "aliases": ["gj 667 c c", "gl 667 c c", "gliese 667c c"],
        "hostname": "Gliese 667 C",
        "ra_deg": 259.0833,
        "dec_deg": -34.9969,
        "distance_pc": 7.24,
        "distance_ly": 23.62,
        "pmra_mas_yr": 1129.74,
        "pmdec_mas_yr": -80.99,
        "pl_rade": 1.54,
        "st_mass_solar": 0.73,
        "constellation": "Scorpius",
        "description": "Super-Earth in a triple star system receiving ~90% of Earth's solar flux.",
    },
    "Epsilon Eridani b": {
        "name": "Epsilon Eridani b",
        "aliases": ["eps eri b", "hd 22049 b", "aegir"],
        "hostname": "Epsilon Eridani",
        "ra_deg": 53.2327,
        "dec_deg": -9.4583,
        "distance_pc": 3.22,
        "distance_ly": 10.50,
        "pmra_mas_yr": -976.44,
        "pmdec_mas_yr": 17.98,
        "pl_rade": 12.0,
        "st_mass_solar": 0.82,
        "constellation": "Eridanus",
        "description": "Giant planet around a young K-type star at only 3.2 pc; testbed for circumplanetary rings.",
    },
    "Wolf 1061 c": {
        "name": "Wolf 1061 c",
        "aliases": ["wolf1061 c", "gj 628 c"],
        "hostname": "Wolf 1061",
        "ra_deg": 247.5833,
        "dec_deg": -12.6639,
        "distance_pc": 4.31,
        "distance_ly": 14.05,
        "pmra_mas_yr": -1071.0,
        "pmdec_mas_yr": -437.0,
        "pl_rade": 1.66,
        "st_mass_solar": 0.29,
        "constellation": "Ophiuchus",
        "description": "Rocky super-Earth in the habitable zone of an M dwarf at 4.3 pc.",
    },
    "Luyten b": {
        "name": "Luyten b",
        "aliases": ["gj 273 b", "luyten's star b", "luyten star b"],
        "hostname": "Luyten's Star",
        "ra_deg": 111.8542,
        "dec_deg": 5.2250,
        "distance_pc": 3.80,
        "distance_ly": 12.39,
        "pmra_mas_yr": -570.8,
        "pmdec_mas_yr": -3693.0,
        "pl_rade": 1.18,
        "st_mass_solar": 0.29,
        "constellation": "Canis Minor",
        "description": "Nearby super-Earth (1.35 M_earth) receiving roughly 1.06x Earth insolation.",
    },
    "Kapteyn b": {
        "name": "Kapteyn b",
        "aliases": ["kapteyn's star b", "gj 191 b"],
        "hostname": "Kapteyn's Star",
        "ra_deg": 77.9192,
        "dec_deg": -45.0181,
        "distance_pc": 3.93,
        "distance_ly": 12.82,
        "pmra_mas_yr": 6506.0,
        "pmdec_mas_yr": -5731.0,
        "pl_rade": 1.60,
        "st_mass_solar": 0.28,
        "constellation": "Pictor",
        "description": "Subdwarf galactic halo star planet with massive proper motion (>8 arcsec/yr).",
    },
    "Gliese 1061 d": {
        "name": "Gliese 1061 d",
        "aliases": ["gj 1061 d", "gl 1061 d"],
        "hostname": "Gliese 1061",
        "ra_deg": 54.8967,
        "dec_deg": -44.5147,
        "distance_pc": 3.67,
        "distance_ly": 11.97,
        "pmra_mas_yr": 739.0,
        "pmdec_mas_yr": -467.0,
        "pl_rade": 1.14,
        "st_mass_solar": 0.12,
        "constellation": "Horologium",
        "description": "Nearby red dwarf system with a planet in the conservative habitable zone.",
    },
    "TOI-700 d": {
        "name": "TOI-700 d",
        "aliases": ["toi 700 d"],
        "hostname": "TOI-700",
        "ra_deg": 97.4371,
        "dec_deg": -65.6744,
        "distance_pc": 31.13,
        "distance_ly": 101.53,
        "pmra_mas_yr": 41.5,
        "pmdec_mas_yr": 147.2,
        "pl_rade": 1.14,
        "st_mass_solar": 0.42,
        "constellation": "Dorado",
        "description": "First Earth-sized habitable-zone planet discovered by NASA's TESS mission.",
    },
}


def list_curated_targets() -> List[Dict[str, Any]]:
    """Return the curated list of top 15 prime SGL exoplanet targets."""
    return list(TOP_15_SGL_TARGETS.values())


def _find_in_curated_catalog(name: str) -> Optional[Dict[str, Any]]:
    """Look up exoplanet by primary name or known aliases in the curated catalog."""
    norm = name.strip().lower()
    for target in TOP_15_SGL_TARGETS.values():
        if norm == target["name"].lower():
            return dict(target)
        for alias in target.get("aliases", []):
            if norm == alias.lower():
                return dict(target)
    # Substring / partial match
    for target in TOP_15_SGL_TARGETS.values():
        if norm in target["name"].lower() or any(norm in a.lower() for a in target.get("aliases", [])):
            return dict(target)
    return None


def _parse_coordinate_string(text: str) -> Optional[Dict[str, Any]]:
    """
    Attempt to parse custom coordinates from a string.
    Supports formats like '217.42, -62.68' or 'RA: 217.42, Dec: -62.68'.
    """
    numbers = re.findall(r"[-+]?\d*\.?\d+", text)
    if len(numbers) >= 2:
        try:
            ra = float(numbers[0]) % 360.0
            dec = float(numbers[1])
            if -90.0 <= dec <= 90.0:
                dist_pc = float(numbers[2]) if len(numbers) >= 3 else 10.0
                sc = SkyCoord(ra=ra * u.deg, dec=dec * u.deg, frame="icrs")
                return {
                    "name": f"Custom Coordinates ({ra:.2f}°, {dec:.2f}°)",
                    "hostname": "User Defined",
                    "ra_deg": float(ra),
                    "dec_deg": float(dec),
                    "distance_pc": float(dist_pc),
                    "distance_ly": float(dist_pc * 3.26156),
                    "pmra_mas_yr": 0.0,
                    "pmdec_mas_yr": 0.0,
                    "pl_rade": 1.0,
                    "st_mass_solar": 1.0,
                    "constellation": sc.get_constellation(),
                    "source": "Custom Input",
                    "description": "User-specified custom celestial coordinates.",
                }
        except (ValueError, TypeError):
            pass
    return None


def resolve_exoplanet(name_or_coords: Union[str, Dict[str, Any]]) -> Dict[str, Any]:
    """
    Resolve an exoplanet target using the NASA Exoplanet Archive, Astropy, or curated catalog.

    Parameters
    ----------
    name_or_coords : str or dict
        Exoplanet name (e.g. 'Proxima Cen b', 'TRAPPIST-1 e'), coordinate string
        (e.g. '217.42, -62.68'), or dictionary with target properties.

    Returns
    -------
    dict
        Standardized target dictionary with RA, Dec, distance, proper motions,
        planet radius, and constellation.
    """
    if isinstance(name_or_coords, dict):
        # Already a dictionary; validate and augment
        target = dict(name_or_coords)
        ra = float(target.get("ra_deg", target.get("ra", 0.0)))
        dec = float(target.get("dec_deg", target.get("dec", 0.0)))
        dist_pc = float(target.get("distance_pc", target.get("sy_dist", 10.0)))
        sc = SkyCoord(ra=ra * u.deg, dec=dec * u.deg, frame="icrs")
        target.setdefault("name", "Custom Target")
        target.setdefault("hostname", "Unknown Host")
        target["ra_deg"] = ra
        target["dec_deg"] = dec
        target["distance_pc"] = dist_pc
        target.setdefault("distance_ly", dist_pc * 3.26156)
        target.setdefault("pmra_mas_yr", float(target.get("pmra", 0.0)))
        target.setdefault("pmdec_mas_yr", float(target.get("pmdec", 0.0)))
        target.setdefault("pl_rade", float(target.get("pl_rade", 1.0)))
        target.setdefault("st_mass_solar", float(target.get("st_mass", 1.0)))
        target.setdefault("constellation", sc.get_constellation())
        target.setdefault("source", "User Dictionary")
        return target

    query_str = str(name_or_coords).strip()

    # 1. Check curated offline catalog first
    curated = _find_in_curated_catalog(query_str)
    if curated is not None:
        curated["source"] = "Curated SGL Catalog"
        return curated

    # 2. Check if query is a numeric coordinate pair (e.g. '217.42, -62.68')
    coords = _parse_coordinate_string(query_str)
    if coords is not None:
        return coords

    # 3. Query the official NASA Exoplanet Archive TAP API
    # https://exoplanetarchive.ipac.caltech.edu/docs/TAP/API_TAP_tutorial.html
    try:
        clean_name = query_str.replace("'", "''")
        adql = (
            f"SELECT TOP 1 pl_name, hostname, ra, dec, sy_dist, pmra, pmdec, pl_rade, st_mass "
            f"FROM ps "
            f"WHERE lower(pl_name) LIKE lower('%{clean_name}%') "
            f"ORDER BY default_flag DESC"
        )
        url = "https://exoplanetarchive.ipac.caltech.edu/TAP/sync?query=" + urllib.parse.quote(adql) + "&format=json"
        req = urllib.request.Request(url, headers={"User-Agent": "sgl-sim/0.1.0"})
        with urllib.request.urlopen(req, timeout=3.5) as response:
            payload = json.loads(response.read().decode("utf-8"))
            if payload and len(payload) > 0:
                row = payload[0]
                ra = float(row.get("ra", 0.0))
                dec = float(row.get("dec", 0.0))
                dist_pc = float(row.get("sy_dist")) if row.get("sy_dist") is not None else 10.0
                sc = SkyCoord(ra=ra * u.deg, dec=dec * u.deg, frame="icrs")
                return {
                    "name": row.get("pl_name", query_str),
                    "hostname": row.get("hostname", query_str),
                    "ra_deg": ra,
                    "dec_deg": dec,
                    "distance_pc": dist_pc,
                    "distance_ly": float(dist_pc * 3.26156),
                    "pmra_mas_yr": float(row.get("pmra") or 0.0),
                    "pmdec_mas_yr": float(row.get("pmdec") or 0.0),
                    "pl_rade": float(row.get("pl_rade") or 1.0),
                    "st_mass_solar": float(row.get("st_mass") or 1.0),
                    "constellation": sc.get_constellation(),
                    "source": "NASA Exoplanet Archive (Live TAP)",
                    "description": f"Retrieved live from NASA Exoplanet Archive TAP service.",
                }
    except Exception:
        # Fall back to Astropy's SkyCoord resolver (e.g. SIMBAD/NED) if available
        try:
            sc = SkyCoord.from_name(query_str)
            dist_pc = sc.distance.pc if sc.distance is not None and not np.isnan(sc.distance.pc) else 10.0
            return {
                "name": query_str,
                "hostname": query_str,
                "ra_deg": float(sc.ra.deg),
                "dec_deg": float(sc.dec.deg),
                "distance_pc": float(dist_pc),
                "distance_ly": float(dist_pc * 3.26156),
                "pmra_mas_yr": 0.0,
                "pmdec_mas_yr": 0.0,
                "pl_rade": 1.0,
                "st_mass_solar": 1.0,
                "constellation": sc.get_constellation(),
                "source": "Astropy SkyCoord.from_name()",
                "description": f"Resolved via Astropy name resolver.",
            }
        except Exception:
            pass

    # If all resolutions fail, provide fallback or raise helpful error
    raise ValueError(
        f"Unable to resolve exoplanet '{query_str}'. Please select from the curated catalog "
        f"({', '.join(list(TOP_15_SGL_TARGETS.keys())[:5])}...) or provide coordinates as 'RA, Dec'."
    )


def compute_sgl_deployment_vector(
    target_data: Union[str, Dict[str, Any]],
    z_rec_au: Union[float, u.Quantity] = 650.0,
    arrival_year: Optional[float] = 2048.0,
    cruise_vel_au_yr: float = 20.0,
) -> Dict[str, Any]:
    """
    Compute the 3D heliocentric coordinates, celestial antipode, and drift kinematics
    required to place a telescope on the Solar Gravitational Lens focal line.

    Parameters
    ----------
    target_data : str or dict
        Target exoplanet name or dictionary resolved via resolve_exoplanet.
    z_rec_au : float or astropy.units.Quantity, optional
        Telescope receiver distance in AU (default: 650.0 AU).
    arrival_year : float, optional
        Target mission arrival year to apply proper motion space propagation
        (default: 2048.0). If None, uses J2000 coordinates without space motion.
    cruise_vel_au_yr : float, optional
        Spacecraft cruise velocity in AU/year (default: 20.0 AU/yr, standard Solar Oberth).

    Returns
    -------
    dict
        Dictionary containing:
        - target_name, target coordinates (J2000 & arrival year), constellation
        - telescope antipodal coordinates (RA/Dec), constellation direction
        - 3D Heliocentric Cartesian coordinates (X, Y, Z) in AU
        - Heliocentric Ecliptic coordinates (longitude, latitude/inclination)
        - Communication light delay (seconds, hours, light-days)
        - Cruise transit time (years)
        - Projected exoplanet image cylinder diameter (m and km)
        - Lateral proper-motion drift velocity (m/s and km/yr)
    """
    if isinstance(target_data, str):
        target = resolve_exoplanet(target_data)
    else:
        target = dict(target_data)

    # 1. Receiver Distance Handling
    if isinstance(z_rec_au, u.Quantity):
        z_au = float(z_rec_au.to(u.AU).value)
    else:
        z_val = float(z_rec_au)
        # If passed in meters (> 1e6), convert to AU
        if z_val > 1.0e6:
            z_au = z_val / AU_SI
        else:
            z_au = z_val

    z_m = z_au * AU_SI

    # 2. Celestial Coordinates & Space Motion Propagation
    ra_j2000 = float(target["ra_deg"])
    dec_j2000 = float(target["dec_deg"])
    dist_pc = float(target.get("distance_pc", 10.0))
    dist_ly = float(target.get("distance_ly", dist_pc * 3.26156))
    dist_m = dist_pc * PC_SI
    pmra = float(target.get("pmra_mas_yr", 0.0))
    pmdec = float(target.get("pmdec_mas_yr", 0.0))
    pl_rade = float(target.get("pl_rade", 1.0))
    r_exo_m = pl_rade * R_EARTH_SI

    sc_j2000 = SkyCoord(
        ra=ra_j2000 * u.deg,
        dec=dec_j2000 * u.deg,
        distance=dist_pc * u.pc,
        pm_ra_cosdec=pmra * (u.mas / u.yr),
        pm_dec=pmdec * (u.mas / u.yr),
        obstime=Time("J2000.0"),
        frame="icrs",
    )

    if arrival_year is not None and (abs(pmra) > 1e-5 or abs(pmdec) > 1e-5):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            t_target = Time(float(arrival_year), format="decimalyear")
            sc_propagated = sc_j2000.apply_space_motion(new_obstime=t_target)
        target_ra = float(sc_propagated.ra.deg)
        target_dec = float(sc_propagated.dec.deg)
    else:
        target_ra = ra_j2000
        target_dec = dec_j2000

    target_constellation = sc_j2000.get_constellation()

    # 3. Telescope Placement Direction (Celestial Antipode)
    # The telescope is placed on the opposite side of the Sun from the exoplanet:
    # tel_ra = (target_ra + 180.0) % 360.0
    # tel_dec = -target_dec
    tel_ra_deg = float((target_ra + 180.0) % 360.0)
    tel_dec_deg = float(-target_dec)

    tel_coord = SkyCoord(
        ra=tel_ra_deg * u.deg,
        dec=tel_dec_deg * u.deg,
        distance=z_au * u.AU,
        frame="icrs",
    )
    tel_constellation = tel_coord.get_constellation()

    # 4. 3D Heliocentric Cartesian Coordinates (AU)
    # X = z_au * cos(dec) * cos(ra)
    # Y = z_au * cos(dec) * sin(ra)
    # Z = z_au * sin(dec)
    x_au = float(tel_coord.cartesian.x.to(u.AU).value)
    y_au = float(tel_coord.cartesian.y.to(u.AU).value)
    z_au_coord = float(tel_coord.cartesian.z.to(u.AU).value)
    norm_au = float(np.sqrt(x_au**2 + y_au**2 + z_au_coord**2))

    # 5. Heliocentric Ecliptic Coordinates
    # Used to determine out-of-ecliptic inclination angle
    ecl = tel_coord.transform_to(HeliocentricTrueEcliptic())
    ecl_lon_deg = float(ecl.lon.deg)
    ecl_lat_deg = float(ecl.lat.deg)
    ecl_inclination_deg = float(abs(ecl_lat_deg))

    # 6. Communication Light Delay & Transit Time
    # c = 299,792,458 m/s
    light_sec = float(z_m / C_SI)
    light_hours = float(light_sec / 3600.0)
    light_days = float(light_sec / 86400.0)

    # Cruise time at escape velocity (e.g. 20 AU/year)
    cruise_years = float(z_au / max(cruise_vel_au_yr, 1e-3))

    # 7. Projected Exoplanet Image Cylinder Diameter (D_img = 2 * R_exo * z_rec / d_source)
    img_cyl = image_cylinder_diameter(
        z_rec=z_m,
        distance_source=dist_m,
        exoplanet_radius=r_exo_m,
    )
    d_img_m = float(img_cyl["d_img_m"])
    d_img_km = float(img_cyl["d_img_km"])

    # 8. Lateral Proper-Motion Focal Line Drift
    # As the host star traverses the sky at proper motion rate mu (mas/yr),
    # the focal line sweeps laterally across space: v_drift = z_rec * mu_rad_s
    pm_total_mas_yr = float(np.sqrt((pmra * np.cos(np.radians(dec_j2000)))**2 + pmdec**2))
    # Convert mas/yr to rad/s: 1 mas = pi / (180 * 3600 * 1000) rad, 1 yr = 365.25 * 86400 s
    mas_to_rad = np.pi / (180.0 * 3600.0 * 1000.0)
    yr_to_sec = 365.25 * 86400.0
    mu_rad_s = pm_total_mas_yr * mas_to_rad / yr_to_sec
    drift_m_s = float(z_m * mu_rad_s)
    drift_km_s = float(drift_m_s / 1000.0)
    annual_drift_km = float(drift_m_s * yr_to_sec / 1000.0)

    return {
        "target_name": target.get("name", "Custom Target"),
        "hostname": target.get("hostname", "Unknown Host"),
        "target_description": target.get("description", ""),
        "source": target.get("source", "Catalog"),
        
        # Target Celestial Coordinates
        "target_ra_deg": float(target_ra),
        "target_dec_deg": float(target_dec),
        "target_ra_j2000_deg": float(ra_j2000),
        "target_dec_j2000_deg": float(dec_j2000),
        "target_constellation": target_constellation,
        "target_distance_pc": float(dist_pc),
        "target_distance_ly": float(dist_ly),
        "target_pl_rade": float(pl_rade),
        "target_pmra_mas_yr": float(pmra),
        "target_pmdec_mas_yr": float(pmdec),
        "target_pm_total_mas_yr": float(pm_total_mas_yr),
        "arrival_year": arrival_year,

        # Telescope Deployment Antipode
        "telescope_ra_deg": float(tel_ra_deg),
        "telescope_dec_deg": float(tel_dec_deg),
        "telescope_constellation": tel_constellation,

        # 3D Heliocentric Cartesian Coordinates
        "z_rec_au": float(z_au),
        "x_au": float(x_au),
        "y_au": float(y_au),
        "z_au": float(z_au_coord),
        "vector_norm_au": float(norm_au),

        # Heliocentric Ecliptic Coordinates
        "ecliptic_lon_deg": float(ecl_lon_deg),
        "ecliptic_lat_deg": float(ecl_lat_deg),
        "ecliptic_inclination_deg": float(ecl_inclination_deg),

        # Logistics & Communications
        "light_delay_seconds": float(light_sec),
        "light_delay_hours": float(light_hours),
        "light_delay_days": float(light_days),
        "cruise_velocity_au_yr": float(cruise_vel_au_yr),
        "cruise_time_years": float(cruise_years),

        # Image Cylinder & Proper-Motion Drift
        "image_diameter_m": float(d_img_m),
        "image_diameter_km": float(d_img_km),
        "proper_motion_drift_m_s": float(drift_m_s),
        "proper_motion_drift_km_s": float(drift_km_s),
        "annual_lateral_drift_km": float(annual_drift_km),
    }
