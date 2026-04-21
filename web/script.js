let currentPage = 1;
const totalPages = 8;

window.onload = () => {
    initBackgroundEffects();
    setTimeout(() => {
        document.getElementById('splash').style.opacity = '0';
        setTimeout(() => document.getElementById('splash').style.display = 'none', 800);
    }, 1500);
};

function initBackgroundEffects() {
    const container = document.getElementById('star-container');
    const starCount = 50;
    for (let i = 0; i < starCount; i++) {
        const star = document.createElement('div');
        star.className = 'star';
        star.style.left = Math.random() * 100 + 'vw';
        star.style.top = Math.random() * 50 + 'vh'; // Only top half
        star.style.width = (Math.random() * 4 + 2) + 'px';
        star.style.height = star.style.width;
        star.style.setProperty('--duration', (Math.random() * 3 + 2) + 's');
        star.style.animationDelay = Math.random() * 5 + 's';
        container.appendChild(star);
    }

    // Shooting stars loop
    setInterval(() => {
        if (Math.random() > 0.7) {
            const ss = document.createElement('div');
            ss.className = 'shooting-star';
            ss.style.left = Math.random() * 80 + 'vw';
            ss.style.top = '-100px';
            ss.style.animation = 'shooting 3s linear forwards';
            container.appendChild(ss);
            setTimeout(() => ss.remove(), 3000);
        }
    }, 4000);
}

function changePage(delta) {
    const next = currentPage + delta;
    if (next < 1 || next > totalPages) return;
    jumpToPage(next);
}

function jumpToPage(step) {
    // Safety: prevent jumping while simulation/optimization is running
    if (currentPage === 3 || currentPage === 7) {
        const bar = document.getElementById(currentPage === 7 ? 'opt-progress-bar' : 'progress-bar');
        if (bar && bar.style.width !== '100%' && bar.style.width !== '0%') {
            console.log("Process in progress, navigation locked.");
            return;
        }
    }

    // Special trigger logic
    if (step === 3 && currentPage === 2) {
        generateGeometry();
    } else if (step === 7 && currentPage === 6) {
        startOptimization();
    } else {
        nextStep(step);
    }
}

function nextStep(step) {
    document.getElementById(`page-${currentPage}`).classList.remove('active');
    currentPage = step;
    document.getElementById(`page-${currentPage}`).classList.add('active');

    // Update buttons
    document.getElementById('btn-prev').style.display = currentPage === 1 ? 'none' : 'block';
    const nextBtn = document.getElementById('btn-next');
    if (currentPage === 3 || currentPage === 7) {
        nextBtn.style.display = 'none';
    } else {
        nextBtn.style.display = 'block';
        nextBtn.innerText = currentPage === 8 ? 'Finish' : 'Continue';
    }

    // Update Sidebar & Dots
    document.querySelectorAll('.step-item').forEach((s, idx) => {
        s.classList.toggle('active', idx + 1 === currentPage);
    });
    document.querySelectorAll('.dot').forEach((d, idx) => {
        d.classList.toggle('active', idx + 1 === currentPage);
    });

    // Update Header Title
    const titleMap = {
        1: "1. Mission Brief",
        2: "2. Base Geometry",
        3: "3. Reference Physics",
        4: "4. CAD Verification",
        5: "5. Survivability Targets",
        6: "6. Final Review",
        7: "7. High-Fidelity SBO",
        8: "8. Mission Success"
    };
    const titleEl = document.getElementById('current-step-title');
    if (titleEl) titleEl.innerText = titleMap[currentPage] || "Baloon Shield Maker";

    // Page Specific Logic
    if (currentPage === 4) init3DView();
    if (currentPage === 6) updateSummary();
}

function appendLog(msg) {
    const terminal = document.getElementById(currentPage === 7 ? 'opt-terminal' : 'terminal');
    if (terminal) {
        terminal.innerHTML += msg + '<br>';
        terminal.scrollTop = terminal.scrollHeight;
    }
}

function updateProgress(val) {
    const bar = document.getElementById(currentPage === 7 ? 'opt-progress-bar' : 'progress-bar');
    if (bar) bar.style.width = val + '%';
}

