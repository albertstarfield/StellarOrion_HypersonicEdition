def get_slide_data() -> dict:
    return {
        'title': 'Collision Integral',
        'content': '\n# Glossary: Collision Integral\n\nThe **Collision Integral** is the non-linear term on the right-hand side of the Boltzmann equation modeling changes to the molecular distribution function due to binary collisions:\n\n$$\\left(\\frac{\\partial f}{\\partial t}\\right)_{\\!\\text{coll}} = \\iint (f\' f\'_1 - f f_1) g \\sigma \\, d\\Omega \\, d\\mathbf{v}_1$$\n\n### Context\nDue to its high dimensionality (5D integral), solving it analytically is extremely difficult. DSMC solves this stochastically using representative particles and pairing algorithms in local cells.\n\n<div style="margin-top: 1.5rem; text-align: right;">\n    <a href="#" class="back-btn" style="margin-bottom:0; background:rgba(99,102,241,0.15); border-color:rgba(99,102,241,0.3); color:#a5b4fc;" onclick="loadTheoremSlide(3)">Return to Boltzmann Step 1 &rarr;</a>\n</div>\n'
    }
