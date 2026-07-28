// StellarOrion Week 11 Interactive Presentation Engine
let slidesData = [];

function animateSplash() {
    const loader = document.getElementById('splash-loader');
    const splash = document.getElementById('splash-screen');
    if (!loader || !splash) return;

    let width = 0;
    const interval = setInterval(() => {
        width += 15;
        loader.style.width = width + '%';
        if (width >= 100) {
            clearInterval(interval);
            setTimeout(() => {
                splash.style.opacity = '0';
                splash.style.visibility = 'hidden';
            }, 300);
        }
    }, 50);
}

function switchView(mode) {
    const map = document.getElementById('view-map');
    const table = document.getElementById('view-table');
    const tabMap = document.getElementById('tab-map');
    const tabTable = document.getElementById('tab-table');

    if (!map || !table) return;

    if (mode === 'map') {
        map.style.display = 'flex';
        table.style.display = 'none';
        tabMap.classList.add('active');
        tabTable.classList.remove('active');
    } else if (mode === 'table') {
        map.style.display = 'none';
        table.style.display = 'flex';
        tabTable.classList.add('active');
        tabMap.classList.remove('active');
    }
}

async function openTheoremByName(slideName) {
    const modal = document.getElementById('theorem-modal');
    const content = document.getElementById('modal-content');
    if (!modal || !content) return;

    try {
        const res = await fetch(`../../Slides/${slideName}.py`);
        if (res.ok) {
            const text = await res.text();
            const titleMatch = text.match(/'title':\s*r?['"]([^'"]+)['"]/);
            const contentMatch = text.match(/'content':\s*r?'''([\s\S]*?)'''/);
            const title = titleMatch ? titleMatch[1] : slideName;
            const body = contentMatch ? contentMatch[1] : text;

            content.innerHTML = `
                <h2 style="color: #fff; font-family:'Outfit',sans-serif; margin-bottom:1rem;">${title}</h2>
                <div>${marked.parse(body)}</div>
            `;
            renderMathInElement(content);
            modal.style.display = 'flex';
        }
    } catch (e) {
        console.error("Failed to load slide theorem:", e);
    }
}

function closeTheoremModal() {
    const modal = document.getElementById('theorem-modal');
    if (modal) modal.style.display = 'none';
}

function renderMathInElement(el) {
    if (!window.katex || !el) return;
    el.innerHTML = el.innerHTML.replace(/\$([^\$]+)\$/g, (match, expr) => {
        try {
            return katex.renderToString(expr, { throwOnError: false });
        } catch (e) {
            return match;
        }
    });
}

// Global theorem slide loader for markdown onclick references
window.loadTheoremSlide = function(idx) {
    const slideNames = [
        "slide_1", "slide_2", "slide_3", "slide_4", "slide_5", "slide_6", "slide_7", "slide_8",
        "slide_10_optimization", "slide_11_sparta_overview", "slide_12_move_step", "slide_13_migrate_step",
        "slide_14_collide_step", "slide_15_sort_step", "slide_16_chemistry", "slide_17_postprocessing",
        "slide_18_grid", "slide_19_atmosphere", "slide_20_opt_setup", "slide_21_opt_baseline",
        "slide_22_opt_lhs", "slide_23_opt_mop", "slide_24_opt_ga", "slide_25_sampling_variants",
        "slide_26_sampling_methods", "slide_27_sparta_openfoam_hybrid", "slide_27b_execution1_boundary",
        "slide_28_execution1_timing", "slide_29_execution1_validation", "slide_30_execution1_progress",
        "slide_31_result_comparison_table"
    ];
    if (typeof idx === 'number' && idx >= 0 && idx < slideNames.length) {
        openTheoremByName(slideNames[idx]);
    }
};

window.addEventListener('DOMContentLoaded', () => {
    animateSplash();
});