function toggleMSIS() {
    const val = document.getElementById('env-preset').value;
    document.getElementById('msis-panel').style.display = (val === 'nrlmsis') ? 'block' : 'none';
    fetchAtmosphereData();
}

function toggleRemoteFields() {
    const val = document.getElementById('solver-backend').value;
    document.getElementById('remote-fields').style.display = (val === 'pyfluent') ? 'block' : 'none';
}

async function fetchAtmosphereData() {
    const params = {
        env_preset: document.getElementById('env-preset').value,
        msis_alt: document.getElementById('msis-alt').value,
        msis_lat: document.getElementById('msis-lat').value,
        msis_lon: document.getElementById('msis-lon').value,
        msis_f107: document.getElementById('msis-f107').value,
        msis_ap: document.getElementById('msis-ap').value
    };
    const res = await window.pywebview.api.get_atmosphere_data(params);
    if (res) {
        document.getElementById('env-nrho').value = res.nrho.toExponential(2);
        document.getElementById('env-temp-inf').value = res.temp.toFixed(1);
    }
}

function generateGeometry() {
    const params = {
        diameter: document.getElementById('ref-diameter').value,
        angle: document.getElementById('ref-angle').value,
        toroids: document.getElementById('ref-toroids').value,
        mass: document.getElementById('mass').value,
        thickness: document.getElementById('thickness').value,
        nose_radius: document.getElementById('nose-radius').value,
        scallop_pts: document.getElementById('scallop-pts').value,
        scallop_angle: document.getElementById('scallop-angle').value,
        nose_type: document.getElementById('nose-type').value,
        flat_skin: document.getElementById('flat-skin').checked
    };
    // This now only generates the CAD/3D view
    window.pywebview.api.generate_cad_preview(params);
    nextStep(3); // Log for CAD
}

function startOptimization() {
    nextStep(7);
    const optParams = {
        // Variability Switches
        v_diameter: document.getElementById('v-diameter').checked,
        v_angle: document.getElementById('v-angle').checked,
        v_toroids: document.getElementById('v-toroids').checked,
        v_nose: document.getElementById('v-nose').checked,
        v_thick: document.getElementById('v-thick').checked,
        v_scallop_pts: document.getElementById('v-scallop-pts').checked,
        v_scallop_ang: document.getElementById('v-scallop-ang').checked,
        v_mass: document.getElementById('v-mass').checked,

        // Base Geometry for Baseline & LHS Variation
        base_diameter: document.getElementById('ref-diameter').value,
        base_angle: document.getElementById('ref-angle').value,
        base_toroids: document.getElementById('ref-toroids').value,
        base_nose: document.getElementById('nose-radius').value,
        base_thick: document.getElementById('thickness').value,
        base_scallop_pts: document.getElementById('scallop-pts').value,
        base_scallop_ang: document.getElementById('scallop-angle').value,
        base_mass: document.getElementById('mass').value,

        // Deltas for Variability
        delta_angle: document.getElementById('delta-angle').value,
        delta_toroids: document.getElementById('delta-toroids').value,
        delta_nose: document.getElementById('delta-nose').value,
        delta_thick: document.getElementById('delta-thick').value,
        delta_scallop_pts: document.getElementById('delta-scallop-pts').value,
        delta_scallop_ang: document.getElementById('delta-scallop-ang').value,
        delta_mass: document.getElementById('delta-mass').value,

        d_min: document.getElementById('opt-d-min').value,
        d_max: document.getElementById('opt-d-max').value,
        samples: document.getElementById('opt-samples').value,
        mass: document.getElementById('opt-mass').value,
        targets: {
            beta: { val: document.getElementById('target-beta-val').value, tol: document.getElementById('target-beta-tol').value },
            heat: { val: document.getElementById('target-heat-val').value, tol: document.getElementById('target-heat-tol').value },
            gload: { val: document.getElementById('target-g-val').value, tol: document.getElementById('target-g-tol').value },
            temp: { val: document.getElementById('target-temp-val').value, tol: document.getElementById('target-temp-tol').value },
            dynp: { val: document.getElementById('target-q-val').value, tol: document.getElementById('target-q-tol').value }
        },
        env_preset: document.getElementById('env-preset').value,
        env_run: document.getElementById('env-run').value,
        env_temp: document.getElementById('env-temp').value,
        env_nrho: document.getElementById('env-nrho').value,
        env_temp_inf: document.getElementById('env-temp-inf').value,
        env_step: document.getElementById('env-step').value,
        env_fnum: document.getElementById('env-fnum').value,
        env_react: document.getElementById('env-react').value,
        env_vstream: document.getElementById('env-vstream').value,
        env_duration: document.getElementById('env-duration').value,
        env_thermal_lag: document.getElementById('env-thermal-lag').value,
        env_chem_mode: document.getElementById('env-chem-mode').value,
        env_steady_state: document.getElementById('env-steady-state').checked,
        env_steady_tol: document.getElementById('env-steady-tol').value,
        env_xmin: document.getElementById('env-xmin').value,
        env_xmax: document.getElementById('env-xmax').value,
        env_ymax: document.getElementById('env-ymax').value,
        env_zthick: document.getElementById('env-zthick').value,

        msis_ap: document.getElementById('msis-ap').value,
        
        // Backend & SSH
        solver: document.getElementById('solver-backend').value,
        ssh_host: document.getElementById('ssh-host').value,
        ssh_user: document.getElementById('ssh-user').value,
        ssh_pass: document.getElementById('ssh-pass').value,
        ssh_key: document.getElementById('ssh-key').value,
        solver_dim: document.getElementById('solver-dim').value,
        solver_gpu: document.getElementById('solver-gpu').checked,
        solver_bl_layers: document.getElementById('solver-bl-layers').value,
        viscous_model: document.getElementById('env-viscous-model').value
    };
    window.pywebview.api.run_optimization(optParams);
}

