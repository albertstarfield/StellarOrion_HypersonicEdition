// StellarOrion Week 11 — Validation Flowfield & Interactive Physics Engine
let currentBgIdx = 0;
let shuffleInterval = null;
let isShufflePaused = false;

function dismissSplash() {
    const splash = document.getElementById('splash-screen');
    if (splash && splash.style.visibility !== 'hidden') {
        splash.style.opacity = '0';
        splash.style.visibility = 'hidden';
        startImageShuffle();
    }
}

function animateSplash() {
    const loader = document.getElementById('loader-fill');
    const text = document.getElementById('loader-text');
    const splash = document.getElementById('splash-screen');
    if (!splash) return;

    splash.addEventListener('click', dismissSplash);

    let width = 0;
    const interval = setInterval(() => {
        width += 1;
        if (loader) loader.style.width = width + '%';
        if (text) text.textContent = width + '%';
        if (width >= 100) {
            clearInterval(interval);
            setTimeout(dismissSplash, 300);
        }
    }, 20);
}

function startImageShuffle() {
    const slides = document.querySelectorAll('.bg-slide');
    if (slides.length === 0) return;

    if (shuffleInterval) clearInterval(shuffleInterval);
    shuffleInterval = setInterval(() => {
        if (!isShufflePaused) {
            const nextIdx = (currentBgIdx + 1) % slides.length;
            setBgImage(nextIdx);
        }
    }, 4500);
}

function toggleShufflePlayback() {
    isShufflePaused = !isShufflePaused;
    const label = document.getElementById('play-status-label');
    const icon = document.getElementById('play-status-icon');

    if (label && icon) {
        if (isShufflePaused) {
            label.textContent = 'Resume Shuffle';
            icon.textContent = '▶️';
        } else {
            label.textContent = 'Pause Shuffle';
            icon.textContent = '⏸️';
        }
    }
}

function toggleSandwichMenu() {
    const panel = document.getElementById('sandwich-panel');
    if (panel) {
        panel.classList.toggle('open');
    }
}

function setBgImage(idx) {
    currentBgIdx = idx;
    const slides = document.querySelectorAll('.bg-slide');
    const menuItems = document.querySelectorAll('.sandwich-menu-panel .menu-item');

    slides.forEach((slide, i) => {
        if (i === idx) {
            slide.classList.add('active');
        } else {
            slide.classList.remove('active');
        }
    });

    // Skip first menu item (playback control button)
    menuItems.forEach((item, i) => {
        if (i > 0) {
            if (i - 1 === idx) {
                item.classList.add('active');
            } else {
                item.classList.remove('active');
            }
        }
    });
}

