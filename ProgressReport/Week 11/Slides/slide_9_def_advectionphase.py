def get_slide_data() -> dict:
    return {
        'title': 'Advection Phase',
        'content': '\n# Glossary: Advection Phase\n\nThe **Advection Phase** (or deterministic motion phase) is the step in the splitting scheme where particles are moved along straight lines according to their current velocities, ignoring collisions:\n\n$$\\mathbf{x}_i(t + \\Delta t) = \\mathbf{x}_i(t) + \\mathbf{v}_i(t) \\Delta t$$\n\n### Context\nDuring this phase, boundary interactions (specular or diffuse reflections off the vehicle surface) are calculated geometrically.\n\n<div style="margin-top: 1.5rem; text-align: right;">\n    <a href="#" class="back-btn" style="margin-bottom:0; background:rgba(99,102,241,0.15); border-color:rgba(99,102,241,0.3); color:#a5b4fc;" onclick="loadTheoremSlide(4)">Return to Splitting Step 2 &rarr;</a>\n</div>\n'
    }