function refreshDomainPreview() {
    const params = {
        env_xmin: document.getElementById('env-xmin').value,
        env_xmax: document.getElementById('env-xmax').value,
        env_ymax: document.getElementById('env-ymax').value,
        env_zthick: document.getElementById('env-zthick').value,
        diameter: document.getElementById('target-beta-val').value / 50.0, // Mock for preview
        angle: 60,
        env_preset: document.getElementById('env-preset').value
    };
    window.pywebview.api.request_domain_preview(params);
}

function onDomainPreviewReady() {
    const img = document.getElementById('domain-live-preview');
    if (img) img.src = 'assets/plots/domain_preview.png?t=' + Date.now();
    const confImg = document.getElementById('domain-preview-img');
    if (confImg) confImg.src = 'assets/plots/domain_preview.png?t=' + Date.now();
}

function syncTarget(id, type) {
    const range = document.getElementById(`target-${id}-range`);
    const val = document.getElementById(`target-${id}-val`);
    if (type === 'range') {
        val.value = range.value;
    } else {
        range.value = val.value;
    }
}

function applyPreset() {
    const preset = document.getElementById('env-preset').value;
    if (preset === 'artemis') {
        document.getElementById('env-temp').value = 1000.0;
        document.getElementById('env-step').value = 1.0e-6;
        document.getElementById('env-fnum').value = 1.0e16;
        document.getElementById('env-react').value = 'tce';
        document.getElementById('target-beta-val').value = 150;
        syncTarget('beta', 'val');
    } else if (preset === 'mars') {
        document.getElementById('env-temp').value = 800.0;
        document.getElementById('env-step').value = 2.0e-6;
        document.getElementById('env-fnum').value = 5.0e15;
        document.getElementById('env-react').value = 'none';
        document.getElementById('target-beta-val').value = 100;
        syncTarget('beta', 'val');
    }
}