function openHotspotModal(key) {
    const modal = document.getElementById('app-modal');
    const content = document.getElementById('modal-content');
    if (!modal || !content) return;

    let html = '';
    if (key === 'shock') {
        html = `
            <h2 style="color:var(--accent-rose); font-family:'Google Sans',sans-serif; font-weight:500; margin-bottom:1rem;">💥 Hypersonic Bow Shock Standoff</h2>
            <p style="font-weight:400; line-height:1.6; color:var(--text-secondary);"><b>Shock Standoff Distance ($\\Delta$):</b> Derived from Billig's correlation for blunt aeroshells in hypersonic entry.</p>
            <p style="font-weight:400; line-height:1.6; color:var(--text-secondary); margin-top:0.8rem;"><b>Shock Compression Wave:</b> High-velocity freestream molecules ($V_\\infty = 2,700\\text{ m/s}$) undergo intense kinetic compression upon crossing the detached bow shock front.</p>
            <p style="font-weight:400; line-height:1.6; color:var(--text-secondary); margin-top:0.8rem;"><b>Peak Dissociation Temperature:</b> Kinetic energy converts into vibrational excitation and thermal dissociation ($\text{N}_2 \\to 2\text{N}$, $\text{O}_2 \\to 2\text{O}$), reaching peak shock temperatures of $12,362\\text{ K}$.</p>
        `;
    } else if (key === 'ballistic') {
        html = `
            <h2 style="color:var(--accent-amber); font-family:'Google Sans',sans-serif; font-weight:500; margin-bottom:1rem;">🚀 Ballistic Coefficient & Deceleration</h2>
            <p style="font-weight:400; line-height:1.6; color:var(--text-secondary);"><b>Ballistic Coefficient ($\\beta$):</b> $\\beta = \\frac{m}{C_D \\cdot A_{\\text{ref}}} = 26.90\\text{ kg/m}^2$ (Baseline IRVE-3 Flight Scale)</p>
            <p style="font-weight:400; line-height:1.6; color:var(--text-secondary); margin-top:0.8rem;"><b>Vehicle Entry Mass ($m$):</b> $33.30\\text{ kg}$ payload & aeroshell stack</p>
            <p style="font-weight:400; line-height:1.6; color:var(--text-secondary); margin-top:0.8rem;"><b>Reference Area ($A_{\\text{ref}}$):</b> $7.07\\text{ m}^2$ ($D = 3.00\\text{ m}$ major diameter)</p>
            <p style="font-weight:400; line-height:1.6; color:var(--text-secondary); margin-top:0.8rem;"><b>Deceleration Profile:</b> Governs high-altitude atmospheric momentum exchange, triggering peak G-load ($n_{\\text{max}}$) during trajectory deceleration.</p>
        `;
    } else if (key === 'particles') {
        html = `
            <h2 style="color:var(--accent-purple); font-family:'Google Sans',sans-serif; font-weight:500; margin-bottom:1rem;">⚛️ Rarefied Particle Kinetic Transport</h2>
            <p style="font-weight:400; line-height:1.6; color:var(--text-secondary);"><b>Knudsen Number ($Kn$):</b> $Kn = \\frac{\\lambda}{L} > 0.01$ (Transitional to Free-Molecular Flow Regime)</p>
            <p style="font-weight:400; line-height:1.6; color:var(--text-secondary); margin-top:0.8rem;"><b>Solver Architecture:</b> 5-Species non-equilibrium DSMC kinetic solver (SPARTA DSMC core).</p>
            <p style="font-weight:400; line-height:1.6; color:var(--text-secondary); margin-top:0.8rem;"><b>Collision Kinetics:</b> VHS (Variable Hard Sphere) molecular model with NTC (No-Time-Counter) collision pairing algorithm.</p>
        `;
    } else if (key === 'thermal') {
        html = `
            <h2 style="color:var(--accent-cyan); font-family:'Google Sans',sans-serif; font-weight:500; margin-bottom:1rem;">🔥 Thermal Protection & Heat Flux</h2>
            <p style="font-weight:400; line-height:1.6; color:var(--text-secondary);"><b>Stagnation Heat Flux ($\\dot{q}_{\\text{stag}}$):</b> $14.36\\text{ W/cm}^2$ ($143.6\\text{ kW/m}^2$) via Sutton-Graves correlation ($q_{\\text{stag}} = C_{\\text{sg}} \\sqrt{\\rho_\\infty / R_n} V_\\infty^3$).</p>
            <p style="font-weight:400; line-height:1.6; color:var(--text-secondary); margin-top:0.8rem;"><b>Radiative Surface Temperature ($T_{\\text{surf}}$):</b> $1,453\\text{ K}$ radiative equilibrium skin temperature.</p>
            <p style="font-weight:400; line-height:1.6; color:var(--text-secondary); margin-top:0.8rem;"><b>FTPS Layer Protection:</b> Multi-layer flexible Pyrogel / Saffil insulation laminate preventing thermal penetration to inner structural bladders.</p>
        `;
    } else if (key === 'mach') {
        html = `
            <h2 style="color:var(--accent-green); font-family:'Google Sans',sans-serif; font-weight:500; margin-bottom:1rem;">⚡ Hypersonic Mach Speed & Velocity</h2>
            <p style="font-weight:400; line-height:1.6; color:var(--text-secondary);"><b>Freestream Mach Number:</b> $M_\\infty = 9.0$ Hypersonic Flowfield</p>
            <p style="font-weight:400; line-height:1.6; color:var(--text-secondary); margin-top:0.8rem;"><b>Freestream Entry Velocity ($V_\\infty$):</b> $2,700\\text{ m/s}$ ($9,720\\text{ km/h}$)</p>
            <p style="font-weight:400; line-height:1.6; color:var(--text-secondary); margin-top:0.8rem;"><b>Stagnation Flow Velocity:</b> Rapid deceleration to zero relative velocity at the blunt nose apex, creating the recirculating sonic line.</p>
        `;
    }

    content.innerHTML = html;
    renderMathInElement(content);
    modal.classList.add('open');
}

