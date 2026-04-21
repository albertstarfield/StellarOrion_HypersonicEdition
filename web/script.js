let currentPage = 1;
const totalPages = 8;

window.onload = () => {
    initBackgroundEffects();
    initVariabilityListeners();
    setTimeout(() => {
        const splash = document.getElementById('splash');
        if (splash) {
            splash.style.opacity = '0';
            setTimeout(() => splash.style.display = 'none', 800);
        }
    }, 1500);

    // Initialize Mermaid
    if (typeof mermaid !== 'undefined') {
        mermaid.initialize({ 
            startOnLoad: false, 
            theme: 'dark',
            securityLevel: 'loose',
            fontFamily: 'Inter'
        });
    }
};

function initVariabilityListeners() {
    const varCheckboxes = [
        'v-diameter', 'v-angle', 'v-toroids', 'v-nose', 
        'v-thick', 'v-scallop-pts', 'v-scallop-ang', 'v-mass'
    ];
    varCheckboxes.forEach(id => {
        const el = document.getElementById(id);
        if (el) {
            el.addEventListener('change', updateLHSSamples);
        }
    });
}


function initBackgroundEffects() {
    const container = document.getElementById('star-container');
    if (!container) return;
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
    if (currentPage === 3 || currentPage === 7) {
        const bar = document.getElementById(currentPage === 7 ? 'opt-progress-bar' : 'progress-bar');
        if (bar && bar.style.width !== '100%' && bar.style.width !== '0%') {
            console.log("Process in progress, navigation locked.");
            return;
        }
    }

    // Enforce Solver Readiness Guard for Page 5 -> 6
    if (currentPage === 5 && step > 5 && !remoteVerified) {
        const status = document.getElementById('test-readiness-status');
        if (status) {
            status.style.color = "#ef4444";
            status.innerText = "✗ Please test solver readiness first!";
        }
        return;
    }

    if (step === 3 && currentPage === 2) {
        generateGeometry();
    } else if (step === 7 && currentPage === 6) {
        startOptimization();
    } else {
        nextStep(step);
    }
}

function nextStep(step) {
    const currentPageEl = document.getElementById(`page-${currentPage}`);
    if (currentPageEl) currentPageEl.classList.remove('active');
    
    currentPage = step;
    
    const nextPageEl = document.getElementById(`page-${currentPage}`);
    if (nextPageEl) nextPageEl.classList.add('active');

    const btnPrev = document.getElementById('btn-prev');
    if (btnPrev) btnPrev.style.display = currentPage === 1 ? 'none' : 'block';
    
    const nextBtn = document.getElementById('btn-next');
    if (nextBtn) {
        if (currentPage === 3 || currentPage === 7) {
            nextBtn.style.display = 'none';
        } else {
            nextBtn.style.display = 'block';
            nextBtn.innerText = currentPage === 8 ? 'Finish' : 'Continue';
        }

        if (currentPage === 5) {
            if (!remoteVerified) {
                nextBtn.disabled = true;
                nextBtn.style.opacity = "0.5";
                nextBtn.style.cursor = "not-allowed";
            }
        } else {
            nextBtn.disabled = false;
            nextBtn.style.opacity = "1";
            nextBtn.style.cursor = "pointer";
        }
    }

    document.querySelectorAll('.step-item').forEach((s, idx) => {
        s.classList.toggle('active', idx + 1 === currentPage);
    });

    document.querySelectorAll('.dot').forEach((d, idx) => {
        d.classList.toggle('active', idx + 1 === currentPage);
    });

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
    const el = document.getElementById('env-preset');
    if (!el) return;
    const val = el.value;
    const msisPanel = document.getElementById('msis-panel');
    if (msisPanel) msisPanel.style.display = (val === 'nrlmsis') ? 'block' : 'none';
    fetchAtmosphereData();
}

async function toggleRemoteFields() {
    const backendEl = document.getElementById('solver-backend');
    if (!backendEl) return;
    const val = backendEl.value;
    const remotePanel = document.getElementById('remote-fields');
    const hostField = document.getElementById('ssh-host');
    const userField = document.getElementById('ssh-user');
    
    if (val === 'pyfluent' || val === 'pyfluent_local') {
        if (remotePanel) remotePanel.style.display = 'block';
        if (val === 'pyfluent_local') {
            if (hostField) {
                hostField.value = "localhost";
                hostField.disabled = true;
                hostField.style.background = "rgba(0,0,0,0.05)"; 
            }
            try {
                const localUser = await window.pywebview.api.get_local_user();
                if (userField) {
                    userField.value = localUser;
                    userField.disabled = true;
                    userField.style.background = "rgba(0,0,0,0.05)";
                }
            } catch (e) { console.error(e); }
        } else {
            if (hostField) {
                hostField.disabled = false;
                hostField.style.background = "white";
            }
            if (userField) {
                userField.disabled = false;
                userField.style.background = "white";
            }
        }
    } else {
        if (remotePanel) remotePanel.style.display = 'none';
    }
}

