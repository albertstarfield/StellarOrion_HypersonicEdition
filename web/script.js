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
        status.style.color = "#ef4444";
        status.innerText = "✗ Please test solver readiness first!";
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
    document.getElementById(`page-${currentPage}`).classList.remove('active');
    currentPage = step;
    document.getElementById(`page-${currentPage}`).classList.add('active');

    document.getElementById('btn-prev').style.display = currentPage === 1 ? 'none' : 'block';
    const nextBtn = document.getElementById('btn-next');
    if (currentPage === 3 || currentPage === 7) {
        nextBtn.style.display = 'none';
    } else {
        nextBtn.style.display = 'block';
        nextBtn.innerText = currentPage === 8 ? 'Finish' : 'Continue';
    }

    document.querySelectorAll('.step-item').forEach((s, idx) => {
        s.classList.toggle('active', idx + 1 === currentPage);
    });

    const nextBtnEl = document.getElementById('btn-next');
    if (currentPage === 5) {
        if (!remoteVerified) {
            nextBtnEl.disabled = true;
            nextBtnEl.style.opacity = "0.5";
            nextBtnEl.style.cursor = "not-allowed";
        }
    } else {
        nextBtnEl.disabled = false;
        nextBtnEl.style.opacity = "1";
        nextBtnEl.style.cursor = "pointer";
    }

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
    const val = document.getElementById('env-preset').value;
    document.getElementById('msis-panel').style.display = (val === 'nrlmsis') ? 'block' : 'none';
    fetchAtmosphereData();
}

async function toggleRemoteFields() {
    const val = document.getElementById('solver-backend').value;
    const remotePanel = document.getElementById('remote-fields');
    const hostField = document.getElementById('ssh-host');
    const userField = document.getElementById('ssh-user');
    
    if (val === 'pyfluent' || val === 'pyfluent_local') {
        remotePanel.style.display = 'block';
        if (val === 'pyfluent_local') {
            hostField.value = "localhost";
            hostField.disabled = true;
            hostField.style.background = "rgba(0,0,0,0.05)"; 
            try {
                const localUser = await window.pywebview.api.get_local_user();
                userField.value = localUser;
                userField.disabled = true;
                userField.style.background = "rgba(0,0,0,0.05)";
            } catch (e) { console.error(e); }
        } else {
            hostField.disabled = false;
            hostField.style.background = "white";
            userField.disabled = false;
            userField.style.background = "white";
        }
    } else {
        remotePanel.style.display = 'none';
    }
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
    window.pywebview.api.generate_cad_preview(params);
    nextStep(3);
}

function startOptimization() {
    nextStep(7);
    const optParams = {
        solver: document.getElementById('solver-backend').value,
        ssh_host: document.getElementById('ssh-host').value,
        ssh_user: document.getElementById('ssh-user').value,
        ssh_pass: document.getElementById('ssh-pass').value,
        ssh_key: document.getElementById('ssh-key').value,
        samples: document.getElementById('opt-samples').value,
        // ... (all other params from previous state)
    };
    window.pywebview.api.run_optimization(optParams);
}

// REMOTE ORCHESTRATION & DIAGNOSTICS
let remoteVerified = false;
let remoteCaptureInterval = null;

async function onBackendChange() {
    await toggleRemoteFields();
    remoteVerified = (document.getElementById('solver-backend').value === 'sparta');
    document.getElementById('test-readiness-status').innerText = "";
    document.getElementById('python-install-container').innerHTML = "";
    lockContinueButton();
}

function lockContinueButton() {
    const nextBtn = document.getElementById('btn-next');
    if (currentPage === 5 && !remoteVerified) {
        nextBtn.disabled = true;
        nextBtn.style.opacity = "0.5";
    } else {
        nextBtn.disabled = false;
        nextBtn.style.opacity = "1";
    }
}

async function testReadiness() {
    startRemoteAutoCapture();
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
            
            if (result.arch === "AMD64") logReadiness("[SYSTEM] Architecture: AMD64. Status Quo.");
            else if (result.arch === "ARM64") logReadiness("[SYSTEM] Architecture: ARM64. Bleeding Edge.");

            if (result.message && result.message.includes("Native ARM64 Python detected")) {
                document.getElementById('python-install-container').innerHTML = '<button onclick="purgeArmPython()" class="btn-purge">Purge ARM Python</button>';
            } else if (result.python_missing) {
                document.getElementById('python-install-container').innerHTML = '<button onclick="installRemotePython()" class="btn-install">Install x64 Python</button>';
            } else if (result.pyansys_missing) {
                document.getElementById('python-install-container').innerHTML = '<button onclick="installPyAnsys()" class="btn-install">Install PyFluent Libs</button>';
            }
            
            if (!result.python_missing && !result.pyansys_missing) {
                document.getElementById('btn-run-test').style.display = "block";
            }
            lockContinueButton();
        } else {
            status.style.color = "#ef4444";
            status.innerText = "✗ Readiness Test Failed.";
            logReadiness("[ERROR] " + result.message);
        }
    } catch (e) {
        status.innerText = "✗ Error: " + e;
    } finally {
        btn.innerText = originalText;
        btn.disabled = false;
        setTimeout(stopRemoteAutoCapture, 15000);
    }
}