function closeHotspotModal() {
    const modal = document.getElementById('app-modal');
    if (modal) modal.classList.remove('open');
}

function renderMathInElement(el) {
    if (el) renderKaTeXOnElement(el);
}

let cachedSlidesData = null;

async function fetchSlidesData() {
    if (cachedSlidesData) return cachedSlidesData;
    if (window.pywebview && window.pywebview.api) {
        try {
            cachedSlidesData = await window.pywebview.api.get_slides_data();
            return cachedSlidesData;
        } catch (e) {
            console.warn("Pywebview API notice:", e);
        }
    }
    return [];
}

// ── Twinkling Plus-Star Cross Background Canvas ──
let starfieldAnimId = null;
const starsList = [];

function initStarfield() {
    const canvas = document.getElementById('starfield-canvas');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');

    const width = canvas.width = canvas.offsetWidth || window.innerWidth;
    const height = canvas.height = canvas.offsetHeight || window.innerHeight;

    starsList.length = 0;
    const starCount = 140;

    for (let i = 0; i < starCount; i++) {
        starsList.push({
            x: Math.random() * width,
            y: Math.random() * height,
            vx: (Math.random() - 0.5) * 0.35,
            vy: (Math.random() - 0.5) * 0.35,
            size: 2 + Math.random() * 4,
            alpha: 0.1 + Math.random() * 0.8,
            speed: 0.008 + Math.random() * 0.018,
            phase: Math.random() * Math.PI * 2
        });
    }

    function renderStars() {
        ctx.clearRect(0, 0, width, height);

        starsList.forEach(star => {
            star.x += star.vx;
            star.y += star.vy;
            star.phase += star.speed;

            if (star.x < 0) star.x = width;
            if (star.x > width) star.x = 0;
            if (star.y < 0) star.y = height;
            if (star.y > height) star.y = 0;

            const currentAlpha = 0.15 + (Math.sin(star.phase) + 1) * 0.4;
            const half = star.size / 2;

            ctx.strokeStyle = `rgba(226, 232, 240, ${currentAlpha})`;
            ctx.lineWidth = 1.2;

            // Draw plus-cross star (+)
            ctx.beginPath();
            ctx.moveTo(star.x - half, star.y);
            ctx.lineTo(star.x + half, star.y);
            ctx.moveTo(star.x, star.y - half);
            ctx.lineTo(star.x, star.y + half);
            ctx.stroke();
        });

        starfieldAnimId = requestAnimationFrame(renderStars);
    }

    if (starfieldAnimId) cancelAnimationFrame(starfieldAnimId);
    renderStars();
}

// ── Pan and Zoom Controller with Smooth Inertia ──
let zoomScale = 0.9;
let panX = 0;
let panY = 0;
let isPanning = false;
let startPanX = 0;
let startPanY = 0;

function updateContainerTransform() {
    const container = document.getElementById('cobweb-canvas-container');
    if (container) {
        container.style.transform = `translate(${panX}px, ${panY}px) scale(${zoomScale})`;
    }
}

