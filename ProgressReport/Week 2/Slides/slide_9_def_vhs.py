def get_slide_data() -> dict:
    return {
        'title': 'Variable Hard Sphere (VHS)',
        'content': '\n# Glossary: Variable Hard Sphere (VHS)\n\nThe **Variable Hard Sphere (VHS)** model is a molecular interaction model where the molecular cross-section diameter $d$ decreases as the relative collision velocity $g$ increases:\n\n$$d = d_{\\text{ref}} \\left(\\frac{g_{\\text{ref}}}{g}\\right)^{\\omega - 1/2}$$\n\n### Context\nIt correctly reproduces the viscosity temperature dependence of real gases ($\\mu \\propto T^\\omega$), which is essential for capturing aerothermal heating profiles correctly.\n\n<div style="margin-top: 1.5rem; text-align: right;">\n    <a href="#" class="back-btn" style="margin-bottom:0; background:rgba(99,102,241,0.15); border-color:rgba(99,102,241,0.3); color:#a5b4fc;" onclick="loadTheoremSlide(6)">Return to Collision Step 4 &rarr;</a>\n</div>\n'
    }
