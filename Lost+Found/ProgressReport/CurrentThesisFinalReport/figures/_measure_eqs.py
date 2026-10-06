#!/usr/bin/env python3
"""Measure equation widths at various font sizes to inform layout."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

eqs = [
    r"$\partial f/\partial t + \mathbf{v}\cdot\nabla f = \int (f' f_1' - f f_1)\, g\, \sigma\, d\Omega\, d\mathbf{v}_1$",
    r"$\Delta x \leq \lambda/3, \quad \Delta t \leq 1/\nu$",
    r"$\partial \rho/\partial t + \nabla\cdot(\rho \mathbf{u}) = 0$",
    r"$\dot{q}_s = k \sqrt{\rho_\infty/R_N}\, V_\infty^3$",
    r"$\mathcal{L} = \lambda_d \mathcal{L}_{data} + \lambda_{pde} \mathcal{L}_{PDE}$",
    r"$J^* = \min(\beta - \beta_{target})^2 + \lambda \sum \max(0, g_i)$",
]

for fs in [11.5, 12.0, 13.0]:
    fig = plt.figure(figsize=(14, 5))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 5)
    ax.axis("off")
    for i, eq in enumerate(eqs):
        ax.text(0.1, 4.2 - i * 0.7, eq, fontsize=fs, ha="left", va="center")
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    print(f"--- fontsize {fs} ---")
    for i, eq in enumerate(eqs):
        t = ax.texts[i]
        ext = t.get_window_extent(renderer=renderer)
        w_in = ext.x1 / fig.dpi - ext.x0 / fig.dpi
        print(f"  Eq {i+1}: {w_in:.3f} in")
    plt.close(fig)
