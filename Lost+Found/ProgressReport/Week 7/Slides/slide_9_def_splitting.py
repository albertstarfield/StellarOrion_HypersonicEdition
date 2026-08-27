def get_slide_data() -> dict:
    return {
        'title': 'Fractional-Step Splitting Algorithm',
        'content': '\n# Glossary: Fractional-Step Splitting Algorithm\n\nThe **Fractional-Step Splitting Algorithm** is a numerical scheme that decouples complex coupled processes (like advection and collision) by solving them sequentially over small time increments $\\Delta t$.\n\n### Context\nIn DSMC, this allows splitting the Boltzmann equation into a deterministic free-flight advection phase and a stochastic collision relaxation phase. This approximation is valid as long as the timestep $\\Delta t$ is smaller than the mean collision time.\n\n<div style="margin-top: 1.5rem; text-align: right;">\n    <a href="#" class="back-btn" style="margin-bottom:0; background:rgba(99,102,241,0.15); border-color:rgba(99,102,241,0.3); color:#a5b4fc;" onclick="loadTheoremSlide(4)">Return to Splitting Step 2 &rarr;</a>\n</div>\n'
    }