function updateSummary() {
    const content = `
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
            <div>
                <p><strong>Baseline Geometry:</strong></p>
                <ul>
                    <li>Base Diameter: ${document.getElementById('ref-diameter').value}m</li>
                    <li>Cone Angle: ${document.getElementById('ref-angle').value}°</li>
                </ul>
                <p><strong>Optimization Strategy:</strong></p>
                <ul>
                    <li>Search Range: ${document.getElementById('opt-d-min').value}m - ${document.getElementById('opt-d-max').value}m</li>
                    <li>LHS Samples: ${document.getElementById('opt-samples').value} points</li>
                    <li>Payload Mass: ${document.getElementById('opt-mass').value} kg</li>
                </ul>
            </div>
            <div>
                <p><strong>Survivability Targets:</strong></p>
                <ul>
                    <li>β Target: ${document.getElementById('target-beta-val').value} (±${document.getElementById('target-beta-tol').value})</li>
                    <li>Heat Flux: ${document.getElementById('target-heat-val').value} (±${document.getElementById('target-heat-tol').value})</li>
                    <li>Peak G: ${document.getElementById('target-g-val').value} (±${document.getElementById('target-g-tol').value})</li>
                </ul>
                <p><strong>Environment:</strong></p>
                <ul>
                    <li>Preset: ${document.getElementById('env-preset').value}</li>
                    <li>Vstream: ${document.getElementById('env-vstream').value} m/s</li>
                    <li>Chemistry: ${document.getElementById('env-chem-mode').value}</li>
                    <li>Steady State: ${document.getElementById('env-steady-state').checked ? 'ON' : 'OFF'}</li>
                    <li>Backend: ${document.getElementById('solver-backend').value.toUpperCase()}</li>
                    ${document.getElementById('solver-backend').value === 'pyfluent' ? `<li>Remote: ${document.getElementById('ssh-host').value}</li>` : ''}
                </ul>
            </div>
        </div>
    `;
    document.getElementById('summary-content').innerHTML = content;
    
    // Refresh preview image
    const img = document.getElementById('domain-preview-img');
    if (img) img.src = 'assets/plots/domain_preview.png?t=' + Date.now();

    // Refresh final video if on page 8
    const vid = document.getElementById('vid-simulation');
    if (vid) {
        vid.src = 'assets/plots/simulation_anim.mp4?t=' + Date.now();
        vid.load();
        vid.play();
    }
}

// Three.js Logic
function init3DView() {
    const viewport = document.getElementById('viewport');
    viewport.innerHTML = ''; // Clear placeholder
    
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x0f172a);
    
    const camera = new THREE.PerspectiveCamera(75, viewport.clientWidth / viewport.clientHeight, 0.1, 1000);
    const renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setSize(viewport.clientWidth, viewport.clientHeight);
    viewport.appendChild(renderer.domElement);
    
    const light = new THREE.DirectionalLight(0xffffff, 1);
    light.position.set(1, 1, 1).normalize();
    scene.add(light);
    scene.add(new THREE.AmbientLight(0x404040));
    
    window.pywebview.api.get_model_paths().then(res => {
        if (res.stl) {
            const loader = new THREE.STLLoader();
            loader.load(res.stl, (geometry) => {
                const material = new THREE.MeshPhongMaterial({ 
                    color: 0x008080, 
                    specular: 0x111111, 
                    shininess: 200,
                    side: THREE.DoubleSide
                });
                const mesh = new THREE.Mesh(geometry, material);
                
                geometry.computeBoundingBox();
                const center = new THREE.Vector3();
                geometry.boundingBox.getCenter(center);
                mesh.position.sub(center);
                scene.add(mesh);
                
                camera.position.set(0, 2, 5);
                
                const controls = new THREE.OrbitControls(camera, renderer.domElement);
                controls.enableDamping = true;
                controls.autoRotate = true;
                controls.autoRotateSpeed = 2.0;
                
                function animate() {
                    requestAnimationFrame(animate);
                    controls.update(); // handles auto-rotate and interaction
                    renderer.render(scene, camera);
                }
                animate();
            });
        }
    });
}

function copyToClipboard(elementId) {
    const text = document.getElementById(elementId).innerText;
    navigator.clipboard.writeText(text).then(() => {
        const btn = event.target;
        const originalText = btn.innerText;
        btn.innerText = "Copied!";
        btn.style.background = "#10b981";
        setTimeout(() => {
            btn.innerText = originalText;
            btn.style.background = "";
        }, 2000);
    });
}

