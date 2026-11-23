# Contributing to sgl-sim

Thank you for your interest in contributing to **`sgl-sim`**! 

`sgl-sim` is an open-source, peer-reviewed scientific Python library for gravitational lens telescopes and mission design, developed in compliance with **Astropy** ecosystem conventions and **Journal of Open Source Software (JOSS)** guidelines.

---

## Code of Conduct

We are committed to providing a welcoming, inclusive, and harassment-free environment for all contributors. Please treat fellow researchers, developers, and students with respect and kindness.

---

## How to Contribute

### 1. Reporting Bugs
- Check the [GitHub Issues](https://github.com/teom275/sgl-sim/issues) to ensure the issue has not already been reported.
- If creating a new issue, include:
  - Clear description of the unexpected behavior.
  - Minimal, reproducible example (Python code snippet).
  - Expected versus actual mathematical/physical result.
  - OS version and Python version (`python --version`).

### 2. Suggesting Features & Scientific Extensions
We welcome proposals for new astrophysical models, including:
- Rotating Kerr black hole null geodesics and framing-dragging effects.
- Higher-order stellar multipole moments ($J_4, J_6$).
- Spectral band integration and chromatic PSF chromaticity.
- Alternative formation flying control strategies and ion engine propulsion profiles.

Please open an issue labelled `enhancement` describing the physics, governing equations, and references to published literature.

---

## Development Workflow

### Setting Up a Development Environment

1. Fork the repository on GitHub and clone your fork:
   ```bash
   git clone https://github.com/<your-username>/sgl-sim.git
   cd sgl-sim
   ```

2. Create and activate a clean Python virtual environment:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\Activate.ps1
   ```

3. Install `sgl-sim` in editable mode with development/test dependencies:
   ```bash
   pip install -e ".[test]"
   ```

### Code Standards & Conventions

- **Python Version:** Compatible with Python 3.9, 3.10, 3.11, and 3.12.
- **Physical Quantities:** Functions should accept both raw floats (assumed SI) and `astropy.units.Quantity` objects.
- **Documentation & Docstrings:** Follow the NumPy docstring standard (`Parameters`, `Returns`, mathematical equations in LaTeX).
- **Type Annotations:** Use Python typing annotations (`typing.Union`, `typing.Dict`, `typing.Optional`, etc.).
- **Code Style:** Follow PEP 8 guidelines.

### Running Tests

Before submitting a pull request, verify that all unit tests pass:

```bash
pytest -v tests/
```

To run tests with coverage reporting:

```bash
pytest --cov=sgl_sim --cov-report=term-missing tests/
```

Ensure new features include corresponding test cases in `tests/`.

### Regenerating Publication Figures

If you modify plotting styles or trajectory models, verify that the figure generation script runs without warnings:

```bash
python scripts/generate_paper_figures.py
```

---

## Pull Request Guidelines

1. Create a feature branch: `git checkout -b feature/my-new-feature`.
2. Commit your changes with clear, descriptive commit messages.
3. Push to your branch: `git push origin feature/my-new-feature`.
4. Open a Pull Request against the `main` branch of `teom275/sgl-sim`.
5. Describe the scientific motivation and test results in the PR description.