async function fetchAtmosphereData() {
    const getVal = (id) => document.getElementById(id) ? document.getElementById(id).value : null;
    const params = {
        env_preset: getVal('env-preset'),
        msis_alt: getVal('msis-alt'),
        msis_lat: getVal('msis-lat'),
        msis_lon: getVal('msis-lon'),
        msis_f107: getVal('msis-f107'),
        msis_ap: getVal('msis-ap')
    };
    const res = await window.pywebview.api.get_atmosphere_data(params);
    if (res) {
        const nrhoEl = document.getElementById('env-nrho');
        const tempEl = document.getElementById('env-temp-inf');
        if (nrhoEl) nrhoEl.value = res.nrho.toExponential(2);
        if (tempEl) tempEl.value = res.temp.toFixed(1);
    }
}

function generateGeometry() {
    const getVal = (id) => document.getElementById(id) ? document.getElementById(id).value : null;
    const getCheck = (id) => document.getElementById(id) ? document.getElementById(id).checked : false;
    
    const params = {
        diameter: getVal('ref-diameter'),
        angle: getVal('ref-angle'),
        toroids: getVal('ref-toroids'),
        mass: getVal('mass'),
        thickness: getVal('thickness'),
        nose_radius: getVal('nose-radius'),
        scallop_pts: getVal('scallop-pts'),
        scallop_angle: getVal('scallop-angle'),
        nose_type: getVal('nose-type'),
        flat_skin: getCheck('flat-skin')
    };
    window.pywebview.api.generate_cad_preview(params);
    nextStep(3);
}

function startOptimization() {
    nextStep(7);
    const getVal = (id) => {
        const el = document.getElementById(id);
        if (!el) return null;
        return (el.type === 'checkbox') ? el.checked : el.value;
    };

    const optParams = {
        // Backend & Remote
        solver: getVal('solver-backend'),
        ssh_host: getVal('ssh-host'),
        ssh_user: getVal('ssh-user'),
        ssh_pass: getVal('ssh-pass'),
        ssh_key: getVal('ssh-key'),
        solver_dim: getVal('solver-dim'),
        solver_gpu: getVal('solver-gpu'),
        solver_bl_layers: getVal('solver-bl-layers'),

        // Optimization
        samples: getVal('opt-samples'),
        d_min: getVal('opt-d-min'),
        d_max: getVal('opt-d-max'),
        
        // Base Geometry
        base_diameter: getVal('ref-diameter'),
        base_angle: getVal('ref-angle'),
        base_toroids: getVal('ref-toroids'),
        base_nose: getVal('nose-radius'),
        base_thick: getVal('thickness'),
        base_scallop_pts: getVal('scallop-pts'),
        base_scallop_ang: getVal('scallop-angle'),
        base_mass: getVal('mass'),

        // Variability (Checkboxes)
        v_diameter: getCheck('v-diameter'),
        v_angle: getCheck('v-angle'),
        v_toroids: getCheck('v-toroids'),
        v_nose: getCheck('v-nose'),
        v_thick: getCheck('v-thick'),
        v_scallop_pts: getCheck('v-scallop-pts'),
        v_scallop_ang: getCheck('v-scallop-ang'),
        v_mass: getCheck('v-mass'),

        // Deltas
        delta_angle: getVal('delta-angle'),
        delta_toroids: getVal('delta-toroids'),
        delta_nose: getVal('delta-nose'),
        delta_thick: getVal('delta-thick'),
        delta_scallop_pts: getVal('delta-scallop-pts'),
        delta_scallop_ang: getVal('delta-scallop-ang'),
        delta_mass: getVal('delta-mass'),

        // Physics & Env
        env_preset: getVal('env-preset'),
        env_nrho: getVal('env-nrho'),
        env_temp_inf: getVal('env-temp-inf'),
        env_vstream: getVal('env-vstream'),
        env_duration: getVal('env-duration'),
        env_thermal_lag: getVal('env-thermal-lag'),
        env_viscous_model: getVal('env-viscous-model'),
        env_chem_mode: getVal('env-chem-mode'),
        env_steady_state: getCheck('env-steady-state'),
        env_steady_tol: getVal('env-steady-tol'),
        pinn_accel: getCheck('pinn-accel'),
        env_temp: getVal('env-temp'),
        env_step: getVal('env-step'),
        env_fnum: getVal('env-fnum'),
        env_react: getVal('env-react'),
        env_run: getVal('env-run'),

        // Domain
        env_xmin: getVal('env-xmin'),
        env_xmax: getVal('env-xmax'),
        env_ymax: getVal('env-ymax'),
        env_zthick: getVal('env-zthick')
    };
    
    window.pywebview.api.run_optimization(optParams);
}

