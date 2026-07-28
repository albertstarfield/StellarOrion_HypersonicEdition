// StellarOrion Week 11 — Validation Flowfield & Interactive Physics Engine
let currentBgIdx = 0;
let shuffleInterval = null;
let isShufflePaused = false;

function animateSplash() {
    const loader = document.getElementById('loader-fill');
    const splash = document.getElementById('splash-screen');
    if (!loader || !splash) return;

    let width = 0;
    const interval = setInterval(() => {
        width += 20;
        loader.style.width = width + '%';
        if (width >= 100) {
            clearInterval(interval);
            setTimeout(() => {
                splash.style.opacity = '0';
                splash.style.visibility = 'hidden';
                startImageShuffle();
            }, 300);
        }
    }, 40);
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
    modal.style.display = 'flex';
}

function closeHotspotModal() {
    const modal = document.getElementById('app-modal');
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

// Close sandwich menu when clicking outside
document.addEventListener('click', (e) => {
    const wrapper = document.querySelector('.sandwich-control-wrapper');
    const panel = document.getElementById('sandwich-panel');
    if (wrapper && panel && !wrapper.contains(e.target)) {
        panel.classList.remove('open');
    }
});

window.addEventListener('DOMContentLoaded', () => {
    animateSplash();
    renderMathInElement(document.body);
});
