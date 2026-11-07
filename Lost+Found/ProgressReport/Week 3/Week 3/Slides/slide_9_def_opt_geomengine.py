def get_slide_data() -> dict:
    return {
        'title': 'Geometry Engine',
        'content': '\n## HIAD Geometry Generation Engine\n\nDefined in `HIAD_GeometryEngine.py`, this component translates the independent parameters $[N, \\theta, r_{torus}, r_{out}]$ into a fully resolved 2D profile.\n\n**Key Operations:**\n1. Stacks $N$ toroidal bladders at angle $\\theta$.\n2. Enforces structural encapsulation of $r_{pay}$ and $h_{pay}$.\n3. Computes the scallop pocket regions where adjacent tori intersect (critical for localized peak aerothermal heating calculation).\n4. Generates axisymmetric coordinates used to build the SPARTA 2D surface grid (`SPARTA.surface` format).\n'
    }
