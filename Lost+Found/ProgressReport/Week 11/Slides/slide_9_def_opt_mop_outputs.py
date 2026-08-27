def get_slide_data() -> dict:
    return {
        'title': 'MoP Output Channels',
        'content': '\n## MoP Predicted Outputs\n\nThe 8-channel output layer from the surrogate represents key variables needed to assess feasibility and objectives:\n\n1.  **$\\beta$**: Ballistic coefficient.\n2.  **$C_D$**: Total drag coefficient.\n3.  **$\\dot{q}_{stag}$**: Stagnation point heat flux.\n4.  **$T_{surface}$**: Outer SiC surface temperature.\n5.  **$T_{bondline}$**: Inner Kapton bondline temperature.\n6.  **$G$**: Peak deceleration load.\n7.  **$SM$**: Pitch static margin.\n8.  **$v_{term}$**: Parachute terminal velocity window.\n'
    }
