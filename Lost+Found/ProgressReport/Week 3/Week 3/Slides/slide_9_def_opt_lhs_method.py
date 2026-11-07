def get_slide_data() -> dict:
    return {
        'title': 'Latin Hypercube Sampling',
        'content': '\n## Jittered Latin Hypercube Sampling (LHS)\n\nInitial exploration of the multidimensional search space uses Latin Hypercube Sampling to build a balanced, space-filling dataset.\n\n**Configuration:**\n*   **Sample count**: Typically $N_{samples} = 100 - 500$ points.\n*   **Jittering**: Adds a randomized perturbation to points within each hyper-grid interval to avoid alignment artifacts.\n*   Provides the training dataset for the Methodology of Physics (MoP) PyTorch surrogate metamodel.\n'
    }