function setupPanZoom() {
    const viewport = document.getElementById('cobweb-viewport');
    if (!viewport) return;

    viewport.addEventListener('wheel', (e) => {
        e.preventDefault();
        const zoomDelta = e.deltaY > 0 ? -0.06 : 0.06;
        const newZoom = Math.min(Math.max(0.35, zoomScale + zoomDelta), 2.5);
        
        // Smoothly adjust zoom centered on cursor
        zoomScale = newZoom;
        updateContainerTransform();
    }, { passive: false });

    viewport.addEventListener('mousedown', (e) => {
        if (e.target.closest('.cobweb-node-btn') || e.target.closest('.modal-close')) return;
        isPanning = true;
        startPanX = e.clientX - panX;
        startPanY = e.clientY - panY;
        viewport.style.cursor = 'grabbing';
    });

    window.addEventListener('mousemove', (e) => {
        if (!isPanning) return;
        panX = e.clientX - startPanX;
        panY = e.clientY - startPanY;
        updateContainerTransform();
    });

    window.addEventListener('mouseup', () => {
        if (isPanning) {
            isPanning = false;
            const viewport = document.getElementById('cobweb-viewport');
            if (viewport) viewport.style.cursor = 'grab';
        }
    });
}

function getElementCenter(el, container) {
    let x = el.offsetLeft + el.offsetWidth / 2;
    let y = el.offsetTop + el.offsetHeight / 2;

    const style = window.getComputedStyle(el);
    if (style.transform && style.transform !== 'none') {
        try {
            const matrix = new DOMMatrix(style.transform);
            x += matrix.e;
            y += matrix.f;
        } catch (e) {}
    }

    let curr = el.offsetParent;
    while (curr && curr !== container) {
        x += curr.offsetLeft;
        y += curr.offsetTop;
        const pStyle = window.getComputedStyle(curr);
        if (pStyle.transform && pStyle.transform !== 'none') {
            try {
                const pMatrix = new DOMMatrix(pStyle.transform);
                x += pMatrix.e;
                y += pMatrix.f;
            } catch (e) {}
        }
        curr = curr.offsetParent;
    }
    return { x, y };
}

// ── Intra-Cluster Sequential Derivation & Inter-Cluster Mesh Lines ──
function drawCobwebLines() {
    const container = document.getElementById('cobweb-canvas-container');
    const svg = document.getElementById('cobweb-svg');
    const root = document.getElementById('node-root');
    if (!container || !svg || !root) return;

    const rootCenter = getElementCenter(root, container);
    const rx = rootCenter.x;
    const ry = rootCenter.y;

    let svgContent = '';

    const clusterIds = ['cluster-physics', 'cluster-sparta', 'cluster-mdao', 'cluster-glossary'];

    // 1. Connect Central Root to 1st Node of Each Cluster Box
    clusterIds.forEach(clusterId => {
        const clusterBox = document.getElementById(clusterId);
        if (!clusterBox) return;
        const firstBtn = clusterBox.querySelector('.cobweb-node-btn');
        if (!firstBtn) return;

        const slideId = firstBtn.getAttribute('data-slide-id');
        const pos = getElementCenter(firstBtn, container);

        svgContent += `<line class="cobweb-mesh-line" data-from-slide="root" data-to-slide="${slideId}" x1="${rx}" y1="${ry}" x2="${pos.x}" y2="${pos.y}" stroke="rgba(6, 182, 212, 0.30)" stroke-width="2" stroke-dasharray="6,4" />`;
    });

    // 2. Sequential Intra-Cluster Derivation Lines (Node i -> Node i+1)
    clusterIds.forEach(clusterId => {
        const clusterBox = document.getElementById(clusterId);
        if (!clusterBox) return;
        const btns = Array.from(clusterBox.querySelectorAll('.cobweb-node-btn'));

        for (let i = 0; i < btns.length - 1; i++) {
            const b1 = btns[i];
            const b2 = btns[i + 1];
            const id1 = b1.getAttribute('data-slide-id');
            const id2 = b2.getAttribute('data-slide-id');

            const p1 = getElementCenter(b1, container);
            const p2 = getElementCenter(b2, container);

            svgContent += `<line class="cobweb-mesh-line" data-from-slide="${id1}" data-to-slide="${id2}" x1="${p1.x}" y1="${p1.y}" x2="${p2.x}" y2="${p2.y}" stroke="rgba(99, 102, 241, 0.30)" stroke-width="2" />`;
        }
    });

    // 3. Inter-Cluster Highway Connections between Phase 1 -> Phase 2 -> Phase 3 -> Phase 4
    const interClusterPairs = [
        ['slide_8', 'slide_11_sparta_overview'],
        ['slide_18_grid', 'slide_10_optimization'],
        ['slide_31_result_comparison_table', 'slide_9_def_aeroshell'],
        ['slide_9_def_stagnationpress', 'slide_2'],
        ['slide_1', 'slide_11_sparta_overview'],
        ['slide_11_sparta_overview', 'slide_10_optimization'],
        ['slide_10_optimization', 'slide_9_def_aeroshell']
    ];

    interClusterPairs.forEach(([fromId, toId]) => {
        const b1 = container.querySelector(`[data-slide-id="${fromId}"]`);
        const b2 = container.querySelector(`[data-slide-id="${toId}"]`);
        if (!b1 || !b2) return;

        const p1 = getElementCenter(b1, container);
        const p2 = getElementCenter(b2, container);

        svgContent += `<line class="cobweb-mesh-line" data-from-slide="${fromId}" data-to-slide="${toId}" x1="${p1.x}" y1="${p1.y}" x2="${p2.x}" y2="${p2.y}" stroke="rgba(6, 182, 212, 0.30)" stroke-width="2" stroke-dasharray="5,5" />`;
    });

    svgContent += `<circle cx="${rx}" cy="${ry}" r="8" fill="#06b6d4" />`;
    svg.innerHTML = svgContent;

    setupNodeHoverListeners();
}