async function testConnection() {
    const btn = document.getElementById('btn-test-conn');
    const status = document.getElementById('test-conn-status');
    const container = document.getElementById('python-install-container');
    const originalText = btn.innerText;
    
    btn.innerText = "Testing...";
    btn.disabled = true;
    status.innerText = "";
    container.innerHTML = "";
    
    const params = {
        ssh_host: document.getElementById('ssh-host').value,
        ssh_user: document.getElementById('ssh-user').value,
        ssh_pass: document.getElementById('ssh-pass').value
    };
    
    try {
        const result = await window.pywebview.api.test_ssh_connection(params);
        if (result.status === "success") {
            status.style.color = "#10b981";
            status.innerText = "✓ " + result.message;
            remoteVerified = true; // Connection verified!
            
            if (result.python_missing) {
                status.style.color = "#f59e0b"; // Warning color
                container.innerHTML = '<button onclick="installRemotePython()" style="background: #f59e0b; color: white; border: none; padding: 8px 16px; border-radius: 8px; cursor: pointer; font-size: 0.8rem; font-weight: 600; animation: pulse 2s infinite;">Should i install python?</button>';
            } else if (result.pyansys_missing) {
                status.style.color = "#f59e0b";
                container.innerHTML = '<button onclick="installPyAnsys()" style="background: #6366f1; color: white; border: none; padding: 8px 16px; border-radius: 8px; cursor: pointer; font-size: 0.8rem; font-weight: 600;">Install PyFluent Lib?</button>';
            } else if (result.ansys_missing) {
                status.style.color = "#ef4444";
                status.innerText += " (Check ANSYS installation path!)";
            }
        } else {
            status.style.color = "#ef4444";
            status.innerText = "✗ " + result.message;
        }
    } catch (err) {
        status.style.color = "#ef4444";
        status.innerText = "✗ API Error: " + err;
    } finally {
        btn.innerText = originalText;
        btn.disabled = false;
    }
}

async function installRemotePython() {
    const container = document.getElementById('python-install-container');
    const status = document.getElementById('test-conn-status');
    
    container.innerHTML = '<button disabled style="background: #94a3b8; color: white; border: none; padding: 8px 16px; border-radius: 8px; font-size: 0.8rem;">Installing...</button>';
    status.innerText = "Installing Python on remote machine...";
    
    const params = {
        ssh_host: document.getElementById('ssh-host').value,
        ssh_user: document.getElementById('ssh-user').value,
        ssh_pass: document.getElementById('ssh-pass').value
    };
    
    try {
        const result = await window.pywebview.api.install_remote_python(params);
        if (result.status === "success") {
            status.style.color = "#10b981";
            status.innerText = "✓ " + result.message;
            container.innerHTML = "";
        } else {
            status.style.color = "#ef4444";
            status.innerText = "✗ " + result.message;
            container.innerHTML = '<button onclick="installRemotePython()" style="background: #f59e0b; color: white; border: none; padding: 8px 16px; border-radius: 8px; cursor: pointer; font-size: 0.8rem;">Retry Install?</button>';
        }
    } catch (err) {
        status.style.color = "#ef4444";
        status.innerText = "✗ Install Error: " + err;
    }
}

async function installPyAnsys() {
    const container = document.getElementById('python-install-container');
    const status = document.getElementById('test-conn-status');
    
    container.innerHTML = '<button disabled style="background: #94a3b8; color: white; border: none; padding: 8px 16px; border-radius: 8px; font-size: 0.8rem;">Installing PyFluent...</button>';
    status.innerText = "Installing PyFluent library on remote machine...";
    
    const params = {
        ssh_host: document.getElementById('ssh-host').value,
        ssh_user: document.getElementById('ssh-user').value,
        ssh_pass: document.getElementById('ssh-pass').value
    };
    
    try {
        const result = await window.pywebview.api.install_pyansys(params);
        if (result.status === "success") {
            status.style.color = "#10b981";
            status.innerText = "✓ " + result.message;
            container.innerHTML = "";
        } else {
            status.style.color = "#ef4444";
            status.innerText = "✗ " + result.message;
            container.innerHTML = '<button onclick="installPyAnsys()" style="background: #6366f1; color: white; border: none; padding: 8px 16px; border-radius: 8px; cursor: pointer; font-size: 0.8rem;">Retry Lib Install?</button>';
        }
    } catch (err) {
        status.style.color = "#ef4444";
        status.innerText = "✗ Install Error: " + err;
    }
}

