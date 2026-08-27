def get_slide_data() -> dict:
    return {
        'title': 'Relaxation Phase',
        'content': '\n# Glossary: Relaxation Phase\n\nThe **Relaxation Phase** (or stochastic collision phase) is the step in the splitting scheme where particle velocities are modified stochastically in each grid cell to simulate binary collisions.\n\n### Context\nUnlike classical molecular dynamics, trajectories are not calculated. Instead, a statistical sampling method (like NTC) evaluates the probability of collisions between nearby particles in the same cell.\n\n<div style="margin-top: 1.5rem; text-align: right;">\n    <a href="#" class="back-btn" style="margin-bottom:0; background:rgba(99,102,241,0.15); border-color:rgba(99,102,241,0.3); color:#a5b4fc;" onclick="loadTheoremSlide(4)">Return to Splitting Step 2 &rarr;</a>\n</div>\n'
    }