function setupNodeHoverListeners() {
    const container = document.getElementById('cobweb-canvas-container');
    if (!container) return;

    const allBtns = container.querySelectorAll('.cobweb-node-btn');
    const allLines = container.querySelectorAll('.cobweb-mesh-line');
    const hub = document.getElementById('node-root');

    allBtns.forEach(btn => {
        const slideId = btn.getAttribute('data-slide-id');
        if (!slideId) return;

        btn.onmouseenter = () => {
            // Find connected nodes via lines
            const connectedSlideIds = new Set([slideId]);
            allLines.forEach(line => {
                const fromId = line.getAttribute('data-from-slide');
                const toId = line.getAttribute('data-to-slide');
                if (fromId === slideId) connectedSlideIds.add(toId);
                if (toId === slideId) connectedSlideIds.add(fromId);
            });

            // Highlight connected node buttons
            allBtns.forEach(b => {
                const bId = b.getAttribute('data-slide-id');
                if (b === btn) {
                    b.classList.add('hovered');
                    b.classList.remove('dimmed');
                } else if (connectedSlideIds.has(bId)) {
                    b.classList.remove('hovered');
                    b.classList.remove('dimmed');
                    b.style.borderColor = 'var(--accent-cyan)';
                    b.style.color = '#fff';
                } else {
                    b.classList.remove('hovered');
                    b.classList.add('dimmed');
                }
            });

            // Dim non-connected lines into dashed stripes, bold cyan for connected lines
            allLines.forEach(line => {
                const fromId = line.getAttribute('data-from-slide');
                const toId = line.getAttribute('data-to-slide');
                if (fromId === slideId || toId === slideId) {
                    line.setAttribute('stroke', '#06b6d4');
                    line.setAttribute('stroke-width', '3.5');
                    line.removeAttribute('stroke-dasharray');
                    line.style.opacity = '1';
                    line.style.filter = 'drop-shadow(0 0 10px #06b6d4)';
                } else {
                    line.setAttribute('stroke', 'rgba(255,255,255,0.06)');
                    line.setAttribute('stroke-width', '1');
                    line.setAttribute('stroke-dasharray', '4,6');
                    line.style.opacity = '0.12';
                    line.style.filter = 'none';
                }
            });

            if (connectedSlideIds.has('root')) {
                if (hub) hub.style.opacity = '1';
            } else {
                if (hub) hub.style.opacity = '0.4';
            }
        };

        btn.onmouseleave = () => {
            // Reset all buttons
            allBtns.forEach(b => {
                b.classList.remove('hovered');
                b.classList.remove('dimmed');
                b.style.borderColor = '';
                b.style.color = '';
            });

            // Reset all lines to default mesh state
            allLines.forEach(line => {
                const fromId = line.getAttribute('data-from-slide');
                if (fromId === 'root') {
                    line.setAttribute('stroke', 'rgba(6, 182, 212, 0.5)');
                    line.setAttribute('stroke-width', '2');
                    line.setAttribute('stroke-dasharray', '5,5');
                } else {
                    line.setAttribute('stroke', 'rgba(99, 102, 241, 0.45)');
                    line.setAttribute('stroke-width', '1.8');
                    line.removeAttribute('stroke-dasharray');
                }
                line.style.opacity = '1';
                line.style.filter = 'none';
            });

            if (hub) hub.style.opacity = '1';
        };
    });
}