// Persist Remote Credentials and Backend Selection
function saveRemoteParams() {
    const params = {
        backend: document.getElementById('solver-backend').value,
        host: document.getElementById('ssh-host').value,
        user: document.getElementById('ssh-user').value,
        pass: document.getElementById('ssh-pass').value,
        key: document.getElementById('ssh-key').value,
        dim: document.getElementById('solver-dim').value,
        gpu: document.getElementById('solver-gpu').checked,
        bl_layers: document.getElementById('solver-bl-layers').value,
        viscous: document.getElementById('env-viscous-model').value
    };
    localStorage.setItem('stellar_orion_remote_params', JSON.stringify(params));
}

function loadRemoteParams() {
    const saved = localStorage.getItem('stellar_orion_remote_params');
    if (saved) {
        const params = JSON.parse(saved);
        document.getElementById('solver-backend').value = params.backend || 'sparta';
        document.getElementById('ssh-host').value = params.host || '';
        document.getElementById('ssh-user').value = params.user || '';
        document.getElementById('ssh-pass').value = params.pass || '';
        document.getElementById('ssh-key').value = params.key || '';
        document.getElementById('solver-dim').value = params.dim || '2d';
        document.getElementById('solver-gpu').checked = params.gpu !== false;
        document.getElementById('solver-bl-layers').value = params.bl_layers || '15';
        document.getElementById('env-viscous-model').value = params.viscous || 'sst-k-omega';
        
        // Trigger UI updates
        toggleRemoteFields();
    }
}

// Add listeners to all relevant fields
const persistFields = ['solver-backend', 'ssh-host', 'ssh-user', 'ssh-pass', 'ssh-key', 'solver-dim', 'solver-gpu', 'solver-bl-layers', 'env-viscous-model'];
persistFields.forEach(id => {
    const el = document.getElementById(id);
    if (el) {
        el.addEventListener('input', saveRemoteParams);
        el.addEventListener('change', saveRemoteParams);
    }
});

// Run on load
document.addEventListener('DOMContentLoaded', loadRemoteParams);

// Update collectParams and persist logic for SSH Key
function updateParamsWithKey() {
    const originalRun = window.pywebview.api.run_optimization;
    // We don't actually need to wrap it, just ensure the object sent has the key
}

// Ensure the key is collected in all API calls
const originalTest = testConnection;
testConnection = async function() {
    // This is already using document.getElementById, so it will pick up the new value if we add it to the params object in script.js
};

// Connection Verification Guard
let remoteVerified = false;

// Override changePage to enforce testing
const originalChangePage = window.changePage;
window.changePage = function(delta) {
    const backend = document.getElementById('solver-backend').value;
    const currentPage = window.currentPage || 1; // Assuming currentPage is tracked
    
    if (currentPage === 5 && delta > 0 && !remoteVerified) {
        const status = document.getElementById('test-readiness-status');
        status.style.color = "#ef4444";
        status.innerText = "✗ Please test solver readiness first!";
        
        const btnNext = document.getElementById('btn-next');
        btnNext.innerText = "Verify Readiness First";
        btnNext.style.background = "#64748b";
        
        setTimeout(() => {
            btnNext.innerText = "Continue";
            btnNext.style.background = "";
        }, 3000);
        return;
    }
    
    // Proceed if verified or SPARTA
    if (typeof originalChangePage === 'function') {
        originalChangePage(delta);
    } else {
        // Fallback for page navigation logic
        if (delta > 0) nextPage();
        else prevPage();
    }
};

// Reset verification on input change
const remoteInputs = ['ssh-host', 'ssh-user', 'ssh-pass', 'ssh-key', 'solver-backend'];
remoteInputs.forEach(id => {
    document.getElementById(id).addEventListener('input', () => {
        if (document.getElementById('solver-backend').value === 'pyfluent') {
            remoteVerified = false;
        } else {
            remoteVerified = true;
        }
    });
});

