def get_slide_data() -> dict:
    return {
        'title': 'Physics Constraints',
        'content': '\n## Multi-Disciplinary Physics Constraints (MoP)\n\nTo prevent structural or thermal failure during hypersonic entry, candidates must satisfy the following constraints:\n\n*   **Peak Surface Temperature**: $T_{surface} < 1870\\text{ K}$ (melting limit of Nicalon SiC outer fabric).\n*   **Bondline Temperature**: $T_{bondline} < 773\\text{ K}$ (thermal degradation limit of Kapton gas barrier and polyurethane bladders). Calculated via 1D transient heat conduction model.\n*   **Deceleration Load (G-Limit)**: $a_{max} < 25\\text{ G}$ (payload structural margin).\n*   **Static Margin (Stability)**: $SM > 15\\%$ (stable trim point, self-correcting pitching moment $\\partial C_m / \\partial \\alpha < 0$).\n'
    }
