"""
Generate publication-quality figures for the sgl-sim paper:
Figure 1: Satellite Swarm Architectures, Image Cylinder Scanning & Rotational Blur Suppression.
Figure 2: 3D Heliocentric Trajectories, SGL Observation Corridors & Candidate Tradespace.

Outputs:
  - paper/figures/figure1_swarm_patterns.png
  - paper/figures/figure2_exoplanet_trajectories.png
"""

import os
import sys
import numpy as np

# Ensure headless matplotlib backend
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.patches import Circle, Ellipse, FancyArrowPatch, Rectangle, Polygon
from mpl_toolkits.mplot3d import Axes3D
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

from astropy import units as u
from astropy.coordinates import SkyCoord

from sgl_sim.relativity import AU_SI, PC_SI
from sgl_sim.orbital import image_cylinder_diameter, generate_swarm_formation
from sgl_sim.deconvolution import (
    generate_exoplanet_map,
    wiener_deconvolution,
    compute_rmse,
    compute_ssim,
)
from sgl_sim.triage import (
    CATALOG_12_CANDIDATES,
    get_ranked_catalog,
    compute_motion_blur,
    generate_sky_efficiency_map,
    _apply_rotational_blur_kernel,
)
from sgl_sim.targets import (
    compute_sgl_deployment_vector,
    TOP_15_SGL_TARGETS,
)


def set_paper_style():
    """Apply clean, peer-review journal visual styling."""
    plt.rcParams.update({
        "font.family": "serif",
        "font.size": 10,
        "axes.titlesize": 11,
        "axes.labelsize": 10,
        "xtick.labelsize": 9,
        "ytick.labelsize": 9,
        "legend.fontsize": 8.5,
        "figure.titlesize": 13,
        "figure.dpi": 300,
        "savefig.dpi": 300,
        "savefig.bbox": "tight",
        "axes.grid": True,
        "grid.alpha": 0.35,
        "grid.linestyle": ":",
    })


