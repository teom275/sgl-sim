"""
Pure-NumPy scene geometry for the ManimGL interactive scenes.

Everything here converts *physical* sgl-sim quantities into 3-vectors in manim
scene coordinates (the default ManimGL frame is 14.22 x 8 units, centred on the
origin). Nothing in this module imports ManimGL, so it can be unit-tested in
the regular CI environment.

Display conventions
-------------------
Focal-line view (``FocalLineView``)
    * Horizontal axis: distance ``z`` behind the lens in AU, linear.
    * Vertical axis: impact parameter ``b`` in stellar radii (``R_sun``).
    The two axes have wildly different scales (a ray grazing the Sun bends by
    only 1.75 arcsec), so the drawing is *not* angle-preserving. It *is*
    exact about **where** every ray crosses the optical axis: a ray with impact
    parameter ``b`` is drawn as a straight segment from the lens plane at
    height ``b`` to the axis crossing ``z(b) = b^2 / (2 R_s)``.

Caustic view (``CausticView``)
    * The transverse receiver plane is drawn in units of the astroid semi-width
      ``a_caustic``. Because the quadrupole lens equation
      ``x0 sin(phi) - y0 cos(phi) - (a/2) sin(2 phi) = 0`` only depends on the
      ratios ``x0/a`` and ``y0/a``, the image configuration is independent of
      the absolute scale, which is reported separately in metres.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Sequence

import numpy as np

from sgl_sim.relativity import AU_SI, M_SUN_SI, R_SUN_SI, schwarzschild_radius
from sgl_sim.optics import (
    einstein_ring_properties,
    minimum_focal_distance,
    peak_magnification,
    psf_intensity,
)
from sgl_sim.caustics import (
    astroid_caustic_semi_width,
    check_caustic_regime,
    solve_quadrupole_images,
)


def _p(x: float, y: float) -> np.ndarray:
    """Build a manim 3-vector (z = 0)."""
    return np.array([float(x), float(y), 0.0])


# ---------------------------------------------------------------------------
# Focal line / ray bundle
# ---------------------------------------------------------------------------


def focal_distance_au(b_rsun: float, mass_msun: float) -> float:
    """Axis crossing distance ``z(b) = b^2 / (2 R_s)`` in AU for ``b`` in R_sun."""
    rs = schwarzschild_radius(mass_msun * M_SUN_SI)
    b_m = b_rsun * R_SUN_SI
    return float(b_m**2 / (2.0 * rs) / AU_SI)


def ring_impact_parameter_rsun(z_au: float, mass_msun: float) -> float:
    """Impact parameter (R_sun) of the ray that focuses exactly at ``z_au``."""
    ring = einstein_ring_properties(z_rec=z_au * AU_SI, mass=mass_msun * M_SUN_SI)
    return float(ring["b_ring_r_sun"])


@dataclass(frozen=True)
class FocalLineView:
    """Mapping from (z [AU], b [R_sun]) to manim scene coordinates."""

    x_left: float = -7.2
    x_lens: float = -5.0
    x_right: float = 7.2
    y_axis: float = -0.4
    z_max_au: float = 2000.0
    y_per_rsun: float = 0.9
    y_limit: float = 3.4

    @property
    def x_per_au(self) -> float:
        return (self.x_right - self.x_lens) / self.z_max_au

    def x_of_z(self, z_au: float) -> float:
        return self.x_lens + z_au * self.x_per_au

    def y_of_b(self, b_rsun: float) -> float:
        return self.y_axis + b_rsun * self.y_per_rsun

    def point(self, z_au: float, b_rsun: float) -> np.ndarray:
        return _p(self.x_of_z(z_au), self.y_of_b(b_rsun))


@dataclass
class RayPath:
    """A single lensed (or occulted) ray in scene coordinates."""

    b_rsun: float
    blocked: bool
    z_focus_au: float
    points: np.ndarray = field(repr=False)


def lens_ray_paths(
    mass_msun: float,
    radius_rsun: float,
    impact_params_rsun: Sequence[float],
    view: FocalLineView = FocalLineView(),
) -> List[RayPath]:
    """
    Compute polylines for a bundle of rays arriving parallel from the left.

    Positive and negative impact parameters are both allowed (rays above and
    below the optical axis). Rays with ``|b| < R_star`` end on the stellar limb.
    Lensed rays are drawn as a horizontal segment up to the lens plane and a
    straight segment through the axis crossing ``z(b)``, continued until they
    leave the drawing area (``x_right`` or ``|y - y_axis| = y_limit``).
    """
    paths: List[RayPath] = []
    r_disp = radius_rsun * view.y_per_rsun
    for b in impact_params_rsun:
        b = float(b)
        y0 = view.y_of_b(b)
        start = _p(view.x_left, y0)
        if abs(b) < radius_rsun:
            dy = abs(b) * view.y_per_rsun
            x_hit = view.x_lens - np.sqrt(max(r_disp**2 - dy**2, 0.0))
            pts = np.array([start, _p(x_hit, y0)])
            paths.append(RayPath(b, True, float("nan"), pts))
            continue

        z_f = focal_distance_au(abs(b), mass_msun)
        x_f = view.x_of_z(z_f)
        lens_pt = _p(view.x_lens, y0)
        # Straight line from the lens plane through the axis crossing.
        slope = (view.y_axis - y0) / (x_f - view.x_lens)
        x_end = view.x_right
        y_end = y0 + slope * (x_end - view.x_lens)
        if abs(y_end - view.y_axis) > view.y_limit:
            y_end = view.y_axis + np.sign(y_end - view.y_axis) * view.y_limit
            x_end = view.x_lens + (y_end - y0) / slope
        pts = np.array([start, lens_pt, _p(x_end, y_end)])
        paths.append(RayPath(b, False, z_f, pts))
    return paths


def focal_line_readout(mass_msun: float, radius_rsun: float, z_rec_au: float,
                       wavelength_m: float = 1.0e-6) -> Dict[str, float]:
    """Physical numbers shown next to the focal-line diagram."""
    m_kg = mass_msun * M_SUN_SI
    zmin = minimum_focal_distance(mass=m_kg, radius=radius_rsun * R_SUN_SI)
    ring = einstein_ring_properties(z_rec=z_rec_au * AU_SI, mass=m_kg)
    return {
        "z_min_au": zmin["z_min_au"],
        "b_ring_rsun": ring["b_ring_r_sun"],
        "theta_E_arcsec": ring["theta_E_arcsec"],
        "mu_max": peak_magnification(wavelength=wavelength_m, mass=m_kg),
        "in_focus": bool(z_rec_au >= zmin["z_min_au"]),
    }


# ---------------------------------------------------------------------------
# J2 astroid caustic / Einstein cross
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CausticView:
    """Transverse receiver plane, drawn in units of ``a_caustic``."""

    center: tuple = (-2.6, -0.2)
    units_per_a: float = 2.2
    ring_center: tuple = (4.0, 0.3)
    ring_radius: float = 1.9

    def plane_point(self, u: float, v: float) -> np.ndarray:
        cx, cy = self.center
        return _p(cx + u * self.units_per_a, cy + v * self.units_per_a)

    def plane_coords(self, point: Sequence[float]) -> tuple:
        cx, cy = self.center
        return ((point[0] - cx) / self.units_per_a, (point[1] - cy) / self.units_per_a)

    def ring_point(self, phi: float, scale: float = 1.0) -> np.ndarray:
        cx, cy = self.ring_center
        r = self.ring_radius * scale
        return _p(cx + r * np.cos(phi), cy + r * np.sin(phi))


#: Reference configuration used as the length unit of the caustic plane.
CAUSTIC_REF_J2 = 2.2e-7
CAUSTIC_REF_Z_AU = 650.0


def caustic_scale(j2: float, z_rec_au: float, mass_msun: float = 1.0,
                  radius_rsun: float = 1.0) -> float:
    """
    Astroid semi-width relative to the reference (``J2 = 2.2e-7`` at 650 AU).

    The receiver plane is drawn in these fixed physical units, so changing
    ``J2`` or ``z_rec`` visibly grows/shrinks the caustic under a receiver that
    stays put.
    """
    kw = dict(mass=mass_msun * M_SUN_SI, star_radius=radius_rsun * R_SUN_SI)
    a = astroid_caustic_semi_width(z_rec=z_rec_au * AU_SI, j2=j2, **kw)["a_caustic_m"]
    a_ref = astroid_caustic_semi_width(z_rec=CAUSTIC_REF_Z_AU * AU_SI, j2=CAUSTIC_REF_J2,
                                       **kw)["a_caustic_m"]
    return float(a / a_ref)


def astroid_curve(view: CausticView = CausticView(), scale: float = 1.0,
                  num_points: int = 241) -> np.ndarray:
    """Closed astroid ``scale * (cos^3 t, sin^3 t)`` in scene coordinates."""
    t = np.linspace(0.0, 2.0 * np.pi, num_points)
    return np.array([view.plane_point(scale * np.cos(s) ** 3, scale * np.sin(s) ** 3) for s in t])


def einstein_cross_state(u: float, v: float, z_rec_au: float = 650.0,
                         j2: float = 2.2e-7, mass_msun: float = 1.0,
                         radius_rsun: float = 1.0) -> Dict[str, object]:
    """
    Image configuration for a receiver at normalised offset ``(u, v) = (x0/a, y0/a)``.

    Returns the regime, the image azimuths on the Einstein ring, their relative
    intensities (normalised to the brightest image), the 360-degree ring
    profile and the physical astroid semi-width in metres.
    """
    m_kg = mass_msun * M_SUN_SI
    r_m = radius_rsun * R_SUN_SI
    a = astroid_caustic_semi_width(z_rec=z_rec_au * AU_SI, mass=m_kg,
                                   star_radius=r_m, j2=j2)["a_caustic_m"]
    sol = solve_quadrupole_images(x0=u * a, y0=v * a, z_rec=z_rec_au * AU_SI,
                                  mass=m_kg, star_radius=r_m, j2=j2)
    intens = np.asarray(sol["image_intensities"], dtype=float)
    if intens.size:
        intens = intens / intens.max()
    regime = check_caustic_regime(u * a, v * a, a)
    return {
        "regime": regime["regime"],
        "astroid_val": regime["astroid_val"],
        "num_images": int(sol["num_images"]),
        "image_angles_rad": [float(x) for x in sol["image_angles_rad"]],
        "image_intensities": intens.tolist(),
        "phi_grid": np.asarray(sol["phi_grid"]),
        "ring_profile": np.asarray(sol["ring_profile"]),
        "a_caustic_m": float(a),
    }


# ---------------------------------------------------------------------------
# Wave-optics PSF
# ---------------------------------------------------------------------------


def psf_first_zero_m(z_rec_au: float, wavelength_m: float, mass_msun: float = 1.0) -> float:
    """Radius of the first dark ring of the ``J_0^2`` PSF (2.405 / (k theta_E))."""
    ring = einstein_ring_properties(z_rec=z_rec_au * AU_SI, mass=mass_msun * M_SUN_SI)
    k = 2.0 * np.pi / wavelength_m
    return float(2.404825557695773 / (k * ring["theta_E_rad"]))


def psf_curve(z_rec_au: float, wavelength_m: float, rho_max_m: float,
              mass_msun: float = 1.0, num: int = 600) -> Dict[str, np.ndarray]:
    """Normalised radial PSF ``J_0^2`` sampled on ``[0, rho_max_m]``."""
    rho = np.linspace(0.0, rho_max_m, num)
    inten = psf_intensity(rho, z_rec=z_rec_au * AU_SI, wavelength=wavelength_m,
                          mass=mass_msun * M_SUN_SI, normalize=True)
    return {"rho_m": rho, "intensity": np.asarray(inten, dtype=float)}
