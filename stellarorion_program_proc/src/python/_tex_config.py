#!/usr/bin/env python3
"""TeX font configuration for matplotlib — conditional on LaTeX availability.

AXIOMS:
  1. LaTeX provides publication-quality fonts (Computer Modern, Latin Modern)
  2. If pdflatex is not installed, fall back to matplotlib defaults
  3. Configuration is applied once per process via setup_tex_fonts()

[Citation: matplotlib usetex — https://matplotlib.org/stable/gallery/text_labels_and_annotations/usetex_fontselection.html]
[Citation: matplotlib rcParams — https://matplotlib.org/stable/api/matplotlibrc_params.html]
"""

import shutil
import os

# Module-level state: initialized once
_tex_available = None


def setup_tex_fonts():
    """Configure matplotlib to use TeX/LaTeX fonts if available on the system.

    Checks for pdflatex via shutil.which(). If found, enables:
      - text.usetex = True
      - font.family = serif
      - font.serif = Latin Modern Roman (via lmodern package)
      - mathtext.fontset = cm (Computer Modern math)
      - figure.dpi = 150
      - savefig.dpi = 200

    If pdflatex is not found, prints a warning and leaves defaults unchanged.

    Returns: True if TeX fonts are active, False otherwise.

    [Citation: matplotlib usetex tutorial — https://matplotlib.org/stable/gallery/text_labels_and_annotations/usetex_demo.html]
    [Citation: lmodern package — https://ctan.org/pkg/lmodern]
    """
    global _tex_available

    if _tex_available is not None:
        return _tex_available

    if not shutil.which("pdflatex"):
        print("[tex_config] pdflatex not found — using matplotlib default fonts")
        _tex_available = False
        return False

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        plt.rcParams.update({
            # Enable LaTeX text rendering
            "text.usetex": True,
            "text.latex.preamble": r"\usepackage{lmodern}\usepackage{amsmath}\usepackage{amssymb}",

            # Force serif font family (Latin Modern via lmodern)
            "font.family": "serif",
            "font.serif": ["Latin Modern Roman", "Computer Modern Roman", "DejaVu Serif"],
            "font.sans-serif": ["Latin Modern Sans", "Computer Modern Sans", "DejaVu Sans"],
            "font.monospace": ["Latin Modern Mono", "Computer Modern Mono", "DejaVu Sans Mono"],

            # Math text — Computer Modern via LaTeX
            "mathtext.fontset": "cm",
            "mathtext.rm": "serif",
            "mathtext.it": "serif:italic",
            "mathtext.bf": "serif:bold",

            # Force PostScript/PDF fonts to use Type 1 (Computer Modern)
            "ps.useafm": True,
            "pdf.use14corefonts": True,

            # Figure quality
            "figure.dpi": 150,
            "savefig.dpi": 200,
            "savefig.bbox": "tight",

            # Font sizes — academic standard
            "font.size": 11,
            "axes.titlesize": 13,
            "axes.labelsize": 12,
            "xtick.labelsize": 10,
            "ytick.labelsize": 10,
            "legend.fontsize": 10,

            # Axes
            "axes.linewidth": 0.8,
            "grid.linewidth": 0.5,
            "lines.linewidth": 1.5,
        })

        # Do NOT delete font cache — that triggers rebuild per worker process.
        # Instead, let matplotlib use whatever cache exists. First call builds it,
        # subsequent calls (including in forked workers) reuse it.

        print("[tex_config] TeX fonts ENABLED (pdflatex found)")
        _tex_available = True
        return True

    except Exception as e:
        print(f"[tex_config] Failed to configure TeX fonts: {e}")
        print("[tex_config] Falling back to matplotlib defaults")
        _tex_available = False
        return False


def tex_available():
    """Return whether TeX fonts were successfully configured.

    Returns: True if TeX fonts are active, False otherwise.
    """
    global _tex_available
    if _tex_available is None:
        setup_tex_fonts()
    return _tex_available
