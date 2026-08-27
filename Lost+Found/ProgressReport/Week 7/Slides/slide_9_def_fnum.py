def get_slide_data() -> dict:
    return {
        'title': 'F_num Scaling',
        'content': '\n# Glossary: F_num Scaling\n\n**F_num Scaling** represents the ratio of real gas molecules represented by each simulated computational particle:\n\n$$F_{\\text{num}} = \\frac{N_{\\text{real}}}{N_{\\text{sim}}}$$\n\n### Context\nTo make simulations computationally feasible, $F_{\\text{num}}$ typically scales from $10^{15}$ to $10^{20}$ real molecules per simulation particle. Choosing $F_{\\text{num}}$ balances statistical resolution against computational overhead.\n\n<div style="margin-top: 1.5rem; text-align: right;">\n    <a href="#" class="back-btn" style="margin-bottom:0; background:rgba(99,102,241,0.15); border-color:rgba(99,102,241,0.3); color:#a5b4fc;" onclick="loadTheoremSlide(5)">Return to Discretization Step 3 &rarr;</a>\n</div>\n'
    }
