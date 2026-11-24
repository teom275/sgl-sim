"""
Generate high-resolution visual guide and comparison diagram of satellite swarm
formation patterns in the Solar Gravitational Lens (SGL) image cylinder.
"""

import numpy as np
import matplotlib.pyplot as plt
from sgl_sim.orbital import generate_swarm_formation

def main():
    plt.style.use("dark_background")
    fig, axes = plt.subplots(1, 4, figsize=(18, 4.6), dpi=300)

    patterns = [
        ("hexagonal", 7, 10.0, "Hexagonal Array", "Minimal inter-craft distance\nUniform quadrant coverage"),
        ("concentric", 12, 10.0, "Concentric Rings", "Azimuthal Fourier modes\nCaustic multipole mapping"),
        ("spiral", 14, 10.0, "Fermat Golden Spiral", "Isotropic UV-plane coverage\nAperture synthesis imaging"),
        ("linear_rake", 8, 10.0, "Linear Pushbroom Rake", "Synchronous parallel scan\nAccelerates scan by 1/N"),
    ]

    colors = ["#ffc24b", "#38bdf8", "#a78bfa", "#34d399"]

    for ax, (pat, n_sats, radius, title, subtitle), col in zip(axes, patterns, colors):
        swarm = generate_swarm_formation(pattern=pat, num_satellites=n_sats, radius_km=radius)
        positions = swarm["positions"]
        xs = [p["x_km"] for p in positions]
        ys = [p["y_km"] for p in positions]

        # Draw cylinder circle
        theta = np.linspace(0, 2 * np.pi, 200)
        ax.plot(radius * np.cos(theta), radius * np.sin(theta), color=col, linestyle="--", linewidth=1.5, alpha=0.7)
        ax.fill(radius * np.cos(theta), radius * np.sin(theta), color=col, alpha=0.04)

        # Concentric inner range circles
        for r_frac in [0.25, 0.5, 0.75]:
            ax.plot(radius * r_frac * np.cos(theta), radius * r_frac * np.sin(theta), color="white", linestyle=":", linewidth=0.6, alpha=0.15)

        # Baselines mesh
        for i in range(len(positions)):
            for j in range(i + 1, len(positions)):
                d = np.hypot(xs[i] - xs[j], ys[i] - ys[j])
                if len(positions) <= 10 or d <= (swarm["mean_separation_km"] * 1.35):
                    ax.plot([xs[i], xs[j]], [ys[i], ys[j]], color=col, alpha=0.2, linewidth=0.8)

        # Spacecraft nodes
        ax.scatter(xs, ys, color=col, s=70, edgecolors="white", linewidth=1.2, zorder=5)

        # Node labels
        for p in positions:
            ax.annotate(f"S{p['id']}", (p["x_km"], p["y_km"]), textcoords="offset points", xytext=(5, 4),
                        color="white", fontsize=8, weight="bold")

        # Scan motion vectors or indicators
        if pat == "linear_rake":
            for x, y in zip(xs, ys):
                ax.arrow(x, y - 1.2, 0, 2.4, head_width=0.4, head_length=0.4, fc=col, ec=col, alpha=0.6)

        ax.set_aspect("equal")
        limit = radius * 1.35
        ax.set_xlim(-limit, limit)
        ax.set_ylim(-limit, limit)
        ax.axhline(0, color="white", linestyle="-", linewidth=0.5, alpha=0.12)
        ax.axvline(0, color="white", linestyle="-", linewidth=0.5, alpha=0.12)
        ax.set_xlabel("Transverse X (km)", fontsize=9, color="#94a3b8")
        ax.set_ylabel("Transverse Y (km)", fontsize=9, color="#94a3b8")

        info_box = f"$N_{{sat}} = {n_sats}$\n$B_{{max}} = {swarm['max_baseline_km']:.1f}$ km\n$\\bar{{d}} = {swarm['mean_separation_km']:.1f}$ km"
        ax.text(0.04, 0.05, info_box, transform=ax.transAxes, fontsize=8,
                verticalalignment="bottom", bbox=dict(boxstyle="round,pad=0.4", fc="#10131a", ec=col, alpha=0.8, lw=0.8))

        ax.set_title(f"{title}\n", fontsize=11, weight="bold", pad=2, color="white")
        ax.text(0.5, 1.02, subtitle, transform=ax.transAxes, fontsize=7.5, color="#cbd5e1", ha="center")

    plt.suptitle("SGL Transverse Satellite Swarm Formation Architectures ($D_{\\mathrm{img}} = 20\\,\\mathrm{km}$)",
                 fontsize=14, weight="bold", y=1.03, color="#f1f5f9")
    plt.tight_layout()
    output_path = "paper/figures/figure_swarm_architectures_guide.png"
    plt.savefig(output_path, bbox_inches="tight", dpi=300)
    print(f"Figure saved successfully to {output_path}")

if __name__ == "__main__":
    main()
