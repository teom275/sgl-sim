"""
Interactive ManimGL scenes for the Solar Gravitational Lens (3Blue1Brown ``manim``).

Every scene first plays a short narrated demo (so ``-w`` renders a video), then
hands control to you: drag the slider knobs, or drag the receiver in the
caustic explorer. Press ``q`` / ``Esc`` to quit.

Run (window, interactive)::

    manimgl src/sgl_sim/manim_scenes/sgl_interactive.py SolarLensFocalLine
    manimgl src/sgl_sim/manim_scenes/sgl_interactive.py EinsteinCrossExplorer
    manimgl src/sgl_sim/manim_scenes/sgl_interactive.py WavePSFExplorer

Render to video instead (no window)::

    manimgl src/sgl_sim/manim_scenes/sgl_interactive.py SolarLensFocalLine -w

Interactive tips (ManimGL defaults): skip the demo with ``-n <k>`` or ``-s``
(jump to the final state), or add ``-e`` to drop into an IPython shell where
``self`` is the live scene, e.g. ``self.s_mass.set_value(2.0)``.

All physics comes from the regular ``sgl_sim`` API via
:mod:`sgl_sim.manim_scenes.model`; this file only does drawing and input.
No LaTeX installation is required (only ``Text`` is used).
"""

from __future__ import annotations

from typing import Callable, Hashable, Sequence

import numpy as np
from manimlib import (
    BLUE_B,
    DOWN,
    FadeIn,
    GREEN,
    GREY_A,
    GREY_B,
    GREY_C,
    GREY_D,
    GREY_E,
    Circle,
    DashedLine,
    Dot,
    GlowDot,
    Group,
    LEFT,
    LinearNumberSlider,
    Line,
    Mobject,
    RED,
    RIGHT,
    Scene,
    ShowCreation,
    Square,
    TEAL,
    TEAL_B,
    Text,
    Triangle,
    UL,
    UP,
    UR,
    UpdateFromAlphaFunc,
    VGroup,
    VMobject,
    WHITE,
    YELLOW,
    YELLOW_E,
    Annulus,
    Axes,
    BackgroundRectangle,
    LaggedStartMap,
    color_gradient,
    smooth,
)

from sgl_sim.manim_scenes import model as sglm

BG_COLOR = "#0e1117"
BLACK_ISH = "#05070b"
FOCAL_COLOR = YELLOW
RAY_COLORS = (BLUE_B, TEAL, GREEN)


# ---------------------------------------------------------------------------
# Small reusable widgets
# ---------------------------------------------------------------------------


class Reactive(Group):
    """
    A Group that rebuilds its children whenever ``key()`` changes.

    Rebuilding ``Text`` (Pango -> SVG) every frame is slow, so the scene state
    is reduced to a hashable key and the expensive ``build()`` only runs when
    a slider actually moved.
    """

    def __init__(self, key: Callable[[], Hashable], build: Callable[[], Mobject], **kwargs):
        super().__init__(**kwargs)
        self._key_fn = key
        self._build_fn = build
        self._last_key: Hashable = object()
        self.refresh()
        self.add_updater(lambda m: m.refresh())

    def refresh(self) -> "Reactive":
        key = self._key_fn()
        if key != self._last_key:
            self._last_key = key
            self.set_submobjects([self._build_fn()])
        return self


class LabeledSlider(Group):
    """A ManimGL ``LinearNumberSlider`` with a caption and a live value readout."""

    def __init__(self, label: str, value: float, lo: float, hi: float, step: float,
                 fmt: str = "{:.2f}", width: float = 2.6, color=TEAL, **kwargs):
        self.fmt = fmt
        self.lo, self.hi = lo, hi
        self.slider = LinearNumberSlider(
            value=value, min_value=lo, max_value=hi, step=step,
            rounded_rect_kwargs=dict(height=0.08, width=width, corner_radius=0.04),
            circle_kwargs=dict(radius=0.13, stroke_color=WHITE, stroke_width=2,
                               fill_color=color, fill_opacity=1.0),
        )
        self.slider.bar.set_fill(GREY_D, 1.0).set_stroke(GREY_B, 1)
        self.caption = Text(label, font_size=22, color=GREY_A)
        self.caption.next_to(self.slider.bar, UP, buff=0.18, aligned_edge=LEFT)
        self.readout = Reactive(
            key=lambda: self.fmt.format(self.get_value()),
            build=lambda: Text(self.fmt.format(self.get_value()), font_size=22, color=color)
            .next_to(self.slider.bar, RIGHT, buff=0.25),
        )
        super().__init__(self.caption, self.readout, self.slider, **kwargs)

    def get_value(self) -> float:
        return float(self.slider.get_value())

    def set_value(self, value: float) -> "LabeledSlider":
        self.slider.set_value(float(np.clip(value, self.lo, self.hi)))
        return self