function getCheck(id) {
    const el = document.getElementById(id);
    return el ? el.checked : false;
}

// REMOTE ORCHESTRATION & DIAGNOSTICS
let remoteVerified = false;
let remoteCaptureInterval = null;

async function onBackendChange() {
    await toggleRemoteFields();
    const backendEl = document.getElementById('solver-backend');
    if (backendEl) {
        remoteVerified = (backendEl.value === 'sparta');
    }
    const status = document.getElementById('test-readiness-status');
    if (status) status.innerText = "";
    const installContainer = document.getElementById('python-install-container');
    if (installContainer) installContainer.innerHTML = "";
    lockContinueButton();
}

function lockContinueButton() {
    const nextBtn = document.getElementById('btn-next');
    if (nextBtn && currentPage === 5 && !remoteVerified) {
        nextBtn.disabled = true;
        nextBtn.style.opacity = "0.5";
    } else if (nextBtn) {
        nextBtn.disabled = false;
        nextBtn.style.opacity = "1";
    }
}

async function testReadiness() {
    startRemoteAutoCapture();
    const backendEl = document.getElementById('solver-backend');
    if (!backendEl) return;
    const backend = backendEl.value;
    const btn = document.getElementById('btn-test-readiness');
    const status = document.getElementById('test-readiness-status');
    const originalText = btn ? btn.innerText : "Test";
    
    if (btn) {
        btn.innerText = "Testing...";
        btn.disabled = true;
    }
    if (status) status.innerText = "";
    
    try {
        let result;
        const getVal = (id) => document.getElementById(id) ? document.getElementById(id).value : '';
        if (backend === 'sparta') {
            result = await window.pywebview.api.test_sparta_readiness();
        } else {
            const params = {
                ssh_host: getVal('ssh-host'),
                ssh_user: getVal('ssh-user'),
                ssh_pass: getVal('ssh-pass'),
                ssh_key: getVal('ssh-key')
            };
            result = await window.pywebview.api.test_ssh_connection(params);
        }
        
        if (result.status === "success") {
            if (status) {
                status.style.color = "#10b981";
                status.innerText = "✓ " + result.message;
            }
            remoteVerified = true;
            
            if (result.arch === "AMD64") logReadiness("[SYSTEM] Architecture: AMD64. Status Quo.");
            else if (result.arch === "ARM64") logReadiness("[SYSTEM] Architecture: ARM64. Bleeding Edge.");

            const installContainer = document.getElementById('python-install-container');
            if (installContainer) {
                if (result.message && result.message.includes("Native ARM64 Python detected")) {
                    installContainer.innerHTML = '<button onclick="purgeArmPython()" class="btn-purge">Purge ARM Python</button>';
                } else if (result.python_missing) {
                    installContainer.innerHTML = '<button onclick="installRemotePython()" class="btn-install">Install x64 Python</button>';
                } else if (result.pyansys_missing) {
                    installContainer.innerHTML = '<button onclick="installPyAnsys()" class="btn-install">Install PyFluent Libs</button>';
                } else if (result.sparta_missing) {
                    installContainer.innerHTML = '<button onclick="buildSpartaImage()" class="btn-install">Build SPARTA Image</button>';
                }
            }
            
            const integrationBtn = document.getElementById('btn-run-test');
            if (integrationBtn && !result.python_missing && !result.pyansys_missing) {
                integrationBtn.style.display = "block";
            }
            lockContinueButton();
        } else {
            if (status) {
                status.style.color = "#ef4444";
                status.innerText = "✗ Readiness Test Failed.";
            }
            logReadiness("[ERROR] " + result.message);
            
            const installContainer = document.getElementById('python-install-container');
            if (installContainer && result.sparta_missing) {
                installContainer.innerHTML = '<button onclick="buildSpartaImage()" class="btn-install">Build SPARTA Image</button>';
            }
        }
    } catch (e) {
        if (status) status.innerText = "✗ Error: " + e;
    } finally {
        if (btn) {
            btn.innerText = originalText;
            btn.disabled = false;
        }
        setTimeout(stopRemoteAutoCapture, 15000);
    }
}

