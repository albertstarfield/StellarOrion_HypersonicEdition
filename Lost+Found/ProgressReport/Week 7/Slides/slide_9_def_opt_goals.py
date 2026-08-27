def get_slide_data() -> dict:
    return {
        'title': 'Objective Goals Definition',
        'content': '\n## Multi-Objective Optimization Goals\n\nThe optimization loop in `StellarOrionEngineMach5Up.py` targets two primary coupled objectives:\n\n1. **Ballistic Coefficient Match**: Minimize difference from target (IRVE-3 sounding rocket scale).\n   $$\\min \\quad | \\beta - \\beta_{\\text{target}} | \\quad \\text{where } \\beta_{\\text{target}} \\approx 26.9 \\text{ kg/m}^2$$\n2. **Convective Peak Heat Flux Mitigation**: Minimize maximum stagnation point heat transfer.\n   $$\\min \\quad \\dot{q}_{stag} \\quad \\text{subject to } \\dot{q}_{stag} < 14.36 \\text{ W/cm}^2$$\n\nThe trade-off between the two forms a Pareto front where shallower half-cone angles $\\theta$ reduce peak heat but increase drag footprint.\n'
    }
