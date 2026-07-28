def get_slide_data() -> dict:
    return {
        'title': 'Optimization Penalty Functions',
        'content': '\n## Multi-Objective Fitness and Penalties\n\nThe fitness score evaluated in the GA incorporates objectives and constraint violations as additive penalties:\n\n$$\\text{Cost} = w_1 \\cdot (\\beta - \\beta_{target})^2 + w_2 \\cdot \\dot{q}_{stag} + \\sum \\text{Penalty}_i$$\n\n**Penalty terms applied when:**\n*   $T_{surface} > 1870\\text{ K}$ or $T_{bondline} > 773\\text{ K}$\n*   Static margin $SM < 15\\%$\n*   Inner/Outer torus geometry constraint ($r_{torus} \\le r_{out}$) is violated.\n'
    }