async function captureRemoteView() {
    const container = document.getElementById('remote-view-container');
    const img = document.getElementById('remote-screen-img');
    const placeholder = document.getElementById('remote-screen-placeholder');
    const backendEl = document.getElementById('solver-backend');
    if (!backendEl) return;
    const backend = backendEl.value;
    
    if (backend !== 'pyfluent' && backend !== 'pyfluent_local') return;
    if (container) container.style.display = "block";
    
    const getVal = (id) => document.getElementById(id) ? document.getElementById(id).value : '';
    const params = {
        ssh_host: getVal('ssh-host'),
        ssh_user: getVal('ssh-user'),
        ssh_pass: getVal('ssh-pass'),
        ssh_key: getVal('ssh-key')
    };
    
    const res = await window.pywebview.api.capture_remote_screen(params);
    if (res.status === "success") {
        if (img) {
            img.src = res.image_url;
            img.style.display = "block";
        }
        if (placeholder) placeholder.style.display = "none";
    }
}

function startRemoteAutoCapture() {
    if (remoteCaptureInterval) clearInterval(remoteCaptureInterval);
    captureRemoteView();
    remoteCaptureInterval = setInterval(captureRemoteView, 5000);
}

function stopRemoteAutoCapture() {
    if (remoteCaptureInterval) {
        clearInterval(remoteCaptureInterval);
        remoteCaptureInterval = null;
    }
}

function logReadiness(msg) {
    const logArea = document.getElementById('test-verbose-logs');
    const container = document.getElementById('test-verbose-logs-container');
    if (container) container.style.display = "block";
    if (logArea) {
        logArea.innerText += msg + "\n";
        logArea.scrollTop = logArea.scrollHeight;
    }
}

async function installRemotePython() {
    startRemoteAutoCapture();
    const status = document.getElementById('test-readiness-status');
    if (status) status.innerText = "Installing x64 Python...";
    const getVal = (id) => document.getElementById(id) ? document.getElementById(id).value : '';
    const params = {
        ssh_host: getVal('ssh-host'),
        ssh_user: getVal('ssh-user'),
        ssh_pass: getVal('ssh-pass'),
        ssh_key: getVal('ssh-key')
    };
    const res = await window.pywebview.api.install_remote_python(params);
    if (res.status === "success") testReadiness();
    setTimeout(stopRemoteAutoCapture, 10000);
}

async function installPyAnsys() {
    startRemoteAutoCapture();
    const status = document.getElementById('test-readiness-status');
    if (status) status.innerText = "Installing PyFluent...";
    const getVal = (id) => document.getElementById(id) ? document.getElementById(id).value : '';
    const params = {
        ssh_host: getVal('ssh-host'),
        ssh_user: getVal('ssh-user'),
        ssh_pass: getVal('ssh-pass'),
        ssh_key: getVal('ssh-key')
    };
    const res = await window.pywebview.api.install_pyansys(params);
    if (res.status === "success") testReadiness();
    setTimeout(stopRemoteAutoCapture, 10000);
}

async function purgeArmPython() {
    const status = document.getElementById('test-readiness-status');
    if (status) status.innerText = "Purging ARM64 Python...";
    const getVal = (id) => document.getElementById(id) ? document.getElementById(id).value : '';
    const params = {
        ssh_host: getVal('ssh-host'),
        ssh_user: getVal('ssh-user'),
        ssh_pass: getVal('ssh-pass'),
        ssh_key: getVal('ssh-key')
    };
    const res = await window.pywebview.api.purge_arm_python(params);
    if (res.status === "success") testReadiness();
}

function saveRemoteParams() {
    const getVal = (id) => document.getElementById(id) ? document.getElementById(id).value : '';
    const getCheck = (id) => document.getElementById(id) ? document.getElementById(id).checked : false;
    const params = {
        backend: getVal('solver-backend'),
        host: getVal('ssh-host'),
        user: getVal('ssh-user'),
        pass: getVal('ssh-pass'),
        key: getVal('ssh-key'),
        dim: getVal('solver-dim'),
        gpu: getCheck('solver-gpu'),
        bl_layers: getVal('solver-bl-layers'),
        viscous: getVal('env-viscous-model')
    };
    localStorage.setItem('stellar_orion_remote_params', JSON.stringify(params));
}