function openImaginationMap() {
    const modal = document.getElementById('imagination-modal');
    if (modal) {
        modal.classList.add('open');
        panX = 0; panY = 0; zoomScale = 1.0;
        updateContainerTransform();
        setTimeout(() => {
            initStarfield();
            setupPanZoom();
            drawCobwebLines();
        }, 120);
    }
}

function closeImaginationMap() {
    const modal = document.getElementById('imagination-modal');
    if (modal) modal.classList.remove('open');
}

function renderKaTeXOnElement(container) {
    if (!window.katex) return;

    const walkAndRender = (node) => {
        if (node.nodeType === Node.ELEMENT_NODE && node.tagName !== 'SCRIPT' && node.tagName !== 'STYLE' && node.tagName !== 'CODE' && node.tagName !== 'PRE') {
            const children = Array.from(node.childNodes);
            for (let child of children) {
                if (child.nodeType === Node.TEXT_NODE) {
                    let text = child.nodeValue;
                    if (!text || !text.includes('$')) continue;

                    if (/\$\$[\s\S]+?\$\$|\$[^\$\n\r]+?\$/.test(text)) {
                        const tempSpan = document.createElement('span');
                        let htmlText = text
                            .replace(/\$\$([\s\S]+?)\$\$/g, (m, math) => {
                                const clean = math.replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&amp;/g, '&');
                                try {
                                    return katex.renderToString(clean, { displayMode: true, throwOnError: false });
                                } catch (e) { return m; }
                            })
                            .replace(/\$([^\$\n\r]+?)\$/g, (m, math) => {
                                if (/<[a-zA-Z\/][^>]*>/.test(math)) return m;
                                const clean = math.replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&amp;/g, '&');
                                try {
                                    return katex.renderToString(clean, { displayMode: false, throwOnError: false });
                                } catch (e) { return m; }
                            });

                        tempSpan.innerHTML = htmlText;
                        while (tempSpan.firstChild) {
                            node.insertBefore(tempSpan.firstChild, child);
                        }
                        node.removeChild(child);
                    }
                } else {
                    walkAndRender(child);
                }
            }
        }
    };

    walkAndRender(container);
}

