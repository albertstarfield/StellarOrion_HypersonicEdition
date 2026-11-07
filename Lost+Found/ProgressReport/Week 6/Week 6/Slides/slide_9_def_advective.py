def get_slide_data() -> dict:
    return {
        'title': 'Advective Transport',
        'content': '\n# Glossary: Advective Transport\n\n**Advective transport** describes the physical movement of particles through space due to their velocity. In the Boltzmann transport equation, it is written as:\n\n$$\\mathbf{v} \\cdot \\nabla f$$\n\n### Context\nIn hypersonic boundary layers, advection transports heat and molecules downstream. In DSMC, this is modeled during the deterministic advection phase where particles are moved along straight trajectories.\n\n<div style="margin-top: 1.5rem; text-align: right;">\n    <a href="#" class="back-btn" style="margin-bottom:0; background:rgba(99,102,241,0.15); border-color:rgba(99,102,241,0.3); color:#a5b4fc;" onclick="loadTheoremSlide(3)">Return to Boltzmann Step 1 &rarr;</a>\n</div>\n'
    }
