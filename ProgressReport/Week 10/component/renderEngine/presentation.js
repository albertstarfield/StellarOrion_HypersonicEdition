// StellarOrion Interactive Presentation Engine
let slidesData = [];
let currentSlideIdx = 0;

async function initPresentation() {
    // Check if pywebview API is available
    if (window.pywebview && window.pywebview.api) {
        try {
            const data = await window.pywebview.api.get_slides_data();
            if (data && data.length > 0) {
                slidesData = data;
            }
        } catch (e) {
            console.warn("pywebview API error:", e);
        }
    }

    // Fallback: Fetch slide files via HTTP
    if (slidesData.length === 0) {
        await loadSlidesFromHTTP();
    }

    renderSidebar();
    showSlide(0);
    setupKeyboardListeners();
}

async function loadSlidesFromHTTP() {
    // List of known slide filenames
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

    for (let name of slideNames) {
        try {
            const res = await fetch(`../../Slides/${name}.py`);
            if (res.ok) {
                const text = await res.text();
                // Simple regex extraction of title and content from python file
                const titleMatch = text.match(/'title':\s*r?['"]([^'"]+)['"]/);
                const contentMatch = text.match(/'content':\s*r?'''([\s\S]*?)'''/);
                if (titleMatch && contentMatch) {
                    slidesData.push({
                        title: titleMatch[1],
                        content: contentMatch[1],
                        filename: name
                    });
                }
            }
        } catch (e) {
            console.error(`Failed loading ${name}:`, e);
        }
    }

    // Default emergency slide if empty
    if (slidesData.length === 0) {
        slidesData.push({
            title: "Week 11 MDAO Optimization Result",
            content: "# MDAO Result Overview\n\n- Outer Diameter: 4.86m\n- Drag: 194.84 kN (+210.6%)\n- Backside Payload Temp: 338.5 K (≤ 350 K Limit)"
        });
    }
}

function renderSidebar() {
    const list = document.getElementById('slide-list');
    list.innerHTML = '';
    slidesData.forEach((slide, idx) => {
        const li = document.createElement('li');
        li.className = `slide-item ${idx === 0 ? 'active' : ''}`;
        li.innerHTML = `<span class="slide-num">${idx + 1}</span> <span>${slide.title}</span>`;
        li.onclick = () => showSlide(idx);
        list.appendChild(li);
    });
}

function showSlide(idx) {
    if (idx < 0 || idx >= slidesData.length) return;
    currentSlideIdx = idx;

    const slide = slidesData[idx];
    document.getElementById('slide-title').innerText = slide.title;
    
    // Parse Markdown
    let parsedContent = marked.parse(slide.content || '');
    document.getElementById('slide-content').innerHTML = parsedContent;

    // Render KaTeX Math
    if (window.katex) {
        renderMathInElement(document.getElementById('slide-content'));
    }

    // Update Counter & Active Item
    document.getElementById('slide-counter').innerText = `Slide ${idx + 1} / ${slidesData.length}`;
    const items = document.querySelectorAll('.slide-item');
    items.forEach((item, i) => {
        item.classList.toggle('active', i === idx);
        if (i === idx) item.scrollIntoView({ block: 'nearest' });
    });
}

function prevSlide() { showSlide(currentSlideIdx - 1); }
function nextSlide() { showSlide(currentSlideIdx + 1); }

function setupKeyboardListeners() {
    window.addEventListener('keydown', (e) => {
        if (e.key === 'ArrowRight' || e.key === ' ' || e.key === 'PageDown') nextSlide();
        if (e.key === 'ArrowLeft' || e.key === 'PageUp') prevSlide();
    });
}

function renderMathInElement(el) {
    el.innerHTML = el.innerHTML.replace(/\$([^\$]+)\$/g, (match, expr) => {
        try {
            return katex.renderToString(expr, { throwOnError: false });
        } catch (e) {
            return match;
        }
    });
}

// Initialize on page load
window.addEventListener('DOMContentLoaded', initPresentation);
window.addEventListener('pywebviewready', initPresentation);