async function captureRemoteView() {
    const container = document.getElementById('remote-view-container');
    const img = document.getElementById('remote-screen-img');
    const placeholder = document.getElementById('remote-screen-placeholder');
    const backend = document.getElementById('solver-backend').value;
    
    if (backend !== 'pyfluent' && backend !== 'pyfluent_local') return;
    container.style.display = "block";
    
    const params = {
        ssh_host: document.getElementById('ssh-host').value,
        ssh_user: document.getElementById('ssh-user').value,
        ssh_pass: document.getElementById('ssh-pass').value,
        ssh_key: document.getElementById('ssh-key').value
    };
    
    const res = await window.pywebview.api.capture_remote_screen(params);
    if (res.status === "success") {
        img.src = res.image_url;
        img.style.display = "block";
        placeholder.style.display = "none";
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
    document.getElementById('test-verbose-logs-container').style.display = "block";
    logArea.innerText += msg + "\n";
    logArea.scrollTop = logArea.scrollHeight;
}

async function installRemotePython() {
    startRemoteAutoCapture();
    const status = document.getElementById('test-readiness-status');
    status.innerText = "Installing x64 Python...";
    const params = {
        ssh_host: document.getElementById('ssh-host').value,
        ssh_user: document.getElementById('ssh-user').value,
        ssh_pass: document.getElementById('ssh-pass').value,
        ssh_key: document.getElementById('ssh-key').value
    };
    const res = await window.pywebview.api.install_remote_python(params);
    if (res.status === "success") testReadiness();
    setTimeout(stopRemoteAutoCapture, 10000);
}

async function installPyAnsys() {
    startRemoteAutoCapture();
    const status = document.getElementById('test-readiness-status');
    status.innerText = "Installing PyFluent...";
    const params = {
        ssh_host: document.getElementById('ssh-host').value,
        ssh_user: document.getElementById('ssh-user').value,
        ssh_pass: document.getElementById('ssh-pass').value,
        ssh_key: document.getElementById('ssh-key').value
    };
    const res = await window.pywebview.api.install_pyansys(params);
    if (res.status === "success") testReadiness();
    setTimeout(stopRemoteAutoCapture, 10000);
}

async function purgeArmPython() {
    const status = document.getElementById('test-readiness-status');
    status.innerText = "Purging ARM64 Python...";
    const params = {
        ssh_host: document.getElementById('ssh-host').value,
        ssh_user: document.getElementById('ssh-user').value,
        ssh_pass: document.getElementById('ssh-pass').value,
        ssh_key: document.getElementById('ssh-key').value
    };
    const res = await window.pywebview.api.purge_arm_python(params);
    if (res.status === "success") testReadiness();
}

// ... (Rest of utility functions like copyLogs, saveRemoteParams, loadRemoteParams, init3DView etc)

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

function copyLogs() {
    const logArea = document.getElementById('test-verbose-logs');
    navigator.clipboard.writeText(logArea.innerText).then(() => {
        const btn = document.getElementById('btn-copy-logs');
        const old = btn.innerText;
        btn.innerText = "Copied!";
        setTimeout(() => btn.innerText = old, 2000);
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
    const originalText = btn.innerText;
    btn.innerText = "Running Test...";
    btn.disabled = true;
    
    logReadiness("[*] Initiating 100-step dry run integration test...");
    
    const params = {
        ssh_host: document.getElementById('ssh-host').value,
        ssh_user: document.getElementById('ssh-user').value,
        ssh_pass: document.getElementById('ssh-pass').value,
        ssh_key: document.getElementById('ssh-key').value,
        solver_dim: document.getElementById('solver-dim').value,
        solver_gpu: document.getElementById('solver-gpu').checked,
        env_cores: 2,
        solver_bl_layers: 5,
        viscous_model: "laminar"
    };
    
    try {
        const res = await window.pywebview.api.run_integration_test(params);
        if (res.status === "success") {
            logReadiness("[SUCCESS] Integration test complete!");
            logReadiness(res.log);
        } else {
            logReadiness("[ERROR] Integration test failed.");
            logReadiness(res.log);
        }
    } catch (e) {
        logReadiness("[EXCEPTION] " + e);
    } finally {
        btn.innerText = originalText;
        btn.disabled = false;
        setTimeout(stopRemoteAutoCapture, 10000);
    }
}
