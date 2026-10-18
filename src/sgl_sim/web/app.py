"""
Flask Web Application & API for the SGL Interactive Mission-Design Simulator.

Provides endpoints for real-time ray-tracing, wave optics PSF calculation,
quadrupole astroid caustics, exoplanet Wiener deconvolution, mission tradespace,
and NASA-standard FITS/CSV/JSON exports.
"""

from typing import Dict, Any
import io
import os
import argparse
import numpy as np
from flask import Flask, render_template, request, jsonify, send_file, Response

from sgl_sim.relativity import (
    schwarzschild_radius,
    photon_sphere_radius,
    critical_impact_parameter,
    weak_deflection_angle,
    focal_distance,
    integrate_strong_geodesic,
    M_SUN_SI,
    R_SUN_SI,
    AU_SI,
    PC_SI,
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
    J2_SUN,
)
from sgl_sim.deconvolution import (
    calculate_snr,
    generate_exoplanet_map,
    wiener_deconvolution,
    baumbach_allen_coronal_brightness,
)
from sgl_sim.orbital import (
    orbital_velocity,
    orbital_period,
    image_cylinder_diameter,
    station_keeping_delta_v,
    isco_radius,
)
from sgl_sim.tradespace import evaluate_tradespace
from sgl_sim.targets import (
    resolve_exoplanet,
    compute_sgl_deployment_vector,
    list_curated_targets,
)
from sgl_sim.triage import (
    compute_motion_blur,
    score_exoplanet_candidate,
    get_ranked_catalog,
    generate_sky_efficiency_map,
    check_mission_coalignment,
    CATALOG_12_CANDIDATES,
)
from sgl_sim.exporters import (
    build_simulation_fits_hdulist,
    export_fits,
    export_csv,
    export_json,
)

# Initialize Flask app
current_dir = os.path.dirname(os.path.abspath(__file__))
app = Flask(
    __name__,
    template_folder=os.path.join(current_dir, "templates"),
    static_folder=os.path.join(current_dir, "static"),
)


