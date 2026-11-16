#!/usr/bin/env python3
"""Generate neutral placeholder plots for the Week 16 deck skeleton.

AXIOM: The deck's text budget requires each frame to be dominated by an
       image plot. A skeleton that ships empty frames would violate the
       very rule it declares, so real placeholder graphics are generated.
THEORY: Each placeholder is an empty-but-labelled axis frame, so the
       skeleton demonstrates layout and scale without asserting any result.
APPLICATION: Called once during skeleton build; regenerated when the frame
       list changes.
EXPECTED OUTPUT: figures/placeholder_*.png, one per content frame.
RAISES: RuntimeError if matplotlib is unavailable (never writes a partial
        file set silently).
Citation: matplotlib -- https://matplotlib.org/
"""
from __future__ import annotations

import pathlib
import sys

# Frame labels mirror main.tex's six implementation frames plus the problem
# frame, so a placeholder can be matched to its frame by name alone.
FRAMES: dict[str, str] = {
    "problem": "Previous Problem: Sampling and MoP",
    "bo": "Bayesian Optimization",
    "kriging": "Kriging Denoising",
    "validation": "Validation Run",
    "heatflux": "Heat Flux Definition",
    "topology": "Optimization Result: Topology and Performance",
    "plots": "Bayesian Plot Optimization",
}

# 16:9 at 150 dpi. Matches the deck's aspectratio=169 so the reserved plot
# box is filled edge to edge with no letterboxing.
FIGSIZE: tuple[float, float] = (9.6, 5.4)
DPI: int = 150


def main() -> int:
    """Write one placeholder PNG per frame.

    Returns 0 on success, 1 if matplotlib cannot be imported.
    """
    try:
        import matplotlib
        matplotlib.use("Agg")  # headless: no display required on this node
        import matplotlib.pyplot as plt
    except ImportError as exc:
        print(f"FATAL: matplotlib unavailable: {exc}", file=sys.stderr)
        return 1

    out = pathlib.Path(__file__).resolve().parent / "figures"
    out.mkdir(parents=True, exist_ok=True)

    for slug, label in FRAMES.items():
        fig, ax = plt.subplots(figsize=FIGSIZE, dpi=DPI)
        # Empty grid: axes and frame drawn, no data. Any visible curve here
        # would be an unverified claim, which is precisely what this
        # project's standing rules forbid.
        ax.grid(True, linestyle=":", linewidth=0.6, alpha=0.5)
        ax.set_axisbelow(True)
        ax.set_xlabel("x", fontsize=11)
        ax.set_ylabel("y", fontsize=11)
        ax.set_title(f"PLACEHOLDER: {label}", fontsize=12, fontweight="bold")
        ax.text(
            0.5, 0.5,
            "plot pending",
            transform=ax.transAxes,
            ha="center", va="center",
            fontsize=20, fontweight="bold", alpha=0.35,
        )
        path = out / f"placeholder_{slug}.png"
        fig.tight_layout()
        fig.savefig(path)
        plt.close(fig)
        print(f"wrote {path.name}")

    print(f"\n{len(FRAMES)} placeholders written to {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
