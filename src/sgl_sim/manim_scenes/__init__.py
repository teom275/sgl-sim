"""
Interactive ManimGL (3Blue1Brown ``manim``) scenes for sgl-sim.

This sub-package is **optional**: it is not imported by ``sgl_sim`` itself, so
the core library never requires ManimGL. Install the extra and launch a scene::

    pip install -e ".[manim]"
    manimgl src/sgl_sim/manim_scenes/sgl_interactive.py SolarLensFocalLine

Modules
-------
model
    Pure-NumPy geometry that maps sgl-sim physics (deflection, focal distance,
    Einstein ring, astroid caustic, Bessel PSF) into manim scene coordinates.
    It has no ManimGL dependency and is covered by the regular test-suite.
sgl_interactive
    The ManimGL scenes themselves (sliders, draggable receiver, narrated tour).
"""