def run_full_simulation(params: Dict[str, Any]) -> Dict[str, Any]:
    """Execute complete physics and optics simulation given input parameters."""
    lens_type = params.get("lens_type", "star")
    is_bh = lens_type == "black_hole"
    mass_sol = float(params.get("mass_solar", 1.0))
    mass_kg = mass_sol * M_SUN_SI
    z_rec_au = float(params.get("z_rec_au", 650.0))
    z_rec_m = z_rec_au * AU_SI
    j2 = float(params.get("j2", J2_SUN))
    wavelength_um = float(params.get("wavelength_um", 1.0))
    wavelength_m = wavelength_um * 1e-6
    aperture_m = float(params.get("aperture_m", 1.0))
    t_int_days = float(params.get("t_int_days", 1.0))
    t_int_s = t_int_days * 86400.0
    dist_pc = float(params.get("distance_source_pc", 1.3))
    dist_m = dist_pc * PC_SI
    x0_m = float(params.get("x0_m", 0.0))
    y0_m = float(params.get("y0_m", 0.0))

    # 1. Relativity
    rs = schwarzschild_radius(mass_kg)
    r_ph = photon_sphere_radius(mass_kg)
    bc = critical_impact_parameter(mass_kg)
    r_star = None if is_bh else R_SUN_SI
    z_min_dict = minimum_focal_distance(mass=mass_kg, radius=r_star, is_black_hole=is_bh)

    # Compute a ray bundle for 2D visualization
    ray_bundle = []
    if is_bh:
        # Strong-field rays around black hole
        b_factors = np.linspace(1.2, 5.0, 16)
        for bf in b_factors:
            b_val = bf * bc
            res = integrate_strong_geodesic(
                impact_param=b_val, mass=mass_kg, x_start=-15.0, num_points=100
            )
            # Sample trajectory to 30 points
            stride = max(1, len(res["x_rs"]) // 30)
            ray_bundle.append({
                "status": res["status"],
                "b_rs": float(b_val / rs),
                "x_rs": res["x_rs"][::stride].tolist(),
                "y_rs": res["y_rs"][::stride].tolist(),
            })
    else:
        # Weak-field stellar grazing rays
        b_factors = np.linspace(0.8, 1.8, 12)
        for bf in b_factors:
            b_val = bf * R_SUN_SI
            blocked = b_val < R_SUN_SI
            z_focus_au = (b_val**2) / (2.0 * rs * AU_SI)
            ray_bundle.append({
                "status": "blocked_by_star" if blocked else "focused",
                "b_r_sun": float(bf),
                "z_focus_au": float(z_focus_au),
            })

    # 2. Optics
    ring_props = einstein_ring_properties(z_rec=z_rec_m, mass=mass_kg)
    mu_max = peak_magnification(wavelength=wavelength_m, mass=mass_kg)

    # Radial PSF profile (0 to 60 meters transverse)
    rho_arr = np.linspace(0.0, 40.0, 120)
    psf_vals = psf_intensity(rho=rho_arr, z_rec=z_rec_m, wavelength=wavelength_m, mass=mass_kg, normalize=True)
    psf_actual = psf_intensity(rho=rho_arr, z_rec=z_rec_m, wavelength=wavelength_m, mass=mass_kg, normalize=False)

    # 3. Caustics & Astroid
    caustic_info = astroid_caustic_semi_width(z_rec=z_rec_m, mass=mass_kg, star_radius=R_SUN_SI, j2=j2)
    a_caustic = caustic_info["a_caustic_m"]
    astroid_geom = parametric_astroid(a_caustic, num_points=120)

    # Solve image configuration at current receiver position (x0, y0)
    quad_sol = solve_quadrupole_images(
        x0=x0_m, y0=y0_m, z_rec=z_rec_m, mass=mass_kg, star_radius=R_SUN_SI, j2=j2, wavelength=wavelength_m
    )

    # 2D Caustic map (32x32)
    caustic_map_res = generate_caustic_map_2d(z_rec=z_rec_m, grid_size=32, mass=mass_kg, star_radius=R_SUN_SI, j2=j2)
    caustic_2d = caustic_map_res["caustic_intensity_2d"]

    # 4. Deconvolution
    snr_dict = calculate_snr(
        z_rec=z_rec_m,
        aperture_m=aperture_m,
        integration_time_s=t_int_s,
        distance_source=dist_m,
        wavelength=wavelength_m,
        mass=mass_kg,
    )
    snr_val = snr_dict["snr"]

    # Generate synthetic exoplanet map and Bessel PSF kernel
    gt_map = generate_exoplanet_map(grid_size=32, seed=42)
    psf_2d = generate_2d_psf(grid_size=32, pixel_scale_m=1.0, z_rec=z_rec_m, wavelength=wavelength_m, mass=mass_kg)

    deconv_res = wiener_deconvolution(
        ground_truth=gt_map,
        psf_kernel=psf_2d,
        snr=snr_val,
        seed=101,
    )

    # 5. Orbital Mechanics
    v_orb = orbital_velocity(z_rec=z_rec_m, mass=mass_kg)
    t_orb = orbital_period(z_rec=z_rec_m, mass=mass_kg)
    img_cyl = image_cylinder_diameter(z_rec=z_rec_m, distance_source=dist_m)
    st_keep = station_keeping_delta_v(z_rec=z_rec_m, mass=mass_kg, distance_source=dist_m)

    return {
        "lens_type": lens_type,
        "mass_solar": mass_sol,
        "z_rec_au": z_rec_au,
        "j2": j2,
        "wavelength_um": wavelength_um,
        "wavelength_m": wavelength_m,
        "aperture_m": aperture_m,
        "t_int_days": t_int_days,
        "t_int_s": t_int_s,
        "distance_source_pc": dist_pc,
        "x0_m": x0_m,
        "y0_m": y0_m,
        "schwarzschild_radius_m": rs,
        "photon_sphere_radius_m": r_ph,
        "critical_impact_param_m": bc,
        "z_min_au": z_min_dict["z_min_au"],
        "ray_bundle": ray_bundle,
        "b_ring_m": ring_props["b_ring_m"],
        "b_ring_r_sun": ring_props["b_ring_r_sun"],
        "theta_E_arcsec": ring_props["theta_E_arcsec"],
        "mu_max": mu_max,
        "psf_rho_m": rho_arr.tolist(),
        "psf_intensity": psf_actual.tolist(),
        "psf_j0_sq": psf_vals.tolist(),
        "a_caustic_m": a_caustic,
        "astroid_boundary": {
            "x": astroid_geom["x"].tolist(),
            "y": astroid_geom["y"].tolist(),
        },
        "regime": quad_sol["regime"],
        "num_images": quad_sol["num_images"],
        "image_angles_deg": quad_sol["image_angles_deg"],
        "image_intensities": quad_sol["image_intensities"],
        "ring_profile": quad_sol["ring_profile"].tolist(),
        "caustic_map": caustic_2d.tolist(),
        "snr": snr_val,
        "r_sun_impact": snr_dict["r_sun_impact"],
        "ground_truth": gt_map.tolist(),
        "convolved_noisy": deconv_res["convolved_noisy"].tolist(),
        "deconvolved": deconv_res["deconvolved"].tolist(),
        "rmse_noisy": deconv_res["rmse_noisy"],
        "rmse_deconvolved": deconv_res["rmse_deconvolved"],
        "ssim_noisy": deconv_res["ssim_noisy"],
        "ssim_deconvolved": deconv_res["ssim_deconvolved"],
        "orbital_velocity_m_s": v_orb,
        "orbital_period_years": t_orb["period_years"],
        "image_cylinder_km": img_cyl["d_img_km"],
        "delta_v_hover_m_s": st_keep["delta_v_hover_annual_m_s"],
        "delta_v_scan_m_s": st_keep["delta_v_scan_m_s"],
        "delta_v_total_m_s": st_keep["total_annual_budget_m_s"],
    }


@app.route("/")
def index():
    """Render main interactive dark-mode dashboard."""
    return render_template("index.html")


@app.route("/api/simulate", methods=["GET", "POST"])
def api_simulate():
    """Simulate optical, relativistic, and deconvolution pipeline."""
    if request.method == "POST":
        params = request.get_json(force=True, silent=True) or {}
    else:
        params = request.args.to_dict()

    results = run_full_simulation(params)
    return jsonify(results)


@app.route("/api/research_analysis", methods=["GET", "POST"])
def api_research_analysis():
    """Compute tradespace matrix across (z_rec, aperture_m)."""
    if request.method == "POST":
        params = request.get_json(force=True, silent=True) or {}
    else:
        params = request.args.to_dict()

    target_snr = float(params.get("target_snr", 10.0))
    dist_pc = float(params.get("distance_source_pc", 1.3))

    ts_data = evaluate_tradespace(
        z_min_au=550.0,
        z_max_au=950.0,
        n_z=12,
        aperture_min_m=0.5,
        aperture_max_m=5.0,
        n_aperture=12,
        target_snr=target_snr,
        distance_source=dist_pc * PC_SI,
    )

    return jsonify({
        "z_au_grid": ts_data["z_au_grid"].tolist(),
        "aperture_m_grid": ts_data["aperture_m_grid"].tolist(),
        "snr_matrix": ts_data["snr_matrix"].tolist(),
        "t_req_hours_matrix": ts_data["t_req_hours_matrix"].tolist(),
        "target_snr": ts_data["target_snr"],
    })


@app.route("/api/targets", methods=["GET"])
def api_targets():
    """Return the curated list of top 15 prime SGL exoplanet targets."""
    return jsonify(list_curated_targets())


@app.route("/api/target_ephemeris", methods=["GET", "POST"])
def api_target_ephemeris():
    """
    Compute 3D heliocentric positioning, celestial antipode, and drift kinematics
    for a chosen exoplanet target.
    """
    if request.method == "POST":
        params = request.get_json(force=True, silent=True) or {}
    else:
        params = request.args.to_dict()

    target_query = params.get("target", "Proxima Centauri b")
    z_rec_au = float(params.get("z_rec_au", 650.0))
    arrival_year_raw = params.get("arrival_year", 2048.0)
    arrival_year = float(arrival_year_raw) if arrival_year_raw not in (None, "", "null") else None
    cruise_vel_au_yr = float(params.get("cruise_velocity_au_yr", 20.0))

    try:
        resolved = resolve_exoplanet(target_query)
        ephem = compute_sgl_deployment_vector(
            target_data=resolved,
            z_rec_au=z_rec_au,
            arrival_year=arrival_year,
            cruise_vel_au_yr=cruise_vel_au_yr,
        )
        return jsonify({"status": "success", "data": ephem})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400


@app.route("/api/ranking", methods=["GET"])
def api_ranking():
    """Return ranked exoplanet catalog evaluated for SGL mission feasibility."""
    try:
        z_rec_au = float(request.args.get("z_rec_au", 650.0))
        ranked = get_ranked_catalog(z_rec_au=z_rec_au)
        return jsonify({"status": "success", "data": ranked})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400


@app.route("/api/evaluate_candidate", methods=["POST"])
def api_evaluate_candidate():
    """Score a newly discovered or custom exoplanet candidate and check mission co-alignment."""
    try:
        data = request.get_json(force=True, silent=True) or {}
        name = data.get("name", "Custom Discovery")
        ra_deg = float(data.get("ra_deg", 0.0))
        dec_deg = float(data.get("dec_deg", 0.0))
        dist_pc = float(data.get("dist_pc", 10.0))
        radius_earth = float(data.get("radius_earth", 1.0))
        rot_period_hrs = float(data.get("rot_period_hrs", 24.0))
        tidally_locked = bool(data.get("tidally_locked", False))
        host_star_mag = float(data.get("host_star_mag", 11.0))
        proper_motion_mas_yr = float(data.get("proper_motion_mas_yr", 100.0))
        z_rec_au = float(data.get("z_rec_au", 650.0))

        score_res = score_exoplanet_candidate(
            name=name,
            ra_deg=ra_deg,
            dec_deg=dec_deg,
            dist_pc=dist_pc,
            radius_earth=radius_earth,
            rot_period_hrs=rot_period_hrs,
            tidally_locked=tidally_locked,
            host_star_mag=host_star_mag,
            proper_motion_mas_yr=proper_motion_mas_yr,
            z_rec_au=z_rec_au,
        )

        coalignment_res = check_mission_coalignment(
            active_missions=CATALOG_12_CANDIDATES,
            new_target_ra=ra_deg,
            new_target_dec=dec_deg,
            max_deflection_deg=3.0,
        )

        return jsonify({
            "status": "success",
            "candidate": score_res,
            "coalignment": coalignment_res,
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400


@app.route("/api/swarm_blur_sim", methods=["POST"])
def api_swarm_blur_sim():
    """Simulate rotational motion blur comparing single-spacecraft vs swarm."""
    try:
        data = request.get_json(force=True, silent=True) or {}
        image_diameter_km = float(data.get("image_diameter_km", 4.2))
        grid_pixels = int(data.get("grid_pixels", 32))
        planet_rot_period_hours = float(data.get("planet_rot_period_hours", 24.0))
        tidally_locked = bool(data.get("tidally_locked", False))
        num_satellites = int(data.get("num_satellites", 8))
        integration_time_per_pixel_s = float(data.get("integration_time_per_pixel_s", 10.0))
        max_lateral_accel_m_s2 = float(data.get("max_lateral_accel_m_s2", 1e-4))
        v_drift_m_s = float(data.get("v_drift_m_s", 15.0))
        snr = float(data.get("snr", 25.0))

        # Single craft simulation (N=1)
        single_res = compute_motion_blur(
            image_diameter_km=image_diameter_km,
            grid_pixels=grid_pixels,
            planet_rot_period_hours=planet_rot_period_hours,
            tidally_locked=tidally_locked,
            num_satellites=1,
            integration_time_per_pixel_s=integration_time_per_pixel_s,
            max_lateral_accel_m_s2=max_lateral_accel_m_s2,
            v_drift_m_s=v_drift_m_s,
            snr=snr,
        )

        # Swarm simulation (N=num_satellites)
        swarm_res = compute_motion_blur(
            image_diameter_km=image_diameter_km,
            grid_pixels=grid_pixels,
            planet_rot_period_hours=planet_rot_period_hours,
            tidally_locked=tidally_locked,
            num_satellites=num_satellites,
            integration_time_per_pixel_s=integration_time_per_pixel_s,
            max_lateral_accel_m_s2=max_lateral_accel_m_s2,
            v_drift_m_s=v_drift_m_s,
            snr=snr,
        )

        return jsonify({
            "status": "success",
            "single": single_res,
            "swarm": swarm_res,
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400


@app.route("/api/sky_efficiency", methods=["GET"])
def api_sky_efficiency():
    """Return all-sky solar lens efficiency map grid and candidate markers."""
    try:
        n_ra = int(request.args.get("n_ra", 72))
        n_dec = int(request.args.get("n_dec", 36))
        data = generate_sky_efficiency_map(n_ra=n_ra, n_dec=n_dec)
        return jsonify({"status": "success", "data": data})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400


@app.route("/api/export_fits", methods=["GET", "POST"])
def api_export_fits():
    """Export current simulation data to a NASA-standard multi-extension FITS file."""
    if request.method == "POST":
        params = request.get_json(force=True, silent=True) or {}
    else:
        params = request.args.to_dict()

    sim_res = run_full_simulation(params)

    # Convert lists back to numpy arrays for build_simulation_fits_hdulist
    sim_data_for_fits = dict(sim_res)
    sim_data_for_fits["caustic_map"] = np.asarray(sim_res["caustic_map"])
    sim_data_for_fits["convolved_noisy"] = np.asarray(sim_res["convolved_noisy"])
    sim_data_for_fits["deconvolved"] = np.asarray(sim_res["deconvolved"])
    sim_data_for_fits["psf_rho_m"] = np.asarray(sim_res["psf_rho_m"])
    sim_data_for_fits["psf_intensity"] = np.asarray(sim_res["psf_intensity"])
    sim_data_for_fits["psf_j0_sq"] = np.asarray(sim_res["psf_j0_sq"])

    fits_bytes = export_fits(sim_data_for_fits)

    return send_file(
        io.BytesIO(fits_bytes),
        mimetype="image/fits",
        as_attachment=True,
        download_name="sgl_simulation.fits",
    )


@app.route("/api/export_csv", methods=["GET", "POST"])
def api_export_csv():
    """Export radial PSF profile to CSV."""
    if request.method == "POST":
        params = request.get_json(force=True, silent=True) or {}
    else:
        params = request.args.to_dict()

    sim_res = run_full_simulation(params)
    csv_data = {
        "rho_m": sim_res["psf_rho_m"],
        "intensity": sim_res["psf_intensity"],
        "j0_squared": sim_res["psf_j0_sq"],
    }
    csv_content = export_csv(csv_data)

    return Response(
        csv_content,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=sgl_psf_profile.csv"},
    )


@app.route("/api/export_json", methods=["GET", "POST"])
def api_export_json():
    """Export simulation metadata and outputs to JSON."""
    if request.method == "POST":
        params = request.get_json(force=True, silent=True) or {}
    else:
        params = request.args.to_dict()

    sim_res = run_full_simulation(params)
    json_str = export_json(sim_res, indent=2)

    return Response(
        json_str,
        mimetype="application/json",
        headers={"Content-Disposition": "attachment; filename=sgl_simulation.json"},
    )


def run_server():
    """CLI Entry point for `sgl-sim-server`."""
    parser = argparse.ArgumentParser(description="Run SGL Simulation Web Server")
    parser.add_argument("--host", default="127.0.0.1", help="Host address (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=5000, help="Port (default: 5000)")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    args = parser.parse_args()

    print(f"Starting sgl-sim-server on http://{args.host}:{args.port}")
    app.run(host=args.host, port=args.port, debug=args.debug)


if __name__ == "__main__":
    run_server()
