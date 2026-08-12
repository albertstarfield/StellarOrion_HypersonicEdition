#!/usr/bin/env python3
"""Generate methodology derivation figure showing axioms → equations → implementation chain."""

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import numpy as np

fig, ax = plt.subplots(1, 1, figsize=(14, 10))
ax.set_xlim(0, 14)
ax.set_ylim(0, 10)
ax.axis('off')

# Colors
colors = {
    'axiom': '#2196F3',      # Blue
    'equation': '#FF9800',    # Orange
    'method': '#4CAF50',      # Green
    'impl': '#9C27B0',        # Purple
    'arrow': '#607D8B',       # Gray
    'bg': '#FAFAFA'
}

def draw_box(ax, x, y, w, h, text, color, fontsize=9, bold=False):
    box = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.1",
                          facecolor=color, edgecolor='white', linewidth=2, alpha=0.9)
    ax.add_patch(box)
    weight = 'bold' if bold else 'normal'
    ax.text(x + w/2, y + h/2, text, ha='center', va='center',
            fontsize=fontsize, color='white', fontweight=weight, wrap=True)

def draw_arrow(ax, x1, y1, x2, y2, color='#607D8B'):
    ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle='->', color=color, lw=2, connectionstyle='arc3,rad=0'))

# Title
ax.text(7, 9.7, 'Methodology Derivation from First Principles', ha='center', va='center',
        fontsize=16, fontweight='bold', color='#212121')

# Layer labels
ax.text(0.5, 8.5, 'LAYER 1\nAXIOMS', ha='center', va='center', fontsize=8, color='#757575',
        fontweight='bold', style='italic')
ax.text(0.5, 6.5, 'LAYER 2\nEQUATIONS', ha='center', va='center', fontsize=8, color='#757575',
        fontweight='bold', style='italic')
ax.text(0.5, 4.5, 'LAYER 3\nMETHODS', ha='center', va='center', fontsize=8, color='#757575',
        fontweight='bold', style='italic')
ax.text(0.5, 2.0, 'LAYER 4\nIMPLEMENTATION', ha='center', va='center', fontsize=8, color='#757575',
        fontweight='bold', style='italic')

# ── LAYER 1: AXIOMS ──
axioms = [
    (1.5, 8.0, 2.5, 0.8, 'A1: Conservation\n(Mass, Momentum,\nEnergy)', colors['axiom']),
    (4.5, 8.0, 2.5, 0.8, 'A2: Molecular Chaos\n(Stosszahlansatz)', colors['axiom']),
    (7.5, 8.0, 2.5, 0.8, 'A3: Continuum\nHypothesis\n(valid for Kn<0.01)', colors['axiom']),
    (10.5, 8.0, 2.5, 0.8, 'A4: Equilibrium\nDistribution\n(MB statistics)', colors['axiom']),
]
for x, y, w, h, t, c in axioms:
    draw_box(ax, x, y, w, h, t, c, fontsize=8, bold=True)

# ── LAYER 2: EQUATIONS ──
equations = [
    (1.5, 5.8, 3.0, 0.9, 'Boltzmann Eq.\n∂f/∂t + v·∇f = Q(f,f)', colors['equation']),
    (5.0, 5.8, 3.0, 0.9, 'Navier-Stokes\nρ(∂u/∂t + u·∇u) =\n-∇p + ∇·τ', colors['equation']),
    (8.5, 5.8, 2.8, 0.9, 'Sutton-Graves\nq̇ = k√(ρ∞/Rn)·V∞³', colors['equation']),
    (11.8, 5.8, 2.0, 0.9, 'Conservation\nLaws', colors['equation']),
]
for x, y, w, h, t, c in equations:
    draw_box(ax, x, y, w, h, t, c, fontsize=8)

# ── LAYER 3: METHODS ──
methods = [
    (1.5, 3.8, 2.8, 0.9, 'DSMC\n(Bird Algorithm)\nSPARTA', colors['method']),
    (4.8, 3.8, 2.8, 0.9, 'PINN\n(Physics-Informed\nNeural Network)', colors['method']),
    (8.1, 3.8, 2.8, 0.9, 'Metamodel of\nPhysics (MoP)\nSurrogate', colors['method']),
    (11.4, 3.8, 2.2, 0.9, 'Genetic\nAlgorithm\nOptimization', colors['method']),
]
for x, y, w, h, t, c in methods:
    draw_box(ax, x, y, w, h, t, c, fontsize=8)

