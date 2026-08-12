#!/usr/bin/env python3
"""
Generate MoP (Metamodel Prognosis) MLP Architecture Diagram.
3-layer MLP: Input → Hidden 1 → Hidden 2 → Output
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import os

# Set publication-quality defaults
plt.rcParams.update({
    'font.family': 'serif',
    'font.size': 11,
    'axes.labelsize': 12,
    'axes.titlesize': 13,
    'figure.dpi': 300,
    'savefig.dpi': 300,
    'savefig.bbox': 'tight',
    'savefig.pad_inches': 0.05,
})

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))
FIGURES_DIR = os.path.join(OUTPUT_DIR, 'figures')
os.makedirs(FIGURES_DIR, exist_ok=True)


def generate_mop_architecture():
    """Generate MoP MLP architecture diagram."""
    fig, ax = plt.subplots(1, 1, figsize=(12, 7))
    ax.set_xlim(-0.5, 10.5)
    ax.set_ylim(-1.5, 8.5)
    ax.set_aspect('equal')
    ax.axis('off')

    # Layer positions (x-coordinates)
    layer_x = [1, 3.5, 6, 8.5]
    layer_labels = ['Input\nLayer', 'Hidden\nLayer 1', 'Hidden\nLayer 2', 'Output\nLayer']
    layer_sizes = [4, 64, 64, 1]  # d=4 inputs, 64 neurons, 64 neurons, 1 output
    layer_neurons = [4, 6, 6, 1]  # Visual representation (fewer neurons for clarity)

    # Colors
    input_color = '#2196F3'    # Blue
    hidden_color = '#FF9800'   # Orange
    output_color = '#4CAF50'   # Green
    arrow_color = '#666666'

    # Draw layers
    for layer_idx, (x, label, size, n_neurons) in enumerate(zip(layer_x, layer_labels, layer_sizes, layer_neurons)):
        # Determine color
        if layer_idx == 0:
            color = input_color
        elif layer_idx == len(layer_x) - 1:
            color = output_color
        else:
            color = hidden_color

        # Draw neurons
        neuron_positions = []
        for i in range(n_neurons):
            y = 3.5 + (i - (n_neurons - 1) / 2) * 1.2
            neuron = plt.Circle((x, y), 0.4, color=color, ec='black', lw=1.5, alpha=0.8, zorder=5)
            ax.add_patch(neuron)
            neuron_positions.append((x, y))

            # Label first and last neuron with size
            if i == 0:
                ax.text(x, y - 0.7, f'$x_{{{i+1}}}$' if layer_idx == 0 else
                        (f'$h_{{{i+1}}}^{({layer_idx})}$' if layer_idx < len(layer_x) - 1 else '$\\hat{y}$'),
                        ha='center', va='top', fontsize=9, color='black')
            elif i == 1 and n_neurons > 2:
                ax.text(x, y + 0.7, '$\\vdots$', ha='center', va='bottom', fontsize=14, color='black')

        # Layer label
        ax.text(x, 7.5, label, ha='center', va='center', fontsize=11, fontweight='bold',
                bbox=dict(boxstyle='round,pad=0.3', facecolor='lightyellow', alpha=0.8))

        # Size annotation
        ax.text(x, -1.0, f'$n = {size}$', ha='center', va='center', fontsize=10,
                color=color, fontweight='bold')

        # Draw arrows to next layer
        if layer_idx < len(layer_x) - 1:
            next_x = layer_x[layer_idx + 1]
            next_neurons = layer_neurons[layer_idx + 1]

            for i, (x1, y1) in enumerate(neuron_positions):
                for j in range(next_neurons):
                    next_y = 3.5 + (j - (next_neurons - 1) / 2) * 1.2
                    ax.annotate('', xy=(next_x - 0.4, next_y),
                                xytext=(x1 + 0.4, y1),
                                arrowprops=dict(arrowstyle='->', color=arrow_color,
                                                lw=0.5, alpha=0.3))

    # Activation function annotations
    ax.annotate('ReLU', xy=(2.25, 3.5), fontsize=12, ha='center', va='center',
                bbox=dict(boxstyle='round,pad=0.2', facecolor='lightcyan', alpha=0.9),
                fontweight='bold', color='#E91E63')
    ax.annotate('ReLU', xy=(4.75, 3.5), fontsize=12, ha='center', va='center',
                bbox=dict(boxstyle='round,pad=0.2', facecolor='lightcyan', alpha=0.9),
                fontweight='bold', color='#E91E63')

    # Title
    ax.set_title('MoP (Metamodel Prognosis) MLP Architecture\n'
                 '3-Layer Feedforward Network with ReLU Activation',
                 fontsize=14, fontweight='bold', pad=20)

    # Legend
    legend_elements = [
        mpatches.Patch(facecolor=input_color, edgecolor='black', label='Input Layer ($d$ features)'),
        mpatches.Patch(facecolor=hidden_color, edgecolor='black', label='Hidden Layers (64 neurons each)'),
        mpatches.Patch(facecolor=output_color, edgecolor='black', label='Output Layer (1 prediction)'),
    ]
    ax.legend(handles=legend_elements, loc='upper right', fontsize=10, framealpha=0.9)

    # Add equation annotation
    eq_text = (r'$\hat{y} = \mathbf{W}_3 \cdot \mathrm{ReLU}('
               r'$' + r'$\mathbf{W}_2 \cdot \mathrm{ReLU}($' +
               r'$\mathbf{W}_1 \mathbf{x} + \mathbf{b}_1) + \mathbf{b}_2) + \mathbf{b}_3$')
    ax.text(5.0, -1.3, eq_text, ha='center', va='center', fontsize=10,
            bbox=dict(boxstyle='round,pad=0.4', facecolor='lightyellow', alpha=0.8))

    plt.tight_layout()
    path = os.path.join(FIGURES_DIR, 'mop_architecture.png')
    fig.savefig(path, dpi=300, bbox_inches='tight')
    plt.close(fig)
    print(f'[OK] MoP architecture saved: {path}')


if __name__ == '__main__':
    generate_mop_architecture()
