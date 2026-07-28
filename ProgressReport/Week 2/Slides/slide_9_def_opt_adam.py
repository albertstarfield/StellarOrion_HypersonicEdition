def get_slide_data() -> dict:
    return {
        'title': 'Optimization Training Details',
        'content': '\n## MoP Surrogate Training Configurations\n\nThe MLP is optimized to fit the LHS datasets using standard PyTorch parameters:\n\n*   **Optimizer**: Adam (Learning Rate = $0.005$, Weight Decay = $1\\times10^{-5}$).\n*   **Loss Function**: Mean Squared Error (MSE) loss.\n*   **Learning Rate Schedule**: ReduceLROnPlateau drops the learning rate when validation loss stalls.\n*   **Accuracy Target**: Validated to $R^2 > 0.98$ on held-out test configurations before releasing to the GA solver.\n'
    }
