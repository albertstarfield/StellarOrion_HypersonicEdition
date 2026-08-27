#!/usr/bin/env python3
"""Generate software pipeline figure showing StellarOrion engine architecture."""

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import numpy as np

fig, ax = plt.subplots(1, 1, figsize=(16, 8))
ax.set_xlim(0, 16)
ax.set_ylim(0, 8)
ax.axis('off')

# Colors
colors = {
    'input': '#E3F2FD',     # Light blue
    'core': '#1565C0',       # Dark blue
    'solver': '#2E7D32',     # Green
    'ml': '#E65100',         # Orange
    'output': '#4A148C',     # Purple
    'arrow': '#37474F',      # Dark gray
    'border': '#BDBDBD',
}

def draw_box(ax, x, y, w, h, text, color, fontsize=9, bold=False, border_color=None):
    bc = border_color or color
    box = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.08",
                          facecolor=color, edgecolor=bc, linewidth=1.5, alpha=0.92)
    ax.add_patch(box)
    weight = 'bold' if bold else 'normal'
    ax.text(x + w/2, y + h/2, text, ha='center', va='center',
            fontsize=fontsize, color='white' if color not in ['#E3F2FD'] else '#212121',
            fontweight=weight, wrap=True)

def draw_arrow(ax, x1, y1, x2, y2, color='#37474F', style='->', lw=2):
    ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle=style, color=color, lw=lw))

# Title
ax.text(8, 7.7, 'StellarOrion Engine — Software Pipeline Architecture', ha='center', va='center',
        fontsize=14, fontweight='bold', color='#212121')

# ── INPUT LAYER ──
ax.text(1.5, 6.8, 'INPUT', ha='center', va='center', fontsize=9, color='#757575', fontweight='bold')
draw_box(ax, 0.3, 5.8, 2.5, 0.9, 'CadQuery\nGeometry\nSTL export', colors['input'], fontsize=8, border_color=colors['border'])
draw_box(ax, 0.3, 4.5, 2.5, 0.9, 'Flight\nConditions\nV, T∞, ρ∞', colors['input'], fontsize=8, border_color=colors['border'])
draw_box(ax, 0.3, 3.2, 2.5, 0.9, 'Design\nVariables\nd, θ, n_tor, r_n', colors['input'], fontsize=8, border_color=colors['border'])

# ── CORE ENGINE ──
ax.text(5.0, 6.8, 'CORE ENGINE', ha='center', va='center', fontsize=9, color='#757575', fontweight='bold')
draw_box(ax, 3.5, 4.8, 3.0, 1.2, 'StellarOrionEngine\nMach5Up.py\n(main orchestrator)', colors['core'], fontsize=9, bold=True)

# ── SOLVERS ──
ax.text(9.5, 6.8, 'SOLVERS', ha='center', va='center', fontsize=9, color='#757575', fontweight='bold')
draw_box(ax, 7.5, 5.2, 2.8, 1.0, 'SPARTA\nDSMC Solver\nDocker container', colors['solver'], fontsize=8)
draw_box(ax, 7.5, 3.8, 2.8, 1.0, 'OpenFOAM\nlaplacianFoam\n(solid thermal)', colors['solver'], fontsize=8)

# ── ML MODELS ──
ax.text(12.5, 6.8, 'ML MODELS', ha='center', va='center', fontsize=9, color='#757575', fontweight='bold')
draw_box(ax, 11.0, 5.2, 2.5, 1.0, 'PINN\nDeepXDE\n(FNN 5×128)', colors['ml'], fontsize=8)
draw_box(ax, 11.0, 3.8, 2.5, 1.0, 'MoP Surrogate\nPyTorch MLP\n(3-layer, 8 output)', colors['ml'], fontsize=8)

# ── OUTPUT ──
ax.text(15.0, 6.8, 'OUTPUT', ha='center', va='center', fontsize=9, color='#757575', fontweight='bold')
draw_box(ax, 14.2, 4.8, 1.5, 1.5, 'ParaView\nVTK/\nSTL\nRendering', colors['output'], fontsize=8)

# ── ARROWS ──
# Input → Core
draw_arrow(ax, 2.8, 6.25, 3.5, 5.7, colors['arrow'])
draw_arrow(ax, 2.8, 4.95, 3.5, 5.4, colors['arrow'])
draw_arrow(ax, 2.8, 3.65, 3.5, 5.1, colors['arrow'])

# Core → SPARTA
draw_arrow(ax, 6.5, 5.6, 7.5, 5.7, colors['arrow'])
# Core → OpenFOAM
draw_arrow(ax, 6.5, 5.2, 7.5, 4.3, colors['arrow'])

# SPARTA → PINN (data flow)
draw_arrow(ax, 10.3, 5.7, 11.0, 5.7, colors['arrow'], lw=2.5)
ax.text(10.65, 5.95, 'VTK data', fontsize=7, color='#37474F', ha='center', style='italic')

# SPARTA → MoP (surface data)
draw_arrow(ax, 10.3, 5.3, 11.0, 4.3, colors['arrow'], lw=2.5)
ax.text(10.65, 4.6, 'surface data', fontsize=7, color='#37474F', ha='center', style='italic')

# PINN → MoP (refined data)
draw_arrow(ax, 12.25, 5.2, 12.25, 4.8, colors['arrow'], lw=2, style='->')
ax.text(12.5, 5.0, 'refined', fontsize=7, color='#E65100', ha='left', style='italic')

# MoP → Core (GA feedback)
draw_arrow(ax, 11.0, 4.1, 6.5, 4.9, colors['arrow'], lw=2, style='->')
ax.text(8.5, 4.2, 'GA optimization\nfeedback loop', fontsize=7, color='#E65100', ha='center', style='italic')

# Core → ParaView
draw_arrow(ax, 6.5, 5.3, 14.2, 5.5, colors['arrow'], lw=1.5, style='->')
ax.text(10.0, 6.2, 'VTK/STL files', fontsize=7, color='#37474F', ha='center', style='italic')

# ── LEGEND ──
legend_elements = [
    mpatches.Patch(facecolor=colors['input'], edgecolor=colors['border'], label='Input (Geometry, Conditions)'),
    mpatches.Patch(facecolor=colors['core'], label='Core Engine (Orchestrator)'),
    mpatches.Patch(facecolor=colors['solver'], label='Physics Solvers (SPARTA, OpenFOAM)'),
    mpatches.Patch(facecolor=colors['ml'], label='ML Models (PINN, MoP)'),
    mpatches.Patch(facecolor=colors['output'], label='Visualization (ParaView)'),
]
ax.legend(handles=legend_elements, loc='lower center', ncol=5, fontsize=7,
          frameon=True, fancybox=True, shadow=True, bbox_to_anchor=(0.5, -0.02))

plt.tight_layout()
plt.savefig('/Users/albertstarfield/Documents/NeoSchool14/for_someone/StellarOrion_HypersonicEdition/ProgressReport/CurrentThesisFinalReport/figures/software_pipeline.png',
            dpi=200, bbox_inches='tight', facecolor='white')
print("Saved: figures/software_pipeline.png")
