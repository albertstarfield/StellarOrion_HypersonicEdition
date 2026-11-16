def get_slide_data() -> dict:
    return {
        'title': 'No-Time-Counter / NTC Method',
        'content': '\n# Glossary: No-Time-Counter (NTC) Method\n\nThe **No-Time-Counter (NTC)** method is a highly efficient collision-sampling algorithm where the number of candidate collision pairs selected in a cell is proportional to the square of the particle count $N$:\n\n$$N_{\\text{cand}} = \\frac{N (N - 1) F_{\\text{num}} (\\sigma g)_{\\text{max}} \\Delta t}{2 V_{\\text{cell}}}$$\n\n### Context\nIt replaced older time-counter methods that were sensitive to the order of collision evaluations, preventing grid-induced statistical biases.\n\n<div style="margin-top: 1.5rem; text-align: right;">\n    <a href="#" class="back-btn" style="margin-bottom:0; background:rgba(99,102,241,0.15); border-color:rgba(99,102,241,0.3); color:#a5b4fc;" onclick="loadTheoremSlide(6)">Return to Collision Step 4 &rarr;</a>\n</div>\n'
    }
