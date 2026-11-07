def get_slide_data() -> dict:
    return {
        'title': 'Search Space Definition',
        'content': "\n## `search_map` — The Optimization Search Space\n\nThe `search_map` dictionary in `execute_optimization()` defines all candidate design variables.\n\n**Structure per variable:**\n```python\n'diameter': {\n    'base': 3.0,   # Baseline IRVE-3 value\n    'v':    True,  # Active in optimization\n    'min':  2.5,   # Lower bound [m]\n    'max':  4.5,   # Upper bound [m]\n    'type': float  # float or int\n}\n```\n\n**Active 4D space** (default): $[D, \\theta, N, R_n]$\n\nThe bounds are derived from the **Rapisarda (2023) MDAO envelope** and physical feasibility constraints of the IRVE-3 inflatable structure.\n"
    }
