# pyright: reportMissingImports=false
"""Render a legible schematic of recirculation in a HIAD toroid valley.

The old figure placed in the thesis was a civil-engineering building-wake
illustration whose caption claimed a toroidal-ring inset that the image did
not contain. This script draws the geometry the caption actually describes:
two toroid crests, a bridging shear layer, a primary vortex inside the
valley and a secondary corner vortex outside the solid surface.
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, FancyArrowPatch

OUT = Path(__file__).with_name("recirculation_hiad_valley.png")

fig, ax = plt.subplots(figsize=(12, 5.6), dpi=150)
ax.set_xlim(-0.4, 12.4)
ax.set_ylim(-0.6, 5.8)
ax.set_aspect("equal")
ax.axis("off")

# Two toroid cross-sections; their crests define the shear-layer ends.
for x in (2.4, 9.4):
    ax.add_patch(Circle((x, 1.2), 1.4, facecolor="#d8dee9", edgecolor="#334155", lw=2.2))
    ax.add_patch(Circle((x, 1.2), 0.14, facecolor="#94a3b8", edgecolor="none"))
    ax.text(x, 2.95, "toroid crest", ha="center", va="bottom", fontsize=13, color="#334155")

# Valley floor meets both toroid surfaces.
ax.plot([3.55, 8.25], [-0.12, -0.12], color="#334155", lw=3)
ax.text(5.9, -0.42, "valley floor", ha="center", va="top", fontsize=13, color="#334155")

# Freestream above the bridging shear layer.
for y in (4.85, 4.35, 3.85):
    ax.plot([-0.2, 11.9], [y, y], color="#64748b", lw=1.1, alpha=0.75)
ax.add_patch(
    FancyArrowPatch(
        (0.0, 4.35), (1.15, 4.35), arrowstyle="-|>", mutation_scale=18,
        color="#475569", lw=1.6,
    )
)
ax.text(0.55, 4.58, "freestream", ha="center", fontsize=13, color="#475569")

# The shear layer bridges the two crests, above the primary vortex.
ax.plot([3.7, 8.1], [2.6, 2.6], color="#b91c1c", lw=2.6, ls="--")
ax.text(5.9, 2.82, "bridging shear layer", ha="center", va="bottom", fontsize=14, color="#b91c1c")

# Closed-looking clockwise recirculation loop, entirely below the shear layer.
ax.add_patch(
    FancyArrowPatch(
        (5.15, 1.55), (6.65, 1.55), connectionstyle="arc3,rad=-0.95",
        arrowstyle="-|>", mutation_scale=20, color="#1d4ed8", lw=2.4,
    )
)
ax.add_patch(
    FancyArrowPatch(
        (6.65, 1.35), (5.15, 1.35), connectionstyle="arc3,rad=-0.95",
        arrowstyle="-|>", mutation_scale=20, color="#1d4ed8", lw=2.4,
    )
)
ax.text(5.9, 0.42, "primary vortex", ha="center", fontsize=14, color="#1d4ed8")

# Small counter-rotating eddy in the downstream corner, outside the solid.
ax.add_patch(
    FancyArrowPatch(
        (7.35, 0.75), (7.75, 0.75), connectionstyle="arc3,rad=1.2",
        arrowstyle="-|>", mutation_scale=15, color="#047857", lw=2.0,
    )
)
ax.add_patch(
    FancyArrowPatch(
        (7.75, 0.65), (7.35, 0.65), connectionstyle="arc3,rad=1.2",
        arrowstyle="-|>", mutation_scale=15, color="#047857", lw=2.0,
    )
)
ax.text(7.05, 0.15, "secondary corner vortex", ha="right", fontsize=12, color="#047857")

ax.set_title("Recirculation in a HIAD toroid valley (schematic cross-section)", fontsize=16, pad=12)
fig.savefig(OUT, bbox_inches="tight", facecolor="white")
print(f"wrote {OUT} ({OUT.stat().st_size} bytes)")
