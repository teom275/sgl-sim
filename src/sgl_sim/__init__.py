"""
sgl-sim: Gravitational Lens Telescopes (Solar & Black Hole Focal Line Missions) Simulator.

An open-source scientific Python package adhering to JOSS and Astropy affiliated standards
for mission design, relativistic ray-tracing, wave optics, J2 astroid caustics, and
exoplanet deconvolution around Solar and Black Hole Gravitational Lenses.
"""

__version__ = "0.1.0"
__author__ = "Teo Maggio & Antigravity"

from sgl_sim.relativity import (
    schwarzschild_radius,
    photon_sphere_radius,
    critical_impact_parameter,
    weak_deflection_angle,
    focal_distance,
    integrate_strong_geodesic,
)
from sgl_sim.optics import (
    minimum_focal_distance,
    einstein_ring_properties,
    peak_magnification,
    psf_intensity,
    generate_2d_psf,
)
from sgl_sim.caustics import (
    astroid_caustic_semi_width,
    parametric_astroid,
    check_caustic_regime,
    solve_quadrupole_images,
    generate_caustic_map_2d,
)
from sgl_sim.deconvolution import (
    baumbach_allen_coronal_brightness,
    calculate_snr,
    generate_exoplanet_map,
    compute_ssim,
    compute_rmse,
    wiener_deconvolution,
)
from sgl_sim.orbital import (
    orbital_velocity,
    orbital_period,
    isco_radius,
    check_isco,
    image_cylinder_diameter,
    station_keeping_delta_v,
)
from sgl_sim.tradespace import (
    evaluate_tradespace,
)
from sgl_sim.exporters import (
    build_simulation_fits_hdulist,
    export_fits,
    export_csv,
    export_json,
)

__all__ = [
    "__version__",
    "schwarzschild_radius",
    "photon_sphere_radius",
    "critical_impact_parameter",
    "weak_deflection_angle",
    "focal_distance",
    "integrate_strong_geodesic",
    "minimum_focal_distance",
    "einstein_ring_properties",
    "peak_magnification",
    "psf_intensity",
    "generate_2d_psf",
    "astroid_caustic_semi_width",
    "parametric_astroid",
    "check_caustic_regime",
    "solve_quadrupole_images",
    "generate_caustic_map_2d",
    "baumbach_allen_coronal_brightness",
    "calculate_snr",
    "generate_exoplanet_map",
    "compute_ssim",
    "compute_rmse",
    "wiener_deconvolution",
    "orbital_velocity",
    "orbital_period",
    "isco_radius",
    "check_isco",
    "image_cylinder_diameter",
    "station_keeping_delta_v",
    "evaluate_tradespace",
    "build_simulation_fits_hdulist",
    "export_fits",
    "export_csv",
    "export_json",
]