class SGLScene(Scene):
    """Common configuration: dark background, mouse drags go to widgets."""

    drag_to_pan = False
    default_camera_config = dict(background_color=BG_COLOR)

    def sweep(self, slider: LabeledSlider, target: float, run_time: float = 2.0, **kwargs):
        """Animate a slider to ``target`` (used by the demo intro)."""
        start = slider.get_value()

        def update(_mob, alpha):
            slider.set_value(start + (target - start) * alpha)

        self.play(UpdateFromAlphaFunc(slider.slider, update), run_time=run_time,
                  rate_func=smooth, **kwargs)

    def title(self, text: str, subtitle: str | None = None) -> VGroup:
        t = Text(text, font_size=36, color=WHITE)
        group = VGroup(t)
        if subtitle:
            s = Text(subtitle, font_size=22, color=GREY_B)
            s.next_to(t, DOWN, buff=0.12)
            group.add(s)
        group.to_edge(UP, buff=0.22)
        return group

    @staticmethod
    def info_panel(lines: Sequence[tuple], corner=UR, font_size: int = 22) -> VGroup:
        rows = VGroup()
        for text, color in lines:
            rows.add(Text(text, font_size=font_size, color=color))
        rows.arrange(DOWN, aligned_edge=LEFT, buff=0.12)
        bg = BackgroundRectangle(rows, color=BG_COLOR, fill_opacity=0.85, buff=0.15)
        bg.set_stroke(GREY_D, 1, opacity=1.0)
        panel = VGroup(bg, rows)
        panel.to_corner(corner, buff=0.3)
        return panel


# ---------------------------------------------------------------------------
# 1. Rays -> focal line
# ---------------------------------------------------------------------------