async function openSlideModal(slideId) {
    const modal = document.getElementById('app-modal');
    const content = document.getElementById('modal-content');
    if (!modal || !content) return;

    const slides = await fetchSlidesData();
    const slide = slides.find(s => s.id === slideId || s.filename === slideId || s.filename === slideId + '.py');

    if (slide) {
        let rawText = slide.content || '';

        // 1. Rewrite relative image paths
        rawText = rawText.replace(/(\.\.\/)+temp_slides_v2\//g, '/temp_slides_v2/');
        rawText = rawText.replace(/(src|href)=["']temp_slides_v2\//g, '$1="/temp_slides_v2/');
        rawText = rawText.replace(/src=["'](?:\.\.\/)*LaTeX\/slide_images\/presentation_slide-(\d+)\.(png|jpg)["']/g, 'src="/temp_slides_v2/slide-$1.jpg"');

        // 2. Parse Markdown to HTML
        let html = window.marked ? marked.parse(rawText) : rawText;

        content.innerHTML = `
            <h2 style="color:var(--accent-cyan); font-family:'Google Sans',sans-serif; font-weight:500; margin-bottom:1rem;">${slide.title || slideId}</h2>
            <div style="font-weight:400; line-height:1.65; color:var(--text-secondary);" class="slide-md-body">${html}</div>
        `;

        // 3. Render KaTeX strictly within single text nodes (prevents cross-element DOM swallowing)
        renderKaTeXOnElement(content);
    } else {
        content.innerHTML = `
            <h2 style="color:var(--accent-cyan); font-family:'Google Sans',sans-serif; font-weight:500; margin-bottom:1rem;">Derivation Node: ${slideId}</h2>
            <p style="font-weight:400; line-height:1.6; color:var(--text-secondary);">Knowledge derivation node mapping <b>${slideId}.py</b> into baseline flowfield continuum.</p>
        `;
    }

    modal.classList.add('open');
}

// Close sandwich menu when clicking outside
document.addEventListener('click', (e) => {
    const wrapper = document.querySelector('.sandwich-control-wrapper');
    const panel = document.getElementById('sandwich-panel');
    if (wrapper && panel && !wrapper.contains(e.target)) {
        panel.classList.remove('open');
    }
});

window.loadTheoremSlide = async function(target) {
    if (typeof target === 'number') {
        const slides = await fetchSlidesData();
        if (slides && slides[target]) {
            openSlideModal(slides[target].id || slides[target].filename);
            return;
        }
        openSlideModal('slide_' + target);
    } else if (typeof target === 'string') {
        openSlideModal(target);
    }
};

window.handleCobwebSearch = async function(query) {
    const resultsContainer = document.getElementById('cobweb-search-results');
    const clearBtn = document.getElementById('cobweb-search-clear');
    if (!resultsContainer) return;

    if (clearBtn) clearBtn.style.display = query ? 'block' : 'none';

    const rawQuery = (query || '').trim();
    if (!rawQuery) {
        resultsContainer.innerHTML = '';
        resultsContainer.classList.remove('open');
        return;
    }

    const tokens = rawQuery.toLowerCase().split(/[\s,_\-\/\\]+/).filter(t => t.length > 0);
    if (tokens.length === 0) return;

    const slides = await fetchSlidesData();
    const matchesMap = new Map();

    // 1. Index All 88 Slides from slides data
    slides.forEach(slide => {
        const sId = slide.id || slide.filename || '';
        const sTitle = slide.title || sId;
        const sContent = slide.content || '';
        const sSub = slide.filename || sId;

        let score = 0;
        let matchedTokensCount = 0;

        tokens.forEach(t => {
            let tScore = 0;
            if (sTitle.toLowerCase().includes(t)) tScore += 15;
            if (sId.toLowerCase().includes(t)) tScore += 10;
            if (sContent.toLowerCase().includes(t)) tScore += 4;

            if (tScore > 0) {
                score += tScore;
                matchedTokensCount++;
            }
        });

        if (matchedTokensCount === tokens.length) score += 30; // Complete multi-word match bonus

        if (score > 0) {
            matchesMap.set(sId, {
                slideId: sId,
                title: sTitle,
                sub: sSub,
                score: score
            });
        }
    });

    // 2. Index All DOM Node Buttons in Cobweb Canvas
    const nodeBtns = document.querySelectorAll('#cobweb-canvas-container .cobweb-node-btn');
    nodeBtns.forEach(btn => {
        const bId = btn.getAttribute('data-slide-id') || '';
        const bText = btn.textContent || '';

        let score = 0;
        let matchedTokensCount = 0;

        tokens.forEach(t => {
            let tScore = 0;
            if (bText.toLowerCase().includes(t)) tScore += 20;
            if (bId.toLowerCase().includes(t)) tScore += 12;

            if (tScore > 0) {
                score += tScore;
                matchedTokensCount++;
            }
        });

        if (matchedTokensCount === tokens.length) score += 35;

        if (score > 0) {
            const existing = matchesMap.get(bId);
            if (existing) {
                existing.score += score + 10; // Boost nodes currently rendered in network
                if (bText) existing.title = bText;
            } else {
                matchesMap.set(bId, {
                    slideId: bId,
                    title: bText || bId,
                    sub: bId,
                    score: score + 5
                });
            }
        }
    });

    const matches = Array.from(matchesMap.values());
    matches.sort((a, b) => b.score - a.score);

    if (matches.length === 0) {
        resultsContainer.innerHTML = `<div class="search-result-item" style="cursor:default;"><span class="result-item-title" style="color:var(--text-secondary);">No derivation nodes found matching "${rawQuery}"</span></div>`;
        resultsContainer.classList.add('open');
        return;
    }

    let html = '';
    matches.slice(0, 8).forEach(item => {
        html += `
            <div class="search-result-item" onclick="focusNodeAndLaunch('${item.slideId}')">
                <span class="result-item-title">🔍 ${item.title}</span>
                <span class="result-item-sub">Node: ${item.sub}</span>
            </div>
        `;
    });

    resultsContainer.innerHTML = html;
    resultsContainer.classList.add('open');
};

function animateCameraTo(targetPanX, targetPanY, targetZoom, onComplete) {
    const startPanX = panX;
    const startPanY = panY;
    const startZoom = zoomScale;
    const startTime = performance.now();
    const duration = 450;

    function step(now) {
        const elapsed = now - startTime;
        const progress = Math.min(elapsed / duration, 1);
        const ease = 1 - Math.pow(1 - progress, 3);

        panX = startPanX + (targetPanX - startPanX) * ease;
        panY = startPanY + (targetPanY - startPanY) * ease;
        zoomScale = startZoom + (targetZoom - startZoom) * ease;

        updateTransform();

        if (progress < 1) {
            requestAnimationFrame(step);
        } else if (onComplete) {
            onComplete();
        }
    }

    requestAnimationFrame(step);
}

window.clearCobwebSearch = function() {
    const input = document.getElementById('cobweb-search-input');
    const resultsContainer = document.getElementById('cobweb-search-results');
    const clearBtn = document.getElementById('cobweb-search-clear');
    if (input) input.value = '';
    if (clearBtn) clearBtn.style.display = 'none';
    if (resultsContainer) {
        resultsContainer.classList.remove('open');
    }
};

window.focusNodeAndLaunch = function(slideId) {
    clearCobwebSearch();
    const container = document.getElementById('cobweb-canvas-container');
    const viewport = document.getElementById('cobweb-viewport');

    const cleanId = slideId.replace('.py', '');
    const targetBtn = container ? container.querySelector(`[data-slide-id="${slideId}"], [data-slide-id="${cleanId}"]`) : null;

    if (targetBtn && container && viewport) {
        container.querySelectorAll('.search-focused-node').forEach(el => {
            el.classList.remove('search-focused-node');
        });

        targetBtn.classList.add('search-focused-node');

        const vpRect = viewport.getBoundingClientRect();
        const targetCenter = getElementCenter(targetBtn, container);

        const targetZoom = 1.15;
        const targetPanX = (vpRect.width / 2 - targetCenter.x) * targetZoom;
        const targetPanY = (vpRect.height / 2 - targetCenter.y) * targetZoom;

        animateCameraTo(targetPanX, targetPanY, targetZoom, () => {
            openSlideModal(slideId);
        });
    } else {
        openSlideModal(slideId);
    }
};

function startVideoAutoplay() {
    const videos = document.querySelectorAll('video');
    videos.forEach(v => {
        v.muted = true;
        v.play().catch(err => console.warn("Video play error:", err));
    });
}

window.addEventListener('DOMContentLoaded', () => {
    animateSplash();
    renderMathInElement(document.body);
    startVideoAutoplay();
});
