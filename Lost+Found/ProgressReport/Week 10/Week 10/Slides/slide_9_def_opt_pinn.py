def get_slide_data() -> dict:
    return {
        'title': 'PINN Accelerator',
        'content': '\n## PINNAccelerator (DeepXDE Framework)\n\nTo bypass the expensive DSMC simulations during initial design iterations, a Physics-Informed Neural Network (PINN) is used to approximate flow quantities.\n\n**Architecture:**\n*   Built using `DeepXDE` with a multi-layer perceptron.\n*   Residual loss terms enforce Navier-Stokes (or slip-flow boundary approximations) on the coordinate domain.\n*   Enables evaluating $O(10^4)$ candidate shapes in seconds to steer the optimizer toward promising regions before finalizing with high-fidelity SPARTA evaluations.\n'
    }
