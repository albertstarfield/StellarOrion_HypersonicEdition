def get_slide_data() -> dict:
    return {
        'title': 'Genetic Algorithm Optimization Loop',
        'content': '\n## Genetic Algorithm Steering Search\n\nOnce the surrogate is active, the GA searches the continuous design space over $20,000$ generations.\n\n**GA Configuration:**\n*   **Population**: $100$ individuals per generation.\n*   **Crossover**: Simulated Binary Crossover (SBX) with $\\eta_c = 20$.\n*   **Mutation**: Polynomial mutation with $\\eta_m = 20$.\n*   **Evaluation Speed**: The surrogate allows complete generation sweeps in milliseconds (approx. $10^5$ faster than SPARTA execution).\n'
    }
