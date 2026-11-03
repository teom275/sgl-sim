"""
Tests for the ManimGL scene geometry (sgl_sim.manim_scenes.model).

These run without ManimGL installed: the model module is pure NumPy.
"""

import numpy as np
import pytest

from sgl_sim.manim_scenes import model as sglm


def test_focal_distance_matches_z_min_for_grazing_ray():
    # A ray grazing the solar limb focuses at z_min ~ 547.8 AU.
    assert sglm.focal_distance_au(1.0, 1.0) == pytest.approx(547.8, rel=2e-3)
    # z scales as b^2 / M.
    assert sglm.focal_distance_au(2.0, 1.0) == pytest.approx(4 * 547.8, rel=2e-3)
    assert sglm.focal_distance_au(1.0, 2.0) == pytest.approx(547.8 / 2, rel=2e-3)


def test_ring_impact_parameter_inverts_focal_distance():
    for z in (600.0, 1000.0, 1800.0):
        b = sglm.ring_impact_parameter_rsun(z, 1.0)
        assert sglm.focal_distance_au(b, 1.0) == pytest.approx(z, rel=1e-9)


def test_lens_ray_paths_cross_axis_at_focal_distance():
    view = sglm.FocalLineView()
    bs = [0.5, -0.5, 1.2, -1.2, 2.0]
    paths = sglm.lens_ray_paths(1.0, 1.0, bs, view)
    assert [p.blocked for p in paths] == [True, True, False, False, False]

    for p in paths:
        start = p.points[0]
        assert start[0] == pytest.approx(view.x_left)
        assert start[1] == pytest.approx(view.y_of_b(p.b_rsun))
        if p.blocked:
            # Occulted rays stop on the stellar limb, left of the lens plane.
            end = p.points[-1]
            r = view.y_per_rsun
            assert np.hypot(end[0] - view.x_lens, end[1] - view.y_axis) == pytest.approx(r)
            continue
        # The post-lens segment, extended, must hit the axis at x_of_z(z(b)).
        (x1, y1, _), (x2, y2, _) = p.points[1], p.points[2]
        x_cross = x1 + (view.y_axis - y1) * (x2 - x1) / (y2 - y1)
        assert x_cross == pytest.approx(view.x_of_z(p.z_focus_au))
        assert p.z_focus_au == pytest.approx(sglm.focal_distance_au(abs(p.b_rsun), 1.0))


def test_lens_ray_paths_stay_inside_drawing_area():
    view = sglm.FocalLineView(y_limit=2.0)
    paths = sglm.lens_ray_paths(4.0, 0.3, np.linspace(-2.0, 2.0, 21), view)
    for p in paths:
        assert np.all(p.points[:, 0] <= view.x_right + 1e-9)
        assert np.all(np.abs(p.points[:, 1] - view.y_axis) <= view.y_limit + 1e-9)


def test_focal_line_readout_flags_receivers_inside_z_min():
    inside = sglm.focal_line_readout(1.0, 1.0, 400.0)
    beyond = sglm.focal_line_readout(1.0, 1.0, 650.0)
    assert not inside["in_focus"]
    assert beyond["in_focus"]
    assert beyond["z_min_au"] == pytest.approx(547.8, rel=2e-3)
    assert beyond["mu_max"] == pytest.approx(1.166e11, rel=1e-2)


def test_caustic_view_roundtrip():
    view = sglm.CausticView()
    for u, v in [(0.0, 0.0), (0.4, -1.1), (-1.5, 0.7)]:
        assert sglm.CausticView.plane_coords(view, view.plane_point(u, v)) == pytest.approx((u, v))


def test_caustic_scale_reference_and_scaling():
    assert sglm.caustic_scale(2.2e-7, 650.0) == pytest.approx(1.0)
    # a ~ J2 * z / sqrt(z) = J2 * sqrt(z)
    assert sglm.caustic_scale(4.4e-7, 650.0) == pytest.approx(2.0)
    assert sglm.caustic_scale(2.2e-7, 4 * 650.0) == pytest.approx(2.0)


def test_astroid_curve_is_closed_and_bounded():
    view = sglm.CausticView()
    pts = sglm.astroid_curve(view, scale=1.3)
    assert np.allclose(pts[0], pts[-1])
    rel = (pts[:, :2] - np.array(view.center)) / (view.units_per_a * 1.3)
    assert np.all(np.abs(rel) <= 1.0 + 1e-9)


@pytest.mark.parametrize(
    "uv, regime, n_images",
    [((0.0, 0.0), "inside", 4), ((0.3, 0.2), "inside", 4), ((1.5, 0.4), "outside", 2)],
)
def test_einstein_cross_state(uv, regime, n_images):
    st = sglm.einstein_cross_state(*uv)
    assert st["regime"] == regime
    assert st["num_images"] == n_images
    assert len(st["image_angles_rad"]) == n_images
    assert max(st["image_intensities"]) == pytest.approx(1.0)
    assert st["ring_profile"].shape == st["phi_grid"].shape


def test_psf_first_zero_is_a_zero_of_the_curve():
    rho0 = sglm.psf_first_zero_m(650.0, 1e-6)
    assert rho0 == pytest.approx(0.049, rel=0.02)  # ~5 cm core at 650 AU, 1 um
    curve = sglm.psf_curve(650.0, 1e-6, rho_max_m=0.3, num=3001)
    assert curve["intensity"][0] == pytest.approx(1.0)
    idx = np.argmin(np.abs(curve["rho_m"] - rho0))
    assert curve["intensity"][idx] < 1e-4
    # Core radius scales as lambda * sqrt(z).
    assert sglm.psf_first_zero_m(4 * 650.0, 2e-6) == pytest.approx(4 * rho0)