async function testReadiness() {
    const backend = document.getElementById('solver-backend').value;
    const btn = document.getElementById('btn-test-readiness');
    const status = document.getElementById('test-readiness-status');
    const originalText = btn.innerText;
    
    btn.innerText = "Testing...";
    btn.disabled = true;
    status.innerText = "";
    
    try {
        let result;
        if (backend === 'sparta') {
            result = await window.pywebview.api.test_sparta_readiness();
        } else {
            const params = {
                ssh_host: document.getElementById('ssh-host').value,
                ssh_user: document.getElementById('ssh-user').value,
                ssh_pass: document.getElementById('ssh-pass').value,
                ssh_key: document.getElementById('ssh-key').value
            };
            result = await window.pywebview.api.test_ssh_connection(params);
        }
        
        if (result.status === "success") {
            status.style.color = "#10b981";
            status.innerText = "✓ " + result.message;
            remoteVerified = true;
            document.getElementById('btn-run-test').style.display = "block";
            document.getElementById('test-verbose-logs-container').style.display = "none"; // Hide if success
            
            if (result.python_missing) {
                status.style.color = "#f59e0b";
                document.getElementById('python-install-container').innerHTML = '<button onclick="installRemotePython()" style="background: #f59e0b; color: white; border: none; padding: 8px 16px; border-radius: 8px; cursor: pointer; font-size: 0.8rem; font-weight: 600;">Should i install python?</button>';
            } else if (result.pyansys_missing) {
                status.style.color = "#f59e0b";
                document.getElementById('python-install-container').innerHTML = '<button onclick="installPyAnsys()" style="background: #6366f1; color: white; border: none; padding: 8px 16px; border-radius: 8px; cursor: pointer; font-size: 0.8rem; font-weight: 600;">Install PyFluent Lib?</button>';
            }
        } else {
            status.style.color = "#ef4444";
            status.innerText = "✗ Readiness Test Failed. See logs below.";
            remoteVerified = false;
            
            // Show detailed error in log console
            const logArea = document.getElementById('test-verbose-logs');
            const logContainer = document.getElementById('test-verbose-logs-container');
            logContainer.style.display = "block";
            logArea.style.color = "#ef4444"; // Error red
            logArea.innerText = "[CRITICAL READINESS ERROR]\n" + result.message;
        }
    } catch (err) {
        status.style.color = "#ef4444";
        status.innerText = "✗ API Error. See logs below.";
        remoteVerified = false;
        
        const logArea = document.getElementById('test-verbose-logs');
        document.getElementById('test-verbose-logs-container').style.display = "block";
        logArea.style.color = "#ef4444";
        logArea.innerText = "[API ERROR]\n" + err;
    } finally {
        btn.innerText = originalText;
        btn.disabled = false;
    }
}

function onBackendChange() {
    toggleRemoteFields();
    remoteVerified = false; // Force re-test for the new backend
    document.getElementById('test-readiness-status').innerText = "";
    document.getElementById('python-install-container').innerHTML = "";
}

async function runIntegrationTest() {
    const btn = document.getElementById('btn-run-test');
    const status = document.getElementById('test-readiness-status');
    const logArea = document.getElementById('test-verbose-logs');
    
    btn.disabled = true;
    btn.innerText = "Running Test...";
    document.getElementById('test-verbose-logs-container').style.display = "block";
    logArea.innerText = "[*] Starting 100-step simulation dry run...\n";
    status.innerText = "Simulating...";
    
    const params = {
        ssh_host: document.getElementById('ssh-host').value,
        ssh_user: document.getElementById('ssh-user').value,
        ssh_pass: document.getElementById('ssh-pass').value,
        ssh_key: document.getElementById('ssh-key').value
    };
    
    try {
        const result = await window.pywebview.api.run_integration_test(params);
        logArea.innerText += result.log;
        logArea.scrollTop = logArea.scrollHeight;
        
        if (result.status === "success") {
            status.style.color = "#10b981";
            status.innerText = "✓ Integration Test Success!";
        } else {
            status.style.color = "#ef4444";
            status.innerText = "✗ Integration Test Failed!";
        }
    } catch (err) {
        status.style.color = "#ef4444";
        status.innerText = "✗ API Error: " + err;
        logArea.innerText += "\n[CRITICAL ERROR] " + err;
    } finally {
        btn.disabled = false;
        btn.innerText = "Run 100-Step Dry Run";
    }
}
