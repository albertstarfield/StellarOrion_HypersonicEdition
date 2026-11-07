def get_slide_data() -> dict:
    return {
        'title': 'Out-of-Scope Components',
        'content': '\n## Fixed / Unchanged Properties\n\nTo ensure we isolate the effects of the topology parametric optimization, several complex factors have been strictly designated as out-of-scope for modification:\n\n* **Material Composition:** We are not changing the thermal properties, density, or physical makeup of the HIAD material stack (F-TPS, insulation, structural layers).\n* **Chemistry Modeling:** Advanced gas chemistry interactions and complex non-equilibrium reaction coefficients remain fixed to the established SPARTA baseline.\n* **Operating Regime:** The atmospheric entry altitude, flight conditions, and free stream velocity vector are treated as constants.\n'
    }