class SolarLensFocalLine(SGLScene):
    """
    Parallel light from a distant exoplanet is bent by the Sun's gravity and
    crosses the optical axis at ``z(b) = b^2 / (2 R_s)``. Rays that graze the
    limb focus first, at ``z_min = R^2 / (2 R_s)`` (547.8 AU for the Sun); every
    point beyond is on the *focal line*.

    Controls: lens mass, lens radius, receiver distance ``z_rec``.
    """

    impact_params = np.concatenate([np.linspace(0.3, 2.45, 10), -np.linspace(0.3, 2.45, 10)])

    def construct(self):
        view = sglm.FocalLineView(x_left=-7.3, x_lens=-5.0, x_right=6.6, y_axis=0.1,
                                  y_per_rsun=0.95, y_limit=2.45, z_max_au=2000.0)
        self.view = view

        header = self.title("The Sun as a telescope", "gravitational bending  ->  focal line beyond z_min")

        # --- controls ---------------------------------------------------------
        self.s_mass = LabeledSlider("Lens mass  M / M☉", 1.0, 0.3, 4.0, 0.05, "{:.2f}", color=YELLOW)
        self.s_rad = LabeledSlider("Lens radius  R / R☉", 1.0, 0.3, 2.4, 0.05, "{:.2f}", color=YELLOW_E)
        self.s_zrec = LabeledSlider("Receiver  z_rec [AU]", 650.0, 100.0, 1950.0, 10.0, "{:.0f}", color=TEAL)
        controls = Group(self.s_mass, self.s_rad, self.s_zrec).arrange(RIGHT, buff=0.8)
        controls.to_edge(DOWN, buff=0.35)

        # --- static furniture -------------------------------------------------
        axis = Line(view.point(-120, 0), view.point(view.z_max_au, 0), stroke_width=1.5, color=GREY_C)
        ticks = VGroup()
        for z in (0, 500, 1000, 1500, 2000):
            tick = Line(view.point(z, 0) + 0.06 * DOWN, view.point(z, 0) + 0.06 * UP,
                        stroke_width=1.5, color=GREY_C)
            ticks.add(tick)
            if z > 0:  # z = 0 sits under the lens disk
                ticks.add(Text(f"{z} AU", font_size=16, color=GREY_C).next_to(tick, DOWN, buff=0.06))
        source = Text("light from\ndistant planet", font_size=18, color=GREY_B)
        source.to_edge(LEFT, buff=0.3).set_y(view.y_of_b(2.45) + 0.45)
        scale_note = Text("axes not to scale: real bending is 1.75 arcsec at the limb",
                          font_size=16, color=GREY_C)
        scale_note.next_to(controls, UP, buff=0.18).to_edge(LEFT, buff=0.4)

        params = lambda: (round(self.s_mass.get_value(), 3), round(self.s_rad.get_value(), 3))
        state = lambda: params() + (round(self.s_zrec.get_value(), 1),)

        lens = Reactive(params, self.build_lens)
        rays = Reactive(params, self.build_rays)
        focal = Reactive(params, self.build_focal_line)
        receiver = Reactive(state, self.build_receiver)
        panel = Reactive(state, self.build_panel)

        # --- demo intro --------------------------------------------------------
        self.add(axis)
        self.play(FadeIn(header), FadeIn(lens), FadeIn(ticks), FadeIn(source))
        intro_rays = rays[0].copy()  # animate a copy: Reactive owns the live one
        self.play(LaggedStartMap(ShowCreation, intro_rays, lag_ratio=0.06), run_time=3)
        self.remove(intro_rays)
        self.add(rays)
        self.play(FadeIn(focal), FadeIn(scale_note))
        self.play(FadeIn(receiver), FadeIn(panel), FadeIn(controls))
        self.wait()
        self.sweep(self.s_zrec, 1500.0, run_time=3)
        self.sweep(self.s_zrec, 650.0, run_time=2)
        self.sweep(self.s_mass, 2.0, run_time=2.5)
        self.sweep(self.s_rad, 1.6, run_time=2.5)
        self.sweep(self.s_mass, 1.0, run_time=2)
        self.sweep(self.s_rad, 1.0, run_time=2)
        self.wait()
        # From here on the window stays open and the sliders are live.

    # --- builders (pure functions of slider state) --------------------------

    def build_lens(self) -> Group:
        r = self.s_rad.get_value() * self.view.y_per_rsun
        center = self.view.point(0, 0)
        glow = GlowDot(center, radius=2.2 * r, color=YELLOW, glow_factor=1.5)
        glow.set_opacity(0.35)
        disk = Circle(radius=r, fill_color=YELLOW_E, fill_opacity=1.0, stroke_color=YELLOW, stroke_width=2)
        disk.move_to(center)
        return Group(glow, disk)

    def build_rays(self) -> VGroup:
        paths = sglm.lens_ray_paths(self.s_mass.get_value(), self.s_rad.get_value(),
                                    self.impact_params, self.view)
        colors = color_gradient(RAY_COLORS, len(self.impact_params) // 2)
        group = VGroup()
        for i, p in enumerate(paths):
            ray = VMobject().set_points_as_corners(p.points)
            if p.blocked:
                ray.set_stroke(GREY_D, 1.5)
            else:
                ray.set_stroke(colors[i % len(colors)], 1.8, opacity=0.9)
            group.add(ray)
        return group

    def build_focal_line(self) -> VGroup:
        info = sglm.focal_line_readout(self.s_mass.get_value(), self.s_rad.get_value(), 650.0)
        z_min = info["z_min_au"]
        group = VGroup()
        if z_min < self.view.z_max_au:
            line = Line(self.view.point(z_min, 0), self.view.point(self.view.z_max_au, 0),
                        stroke_width=7, color=FOCAL_COLOR)
            line.set_stroke(opacity=0.85)
            mark = DashedLine(self.view.point(z_min, -0.35), self.view.point(z_min, 0.9),
                              stroke_width=1.5, color=FOCAL_COLOR)
            label = Text(f"z_min = {z_min:.0f} AU", font_size=20, color=FOCAL_COLOR)
            label.next_to(mark, UP, buff=0.08)
            group.add(line, mark, label)
        else:
            label = Text("focal line starts beyond 2000 AU", font_size=20, color=FOCAL_COLOR)
            label.move_to(self.view.point(1500, 0.6))
            group.add(label)
        return group

    def build_receiver(self) -> Group:
        m, r, z = self.s_mass.get_value(), self.s_rad.get_value(), self.s_zrec.get_value()
        info = sglm.focal_line_readout(m, r, z)
        pos = self.view.point(z, 0)
        ok = info["in_focus"]
        color = TEAL_B if ok else RED
        ship = Triangle(fill_color=color, fill_opacity=1.0, stroke_width=0).scale(0.13)
        ship.rotate(-np.pi / 2).move_to(pos)
        group = Group()
        if ok:
            b = info["b_ring_rsun"]
            for sign in (1, -1):
                ray = VMobject().set_points_as_corners([
                    self.view.point(-120, sign * b), self.view.point(0, sign * b), pos,
                ])
                ray.set_stroke(WHITE, 3)
                group.add(ray)
        group.add(GlowDot(pos, radius=0.35, color=color), ship)
        return group

    def build_panel(self) -> VGroup:
        m, r, z = self.s_mass.get_value(), self.s_rad.get_value(), self.s_zrec.get_value()
        info = sglm.focal_line_readout(m, r, z)
        if info["in_focus"]:
            status = ("receiver on the focal line", TEAL_B)
            ring = (f"Einstein ring:  b = {info['b_ring_rsun']:.2f} R☉", WHITE)
            theta = (f"ring radius  θ_E = {info['theta_E_arcsec']:.2f} arcsec", WHITE)
        else:
            status = ("z_rec < z_min: focusing rays hit the star", RED)
            ring = ("Einstein ring:  occulted", GREY_B)
            theta = (" ", GREY_B)
        lines = [
            (f"z_min = {info['z_min_au']:.1f} AU", FOCAL_COLOR),
            status, ring, theta,
            (f"peak gain  μ_max(1 µm) = {info['mu_max']:.2e}", GREY_A),
        ]
        return self.info_panel(lines, corner=UR, font_size=20).shift(0.75 * DOWN)


# ---------------------------------------------------------------------------
# 2. J2 astroid caustic -> Einstein cross
# ---------------------------------------------------------------------------


class EinsteinCrossExplorer(SGLScene):
    """
    The Sun's oblateness (quadrupole ``J_2``) splits the point-like focus into
    a four-cusped astroid caustic in the receiver plane. Inside it a receiver
    sees four images on the Einstein ring (Einstein cross); outside, two.

    Drag the receiver (or click anywhere in the plane). The image azimuths are
    the roots of ``x0 sin(phi) - y0 cos(phi) - (a/2) sin(2 phi) = 0`` solved by
    :func:`sgl_sim.caustics.solve_quadrupole_images`.
    """

    plane_half = 2.0  # half-size of the plane box, in reference units a_ref (J2=2.2e-7, 650 AU)

    def construct(self):
        view = sglm.CausticView(center=(-3.85, 0.3), units_per_a=1.1,
                                ring_center=(4.35, 0.25), ring_radius=1.55)
        self.view = view
        header = self.title("Oblate Sun: astroid caustic & Einstein cross",
                            "drag the receiver through the focal plane")

        self.s_j2 = LabeledSlider("Solar oblateness  J2 [1e-7]", 2.2, 0.5, 3.0, 0.05, "{:.2f}", color=YELLOW)
        self.s_zrec = LabeledSlider("Receiver  z_rec [AU]", 650.0, 550.0, 1200.0, 10.0, "{:.0f}", color=TEAL)
        controls = Group(self.s_j2, self.s_zrec).arrange(RIGHT, buff=1.2)
        controls.to_edge(DOWN, buff=0.35)

        # --- receiver plane ---------------------------------------------------
        size = 2 * self.plane_half * view.units_per_a
        plane = Square(side_length=size, stroke_color=GREY_C, stroke_width=1.5,
                       fill_color=GREY_E, fill_opacity=0.35)
        plane.move_to(view.plane_point(0, 0))
        cross = VGroup(
            Line(view.plane_point(-self.plane_half, 0), view.plane_point(self.plane_half, 0)),
            Line(view.plane_point(0, -self.plane_half), view.plane_point(0, self.plane_half)),
        ).set_stroke(GREY_C, 1, opacity=0.6)
        astroid = Reactive(
            key=lambda: round(self.scale, 4),
            build=lambda: VMobject().set_points_as_corners(sglm.astroid_curve(view, self.scale))
            .set_stroke(FOCAL_COLOR, 3).set_fill(FOCAL_COLOR, 0.08),
        )
        plane_label = Text("receiver plane  (unit = astroid size for J2 = 2.2e-7 at 650 AU)",
                           font_size=16, color=GREY_B)
        plane_label.next_to(plane, UP, buff=0.08)

        # Draggable receiver.
        self.receiver = Group(
            Circle(radius=0.28, stroke_width=0, fill_opacity=0.0),  # generous hit-box
            GlowDot(radius=0.3, color=TEAL_B),
            Dot(radius=0.07, fill_color=WHITE),
        ).move_to(view.plane_point(0.25, 0.15))
        self.receiver.add_mouse_drag_listner(self._on_drag)
        plane.add_mouse_press_listner(self._on_drag)

        # --- Einstein ring panel ---------------------------------------------
        ring = Circle(radius=view.ring_radius, stroke_color=GREY_B, stroke_width=1.5)
        ring.move_to(np.array([*view.ring_center, 0.0]))
        occulter = Circle(radius=0.55 * view.ring_radius, fill_color=BLACK_ISH, fill_opacity=1.0,
                          stroke_color=GREY_D, stroke_width=1)
        occulter.move_to(ring)
        ring_label = Text("telescope view:\nEinstein ring around the occulted Sun",
                          font_size=18, color=GREY_B)
        ring_label.next_to(ring, UP, buff=0.5)

        state = lambda: (
            round(self.uv[0], 3), round(self.uv[1], 3),
            round(self.s_j2.get_value(), 2), round(self.s_zrec.get_value(), 1),
        )
        # Text is expensive to rebuild, so the panel uses a coarser key than the images.
        coarse = lambda: (round(self.uv[0], 2), round(self.uv[1], 2)) + state()[2:]
        images = Reactive(state, self.build_images)
        panel = Reactive(coarse, self.build_panel)

        self.add(plane, cross)
        intro_astroid = astroid[0].copy()
        self.play(FadeIn(header), FadeIn(plane_label), ShowCreation(intro_astroid, run_time=2))
        self.remove(intro_astroid)
        self.add(astroid)
        self.play(FadeIn(self.receiver), FadeIn(ring), FadeIn(occulter), FadeIn(ring_label))
        self.play(FadeIn(images), FadeIn(panel), FadeIn(controls))
        self.wait()

        # Demo path: centre -> towards a cusp -> outside -> along a fold -> back.
        path = [(0.0, 0.0), (0.82, 0.0), (1.35, 0.25), (0.35, 0.35), (-0.3, 1.2), (0.35, 0.2)]
        for target in path:
            self._move_receiver_anim(target, run_time=2.0)
        # Keep the receiver fixed and let the caustic grow/shrink underneath it.
        self.sweep(self.s_j2, 0.9, run_time=2.5)
        self.sweep(self.s_zrec, 1100.0, run_time=2.5)
        self.sweep(self.s_j2, 2.2, run_time=2)
        self.sweep(self.s_zrec, 650.0, run_time=2)
        self.wait()

    # --- interaction --------------------------------------------------------

    @property
    def uv(self) -> tuple:
        return self.view.plane_coords(self.receiver.get_center())

    def _clamp_uv(self, u: float, v: float) -> tuple:
        h = self.plane_half - 0.05
        return float(np.clip(u, -h, h)), float(np.clip(v, -h, h))

    def _on_drag(self, _mob, event_data) -> bool:
        u, v = self._clamp_uv(*self.view.plane_coords(event_data["point"]))
        self.receiver.move_to(self.view.plane_point(u, v))
        return False

    def _move_receiver_anim(self, target_uv, run_time=2.0):
        start = np.array(self.uv)
        end = np.array(target_uv)

        def update(mob, alpha):
            u, v = start + (end - start) * alpha
            mob.move_to(self.view.plane_point(u, v))

        self.play(UpdateFromAlphaFunc(self.receiver, update), run_time=run_time, rate_func=smooth)

    # --- builders -------------------------------------------------------------

    @property
    def scale(self) -> float:
        """Current astroid semi-width in reference units."""
        return sglm.caustic_scale(self.s_j2.get_value() * 1e-7, self.s_zrec.get_value())

    def _state(self):
        u, v = self.uv
        k = self.scale
        return sglm.einstein_cross_state(u / k, v / k, z_rec_au=self.s_zrec.get_value(),
                                         j2=self.s_j2.get_value() * 1e-7)

    def build_images(self) -> Group:
        st = self._state()
        view = self.view
        group = Group()
        # Azimuthal brightness profile drawn as a halo around the ring.
        phi = np.append(st["phi_grid"], st["phi_grid"][0])
        prof = np.append(st["ring_profile"], st["ring_profile"][0])
        halo = VMobject().set_points_as_corners(
            [view.ring_point(p, 1.0 + 0.28 * i) for p, i in zip(phi, prof)]
        )
        halo.set_stroke(FOCAL_COLOR, 2, opacity=0.7)
        group.add(halo)
        for ang, inten in zip(st["image_angles_rad"], st["image_intensities"]):
            pos = view.ring_point(ang)
            group.add(GlowDot(pos, radius=0.25 + 0.45 * inten, color=YELLOW, glow_factor=2.5))
            group.add(Dot(pos, radius=0.05 + 0.04 * inten, fill_color=WHITE))
            # Matching spoke in the receiver plane: image azimuth seen from the receiver.
            r0 = self.receiver.get_center()
            spoke = Line(r0, r0 + 0.55 * np.array([np.cos(ang), np.sin(ang), 0.0]))
            spoke.set_stroke(YELLOW, 2, opacity=0.4 + 0.6 * inten)
            group.add(spoke)
        return group

    def build_panel(self) -> VGroup:
        st = self._state()
        names = {
            "inside": ("inside -> Einstein cross", FOCAL_COLOR),
            "cusp_boundary": ("on caustic: images merge", RED),
            "outside": ("outside -> 2 images", TEAL_B),
            "unperturbed": ("no oblateness: full ring", WHITE),
        }
        regime = names.get(st["regime"], (st["regime"], WHITE))
        a_m = st["a_caustic_m"]
        a_txt = f"{a_m / 1e3:,.0f} km" if a_m >= 1e4 else f"{a_m:,.1f} m"
        u, v = self.uv
        k = self.scale
        lines = [
            regime,
            (f"images on ring:  {st['num_images']}", WHITE),
            (f"|x0/a|^(2/3)+|y0/a|^(2/3) = {st['astroid_val']:.2f}", GREY_A),
            (f"receiver (x0,y0) = ({u / k:+.2f},{v / k:+.2f}) a", GREY_A),
            (f"semi-width  a = {a_txt}", GREY_B),
        ]
        panel = self.info_panel(lines, corner=UL, font_size=17)
        # Centre the panel in the gap between the receiver plane and the ring.
        left = self.view.plane_point(self.plane_half, 0)[0]
        right = self.view.ring_center[0] - self.view.ring_radius * 1.3
        panel.move_to(np.array([0.5 * (left + right), self.view.center[1], 0.0]))
        return panel


# ---------------------------------------------------------------------------
# 3. Wave optics PSF
# ---------------------------------------------------------------------------


class WavePSFExplorer(SGLScene):
    """
    In wave optics the focal line is not a geometric line but a diffraction
    pattern: the PSF is ``J_0^2(k theta_E rho)``. Its core is centimetres wide,
    so a metre-class telescope sees a huge gain ``mu_max = 4 pi^2 R_s / lambda``
    but also blends light from many PSF rings.

    Controls: wavelength and receiver distance.
    """

    rho_max_cm = 30.0

    def construct(self):
        header = self.title("Wave optics on the focal line", "the point-spread function  I(ρ) ∝ J₀²(k θ_E ρ)")

        self.s_lam = LabeledSlider("Wavelength  λ [µm]", 1.0, 0.3, 2.5, 0.02, "{:.2f}", color=TEAL)
        self.s_zrec = LabeledSlider("Receiver  z_rec [AU]", 650.0, 550.0, 2000.0, 10.0, "{:.0f}", color=YELLOW)
        controls = Group(self.s_lam, self.s_zrec).arrange(RIGHT, buff=1.2).to_edge(DOWN, buff=0.35)

        self.axes = Axes(
            x_range=(0, self.rho_max_cm, 5), y_range=(0, 1.0, 0.25),
            width=7.2, height=3.9,
            axis_config=dict(stroke_color=GREY_B, stroke_width=1.5, include_tip=False),
        )
        self.axes.move_to(np.array([-2.2, 0.15, 0.0]))
        self.axes.x_axis.add_numbers(list(range(5, int(self.rho_max_cm) + 1, 5)),
                                     num_decimal_places=0, font_size=18)
        self.axes.y_axis.add_numbers([0.25, 0.5, 0.75, 1.0], num_decimal_places=2, font_size=18)
        x_lab = Text("radial offset ρ [cm]", font_size=18, color=GREY_B)
        x_lab.next_to(self.axes.x_axis, DOWN, buff=0.4)
        y_lab = Text("I / I_max", font_size=18, color=GREY_B)
        y_lab.next_to(self.axes.y_axis, UP, buff=0.12)

        self.detector_center = np.array([4.4, 0.35, 0.0])
        self.detector_radius = 2.0
        frame = Circle(radius=self.detector_radius, stroke_color=GREY_C, stroke_width=1.5)
        frame.move_to(self.detector_center)
        det_lab = Text(f"transverse plane  (radius {self.rho_max_cm:.0f} cm)", font_size=18, color=GREY_B)
        det_lab.next_to(frame, UP, buff=0.15)

        state = lambda: (round(self.s_lam.get_value(), 3), round(self.s_zrec.get_value(), 1))
        curve = Reactive(state, self.build_curve)
        image = Reactive(state, self.build_detector)
        panel = Reactive(state, self.build_panel)

        self.play(FadeIn(header), FadeIn(self.axes), FadeIn(x_lab), FadeIn(y_lab))
        intro_curve = curve[0].copy()
        self.play(ShowCreation(intro_curve), run_time=2)
        self.remove(intro_curve)
        self.add(curve)
        self.play(FadeIn(image), FadeIn(frame), FadeIn(det_lab), FadeIn(panel), FadeIn(controls))
        self.wait()
        self.sweep(self.s_lam, 2.2, run_time=3)
        self.sweep(self.s_lam, 0.5, run_time=3)
        self.sweep(self.s_lam, 1.0, run_time=2)
        self.sweep(self.s_zrec, 1800.0, run_time=3)
        self.sweep(self.s_zrec, 650.0, run_time=2)
        self.wait()

    def _psf(self):
        lam_m = self.s_lam.get_value() * 1e-6
        z = self.s_zrec.get_value()
        return sglm.psf_curve(z, lam_m, self.rho_max_cm / 100.0, num=700), lam_m, z

    def build_curve(self) -> VGroup:
        psf, lam_m, z = self._psf()
        pts = [self.axes.c2p(r * 100.0, i) for r, i in zip(psf["rho_m"], psf["intensity"])]
        graph = VMobject().set_points_as_corners(pts).set_stroke(FOCAL_COLOR, 3)
        rho0 = sglm.psf_first_zero_m(z, lam_m) * 100.0
        group = VGroup(graph)
        if rho0 < self.rho_max_cm:
            mark = DashedLine(self.axes.c2p(rho0, 0), self.axes.c2p(rho0, 0.9),
                              stroke_width=1.5, color=TEAL)
            lab = Text(f"first dark ring {rho0:.1f} cm", font_size=18, color=TEAL)
            lab.next_to(mark, UP, buff=0.08).shift(0.6 * RIGHT)
            group.add(mark, lab)
        return group

    def build_detector(self) -> VGroup:
        psf, _, _ = self._psf()
        n = 90
        edges = np.linspace(0.0, 1.0, n + 1)
        rho_frac = psf["rho_m"] / psf["rho_m"][-1]
        group = VGroup()
        for k in range(n):
            mid = 0.5 * (edges[k] + edges[k + 1])
            inten = float(np.interp(mid, rho_frac, psf["intensity"]))
            # Gamma < 1 so the faint side lobes remain visible.
            alpha = inten ** 0.45
            ann = Annulus(inner_radius=edges[k] * self.detector_radius,
                          outer_radius=edges[k + 1] * self.detector_radius,
                          fill_color=YELLOW, fill_opacity=alpha)
            ann.move_to(self.detector_center)
            group.add(ann)
        return group

    def build_panel(self) -> VGroup:
        psf, lam_m, z = self._psf()
        rho0 = sglm.psf_first_zero_m(z, lam_m)
        mu = sglm.focal_line_readout(1.0, 1.0, z, wavelength_m=lam_m)["mu_max"]
        lines = [
            (f"peak gain  μ_max = {mu:.2e}", FOCAL_COLOR),
            (f"PSF core radius = {rho0 * 100:.2f} cm", TEAL),
            (f"a 1 m telescope spans ~{0.5 / rho0:.0f}x the core radius", GREY_A),
        ]
        panel = self.info_panel(lines, corner=UR, font_size=18)
        panel.next_to(self.detector_center + self.detector_radius * DOWN, DOWN, buff=0.25)
        return panel
