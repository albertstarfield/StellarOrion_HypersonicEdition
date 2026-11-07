def get_slide_data() -> dict:
    return {
        'title': 'Verification and Validation',
        'content': "\n## Final SPARTA Validation Step\n\nThe final optimized candidate returned by the genetic algorithm is subjected to a confirmation check.\n\n**Verification Pipeline:**\n1. Generate the optimized axisymmetric coordinates.\n2. Build the final 2D SPARTA surface mesh.\n3. Run a high-fidelity DSMC simulation to verify if actual drag, shock structure, and convective heating match the surrogate's predictions.\n4. If valid, save the final configuration to the optimization summary database.\n"
    }
