def get_slide_data() -> dict:
    return {
        'title': 'MoP MLP Architecture',
        'content': '\n## MoP Surrogate MLP Architecture\n\nThe PyTorch-based surrogate model replaces the full evaluation workflow during optimization sweeps.\n\n**Model Characteristics:**\n*   **Architecture**: Multi-Layer Perceptron (MLP) mapping $[x_{dim} \\to 128 \\to 128 \\to 8]$.\n*   **Activation**: Swish/SiLU for smooth first and second derivatives.\n*   **Input**: De-normalized design variables $[N, \\theta, r_{torus}, r_{out}]$.\n*   **Output**: Approximations of flight metrics ($\\beta$, $C_D$, $L/D$, $T_{surface}$, $T_{bondline}$).\n'
    }
