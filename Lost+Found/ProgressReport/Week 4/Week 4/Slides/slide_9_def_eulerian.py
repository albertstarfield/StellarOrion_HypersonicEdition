def get_slide_data() -> dict:
    return {
        'title': 'Eulerian Mesh Grid',
        'content': '\n# Glossary: Eulerian Mesh Grid\n\nThe **Eulerian Mesh Grid** in DSMC is a stationary spatial background grid. Unlike grid-based fluid solvers, particles move freely through it.\n\n### Context\nIts primary purposes are to group local particles within cells to evaluate collision probabilities and to calculate macroscopic properties (density, velocity, temperature) by averaging particle statistics inside each cell.\n\n<div style="margin-top: 1.5rem; text-align: right;">\n    <a href="#" class="back-btn" style="margin-bottom:0; background:rgba(99,102,241,0.15); border-color:rgba(99,102,241,0.3); color:#a5b4fc;" onclick="loadTheoremSlide(5)">Return to Discretization Step 3 &rarr;</a>\n</div>\n'
    }