function loadRemoteParams() {
    const saved = localStorage.getItem('stellar_orion_remote_params');
    if (saved) {
        const params = JSON.parse(saved);
        const setVal = (id, val) => { if (document.getElementById(id)) document.getElementById(id).value = val; };
        const setCheck = (id, val) => { if (document.getElementById(id)) document.getElementById(id).checked = val; };
        
        setVal('solver-backend', params.backend || 'sparta');
        setVal('ssh-host', params.host || '');
        setVal('ssh-user', params.user || '');
        setVal('ssh-pass', params.pass || '');
        setVal('ssh-key', params.key || '');
        setVal('solver-dim', params.dim || '2d');
        setCheck('solver-gpu', params.gpu !== false);
        setVal('solver-bl-layers', params.bl_layers || '15');
        setVal('env-viscous-model', params.viscous || 'sst-k-omega');
        toggleRemoteFields();
    }
}

function init3DView() {
    const viewport = document.getElementById('viewport');
    if (!viewport) return;
    viewport.innerHTML = '';
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
                const material = new THREE.MeshPhongMaterial({ color: 0x008080, specular: 0x111111, shininess: 200, side: THREE.DoubleSide });
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
                function animate() { requestAnimationFrame(animate); controls.update(); renderer.render(scene, camera); }
                animate();
            });
        }
    });
}


// Add listeners to persistence fields
const persistFields = ['solver-backend', 'ssh-host', 'ssh-user', 'ssh-pass', 'ssh-key', 'solver-dim', 'solver-gpu', 'solver-bl-layers', 'env-viscous-model'];
persistFields.forEach(id => {
    const el = document.getElementById(id);
    if (el) {
        el.addEventListener('input', saveRemoteParams);
        el.addEventListener('change', saveRemoteParams);
    }
});

document.addEventListener('DOMContentLoaded', loadRemoteParams);

async function runIntegrationTest() {
    startRemoteAutoCapture();
    const btn = document.getElementById('btn-run-test');
    const originalText = btn ? btn.innerText : "Run Test";
    if (btn) {
        btn.innerText = "Running Test...";
        btn.disabled = true;
    }
    
    logReadiness("[*] Initiating 100-step dry run integration test...");
    
    const backendEl = document.getElementById('solver-backend');
    if (!backendEl) return;
    const backend = backendEl.value;
    
    try {
        let res;
        const getVal = (id) => document.getElementById(id) ? document.getElementById(id).value : '';
        const getCheck = (id) => document.getElementById(id) ? document.getElementById(id).checked : false;
        if (backend === 'sparta') {
            res = await window.pywebview.api.run_sparta_integration_test();
        } else {
            const params = {
                ssh_host: getVal('ssh-host'),
                ssh_user: getVal('ssh-user'),
                ssh_pass: getVal('ssh-pass'),
                ssh_key: getVal('ssh-key'),
                solver_dim: getVal('solver-dim'),
                solver_gpu: getCheck('solver-gpu'),
                env_cores: 2,
                solver_bl_layers: 5,
                viscous_model: "laminar"
            };
            res = await window.pywebview.api.run_integration_test(params);
        }
        
        if (res.status === "success") {
            logReadiness("[SUCCESS] Integration test complete!");
            if (res.log) logReadiness(res.log);
        } else {
            logReadiness("[ERROR] Integration test failed.");
            if (res.log) logReadiness(res.log);
            else if (res.message) logReadiness(res.message);
        }
    } catch (e) {
        logReadiness("[EXCEPTION] " + e);
    } finally {
        if (btn) {
            btn.innerText = originalText;
            btn.disabled = false;
        }
        setTimeout(stopRemoteAutoCapture, 10000);
    }
}

function copyToClipboard(id) {
    const el = document.getElementById(id);
    if (!el) return;
    const text = el.innerText || el.value;
    navigator.clipboard.writeText(text).then(() => {
        const btn = event.target;
        const originalText = btn.innerText;
        btn.innerText = "Copied!";
        btn.style.background = "rgba(16, 185, 129, 0.4)";
        setTimeout(() => {
            btn.innerText = originalText;
            btn.style.background = "rgba(16, 185, 129, 0.2)";
        }, 2000);
    }).catch(err => {
        console.error('Failed to copy: ', err);
    });
}

