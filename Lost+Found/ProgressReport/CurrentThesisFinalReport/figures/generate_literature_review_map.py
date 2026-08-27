#!/usr/bin/env python3
"""
Generate Literature Review → Physical Phenomena Mapping Figure
For thesis Chapter 2: Literature Review → Chapter 3 Methodology
Maps 5 key studies to their physical phenomena coverage
"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch
import numpy as np
import os

# Output path
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'literature_review_map.png')

# Literature studies (rows)
studies = [
    'Rapisarda (2022)\nML for HIAD Heating',
    'Rapisarda et al. (2024)\nHIAD Parametric Study',
    'Masciarelli & Cassis (2021)\nLOFTID Design',
    'Schwartzentruber (2018)\nDSMC Hypersonic',
    'This Work\nStellarOrion Pipeline',
]

# Physical phenomena / methodology columns
phenomena = [
    'HIAD\nGeometry',
    'DSMC\nAerothermal',
    'Sutton-Graves\nHeating',
    'PINN\nRefinement',
    'Survivability\nOptimization',
    'Multi-Solver\nPipeline',
]

# Coverage matrix: 1 = covered, 0.5 = partial, 0 = not covered
coverage = np.array([
    [1,   0.5, 0.5, 1,   1,   0.5],  # Rapisarda 2022
    [1,   0.5, 1,   0,   0.5, 0  ],  # Rapisarda 2024
    [1,   0,   1,   0,   0,   0  ],  # Masciarelli & Cassis
    [0,   1,   0,   0,   0,   0  ],  # Schwartzentruber
    [1,   1,   1,   1,   1,   1  ],  # This Work
])

fig, ax = plt.subplots(figsize=(10, 7))

# Color map: dark blue for full, light blue for partial, white for none
colors = {1.0: '#1a5276', 0.5: '#85c1e9', 0.0: '#f2f4f4'}

# Draw cells
cell_w = 1.0
cell_h = 0.8
for i, study in enumerate(studies):
    for j, _ in enumerate(phenomena):
        val = coverage[i, j]
        color = colors[val]
        rect = FancyBboxPatch((j * cell_w, (len(studies) - 1 - i) * cell_h),
                              cell_w - 0.05, cell_h - 0.05,
                              boxstyle="round,pad=0.02",
                              facecolor=color, edgecolor='#2c3e50', linewidth=0.8)
        ax.add_patch(rect)
        if val == 1.0:
            ax.text(j * cell_w + cell_w/2 - 0.025, (len(studies) - 1 - i) * cell_h + cell_h/2 - 0.025,
                    '●', ha='center', va='center', fontsize=14, color='white', fontweight='bold')
        elif val == 0.5:
            ax.text(j * cell_w + cell_w/2 - 0.025, (len(studies) - 1 - i) * cell_h + cell_h/2 - 0.025,
                    '◐', ha='center', va='center', fontsize=14, color='#1a5276')

# Study labels (left)
for i, study in enumerate(studies):
    ax.text(-0.15, (len(studies) - 1 - i) * cell_h + cell_h/2 - 0.025,
            study, ha='right', va='center', fontsize=8, fontweight='bold',
            color='#2c3e50', linespacing=1.2)

# Phenomena labels (top)
for j, ph in enumerate(phenomena):
    ax.text(j * cell_w + cell_w/2 - 0.025, len(studies) * cell_h + 0.1,
            ph, ha='center', va='bottom', fontsize=8, fontweight='bold',
            color='#2c3e50', linespacing=1.2)

# Highlight "This Work" row
ax.add_patch(plt.Rectangle((-0.025, 0 - 0.025), len(phenomena) * cell_w + 0.05,
                            cell_h + 0.05, fill=False,
                            edgecolor='#e74c3c', linewidth=2.0, linestyle='--'))

# Legend
legend_elements = [
    mpatches.Patch(facecolor='#1a5276', edgecolor='#2c3e50', label='Fully covered'),
    mpatches.Patch(facecolor='#85c1e9', edgecolor='#2c3e50', label='Partially covered'),
    mpatches.Patch(facecolor='#f2f4f4', edgecolor='#2c3e50', label='Not covered'),
]
ax.legend(handles=legend_elements, loc='lower center', ncol=3, fontsize=8,
          framealpha=0.9, edgecolor='#2c3e50', bbox_to_anchor=(0.5, -0.12))

ax.set_xlim(-3.5, len(phenomena) * cell_w + 0.5)
ax.set_ylim(-0.8, len(studies) * cell_h + 1.2)
ax.set_aspect('equal')
ax.axis('off')
ax.set_title('Literature Review: Coverage of Physical Phenomena and Methodology',
             fontsize=12, fontweight='bold', color='#2c3e50', pad=20)

plt.tight_layout()
plt.savefig(OUT, dpi=200, bbox_inches='tight', facecolor='white')
print(f'Saved: {OUT}')