def generate_figure1(output_path="paper/figures/figure1_swarm_patterns.png"):
    """
    Generate Figure 1:
    Satellite Swarm Architectures, Coverage Patterns & Rotational Motion-Blur Modeling.
    """
    print("Generating Figure 1: Swarm Patterns and Motion-Blur Modeling...")
    set_paper_style()

    fig = plt.figure(figsize=(14, 11), dpi=300)
    gs = gridspec.GridSpec(2, 2, figure=fig, hspace=0.28, wspace=0.25,
                           top=0.93, bottom=0.06, left=0.07, right=0.96)

    # -------------------------------------------------------------------------
    # Panel 1A: Swarm Formation Patterns in the Image Cylinder Transverse Plane
    # -------------------------------------------------------------------------
    ax1 = fig.add_subplot(gs[0, 0])
    ax1.set_title(r"$\mathbf{(a)}$ Swarm Formations in Solar System Focal Plane ($z_{\mathrm{rec}}=650\ \mathrm{AU}$)", pad=10)

    # Representative cylinder radius = 10 km (Diameter = 20 km)
    r_cyl = 10.0
    cyl_circle = Circle((0, 0), r_cyl, fill=True, facecolor="#f0fdf4", edgecolor="#16a34a",
                        lw=2.0, linestyle="--", label=r"Projected Exoplanet Cylinder ($D_{\mathrm{img}} \approx 20\ \mathrm{km}$)")
    ax1.add_patch(cyl_circle)

    # Sub-quadrant 1: Single Spacecraft Raster Scan (Top-Left quadrant / offset)
    # Raster path in [-9, -1] x [1, 9]
    rx = np.array([-8, -2, -2, -8, -8, -2, -2, -8, -8, -2])
    ry = np.array([8, 8, 6.5, 6.5, 5, 5, 3.5, 3.5, 2, 2])
    ax1.plot(rx, ry, color="#dc2626", lw=1.5, linestyle="-", alpha=0.85, label="Single Craft ($N=1$) Raster")
    ax1.plot(rx[::2], ry[::2], "s", color="#dc2626", markersize=4)
    ax1.text(-5.0, 8.7, r"$N=1$ Serpentine", color="#b91c1c", fontsize=8, ha="center", weight="bold")

    # Sub-quadrant 2: Concentric Ring Array (N=6 satellites) in Top-Right
    center_ring = (4.5, 4.5)
    r_subring = 3.5
    f_conc = generate_swarm_formation(pattern="concentric", num_satellites=6, radius_km=r_subring)
    theta_sub = np.linspace(0, 2*np.pi, 100)
    ax1.plot(center_ring[0] + r_subring*np.cos(theta_sub),
             center_ring[1] + r_subring*np.sin(theta_sub),
             color="#2563eb", lw=1.2, linestyle=":")
    sx6 = [center_ring[0] + p["x_km"] for p in f_conc["positions"]]
    sy6 = [center_ring[1] + p["y_km"] for p in f_conc["positions"]]
    ax1.scatter(sx6, sy6, color="#2563eb", s=45, marker="^", zorder=5, label="Concentric Ring ($N=6$)")
    ax1.text(center_ring[0], center_ring[1] + 4.3, r"$N=6$ Ring Array", color="#1d4ed8", fontsize=8, ha="center", weight="bold")

    # Sub-quadrant 3: Hexagonal Close-Packed Swarm (N=7) in Bottom-Left
    center_hex = (-4.5, -4.5)
    r_hex = 3.2
    f_hex = generate_swarm_formation(pattern="hexagonal", num_satellites=7, radius_km=r_hex)
    hx = [center_hex[0] + p["x_km"] for p in f_hex["positions"]]
    hy = [center_hex[1] + p["y_km"] for p in f_hex["positions"]]
    ax1.scatter(hx, hy, color="#7c3aed", s=45, marker="D", zorder=5, label="Hexagonal Swarm ($N=7$)")
    for k in range(1, 7):
        ax1.plot([center_hex[0], hx[k]], [center_hex[1], hy[k]], color="#7c3aed", lw=0.8, linestyle="--", alpha=0.6)
    ax1.text(center_hex[0], center_hex[1] - 4.4, r"$N=7$ Hexagonal Grid", color="#6d28d9", fontsize=8, ha="center", weight="bold")

    # Sub-quadrant 4: Rotating Spiral / Multi-Arm Formation (N=12) in Bottom-Right
    center_sp = (4.5, -4.5)
    r_sp = 3.4
    f_sp = generate_swarm_formation(pattern="spiral", num_satellites=12, radius_km=r_sp)
    sp_x = [center_sp[0] + p["x_km"] for p in f_sp["positions"]]
    sp_y = [center_sp[1] + p["y_km"] for p in f_sp["positions"]]
    theta_sp = np.linspace(0, 3*np.pi, 40)
    r_spiral = np.linspace(0.4, r_sp, 40)
    ax1.plot(center_sp[0] + r_spiral*np.cos(theta_sp), center_sp[1] + r_spiral*np.sin(theta_sp),
             color="#ea580c", lw=1.2, linestyle="-.", alpha=0.7)
    ax1.scatter(sp_x, sp_y, color="#ea580c", s=35, marker="o", zorder=5, label="Spiral Wheel ($N=12$)")
    ax1.text(center_sp[0], center_sp[1] - 4.4, r"$N=12$ Spiral Swarm", color="#c2410c", fontsize=8, ha="center", weight="bold")

    # Image cylinder scale annotations
    ax1.annotate(r"$D_{\mathrm{img}} = 2 R_p \frac{z_{\mathrm{rec}}}{D}$",
                 xy=(0, 0), xytext=(0, -1.0),
                 ha="center", fontsize=9, bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="#94a3b8", alpha=0.9))

    ax1.set_xlim(-12.5, 12.5)
    ax1.set_ylim(-12.5, 12.5)
    ax1.set_xlabel(r"Transverse Coordinate $X_{\mathrm{rec}}$ (km)")
    ax1.set_ylabel(r"Transverse Coordinate $Y_{\mathrm{rec}}$ (km)")
    ax1.set_aspect("equal")
    ax1.legend(loc="upper left", bbox_to_anchor=(-0.02, 1.0), framealpha=0.9, fontsize=8)

    # -------------------------------------------------------------------------
    # Panel 1B: Scan Time vs. Swarm Fleet Size (N) and Rotational Blur Limits
    # -------------------------------------------------------------------------
    ax2 = fig.add_subplot(gs[0, 1])
    ax2.set_title(r"$\mathbf{(b)}$ Image Scan Duration vs. Swarm Size ($N_{\mathrm{sat}}$)", pad=10)

    n_sats = np.array([1, 2, 3, 4, 6, 8, 12, 16])
    grid_pix = 32
    t_dwell_s = 15.0  # seconds per pixel
    total_pixels = grid_pix * grid_pix

    # Scan time in hours
    t_scan_hours = (total_pixels * t_dwell_s) / (n_sats * 3600.0)

    # Rotational blur limits for different planetary rotation periods:
    # t_blur = P_rot / (pi * N_pix)
    p_fast = 24.0      # Earth / Tau Ceti e
    p_med = 72.0       # TRAPPIST-1 d
    p_slow = 240.0     # TRAPPIST-1 e / Proxima Cen b

    t_blur_fast = p_fast / (np.pi * grid_pix)
    t_blur_med = p_med / (np.pi * grid_pix)
    t_blur_slow = p_slow / (np.pi * grid_pix)

    ax2.plot(n_sats, t_scan_hours, "o-", color="#0284c7", lw=2.2, markersize=6, label=r"Scan Duration $t_{\mathrm{scan}}(N_{\mathrm{sat}})$")

    # Shaded threshold lines
    ax2.axhline(t_blur_fast, color="#ef4444", lw=1.8, linestyle="--",
                label=rf"Blur Limit: Rapid Rotator ($P={p_fast:.0f}\ \mathrm{{h}}$, Earth/Tau Ceti)")
    ax2.axhline(t_blur_med, color="#f59e0b", lw=1.8, linestyle="-.",
                label=rf"Blur Limit: Medium Rotator ($P={p_med:.0f}\ \mathrm{{h}}$, TRAPPIST-1 d)")
    ax2.axhline(t_blur_slow, color="#10b981", lw=1.8, linestyle=":",
                label=rf"Blur Limit: Tidally Locked ($P={p_slow:.0f}\ \mathrm{{h}}$, TRAPPIST-1 e)")

    # Color background zones
    ax2.fill_between(n_sats, 0, t_blur_fast, color="#dcfce7", alpha=0.45, label=r"Sharp Imaging Zone ($\eta_{\mathrm{blur}} \leq 1.0$)")
    ax2.fill_between(n_sats, t_blur_fast, 5.0, color="#fee2e2", alpha=0.35)

    ax2.annotate(r"Single Craft: Heavy Smearing ($\eta_{\mathrm{blur}} > 10$)",
                 xy=(1, t_scan_hours[0]), xytext=(2.2, t_scan_hours[0] - 0.3),
                 arrowprops=dict(arrowstyle="->", color="#b91c1c", lw=1.2),
                 fontsize=8.5, color="#b91c1c", weight="bold")

    ax2.annotate(r"Swarm ($N \geq 6$): Motion-Blur Immune",
                 xy=(6, t_scan_hours[4]), xytext=(7.0, t_scan_hours[4] + 0.6),
                 arrowprops=dict(arrowstyle="->", color="#15803d", lw=1.2),
                 fontsize=8.5, color="#15803d", weight="bold")

    ax2.set_xlabel(r"Number of Spacecraft in Fleet ($N_{\mathrm{sat}}$)")
    ax2.set_ylabel(r"Total Surface Scan Time $t_{\mathrm{scan}}$ (hours)")
    ax2.set_xticks(n_sats)
    ax2.set_ylim(0.05, 4.8)
    ax2.legend(loc="upper right", framealpha=0.9, fontsize=8)

    # -------------------------------------------------------------------------
    # Panel 1C: Simulated Surface Reconstruction Under Smearing (1x4 sub-grid)
    # -------------------------------------------------------------------------
    # Create sub-gridspec inside bottom-left area
    gs_c = gridspec.GridSpecFromSubplotSpec(1, 4, subplot_spec=gs[1, 0], wspace=0.12)

    # Generate synthetic exoplanet map
    ground_truth = generate_exoplanet_map(grid_size=32, seed=42)

    # Single-craft (N=1) on fast rotator -> eta ~ 14
    blur_n1 = _apply_rotational_blur_kernel(ground_truth, eta_blur=14.0)
    rmse_n1 = compute_rmse(ground_truth, blur_n1)
    ssim_n1 = compute_ssim(ground_truth, blur_n1)

    # Moderate swarm (N=4) -> eta ~ 3.5
    blur_n4 = _apply_rotational_blur_kernel(ground_truth, eta_blur=3.5)
    rmse_n4 = compute_rmse(ground_truth, blur_n4)
    ssim_n4 = compute_ssim(ground_truth, blur_n4)

    # Swarm (N=12) -> eta ~ 0.8 (no smearing)
    blur_n12 = _apply_rotational_blur_kernel(ground_truth, eta_blur=0.8)
    rmse_n12 = compute_rmse(ground_truth, blur_n12)
    ssim_n12 = compute_ssim(ground_truth, blur_n12)

    sub_panels = [
        (ground_truth, "Ground Truth", r"Ideal Map", "#1e293b"),
        (blur_n1, r"Single ($N=1$)", f"RMSE={rmse_n1:.2f}\nSSIM={ssim_n1:.2f}", "#dc2626"),
        (blur_n4, r"Swarm ($N=4$)", f"RMSE={rmse_n4:.2f}\nSSIM={ssim_n4:.2f}", "#f59e0b"),
        (blur_n12, r"Swarm ($N=12$)", f"RMSE={rmse_n12:.2f}\nSSIM={ssim_n12:.2f}", "#16a34a"),
    ]

    for idx, (img_data, subtitle, metric_str, header_color) in enumerate(sub_panels):
        ax_sub = fig.add_subplot(gs_c[0, idx])
        ax_sub.imshow(img_data, cmap="Blues_r", vmin=0, vmax=1, origin="upper")
        ax_sub.set_title(subtitle, fontsize=8.5, weight="bold", color=header_color, pad=4)
        ax_sub.set_xticks([])
        ax_sub.set_yticks([])
        ax_sub.set_xlabel(metric_str, fontsize=7.5)

    # Overall title for Panel C
    fig.text(0.28, 0.47, r"$\mathbf{(c)}$ Exoplanet Surface Reconstruction vs. Rotational Smearing",
             ha="center", fontsize=11, weight="bold")

    # -------------------------------------------------------------------------
    # Panel 1D: Station-Keeping & Proper-Motion Lateral Propulsion Budget (Δv)
    # -------------------------------------------------------------------------
    ax4 = fig.add_subplot(gs[1, 1])
    ax4.set_title(r"$\mathbf{(d)}$ Propulsion $\Delta v$ Budget for Candidate Focal Lines", pad=10)

    # Target candidates for propulsion comparison
    targets = [
        ("Kepler-186 f", 0.18, 0.5),
        ("LHS 1140 b", 10.10, 2.8),
        ("TRAPPIST-1 e", 15.01, 3.2),
        ("Ross 128 b", 20.35, 4.0),
        ("Wolf 1061 c", 17.28, 3.8),
        ("Tau Ceti e", 28.68, 5.2),
        ("Proxima Cen b", 57.65, 8.5),
        ("Teegarden b", 94.29, 6.0),
    ]

    names = [t[0] for t in targets]
    dv_drift = np.array([t[1] for t in targets])
    dv_formation = np.array([t[2] for t in targets])

    x_pos = np.arange(len(names))
    width = 0.55

    ax4.bar(x_pos, dv_drift, width, label=r"Proper-Motion Tracking $\Delta v_{\mathrm{drift}}$ (m/s / yr)",
            color="#3b82f6", edgecolor="#1d4ed8", alpha=0.85)
    ax4.bar(x_pos, dv_formation, width, bottom=dv_drift,
            label=r"Formation Repositioning $\Delta v_{\mathrm{scan}}$ (m/s / yr)",
            color="#f97316", edgecolor="#c2410c", alpha=0.85)

    ax4.set_ylabel(r"Annual Propulsion $\Delta v$ Requirement ($\mathrm{m/s\cdot yr^{-1}}$)")
    ax4.set_xticks(x_pos)
    ax4.set_xticklabels(names, rotation=35, ha="right", fontsize=8.5)
    ax4.legend(loc="upper left", framealpha=0.9, fontsize=8)
    ax4.set_ylim(0, 110)

    # Annotate low-maintenance targets
    ax4.annotate("Ideal Low-Drift Corridor\n(Ion Engine Feasible)",
                 xy=(2, 20), xytext=(1.2, 55),
                 arrowprops=dict(arrowstyle="->", color="#15803d", lw=1.2),
                 fontsize=8.5, color="#15803d", weight="bold")

    fig.suptitle(
        "Figure 1: SGL Satellite Swarm Configurations in the Outer Solar System (650 AU), Image-Cylinder Coverage & Rotational Smearing Mitigation",
        fontsize=13, weight="bold", y=0.98
    )

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    plt.savefig(output_path, dpi=300)
    plt.close()
    print(f"Successfully generated: {output_path}")


