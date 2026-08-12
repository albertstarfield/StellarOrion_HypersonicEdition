#!/usr/bin/env python3
"""
Generate Governing Equations Summary Figure
Shows the chain: Boltzmann → DSMC → Navier-Stokes → Sutton-Graves → PINN → GA
With key equations at each step
"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import numpy as np
import os

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'governing_equations.png')

fig, ax = plt.subplots(figsize=(14, 8))

# Define layers: (x_center, label, equation, color)
layers = [
    (1.0, 'Kinetic\nTheory', r'$\frac{\partial f}{\partial t} + \mathbf{v}\cdot\nabla f = \int(f''f_1'' - ff_1)g\sigma d\Omega\,d\mathbf{v}_1$', '#1a5276'),
    (3.0, 'DSMC\nMethod', r'$\Delta x \leq \frac{\lambda}{3},\quad \Delta t \leq \frac{1}{\nu}$', '#2874a6'),
    (5.0, 'Navier-Stokes\nEquations', r'$\frac{\partial \rho}{\partial t} + \nabla\cdot(\rho\mathbf{u}) = 0$', '#2e86c1'),
    (7.0, 'Sutton-Graves\nCorrelation', r'$\dot{q}_s = k\sqrt{\frac{\rho_\infty}{R_N}}\,V_\infty^3$', '#148f77'),
    (9.0, 'PINN\nRefinement', r'$\mathcal{L} = \lambda_d\mathcal{L}_{data} + \lambda_{pde}\mathcal{L}_{PDE}$', '#b7950b'),
    (11.0, 'GA\nOptimization', r'$J^* = \min\left(\beta - \beta_{target}\right)^2 + \lambda\sum\max(0, g_i)$', '#922b21'),
]

# Draw each layer box
for x, label, eq, color in layers:
    # Main box
    rect = FancyBboxPatch((x - 0.8, 4.5), 1.6, 2.5,
                          boxstyle="round,pad=0.1",
                          facecolor=color, edgecolor='#2c3e50',
                          linewidth=1.5, alpha=0.9)
    ax.add_patch(rect)
    ax.text(x, 6.5, label, ha='center', va='center',
            fontsize=9, fontweight='bold', color='white', linespacing=1.3)
    # Equation below box
    ax.text(x, 3.8, eq, ha='center', va='center',
            fontsize=8, color='#2c3e50',
            bbox=dict(boxstyle='round,pad=0.3', facecolor='#fdfefe',
                      edgecolor='#bdc3c7', alpha=0.95))

# Draw arrows between layers
for i in range(len(layers) - 1):
    x1 = layers[i][0] + 0.8
    x2 = layers[i+1][0] - 0.8
    ax.annotate('', xy=(x2, 5.75), xytext=(x1, 5.75),
                arrowprops=dict(arrowstyle='->', color='#2c3e50', lw=2.0))

# Transition labels
transitions = [
    (2.0, 'Discretize\n(Bird, 1994)'),
    (4.0, 'Continuum\nLimit (Kn→0)'),
    (6.0, 'Regression\nCorrelation'),
    (8.0, 'Neural\nApproximation'),
    (10.0, 'Global\nSearch'),
]
for x, label in transitions:
    ax.text(x, 7.8, label, ha='center', va='center',
            fontsize=7, fontstyle='italic', color='#7f8c8d',
            bbox=dict(boxstyle='round,pad=0.2', facecolor='#fef9e7',
                      edgecolor='#f0e68c', alpha=0.8))

# Title
ax.set_title('Governing Equations: Derivation Chain from Kinetic Theory to Optimization',
             fontsize=13, fontweight='bold', color='#2c3e50', pad=25)

# Axiom labels at bottom
axioms = [
    (1.0, 'A1: Conservation\nA2: Molecular Chaos'),
    (3.0, 'A3: Mean Free Path\nA4: M-B Distribution'),
    (5.0, 'A3: Continuum\nAssumption'),
    (7.0, 'A5: Empirical\nHeating'),
    (9.0, 'A7: PINN\nConsistency'),
    (11.0, 'A6: Convergence\nGuarantee'),
]
for x, label in axioms:
    ax.text(x, 2.5, label, ha='center', va='center',
            fontsize=6.5, color='#6c3483',
            bbox=dict(boxstyle='round,pad=0.2', facecolor='#f5eef8',
                      edgecolor='#d2b4de', alpha=0.8))

# Legend for axiom mapping
ax.text(6.0, 1.5, 'Bottom: Axiom references (Table 3.1)     Top: Transition methodology',
        ha='center', va='center', fontsize=7.5, fontstyle='italic', color='#7f8c8d')

ax.set_xlim(-0.5, 12.5)
ax.set_ylim(1.0, 9.0)
ax.set_aspect('equal')
ax.axis('off')

plt.tight_layout()
plt.savefig(OUT, dpi=200, bbox_inches='tight', facecolor='white')
print(f'Saved: {OUT}')
