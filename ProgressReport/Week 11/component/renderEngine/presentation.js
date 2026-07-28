// StellarOrion Week 11 Interactive Presentation Engine

function openHotspotInfo(spotKey) {
    const modal = document.getElementById('app-modal');
    const content = document.getElementById('modal-content-area');
    if (!modal || !content) return;

    let html = '';
    if (spotKey === 'stag') {
        html = `
            <h2 style="color:var(--accent-rose); font-family:'Outfit',sans-serif; margin-bottom:1rem;">🔴 Blunt Nose Stagnation Region</h2>
            <p><b>Nose Radius ($R_n$):</b> $0.60\\text{ m}$ (Expanded cap radius vs $0.55\\text{ m}$ baseline)</p>
            <p><b>Sutton-Graves Continuum Heat Flux:</b> $18.16\\text{ W/cm}^2$ ($181.6\\text{ kW/m}^2$)</p>
            <p style="margin-top:1rem; color:var(--text-secondary);">Enlarging the spherical nose cap pushes the stagnation point bowshock further upstream, distributing kinetic energy across a wider front and keeping thermal loading within FTPS design boundaries.</p>
            <div style="margin-top:1.5rem; text-align:right;">
                <button class="btn-action" onclick="openTheoremByName('slide_17_postprocessing')">Read Thermal Solver Theory &rarr;</button>
            </div>
        `;
    } else if (spotKey === 'drag') {
        html = `
            <h2 style="color:var(--accent-amber); font-family:'Outfit',sans-serif; margin-bottom:1rem;">🟡 Expanded Aeroshell Shoulder ($D = 4.86\\text{m}$)</h2>
            <p><b>Aerodynamic Drag Force ($F_D$):</b> $194.84\\text{ kN}$ (<b>$+210.6\%$ increase</b> over $62.72\\text{ kN}$ IRVE-3 baseline)</p>
            <p><b>Ballistic Coefficient ($\dots$):</b> $\\beta = 8.85\\text{ kg/m}^2$ (Ultra-fast high-altitude deceleration)</p>
            <p><b>Cone Half-Angle ($\\theta$):</b> $45.0^\\circ$</p>
            <p style="margin-top:1rem; color:var(--text-secondary);">Quadruples frontal area, triggering heavy deceleration at $52\\text{ km}$ altitude before entry vehicle penetrates dense atmospheric layers.</p>
            <div style="margin-top:1.5rem; text-align:right;">
                <button class="btn-action" onclick="openTheoremByName('slide_31_result_comparison_table')">View Full Result Table &rarr;</button>
            </div>
        `;
    } else if (spotKey === 'shock') {
        html = `
            <h2 style="color:var(--accent-cyan); font-family:'Outfit',sans-serif; margin-bottom:1rem;">🔵 Hypersonic Bowshock Layer</h2>
            <p><b>Shock Layer Peak Temperature ($T_{\\text{shock}}$):</b> $3,991.3\\text{ K}$ (<b>$-67.7\%$ reduction</b> vs $12,362\\text{ K}$ baseline)</p>
            <p><b>Flow Regime:</b> Transitional Knudsen Number ($Kn > 0.01$)</p>
            <p style="margin-top:1rem; color:var(--text-secondary);">The 5-species non-equilibrium SPARTA DSMC solver captures energy distribution across rotational, vibrational, and chemical dissociation states.</p>
            <div style="margin-top:1.5rem; text-align:right;">
                <button class="btn-action" onclick="openTheoremByName('slide_11_sparta_overview')">Read SPARTA Kinetic Core Theory &rarr;</button>
            </div>
        `;
    } else if (spotKey === 'scallop') {
        html = `
            <h2 style="color:var(--accent-purple); font-family:'Outfit',sans-serif; margin-bottom:1rem;">🟣 Stacked Inflatable Toroids ($N = 7$)</h2>
            <p><b>Toroid Count:</b> $7$ Stacked Inflatable Tori ($202.5\\text{ mm}$ radius)</p>
            <p><b>Scallop Recirculation:</b> Localized pressure and temperature pockets between adjacent torus rings</p>
            <p style="margin-top:1rem; color:var(--text-secondary);">Scalloped surface topology induces micro-recirculation zones that modulate shear stress across the flexible outer fabric skin.</p>
            <div style="margin-top:1.5rem; text-align:right;">
                <button class="btn-action" onclick="openTheoremByName('slide_26_sampling_methods')">Read Scallop Geometry Optimization &rarr;</button>
            </div>
        `;
    } else if (spotKey === 'tps') {
        html = `
            <h2 style="color:var(--accent-green); font-family:'Outfit',sans-serif; margin-bottom:1rem;">🟢 TPS Backside Payload Protection</h2>
            <p><b>Payload Bondline Temperature ($T_{\\text{back}}$):</b> $338.5\\text{ K}$ (<b>PASS</b> $\\le 350\\text{ K}$ safety limit)</p>
            <p><b>Insulation Stack:</b> Multi-layer Pyrogel / Saffil FTPS laminate ($0.0254\\text{ m}$ thickness)</p>
            <p style="margin-top:1rem; color:var(--text-secondary);">1D transient thermal solver confirms structural payload electronics remain safely cool throughout the peak reentry heat pulse window.</p>
            <div style="margin-top:1.5rem; text-align:right;">
                <button class="btn-action" onclick="openTheoremByName('slide_17_postprocessing')">Read TPS Thermal Transport &rarr;</button>
            </div>
        `;
    }

    content.innerHTML = html;
    renderMathInElement(content);
    modal.style.display = 'flex';
}

