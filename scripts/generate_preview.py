"""
Generate high-resolution dark-mode summary preview for sgl-sim.
Outputs: docs/assets/dashboard_preview.png
"""

import os
import matplotlib
os.environ["MPLCONFIGDIR"] = "/tmp/matplotlib_sgl"
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.patches import Circle, Ellipse, Polygon
import numpy as np
from astropy import units as u

from sgl_sim.relativity import (
    schwarzschild_radius,
    critical_impact_parameter,
    focal_distance,
)
from sgl_sim.optics import (
    minimum_focal_distance,
    einstein_ring_properties,
    peak_magnification,
    generate_2d_psf,
)
from sgl_sim.caustics import (
    astroid_caustic_semi_width,
    parametric_astroid,
    solve_quadrupole_images,
)
from sgl_sim.deconvolution import (
    generate_exoplanet_map,
    wiener_deconvolution,
    calculate_snr,
)


def create_preview(output_path="docs/assets/dashboard_preview.png"):
    plt.style.use("dark_background")
    fig = plt.figure(figsize=(16, 10), facecolor="#080c14", dpi=200)

    # Title header
    fig.suptitle(
        "sgl-sim: Solar & Black Hole Gravitational Lens Mission Design Simulator",
        fontsize=18,
        fontweight="bold",
        color="#e0e8ff",
        y=0.97,
    )

    gs = gridspec.GridSpec(2, 2, figure=fig, hspace=0.28, wspace=0.24, top=0.91, bottom=0.06, left=0.07, right=0.95)

    # -------------------------------------------------------------
    # Panel 1: Relativistic Ray-Tracing & Optical Focal Line
    # -------------------------------------------------------------
    ax1 = fig.add_subplot(gs[0, 0])
    ax1.set_facecolor("#0b111e")
    ax1.set_title("1. Relativistic Deflection & SGL Optical Focal Line", fontsize=12, fontweight="bold", color="#00f0ff", pad=10)

    # Mass = 1 M_sun
    rs = schwarzschild_radius(1.0 * u.M_sun)
    r_sun_m = (1.0 * u.R_sun).to(u.m).value
    au_m = (1.0 * u.AU).to(u.m).value

    # Coordinates in AU
    z_min_au = (r_sun_m**2 / (2.0 * rs)) / au_m

    # Plot Sun at (0, 0)
    sun_circ = Ellipse((0, 0), width=35, height=26, color="#ffcc00", ec="#ff9900", lw=2, zorder=5)
    ax1.add_patch(sun_circ)
    ax1.text(0, -22, "Sun (1 M☉)", color="#ffcc00", fontsize=9, ha="center", va="top", fontweight="bold")

    # Plot rays
    impact_factors = np.linspace(1.0, 1.25, 6)
    z_start = -150
    for factor in impact_factors:
        b_m = factor * r_sun_m
        b_au = factor * 22  # scale for visual clarity
        z_cross = (b_m**2 / (2.0 * rs)) / au_m

        # Top ray
        ax1.plot([z_start, 0, z_cross], [b_au, b_au, 0], color="#38bdf8", lw=1.2, alpha=0.75)
        # Bottom ray
        ax1.plot([z_start, 0, z_cross], [-b_au, -b_au, 0], color="#38bdf8", lw=1.2, alpha=0.75)

    # Blocked grazing ray demonstration
    ax1.plot([z_start, 0], [8, 8], color="#ef4444", lw=1.0, linestyle="--", alpha=0.7)
    ax1.plot([z_start, 0], [-8, -8], color="#ef4444", lw=1.0, linestyle="--", alpha=0.7)
    ax1.text(-75, 12, "Impact b < R☉ (Occulted)", color="#f87171", fontsize=8, ha="center")

    # Golden Focal Line
    z_focal = np.linspace(z_min_au, 850, 200)
    ax1.plot(z_focal, np.zeros_like(z_focal), color="#fbbf24", lw=3.5, label="Caustic Focal Line", zorder=6)
    ax1.axvline(z_min_au, color="#f59e0b", linestyle=":", lw=1.5, alpha=0.8)
    ax1.text(z_min_au, 50, f"z_min = {z_min_au:.1f} AU", color="#fbbf24", fontsize=9, ha="center", fontweight="bold")

    # Spacecraft position at 650 AU
    ax1.plot([650], [0], marker="^", markersize=10, color="#c084fc", label="Receiver Spacecraft (650 AU)", zorder=7)
    ax1.text(650, -25, "Spacecraft\n(650 AU)", color="#c084fc", fontsize=8.5, ha="center")

    ax1.set_xlim(-180, 850)
    ax1.set_ylim(-75, 75)
    ax1.set_xlabel("Optical Axis z [AU]", color="#94a3b8", fontsize=10)
    ax1.set_ylabel("Transverse Offset [AU eq.]", color="#94a3b8", fontsize=10)
    ax1.tick_params(colors="#64748b", labelsize=9)
    ax1.grid(True, color="#1e293b", linestyle="--", alpha=0.6)
    ax1.legend(loc="upper right", facecolor="#0f172a", edgecolor="#334155", fontsize=8)

    # -------------------------------------------------------------
    # Panel 2: Quadrupole (J2) Astroid Caustic & Einstein Cross
    # -------------------------------------------------------------
    ax2 = fig.add_subplot(gs[0, 1])
    ax2.set_facecolor("#0b111e")
    ax2.set_title("2. Stellar Oblateness (J₂) Astroid Caustic & Einstein Cross", fontsize=12, fontweight="bold", color="#38bdf8", pad=10)

    z_rec_m = (650.0 * u.AU).to(u.m).value
    j2_val = 2.2e-7
    a_caustic_info = astroid_caustic_semi_width(z_rec=z_rec_m, j2=j2_val)
    a_m = a_caustic_info["a_caustic_m"]
    a_km = a_m / 1000.0

    theta_arr = np.linspace(0, 2 * np.pi, 500)
    x_astroid_km = (a_m * np.cos(theta_arr)**3) / 1000.0
    y_astroid_km = (a_m * np.sin(theta_arr)**3) / 1000.0

    ax2.plot(x_astroid_km, y_astroid_km, color="#00f0ff", lw=2.2, label=f"Astroid Boundary (a = {a_km:,.0f} km)")
    ax2.fill(x_astroid_km, y_astroid_km, color="#00f0ff", alpha=0.12, label="4-Image Regime (Inside)")

    # Inside receiver position (x0, y0) in meters and km
    x0_km, y0_km = 12000.0, 8000.0
    x0_m, y0_m = x0_km * 1000.0, y0_km * 1000.0
    sol = solve_quadrupole_images(x0=x0_m, y0=y0_m, z_rec=z_rec_m, j2=j2_val)

    ax2.plot([x0_km], [y0_km], marker="o", markersize=9, color="#ec4899", label=f"Receiver ({x0_km:,.0f} km, {y0_km:,.0f} km)", zorder=7)

    # Inset showing resolved 4 images along Einstein Ring
    ax2_inset = ax2.inset_axes([0.62, 0.60, 0.35, 0.35], facecolor="#080c14")
    phi_ring = np.linspace(0, 2 * np.pi, 200)
    ax2_inset.plot(np.cos(phi_ring), np.sin(phi_ring), color="#64748b", linestyle=":", lw=1.0)
    for phi_img in sol["image_angles_rad"]:
        xi = np.cos(phi_img)
        yi = np.sin(phi_img)
        ax2_inset.plot([xi], [yi], marker="*", markersize=10, color="#fbbf24")
    ax2_inset.plot([0], [0], marker="+", markersize=6, color="#94a3b8")
    ax2_inset.set_title("Einstein Cross (4 Images)", color="#fbbf24", fontsize=8, pad=3, fontweight="bold")
    ax2_inset.axis("off")

    ax2.set_xlim(-a_km * 1.45, a_km * 1.45)
    ax2.set_ylim(-a_km * 1.45, a_km * 1.45)
    ax2.set_xlabel("Transverse Coordinate x [km]", color="#94a3b8", fontsize=10)
    ax2.set_ylabel("Transverse Coordinate y [km]", color="#94a3b8", fontsize=10)
    ax2.tick_params(colors="#64748b", labelsize=9)
    ax2.grid(True, color="#1e293b", linestyle="--", alpha=0.6)
    ax2.legend(loc="lower left", facecolor="#0f172a", edgecolor="#334155", fontsize=8)

    # -------------------------------------------------------------
    # Panel 3: Wave-Optics Bessel J0^2 PSF & Coronal Glow
    # -------------------------------------------------------------
    ax3 = fig.add_subplot(gs[1, 0])
    ax3.set_facecolor("#0b111e")
    ax3.set_title("3. Diffraction-Limited Bessel J₀² Point Spread Function", fontsize=12, fontweight="bold", color="#a855f7", pad=10)

    # Generate high-res 2D PSF
    psf_2d = generate_2d_psf(grid_size=64, pixel_scale_m=0.15, z_rec=z_rec_m, wavelength=1.0e-6)
    im3 = ax3.imshow(
        psf_2d,
        cmap="magma",
        origin="lower",
        extent=[-4.8, 4.8, -4.8, 4.8],
        vmin=0,
        vmax=psf_2d.max(),
    )
    cbar3 = fig.colorbar(im3, ax=ax3, fraction=0.046, pad=0.04)
    cbar3.set_label("Normalized Wave Intensity", color="#94a3b8", fontsize=9)
    cbar3.ax.tick_params(colors="#64748b", labelsize=8)

    # Annotate peak magnification & Einstein ring
    mu_peak = peak_magnification(1.0e-6)
    ring_info = einstein_ring_properties(z_rec=z_rec_m)
    theta_e_mas = ring_info["theta_E_arcsec"] * 1e3

    ax3.text(
        -4.4,
        3.5,
        f"Peak Gain μ_max = {mu_peak:.2e}\nθ_E = {theta_e_mas:.1f} mas (at 650 AU)\nFWHM ~ 0.5 m",
        color="#ffffff",
        fontsize=8.5,
        bbox=dict(boxstyle="round,pad=0.4", facecolor="#0f172a", edgecolor="#475569", alpha=0.85),
    )

    ax3.set_xlabel("Focal Plane Offset Δx [m]", color="#94a3b8", fontsize=10)
    ax3.set_ylabel("Focal Plane Offset Δy [m]", color="#94a3b8", fontsize=10)
    ax3.tick_params(colors="#64748b", labelsize=9)

    # -------------------------------------------------------------
    # Panel 4: Exoplanet Reconstruction (Ground Truth -> Coronal Noise -> Wiener)
    # -------------------------------------------------------------
    gs4 = gridspec.GridSpecFromSubplotSpec(1, 3, subplot_spec=gs[1, 1], wspace=0.15)

    gt_map = generate_exoplanet_map(grid_size=32, seed=42)
    snr_eval = 25.0
    deconv_res = wiener_deconvolution(ground_truth=gt_map, psf_kernel=generate_2d_psf(32, 1.0, z_rec_m), snr=snr_eval)

    # 4A: Ground Truth
    ax4a = fig.add_subplot(gs4[0, 0])
    ax4a.set_facecolor("#0b111e")
    ax4a.imshow(gt_map, cmap="viridis", origin="lower", vmin=0, vmax=1)
    ax4a.set_title("Ground Truth\n(Exoplanet Map)", color="#e2e8f0", fontsize=9, fontweight="bold")
    ax4a.axis("off")

    # 4B: Convolved + Poisson Coronal Noise
    ax4b = fig.add_subplot(gs4[0, 1])
    ax4b.set_facecolor("#0b111e")
    ax4b.imshow(deconv_res["convolved_noisy"], cmap="viridis", origin="lower")
    ax4b.set_title(f"SGL Convolved + Noise\n(SNR = {snr_eval:.0f})", color="#f87171", fontsize=9, fontweight="bold")
    ax4b.axis("off")

    # 4C: Regularized 2D Wiener Reconstruction
    ax4c = fig.add_subplot(gs4[0, 2])
    ax4c.set_facecolor("#0b111e")
    ax4c.imshow(deconv_res["deconvolved"], cmap="viridis", origin="lower", vmin=0, vmax=1)
    rmse_str = f"RMSE: {deconv_res['rmse_deconvolved']:.3f}"
    ssim_str = f"SSIM: {deconv_res['ssim_deconvolved']:.3f}"
    ax4c.set_title(f"Wiener Deconvolved\n({rmse_str} | {ssim_str})", color="#4ade80", fontsize=9, fontweight="bold")
    ax4c.axis("off")

    # Header above panel 4
    fig.text(0.74, 0.46, "4. Exoplanet Surface Imaging & Wiener Deconvolution", fontsize=12, fontweight="bold", color="#4ade80", ha="center")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    plt.savefig(output_path, dpi=200, facecolor=fig.get_facecolor(), edgecolor="none")
    plt.close(fig)
    print(f"Generated preview successfully at {output_path}")


if __name__ == "__main__":
    create_preview()
