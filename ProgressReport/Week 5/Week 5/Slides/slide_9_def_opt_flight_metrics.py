def get_slide_data() -> dict:
    return {
        'title': 'Flight Metrics Calculation',
        'content': '\n## Flight Metrics Evaluation\n\n`calculate_flight_metrics()` maps aerodynamic force profiles from the simulation to full trajectory dynamics.\n\n**Key Metrics Derived:**\n*   **Ballistic Coefficient ($\\beta$)**: Calculated from drag coefficient $C_D$ and projection area $A$.\n*   **Peak G-Load**: Integrates equations of motion over the descent trajectory profile.\n*   **Total Convective Heat Load**: Integrates localized $\\dot{q}_{stag}$ thermal flux over the active entry duration.\n'
    }