async function buildSpartaImage() {
    const status = document.getElementById('test-readiness-status');
    if (status) status.innerText = "Building SPARTA Image...";
    logReadiness("[*] Initiating local Docker build for 'sparta-hysp'...");
    
    try {
        const res = await window.pywebview.api.build_sparta_image();
        if (res.status === "success") {
            logReadiness("[SUCCESS] SPARTA Docker image built successfully!");
            testReadiness(); // Re-test to unlock
        } else {
            logReadiness("[ERROR] SPARTA build failed.");
            if (res.log) logReadiness(res.log);
        }
    } catch (e) {
        logReadiness("[EXCEPTION] " + e);
    }
}

// --- MISSING FUNCTIONS START ---

function syncTarget(metric, type) {
    const range = document.getElementById(`target-${metric}-range`);
    const val = document.getElementById(`target-${metric}-val`);
    if (!range || !val) return;

    if (type === 'range') {
        val.value = range.value;
    } else {
        range.value = val.value;
    }
}

function refreshDomainPreview() {
    const getVal = (id) => document.getElementById(id) ? document.getElementById(id).value : null;
    const params = {
        env_xmin: getVal('env-xmin'),
        env_xmax: getVal('env-xmax'),
        env_ymax: getVal('env-ymax'),
        env_zthick: getVal('env-zthick')
    };
    window.pywebview.api.request_domain_preview(params);
}

function onDomainPreviewReady() {
    const timestamp = new Date().getTime();
    const img1 = document.getElementById('domain-live-preview');
    const img2 = document.getElementById('domain-preview-img');
    
    if (img1) img1.src = `assets/plots/domain_preview.png?t=${timestamp}`;
    if (img2) img2.src = `assets/plots/domain_preview.png?t=${timestamp}`;
}

// --- PROJECT MANUAL LOGIC ---
async function openManual() {
    const overlay = document.getElementById('manual-overlay');
    const loader = document.getElementById('manual-loader');
    const textContainer = document.getElementById('manual-text');
    const searchInput = document.getElementById('manual-search');
    const searchCount = document.getElementById('search-count');
    
    if (!overlay) return;
    
    overlay.style.display = 'flex';
    if (loader) loader.style.display = 'flex';
    if (textContainer) textContainer.innerHTML = '';
    if (searchInput) searchInput.value = '';
    if (searchCount) searchCount.innerText = '';
    
    try {
        const markdown = await window.pywebview.api.get_manual_content();
        if (textContainer && typeof marked !== 'undefined') {
            // Custom renderer to wrap mermaid code blocks
            const renderer = new marked.Renderer();
            const originalCode = renderer.code;
            renderer.code = function(code, lang) {
                if (lang === 'mermaid') {
                    return `<div class="mermaid">${code}</div>`;
                }
                return originalCode.call(this, code, lang);
            };

            textContainer.innerHTML = marked.parse(markdown, { renderer });
            // Store original HTML for search resetting
            textContainer.dataset.originalHtml = textContainer.innerHTML;
            
            // Trigger KaTeX rendering
            if (typeof renderMathInElement !== 'undefined') {
                renderMathInElement(textContainer, {
                    delimiters: [
                        {left: '$$', right: '$$', display: true},
                        {left: '$', right: '$', display: false},
                        {left: '\\(', right: '\\)', display: false},
                        {left: '\\[', right: '\\]', display: true}
                    ],
                    throwOnError : false
                });
            }

            // Trigger Mermaid rendering
            if (typeof mermaid !== 'undefined') {
                mermaid.run();
            }
        } else if (textContainer) {
            // Fallback if marked is not loaded
            textContainer.innerText = markdown;
        }
    } catch (e) {
        if (textContainer) textContainer.innerHTML = `<p style="color: #ef4444;">Error loading documentation: ${e}</p>`;
    } finally {
        if (loader) loader.style.display = 'none';
    }
}

function closeManual() {
    const overlay = document.getElementById('manual-overlay');
    if (overlay) overlay.style.display = 'none';
}