# ── LAYER 4: IMPLEMENTATION ──
impls = [
    (1.5, 1.2, 2.5, 0.9, 'SPARTA Docker\nContainer\n5-species air', colors['impl']),
    (4.5, 1.2, 2.5, 0.9, 'DeepXDE\nPINN Library\nStage 1 + Stage 2', colors['impl']),
    (7.5, 1.2, 2.5, 0.9, 'PyTorch MoP\n3-layer MLP\nCCD sampling', colors['impl']),
    (10.5, 1.2, 2.5, 0.9, 'StellarOrion\nEngine (Python)\nmain.py orchestrator', colors['impl']),
]
for x, y, w, h, t, c in impls:
    draw_box(ax, x, y, w, h, t, c, fontsize=8)

# ── ARROWS (vertical) ──
# Axioms → Equations
for i in range(4):
    x_start = 2.75 + i * 3.0
    draw_arrow(ax, x_start, 8.0, x_start, 6.7, colors['arrow'])

# Equations → Methods
draw_arrow(ax, 3.0, 5.8, 2.9, 4.7, colors['arrow'])  # Boltzmann → DSMC
draw_arrow(ax, 6.5, 5.8, 6.2, 4.7, colors['arrow'])  # NS → PINN
draw_arrow(ax, 9.9, 5.8, 9.5, 4.7, colors['arrow'])  # Sutton-Graves → MoP
draw_arrow(ax, 12.8, 5.8, 12.5, 4.7, colors['arrow'])  # Conservation → GA

# Methods → Implementations
draw_arrow(ax, 2.9, 3.8, 2.75, 2.1, colors['arrow'])  # DSMC → SPARTA
draw_arrow(ax, 6.2, 3.8, 5.75, 2.1, colors['arrow'])  # PINN → DeepXDE
draw_arrow(ax, 9.5, 3.8, 8.75, 2.1, colors['arrow'])  # MoP → PyTorch
draw_arrow(ax, 12.5, 3.8, 11.75, 2.1, colors['arrow'])  # GA → StellarOrion

# ── CROSS-LAYER ARROWS (dashed) ──
# DSMC output feeds PINN training data
ax.annotate('', xy=(4.8, 4.25), xytext=(4.3, 4.25),
            arrowprops=dict(arrowstyle='->', color='#F44336', lw=1.5, linestyle='dashed'))
ax.text(4.55, 4.5, 'data', fontsize=7, color='#F44336', ha='center', style='italic')

# PINN output feeds MoP training
ax.annotate('', xy=(8.1, 4.25), xytext=(7.6, 4.25),
            arrowprops=dict(arrowstyle='->', color='#F44336', lw=1.5, linestyle='dashed'))
ax.text(7.85, 4.5, 'refined', fontsize=7, color='#F44336', ha='center', style='italic')

# MoP feeds GA evaluation
ax.annotate('', xy=(11.4, 4.25), xytext=(10.9, 4.25),
            arrowprops=dict(arrowstyle='->', color='#F44336', lw=1.5, linestyle='dashed'))
ax.text(11.15, 4.5, 'eval', fontsize=7, color='#F44336', ha='center', style='italic')

# Legend
legend_elements = [
    mpatches.Patch(facecolor=colors['axiom'], label='Axioms (First Principles)'),
    mpatches.Patch(facecolor=colors['equation'], label='Governing Equations'),
    mpatches.Patch(facecolor=colors['method'], label='Numerical Methods'),
    mpatches.Patch(facecolor=colors['impl'], label='Software Implementation'),
]
ax.legend(handles=legend_elements, loc='lower center', ncol=4, fontsize=8,
          frameon=True, fancybox=True, shadow=True, bbox_to_anchor=(0.5, -0.02))

plt.tight_layout()
plt.savefig('/Users/albertstarfield/Documents/NeoSchool14/for_someone/StellarOrion_HypersonicEdition/ProgressReport/CurrentThesisFinalReport/figures/methodology_derivation.png',
            dpi=200, bbox_inches='tight', facecolor='white')
print("Saved: figures/methodology_derivation.png")