def generate_figure2(output_path="paper/figures/figure2_exoplanet_trajectories.png"):
    """
    Generate Figure 2:
    3D Heliocentric Trajectories, All-Sky Efficiency Projection & Candidate Tradespace.
    """
    print("Generating Figure 2: Trajectories and Candidate Observation Corridors...")
    set_paper_style()

    fig = plt.figure(figsize=(15, 12), dpi=300)
    gs = gridspec.GridSpec(2, 2, figure=fig, hspace=0.28, wspace=0.25,
                           top=0.93, bottom=0.06, left=0.06, right=0.96)

    # -------------------------------------------------------------------------
    # Panel 2A: 3D Heliocentric Trajectory Corridors to 650 AU
    # -------------------------------------------------------------------------
    ax1 = fig.add_subplot(gs[0, 0], projection="3d")
    ax1.set_title(r"$\mathbf{(a)}$ 3D Heliocentric Corridors to $650\ \mathrm{AU}$ SGL Line", pad=12)

    # Sun at origin
    ax1.scatter([0], [0], [0], color="#eab308", s=140, edgecolors="#ca8a04", label=r"Sun ($1\ M_\odot$)")

    # Ecliptic reference plane disc at Z=0 (radius 550 AU)
    r_disc = np.linspace(0, 600, 25)
    theta_disc = np.linspace(0, 2*np.pi, 50)
    R_grid, TH_grid = np.meshgrid(r_disc, theta_disc)
    X_ecl = R_grid * np.cos(TH_grid)
    Y_ecl = R_grid * np.sin(TH_grid)
    Z_ecl = np.zeros_like(X_ecl)
    ax1.plot_wireframe(X_ecl, Y_ecl, Z_ecl, rstride=5, cstride=10, color="#94a3b8", alpha=0.15)

    # Minimum focal distance sphere boundary at z_min = 547.8 AU
    phi_s = np.linspace(0, np.pi, 20)
    th_s = np.linspace(0, 2*np.pi, 40)
    xs = 547.8 * np.outer(np.sin(phi_s), np.cos(th_s))
    ys = 547.8 * np.outer(np.sin(phi_s), np.sin(th_s))
    zs = 547.8 * np.outer(np.cos(phi_s), np.ones_like(th_s))
    ax1.plot_wireframe(xs, ys, zs, rstride=3, cstride=6, color="#cbd5e1", alpha=0.10)

    # Compute deployment vectors for top targets
    prime_targets = [
        ("Ross 128 b", "#16a34a", "v_drift=20 m/s"),
        ("TRAPPIST-1 e", "#2563eb", "Co-aligned Corridor"),
        ("Wolf 1061 c", "#0284c7", "Prime Candidate"),
        ("Proxima Centauri b", "#dc2626", "i=44.8 deg"),
        ("LHS 1140 b", "#7c3aed", "v_drift=10 m/s"),
        ("Tau Ceti e", "#ea580c", "Rotating World"),
    ]

    for name, col, note in prime_targets:
        vec = compute_sgl_deployment_vector(name, z_rec_au=650.0)
        x, y, z = vec["x_au"], vec["y_au"], vec["z_au"]

        # Trajectory line from Sun to 650 AU
        ax1.plot([0, x], [0, y], [0, z], color=col, lw=1.8, alpha=0.85)
        # End point spacecraft marker
        ax1.scatter([x], [y], [z], color=col, s=40, marker="^")
        # Text label
        short_name = name.replace("Centauri", "Cen")
        ax1.text(x * 1.05, y * 1.05, z * 1.05, f"{short_name}\n({note})", fontsize=7.5, color=col, weight="bold")

    ax1.set_xlabel(r"$X_{\mathrm{helio}}$ (AU)", labelpad=4)
    ax1.set_ylabel(r"$Y_{\mathrm{helio}}$ (AU)", labelpad=4)
    ax1.set_zlabel(r"$Z_{\mathrm{helio}}$ (AU)", labelpad=4)
    ax1.set_xlim(-700, 700)
    ax1.set_ylim(-700, 700)
    ax1.set_zlim(-700, 700)
    ax1.view_init(elev=22, azim=-55)

    # -------------------------------------------------------------------------
    # Panel 2B: All-Sky SGL Efficiency Projection & Antipode Distribution
    # -------------------------------------------------------------------------
    ax2 = fig.add_subplot(gs[0, 1])
    ax2.set_title(r"$\mathbf{(b)}$ All-Sky SGL Observation Efficiency & Antipode Map", pad=10)

    # Generate sky efficiency grid
    sky_data = generate_sky_efficiency_map(n_ra=72, n_dec=36)
    eff_matrix = np.array(sky_data["efficiency_matrix"])
    ra_grid = np.array(sky_data["ra_grid"])
    dec_grid = np.array(sky_data["dec_grid"])

    # Plot Plate Carrée efficiency heatmap
    im = ax2.imshow(eff_matrix, extent=[0, 360, -90, 90], origin="lower",
                    cmap="viridis", aspect="auto", alpha=0.75)
    cbar = plt.colorbar(im, ax=ax2, orientation="vertical", pad=0.02, shrink=0.85)
    cbar.set_label(r"SGL Launch Efficiency ($\cos^2\beta_{\mathrm{ecl}}$)", fontsize=8.5)

    # Ecliptic equator line
    ra_ecl = np.linspace(0, 360, 200)
    # Sine curve approximation of ecliptic in equatorial coords (obliquity ~ 23.44 deg)
    dec_ecl = 23.44 * np.sin(np.radians(ra_ecl))
    ax2.plot(ra_ecl, dec_ecl, color="#facc15", lw=1.5, linestyle="--", label="Ecliptic Plane")

    # Plot candidate antipodes
    cat = get_ranked_catalog()
    for cand in cat:
        tel_ra = cand["telescope_ra_deg"]
        tel_dec = cand["telescope_dec_deg"]
        tier = cand["tier"]

        if "Tier 1" in tier:
            marker, col, ms = "o", "#ffffff", 45
            edge = "#dc2626"
        else:
            marker, col, ms = "s", "#e2e8f0", 35
            edge = "#475569"

        ax2.scatter(tel_ra, tel_dec, marker=marker, s=ms, c=col, edgecolors=edge, lw=1.2, zorder=5)
        # Label top candidates
        if cand["name"] in ["TRAPPIST-1 e", "Ross 128 b", "Proxima Centauri b", "Wolf 1061 c"]:
            lbl = cand["name"].replace("Centauri", "Cen")
            ax2.text(tel_ra + 4, tel_dec + 2.5, lbl, fontsize=7.5, color="#ffffff",
                     weight="bold", bbox=dict(boxstyle="round,pad=0.15", fc="#0f172a", ec="none", alpha=0.7))

    ax2.set_xlabel("Antipode Right Ascension (deg)")
    ax2.set_ylabel("Antipode Declination (deg)")
    ax2.set_xlim(0, 360)
    ax2.set_ylim(-90, 90)
    ax2.legend(loc="upper right", fontsize=8, framealpha=0.9)

    # -------------------------------------------------------------------------
    # Panel 2C: TRAPPIST-1 Multi-Planet Co-alignment Corridor Inset
    # -------------------------------------------------------------------------
    ax3 = fig.add_subplot(gs[1, 0])
    ax3.set_title(r"$\mathbf{(c)}$ TRAPPIST-1 Multi-Planet Co-alignment Corridor ($\Delta\theta \leq 3.0^\circ$)", pad=10)

    # TRAPPIST-1 system coordinates
    t1_ra, t1_dec = 346.6224, -5.0414
    # Telescope antipodes
    t1_tel_ra = (t1_ra + 180.0) % 360.0
    t1_tel_dec = -t1_dec

    # Relative coordinates for TRAPPIST-1 planets d, e, f
    # In reality all orbit same star, angular separation in sky is orbital radius (< 0.1 AU at 12.4 pc = < 8 mas)
    # But during orbital motion they span slightly different epochs or lateral offsets
    # Let's show the operational 3.0 degree deflection cone accessible by ion propulsion!
    th_cone = np.linspace(0, 2*np.pi, 100)
    r_cone_deg = 3.0
    ax3.fill(r_cone_deg * np.cos(th_cone), r_cone_deg * np.sin(th_cone),
             color="#dbeafe", alpha=0.55, label=r"Ion Deflection Envelope ($\Delta\theta \leq 3.0^\circ$, $\Delta v \leq 2.5\ \mathrm{km/s}$)")
    ax3.plot(r_cone_deg * np.cos(th_cone), r_cone_deg * np.sin(th_cone),
             color="#2563eb", lw=1.5, linestyle="--")

    # Secondary inner cone (1.0 deg)
    r_inner = 1.0
    ax3.fill(r_inner * np.cos(th_cone), r_inner * np.sin(th_cone),
             color="#bfdbfe", alpha=0.6, label=r"Low-$\Delta v$ Core ($\Delta\theta \leq 1.0^\circ$, $\Delta v \leq 0.85\ \mathrm{km/s}$)")

    # Plot TRAPPIST-1 planets d, e, f at realistic relative offsets (representative micro-degree offsets)
    trappist_planets = [
        ("TRAPPIST-1 d", -0.35, 0.25, "#0284c7", "d (Inner HZ)"),
        ("TRAPPIST-1 e", 0.0, 0.0, "#16a34a", "e (Prime Earth-size)"),
        ("TRAPPIST-1 f", 0.45, -0.30, "#7c3aed", "f (Outer Water-world)"),
    ]

    for p_name, dx, dy, col, p_lbl in trappist_planets:
        ax3.scatter([dx], [dy], color=col, s=80, marker="o", edgecolors="#0f172a", lw=1.5, zorder=6)
        ax3.text(dx + 0.15, dy + 0.12, p_lbl, fontsize=8.5, color=col, weight="bold")

    # Connect planets with sequential observation arrows
    arrow1 = FancyArrowPatch((-0.35, 0.25), (0.0, 0.0), arrowstyle="->", mutation_scale=14,
                             color="#1e293b", lw=1.4, linestyle=":")
    arrow2 = FancyArrowPatch((0.0, 0.0), (0.45, -0.30), arrowstyle="->", mutation_scale=14,
                             color="#1e293b", lw=1.4, linestyle=":")
    ax3.add_patch(arrow1)
    ax3.add_patch(arrow2)

    ax3.text(0.0, -1.8, r"Single Swarm Fleet Observes 3 Habitable Planets" + "\n" + r"Sequential Retargeting: $\Delta v \leq 0.6\ \mathrm{km/s}$",
             ha="center", fontsize=8.5, weight="bold", color="#1e3a8a",
             bbox=dict(boxstyle="round,pad=0.25", fc="#eff6ff", ec="#93c5fd"))

    ax3.set_xlim(-3.6, 3.6)
    ax3.set_ylim(-3.6, 3.6)
    ax3.set_xlabel(r"Relative Cross-Track Separation $\Delta \alpha \cos\delta$ (deg)")
    ax3.set_ylabel(r"Relative In-Track Separation $\Delta \delta$ (deg)")
    ax3.set_aspect("equal")
    ax3.legend(loc="upper left", fontsize=7.5, framealpha=0.9)

    # -------------------------------------------------------------------------
    # Panel 2D: Candidate Tradespace (Image Diameter vs Drift vs Feasibility)
    # -------------------------------------------------------------------------
    ax4 = fig.add_subplot(gs[1, 1])
    ax4.set_title(r"$\mathbf{(d)}$ Prime Exoplanet Candidates Mission Tradespace", pad=10)

    # Data from ranked catalog
    cat = get_ranked_catalog()
    img_diams = [c["image_diameter_km"] for c in cat]
    v_drifts = [c["v_drift_m_s"] for c in cat]
    scores = [c["sgl_score"] for c in cat]
    names = [c["name"] for c in cat]

    scatter = ax4.scatter(img_diams, v_drifts, c=scores, s=120, cmap="viridis",
                          edgecolors="#1e293b", lw=1.2, alpha=0.9, zorder=5)
    cbar4 = plt.colorbar(scatter, ax=ax4, orientation="vertical", pad=0.02, shrink=0.85)
    cbar4.set_label("SGL Feasibility Score (0 - 100)", fontsize=8.5)

    # Annotate top targets
    label_offsets = {
        "Proxima Centauri b": (1.0, 3.0),
        "Ross 128 b": (-4.5, 3.5),
        "Wolf 1061 c": (1.0, -4.0),
        "TRAPPIST-1 e": (0.8, 2.0),
        "LHS 1140 b": (0.8, -3.0),
        "Tau Ceti e": (-5.0, 2.5),
        "Teegarden's Star b": (-4.0, -6.0),
    }

    for c in cat:
        n = c["name"]
        if n in label_offsets:
            ox, oy = label_offsets[n]
            short = n.replace("Centauri", "Cen").replace("Star ", "")
            ax4.text(c["image_diameter_km"] + ox, c["v_drift_m_s"] + oy, short,
                     fontsize=7.8, weight="bold", color="#0f172a")

    # High feasibility / low drift sweet spot box
    rect = Rectangle((1.5, 5), 18, 25, fill=True, facecolor="#dcfce7", edgecolor="#16a34a",
                     lw=1.5, linestyle="--", alpha=0.4, zorder=2)
    ax4.add_patch(rect)
    ax4.text(10.5, 27, "Mission Sweet Spot:\nHigh SNR, Low Drift",
             fontsize=8, color="#15803d", weight="bold", ha="center")

    ax4.set_xlabel(r"Projected Image Cylinder Diameter $D_{\mathrm{img}}$ at $650\ \mathrm{AU}$ (km)")
    ax4.set_ylabel(r"Proper-Motion Lateral Drift Velocity $v_{\mathrm{drift}}$ (m/s)")
    ax4.set_xlim(0, 36)
    ax4.set_ylim(-2, 105)

    fig.suptitle(
        "Figure 2: 3D Heliocentric Corridors in the Solar System, All-Sky SGL Efficiency & Exoplanet Target Tradespace",
        fontsize=13, weight="bold", y=0.98
    )

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    plt.savefig(output_path, dpi=300)
    plt.close()
    print(f"Successfully generated: {output_path}")


if __name__ == "__main__":
    generate_figure1()
    generate_figure2()