function searchManual() {
    const query = document.getElementById('manual-search').value.trim();
    const textContainer = document.getElementById('manual-text');
    const countEl = document.getElementById('search-count');
    
    if (!textContainer || !textContainer.dataset.originalHtml) return;
    
    if (!query) {
        textContainer.innerHTML = textContainer.dataset.originalHtml;
        countEl.innerText = '';
        if (typeof renderMathInElement !== 'undefined') {
            renderMathInElement(textContainer, {
                delimiters: [
                    {left: '$$', right: '$$', display: true},
                    {left: '$', right: '$', display: false},
                    {left: '\\(', right: '\\)', display: false},
                    {left: '\\[', right: '\\]', display: true}
                ],
                throwOnError : false
            });
        }
        if (typeof mermaid !== 'undefined') {
            mermaid.run();
        }
        return;
    }
    
    // Simple highlight logic using regex (ignoring tags)
    const originalHtml = textContainer.dataset.originalHtml;
    
    // We need to be careful not to break HTML tags. 
    // A robust way is to use a temporary container and traverse nodes.
    const temp = document.createElement('div');
    temp.innerHTML = originalHtml;
    
    let count = 0;
    const regex = new RegExp(`(${query})`, 'gi');
    
    function walk(node) {
        if (node.nodeType === 3) { // Text node
            const matches = node.nodeValue.match(regex);
            if (matches) {
                count += matches.length;
                const span = document.createElement('span');
                span.innerHTML = node.nodeValue.replace(regex, '<mark>$1</mark>');
                node.parentNode.replaceChild(span, node);
            }
        } else if (node.nodeType === 1 && node.tagName !== 'SCRIPT' && node.tagName !== 'STYLE' && node.tagName !== 'MARK' && !node.classList.contains('mermaid')) {
            for (let i = node.childNodes.length - 1; i >= 0; i--) {
                walk(node.childNodes[i]);
            }
        }
    }
    
    walk(temp);
    textContainer.innerHTML = temp.innerHTML;
    countEl.innerText = count > 0 ? `${count} found` : 'No results';
    
    // Re-trigger KaTeX after search highlighting
    if (typeof renderMathInElement !== 'undefined') {
        renderMathInElement(textContainer, {
            delimiters: [
                {left: '$$', right: '$$', display: true},
                {left: '$', right: '$', display: false},
                {left: '\\(', right: '\\)', display: false},
                {left: '\\[', right: '\\]', display: true}
            ],
            throwOnError : false
        });
    }

    // Re-trigger Mermaid after search highlighting
    if (typeof mermaid !== 'undefined') {
        mermaid.run();
    }

    // If we have matches, scroll to the first one
    if (count > 0) {
        const firstMatch = textContainer.querySelector('mark');
        if (firstMatch) firstMatch.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
}

function updateSummary() {
    const summaryDiv = document.getElementById('summary-content');
    if (!summaryDiv) return;

    const getVal = (id) => {
        const el = document.getElementById(id);
        if (!el) return 'N/A';
        return el.value;
    };
    
    const getCheck = (id) => {
        const el = document.getElementById(id);
        if (!el) return 'N/A';
        return el.checked ? '✓' : '✗';
    };

    const html = `
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
            <div class="summary-section">
                <h4 style="color: var(--primary); margin-bottom: 10px; font-size: 0.8rem; text-transform: uppercase;">Base Geometry</h4>
                <ul style="list-style: none; padding: 0; font-size: 0.85rem; color: var(--text-dim);">
                    <li>Diameter: <strong>${getVal('ref-diameter')} m</strong></li>
                    <li>Cone Angle: <strong>${getVal('ref-angle')}°</strong></li>
                    <li>Toroid Count: <strong>${getVal('ref-toroids')}</strong></li>
                    <li>Nose Radius: <strong>${getVal('nose-radius')} m</strong></li>
                    <li>Thickness: <strong>${getVal('thickness')} m</strong></li>
                    <li>Initial Mass: <strong>${getVal('mass')} kg</strong></li>
                </ul>
            </div>
            <div class="summary-section">
                <h4 style="color: var(--primary); margin-bottom: 10px; font-size: 0.8rem; text-transform: uppercase;">Survivability Targets</h4>
                <ul style="list-style: none; padding: 0; font-size: 0.85rem; color: var(--text-dim);">
                    <li>Ballistic Coeff (β): <strong>${getVal('target-beta-val')} kg/m²</strong></li>
                    <li>Peak Heat Flux: <strong>${getVal('target-heat-val')} W/cm²</strong></li>
                    <li>Peak g-load: <strong>${getVal('target-g-val')} g</strong></li>
                    <li>Internal Temp: <strong>${getVal('target-temp-val')} °C</strong></li>
                    <li>Dynamic Pressure: <strong>${getVal('target-q-val')} Pa</strong></li>
                </ul>
            </div>
            <div class="summary-section" style="grid-column: span 2; border-top: 1px solid rgba(255,255,255,0.1); padding-top: 15px;">
                <h4 style="color: var(--primary); margin-bottom: 10px; font-size: 0.8rem; text-transform: uppercase;">Physics & Environment</h4>
                <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; font-size: 0.85rem; color: var(--text-dim);">
                    <div>Model: <strong>${getVal('env-preset')}</strong></div>
                    <div>V-Stream: <strong>${getVal('env-vstream')} m/s</strong></div>
                    <div>Duration: <strong>${getVal('env-duration')} s</strong></div>
                    <div>Viscous: <strong>${getVal('env-viscous-model')}</strong></div>
                    <div>Chemistry: <strong>${getVal('env-chem-mode')}</strong></div>
                    <div>Steady State: <strong>${getCheck('env-steady-state')}</strong></div>
                    <div>DeepXDE Tensor: <strong style="color: ${getCheck('pinn-accel') === '✓' ? '#10b981' : '#ef4444'}">${getCheck('pinn-accel')}</strong></div>
                </div>
            </div>
            <div class="summary-section" style="grid-column: span 2; border-top: 1px solid rgba(255,255,255,0.1); padding-top: 15px;">
                <h4 style="color: var(--primary); margin-bottom: 10px; font-size: 0.8rem; text-transform: uppercase;">Optimization Search Space (Variability)</h4>
                <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; font-size: 0.85rem; color: var(--text-dim);">
                    <div>Diameter: <strong>${getCheck('v-diameter')}</strong></div>
                    <div>Angle: <strong>${getCheck('v-angle')}</strong></div>
                    <div>Toroids: <strong>${getCheck('v-toroids')}</strong></div>
                    <div>Nose Rad: <strong>${getCheck('v-nose')}</strong></div>
                    <div>Skin Thk: <strong>${getCheck('v-thick')}</strong></div>
                    <div>Scal. Pts: <strong>${getCheck('v-scallop-pts')}</strong></div>
                    <div>Scal. Ang: <strong>${getCheck('v-scallop-ang')}</strong></div>
                    <div>Mass: <strong>${getCheck('v-mass')}</strong></div>
                </div>
            </div>
            <div class="summary-section" style="grid-column: span 2; background: rgba(0,0,0,0.2); padding: 15px; border-radius: 12px; margin-top: 10px;">
                <h4 style="color: #a855f7; margin-bottom: 10px; font-size: 0.8rem; text-transform: uppercase;">Solver & Backend</h4>
                <div style="display: flex; gap: 30px; font-size: 0.85rem; color: var(--text-dim);">
                    <div>Backend: <strong style="color: #fff;">${getVal('solver-backend').toUpperCase()}</strong></div>
                    <div>Host: <strong style="color: #fff;">${getVal('ssh-host') || 'Localhost'}</strong></div>
                    <div>Dimension: <strong style="color: #fff;">${getVal('solver-dim').toUpperCase()}</strong></div>
                    <div>GPU: <strong style="color: #fff;">${getCheck('solver-gpu')}</strong></div>
                </div>
            </div>
        </div>
    `;
    summaryDiv.innerHTML = html;
}

function updateLHSSamples() {
    const varCheckboxes = [
        'v-diameter', 'v-angle', 'v-toroids', 'v-nose', 
        'v-thick', 'v-scallop-pts', 'v-scallop-ang', 'v-mass'
    ];
    let numChecked = 0;
    varCheckboxes.forEach(id => {
        const el = document.getElementById(id);
        if (el && el.checked) numChecked++;
    });

    const samplesEl = document.getElementById('opt-samples');
    if (samplesEl) {
        // Dynamic LHS logic: 12 base samples + 8 per active dimension
        // Minimizing to 12 if none selected, or up to 64 if all 8 selected
        // Using a rule of thumb: Samples = max(12, numChecked * 8)
        const newCount = Math.max(12, numChecked * 8);
        samplesEl.value = newCount;
        
        // Subtle visual highlight to show the value changed
        samplesEl.style.transition = 'all 0.3s ease';
        samplesEl.style.boxShadow = '0 0 10px var(--primary-glow)';
        setTimeout(() => {
            samplesEl.style.boxShadow = 'none';
        }, 600);
    }
}

// --- MISSING FUNCTIONS END ---
