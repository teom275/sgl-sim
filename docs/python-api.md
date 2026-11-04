# sgl-sim Python API

Every function accepts plain floats (SI units) or `astropy.units` quantities, and most return a dictionary of named results. Everything listed here can be imported from the top-level `sgl_sim` package.

The examples below run in order as a single script: later examples reuse variables from earlier ones, such as `u`, `psf_kernel_2d`, `snr` and `result`. The comments show the output with the default parameters.

- [Modules at a glance](#modules-at-a-glance)
- [1. Relativistic deflection & minimum focal distance](#1-relativistic-deflection--minimum-focal-distance)
- [2. Wave-optics Bessel PSF & peak magnification](#2-wave-optics-bessel-psf--peak-magnification)
- [3. Stellar oblateness (J2) astroid caustics & Einstein cross](#3-stellar-oblateness-j2-astroid-caustics--einstein-cross)
- [4. 2D Wiener deconvolution pipeline](#4-2d-wiener-deconvolution-pipeline)
- [5. NASA multi-extension FITS export](#5-nasa-multi-extension-fits-export)
- [6. Real exoplanet target resolver & 3D heliocentric telemetry](#6-real-exoplanet-target-resolver--3d-heliocentric-telemetry)
- [7. Exoplanet triage, sky efficiency & swarm motion blur](#7-exoplanet-triage-sky-efficiency--swarm-motion-blur)
- [8. What would the Earth look like? Reference bodies](#8-what-would-the-earth-look-like-reference-bodies)
- [9. How long does an image take? Photon budget](#9-how-long-does-an-image-take-photon-budget)
- [10. One telescope or a swarm? Physical image simulation](#10-one-telescope-or-a-swarm-physical-image-simulation)

## Modules at a glance

| Module | What it covers | Main functions |
|---|---|---|
| `sgl_sim.relativity` | Schwarzschild geometry, weak-field deflection, RK45 null geodesics | `schwarzschild_radius`, `photon_sphere_radius`, `critical_impact_parameter`, `weak_deflection_angle`, `focal_distance`, `integrate_strong_geodesic` |
| `sgl_sim.optics` | Focal line, Einstein ring, wave-optics PSF | `minimum_focal_distance`, `einstein_ring_properties`, `peak_magnification`, `psf_intensity`, `generate_2d_psf` |
| `sgl_sim.caustics` | J2 quadrupole astroid caustic and image solver | `astroid_caustic_semi_width`, `parametric_astroid`, `check_caustic_regime`, `solve_quadrupole_images`, `generate_caustic_map_2d` |
| `sgl_sim.deconvolution` | Coronal background, SNR budget, Wiener deconvolution | `baumbach_allen_coronal_brightness`, `calculate_snr`, `generate_exoplanet_map`, `wiener_deconvolution`, `compute_rmse`, `compute_ssim` |
| `sgl_sim.orbital` | Station keeping, image cylinder, ISCO | `orbital_velocity`, `orbital_period`, `image_cylinder_diameter`, `station_keeping_delta_v`, `isco_radius`, `check_isco` |
| `sgl_sim.tradespace` | Distance × aperture SNR trade | `evaluate_tradespace` |
| `sgl_sim.targets` | Exoplanet resolver and deployment geometry | `resolve_exoplanet`, `compute_sgl_deployment_vector`, `list_curated_targets`, `TOP_15_SGL_TARGETS` |
| `sgl_sim.triage` | Feasibility scoring, sky map, swarm motion blur | `score_exoplanet_candidate`, `get_ranked_catalog`, `generate_sky_efficiency_map`, `check_mission_coalignment`, `compute_motion_blur`, `CATALOG_12_CANDIDATES` |
| `sgl_sim.radiometry` | Photon budget of an extended source through the SGL: blur, pixel signal and solar corona; integration time for a target SNR | `sgl_photon_budget`, `integration_time_for_snr`, `solar_photon_flux` |
| `sgl_sim.imaging` | Physical image simulation: SGL blur matrix, corona noise, reconstruction, rotation during the scan, swarm sizing | `simulate_sgl_observation`, `sharp_imaging_requirements`, `required_telescopes`, `sgl_blur_matrix` |
| `sgl_sim.reference_bodies` | Earth and Moon albedo maps to compare image quality against a familiar world | `earth_albedo_map`, `moon_albedo_map`, `reference_body_map`, `REFERENCE_BODIES` |
| `sgl_sim.exporters` | FITS, CSV and JSON output | `build_simulation_fits_hdulist`, `export_fits`, `export_csv`, `export_json` |

Each function's docstring documents its parameters, units and returned keys, for example `help(sgl_sim.solve_quadrupole_images)`.

## 1. Relativistic deflection & minimum focal distance
```python
from astropy import units as u
from sgl_sim import (
    schwarzschild_radius,
    critical_impact_parameter,
    minimum_focal_distance,
    focal_distance
)

# Calculate Schwarzschild radius & photon capture threshold
rs_sun = schwarzschild_radius(1.0 * u.M_sun)
b_crit = critical_impact_parameter(1.0 * u.M_sun)
print(f"Solar R_s: {rs_sun:.2f} m | Critical b_c: {b_crit:.2f} m")
# Solar R_s: 2953.25 m | Critical b_c: 7672.77 m

# Minimum focal crossing distance for grazing solar rays
z_min_info = minimum_focal_distance(mass=1.0 * u.M_sun, radius=1.0 * u.R_sun)
print(f"Solar Gravitational Lens z_min: {z_min_info['z_min_au']:.2f} AU")
# Solar Gravitational Lens z_min: 547.76 AU
```

## 2. Wave-optics Bessel PSF & peak magnification
```python
from sgl_sim import (
    einstein_ring_properties,
    peak_magnification,
    psf_intensity,
    generate_2d_psf
)

z_rec = 650.0 * u.AU
wavelength = 1.0 * u.micron

# Einstein ring angular radius and peak wave magnification
ring = einstein_ring_properties(z_rec=z_rec)
mu_max = peak_magnification(wavelength=wavelength)
print(f"θ_E: {ring['theta_E_arcsec'] * 1000:.2f} mas | μ_max: {mu_max:.2e}")
# θ_E: 1607.57 mas | μ_max: 1.17e+11

# Generate 2D normalized Bessel J_0^2 PSF kernel
psf_kernel_2d = generate_2d_psf(grid_size=32, pixel_scale_m=1.0 * u.m, z_rec=z_rec, wavelength=wavelength)
```

## 3. Stellar oblateness (J2) astroid caustics & Einstein cross
```python
from sgl_sim import astroid_caustic_semi_width, solve_quadrupole_images

# Astroid semi-width at 650 AU
caustic = astroid_caustic_semi_width(z_rec=650.0 * u.AU, j2=2.2e-7)
print(f"Astroid Semi-Width: {caustic['a_caustic_m']:.2f} m")

# Receiver inside astroid at (x0, y0) = (0.0, 0.0) m -> 4 images (Einstein Cross)
sol_inside = solve_quadrupole_images(x0=0.0 * u.m, y0=0.0 * u.m, z_rec=650.0 * u.AU)
print(f"Regime: {sol_inside['regime']} | Resolved Images: {sol_inside['num_images']}")
print(f"Image Angles (deg): {[round(deg, 1) for deg in sol_inside['image_angles_deg']]}")
# Regime: inside | Resolved Images: 4
# Image Angles (deg): [0.0, 90.0, 180.0, 270.0]
```

## 4. 2D Wiener deconvolution pipeline
```python
from sgl_sim import generate_exoplanet_map, wiener_deconvolution, calculate_snr

# Calculate per-pixel SNR for 1m telescope, 1-day integration
snr_budget = calculate_snr(z_rec=650.0 * u.AU, aperture_m=1.0 * u.m)
snr = snr_budget["snr"]
print(f"Per-pixel SNR: {snr:.1f}")  # 32 x 32 image, 1 day, corona included

# Generate ground truth exoplanet map (continents + oceans + polar caps)
ground_truth = generate_exoplanet_map(grid_size=32, seed=42)

# Deconvolve blurred + noise-degraded image
result = wiener_deconvolution(ground_truth=ground_truth, psf_kernel=psf_kernel_2d, snr=snr)
print(f"Noisy RMSE: {result['rmse_noisy']:.4f} -> Deconvolved RMSE: {result['rmse_deconvolved']:.4f}")
print(f"Reconstructed SSIM: {result['ssim_deconvolved']:.4f}")
# Noisy RMSE: 0.2236 -> Deconvolved RMSE: 0.0305
# Reconstructed SSIM: 0.9930
```

## 5. NASA multi-extension FITS export
```python
from sgl_sim import export_fits

# Export complete simulation metadata, 2D images, and radial PSF to standard FITS
fits_path = export_fits(
    sim_data={
        "mass_solar": 1.0,
        "z_rec_au": 650.0,
        "j2": 2.2e-7,
        "wavelength_m": 1.0e-6,
        "snr": snr,
        "convolved_noisy": result["convolved_noisy"],
        "deconvolved": result["deconvolved"],
        "psf_rho_m": [0.0, 10.0, 20.0, 30.0],
        "psf_intensity": [1.0, 0.45, 0.08, 0.02],
    },
    output_path="sgl_mission_run.fits"
)
print(f"Saved NASA-standard FITS file to {fits_path}")
```

## 6. Real exoplanet target resolver & 3D heliocentric telemetry
```python
from sgl_sim import resolve_exoplanet, compute_sgl_deployment_vector

# Resolve real exoplanet from NASA Exoplanet Archive (or curated offline catalog)
target = resolve_exoplanet("Proxima Centauri b")
print(f"Target: {target['name']} | Host: {target['hostname']} ({target['distance_pc']:.2f} pc)")
# Target: Proxima Centauri b | Host: Proxima Centauri (1.30 pc)
print(f"Target Coordinates: RA {target['ra_deg']:.2f}°, Dec {target['dec_deg']:.2f}° [{target['constellation']}]")

# Compute exact antipodal placement and 3D heliocentric coordinates for arrival in 2048
ephem = compute_sgl_deployment_vector(target_data=target, z_rec_au=650.0 * u.AU, arrival_year=2048)
print(f"Required Telescope Direction (Antipode): RA {ephem['telescope_ra_deg']:.2f}°, Dec {ephem['telescope_dec_deg']:+.2f}° [{ephem['telescope_constellation']}]")
print(f"Heliocentric (X, Y, Z): ({ephem['x_au']:+.1f}, {ephem['y_au']:+.1f}, {ephem['z_au']:+.1f}) AU | Norm: {ephem['vector_norm_au']:.1f} AU")
print(f"Ecliptic Inclination: {ephem['ecliptic_inclination_deg']:.2f}° out of ecliptic plane")
print(f"Light-Travel Comms Delay: {ephem['light_delay_days']:.2f} light-days ({ephem['light_delay_hours']:.1f} hours)")
print(f"Image Cylinder Diameter: D_img ≈ {ephem['image_diameter_km']:.1f} km | Proper-Motion Drift: {ephem['proper_motion_drift_m_s']:.1f} m/s")
```

## 7. Exoplanet triage, sky efficiency & swarm motion blur
```python
from sgl_sim import (
    score_exoplanet_candidate,
    compute_motion_blur,
    get_ranked_catalog,
    check_mission_coalignment,
    generate_sky_efficiency_map,
)

# 1. Universal SGL Feasibility Scoring & Ecliptic Access
eval_res = score_exoplanet_candidate(
    name="TRAPPIST-1 e",
    ra_deg=346.62,
    dec_deg=-5.04,
    dist_pc=12.43,
    radius_earth=0.92,
    rot_period_hrs=146.4,
    tidally_locked=True,
    proper_motion_mas_yr=1005.0,
    z_rec_au=650.0,
)
print(f"Candidate: {eval_res['name']} | Score: {eval_res['sgl_score']}/100 | Tier: {eval_res['tier']}")
# Candidate: TRAPPIST-1 e | Score: 78.2/100 | Tier: Tier 1: Prime Swarm/Single Target
print(f"Ecliptic Access: {eval_res['ecliptic_access_score']:.2f} (beta = {eval_res['ecliptic_lat_deg']:.2f}°)")

# 2. Rotational Motion Blur: Single Spacecraft vs. Multi-Satellite Swarm
single = compute_motion_blur(image_diameter_km=5.0, planet_rot_period_hours=24.0, num_satellites=1)
swarm = compute_motion_blur(image_diameter_km=5.0, planet_rot_period_hours=24.0, num_satellites=8)
print(f"Single (N=1) Blur: eta = {single['eta_blur']:.1f} (RMSE: {single['rmse']:.3f})")
print(f"Swarm (N=8) Blur: eta = {swarm['eta_blur']:.2f} (RMSE: {swarm['rmse']:.3f})")

# 3. Check Multi-Planet Mission Co-Alignment (e.g. TRAPPIST-1 system)
active = [{"name": "TRAPPIST-1 e", "ra_deg": 346.62, "dec_deg": -5.04}]
coalign = check_mission_coalignment(active, new_target_ra=346.62, new_target_dec=-5.04)
print(f"Co-aligned? {coalign['is_coaligned']} -> {coalign['message']}")
```

## 8. What would the Earth look like? Reference bodies
```python
from sgl_sim import compute_motion_blur, reference_body_map

# Image a cloud-free Earth (or the Moon's near side) as if it were Tau Ceti e:
# same image size, rotation and noise, only the surface changes.
earth = reference_body_map("earth", grid_size=32)
for n in (1, 8):
    res = compute_motion_blur(
        image_diameter_km=19.8,
        planet_rot_period_hours=35.0,
        tidally_locked=False,
        num_satellites=n,
        ground_truth=earth,
    )
    print(f"N={n}: smear {res['eta_blur']:.2f}x | RMSE {res['rmse']:.3f} | SSIM {res['ssim']:.2f}")
# N=1: smear 8.17x | RMSE 0.056 | SSIM 0.83
# N=8: smear 1.02x | RMSE 0.048 | SSIM 0.88
```

## 9. How long does an image take? Photon budget
```python
from astropy import units as u
from sgl_sim import integration_time_for_snr

# Earth twin at 30 pc, 1 m telescope at 650 AU, 1000 x 1000 pixels, SNR 7
r = integration_time_for_snr(7.0, distance_source=30 * u.pc, aperture_m=1.0, n_pixels=1000)
print(f"{r['per_pixel_s']:.2e} s per pixel, corona/blur = {r['corona'] / r['blur']:.0f}")
# 1.77e+07 s per pixel, corona/blur = 18195   (Toth & Turyshev 2021: 1.33e7 s)
```

## 10. One telescope or a swarm? Physical image simulation
```python
from astropy import units as u
from sgl_sim.imaging import simulate_sgl_observation

# Proxima b as a cloud-free Earth, 32 x 32 pixels, 1 m telescopes, SNR 7.
# Tidally locked: it turns once per orbit (11.19 days) as seen from afar.
kw = dict(n_pixels=32, distance_source=1.301 * u.pc, planet_radius=1.07 * 6.371e6,
          insolation_earth=0.65, rot_period_hours=268.6, geometric_albedo=0.367)
one = simulate_sgl_observation("earth", n_telescopes=1, **kw)
print(f"{one['per_pixel_s']:.0f} s/pixel, one telescope: {one['scan_hours']:.1f} h scan, "
      f"smeared {one['smear_factor']:.1f}x, SSIM {one['ssim']:.2f}; needs {one['telescopes_needed']} telescopes")
swarm = simulate_sgl_observation("earth", n_telescopes=one["telescopes_needed"], **kw)
print(f"swarm of {swarm['n_telescopes']}: {swarm['scan_hours']:.1f} h scan, SSIM {swarm['ssim']:.2f}")
# 70 s/pixel, one telescope: 14.3 h scan, smeared 5.4x, SSIM 0.79; needs 6 telescopes
# swarm of 6: 2.4 h scan, SSIM 0.91
```