function openResultTableModal() {
    const modal = document.getElementById('app-modal');
    const content = document.getElementById('modal-content-area');
    if (!modal || !content) return;

    content.innerHTML = `
        <h2 style="color: #fff; font-family:'Outfit',sans-serif; margin-bottom:1rem;">📊 Week 11 MDAO Result Comparison Table</h2>
        <table class="res-table">
            <thead>
                <tr>
                    <th>Parameter / Metric</th>
                    <th>IRVE-3 Reference (Rapisarda 2023)</th>
                    <th>Optimum A: Max Drag (Sample 9 / 11)</th>
                    <th>Optimum B: Thermal Stability (Sample 7)</th>
                    <th>Delta (Opt A vs Ref)</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td><b>Major Outer Diameter ($D$)</b></td>
                    <td>3.00 m</td>
                    <td style="color:var(--accent-amber); font-weight:700;">4.86 m (Expanded Scale)</td>
                    <td style="color:var(--accent-cyan); font-weight:700;">2.92 m (Standard Scale)</td>
                    <td style="color:var(--accent-green); font-weight:700;">+62.0%</td>
                </tr>
                <tr>
                    <td><b>Cone Half-Angle ($\theta$)</b></td>
                    <td>60.0°</td>
                    <td style="color:var(--accent-amber); font-weight:700;">45.0°</td>
                    <td style="color:var(--accent-cyan); font-weight:700;">75.0°</td>
                    <td style="color:var(--accent-green); font-weight:700;">-15.0°</td>
                </tr>
                <tr>
                    <td><b>Toroid Stack Count ($N$)</b></td>
                    <td>6</td>
                    <td style="color:var(--accent-amber); font-weight:700;">7 (Locked 202.5mm toroid)</td>
                    <td style="color:var(--accent-cyan); font-weight:700;">6</td>
                    <td style="color:var(--accent-green); font-weight:700;">+1 toroid</td>
                </tr>
                <tr>
                    <td><b>Nose Radius ($R_n$)</b></td>
                    <td>0.55 m</td>
                    <td style="color:var(--accent-amber); font-weight:700;">0.60 m</td>
                    <td style="color:var(--accent-cyan); font-weight:700;">0.60 m</td>
                    <td style="color:var(--accent-green); font-weight:700;">+0.05 m</td>
                </tr>
                <tr>
                    <td><b>Aerodynamic Drag ($F_D$)</b></td>
                    <td>62.72 kN</td>
                    <td style="color:var(--accent-amber); font-weight:700;">194.84 kN</td>
                    <td style="color:var(--accent-cyan); font-weight:700;">92.84 kN</td>
                    <td style="color:var(--accent-green); font-weight:700;">+210.6%</td>
                </tr>
                <tr>
                    <td><b>Drag Coefficient ($C_D$)</b></td>
                    <td>≈1.47</td>
                    <td style="color:var(--accent-amber); font-weight:700;">1.49 (Scalloped geometry)</td>
                    <td style="color:var(--accent-cyan); font-weight:700;">1.48</td>
                    <td style="color:var(--accent-green); font-weight:700;">+1.36%</td>
                </tr>
                <tr>
                    <td><b>Ballistic Coeff ($\beta$)</b></td>
                    <td>26.90 kg/m²</td>
                    <td style="color:var(--accent-amber); font-weight:700;">8.85 kg/m² (Ultra-fast decel)</td>
                    <td style="color:var(--accent-cyan); font-weight:700;">18.58 kg/m²</td>
                    <td style="color:var(--accent-green); font-weight:700;">-67.10%</td>
                </tr>
                <tr>
                    <td><b>Stagnation Heat Flux ($\dot{q}_{\text{stag}}$)</b></td>
                    <td>14.36 W/cm² (143.6 kW/m²)</td>
                    <td style="color:var(--accent-amber); font-weight:700;">18.16 W/cm² (181.6 kW/m²)</td>
                    <td style="color:var(--accent-cyan); font-weight:700;">18.16 W/cm² (181.6 kW/m²)</td>
                    <td style="color:var(--accent-green); font-weight:700;">+3.80 W/cm²</td>
                </tr>
                <tr>
                    <td><b>Shock Layer Temp ($T_{\text{shock}}$)</b></td>
                    <td>12,362 K</td>
                    <td style="color:var(--accent-amber); font-weight:700;">3,991.3 K</td>
                    <td style="color:var(--accent-cyan); font-weight:700;">9,492.8 K</td>
                    <td style="color:var(--accent-green); font-weight:700;">-67.7%</td>
                </tr>
                <tr>
                    <td><b>Radiative Surf Temp ($T_{\text{surf}}$)</b></td>
                    <td>1,453 K</td>
                    <td style="color:var(--accent-amber); font-weight:700;">1,675 K</td>
                    <td style="color:var(--accent-cyan); font-weight:700;">1,453 K</td>
                    <td style="color:var(--accent-green); font-weight:700;">+222 K</td>
                </tr>
                <tr>
                    <td><b>Backside Payload Temp ($T_{\text{back}}$)</b></td>
                    <td>≤350 K</td>
                    <td style="color:var(--accent-amber); font-weight:700;">338.5 K</td>
                    <td style="color:var(--accent-cyan); font-weight:700;">341.2 K</td>
                    <td style="color:var(--accent-green); font-weight:700;">PASS (≤350 K Limit)</td>
                </tr>
                <tr>
                    <td><b>Generated CAD & Mesh Artifacts</b></td>
                    <td>HIAD_custom_full.step</td>
                    <td style="color:var(--accent-amber); font-weight:700;">geometry.step</td>
                    <td style="color:var(--accent-cyan); font-weight:700;">geometry.step</td>
                    <td style="color:var(--accent-green); font-weight:700;">3D STEP & STL Produced</td>
                </tr>
            </tbody>
        </table>
    `;
    renderMathInElement(content);
    modal.style.display = 'flex';
}

async function openTheoremByName(slideName) {
    const modal = document.getElementById('app-modal');
    const content = document.getElementById('modal-content-area');
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
                <div style="line-height:1.6;">${marked.parse(body)}</div>
            `;
            renderMathInElement(content);
            modal.style.display = 'flex';
        }
    } catch (e) {
        console.error("Failed to load slide theorem:", e);
    }
}

function closeAppModal() {
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
