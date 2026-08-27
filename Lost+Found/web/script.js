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
    if (currentPage === 8) refreshFinalPlots();
}

function refreshFinalPlots() {
    const timestamp = new Date().getTime();
    const plotIds = ['img-3d-velocity', 'img-3d-mach', 'img-stag', 'img-knudsen', 'img-residence', 'img-scallop-temp'];
    plotIds.forEach(id => {
        const el = document.getElementById(id);
        if (el) {
            const currentSrc = el.src.split('?')[0];
            el.src = `${currentSrc}?t=${timestamp}`;
        }
    });
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

function applyLauncherPreset() {
    const preset = document.getElementById('launcher-preset').value;
    const dField = document.getElementById('fairing-diameter');
    const hField = document.getElementById('fairing-height');
    
    const presets = {
        'delta-iv': { d: 4.572, h: 16.485 },
        'starship': { d: 8.0, h: 17.24 },
        'new-glenn': { d: 6.35, h: 17.836 },
        'atlas-v': { d: 4.57, h: 12.927 },
        'ariane-5': { d: 5.4, h: 17.0 }
    };
    
    if (presets[preset]) {
        dField.value = presets[preset].d;
        hField.value = presets[preset].h;
        
        // Visual feedback
        [dField, hField].forEach(el => {
            el.style.borderColor = 'var(--primary)';
            el.style.boxShadow = '0 0 10px var(--primary-glow)';
            setTimeout(() => {
                el.style.borderColor = 'var(--glass-border)';
                el.style.boxShadow = 'none';
            }, 800);
        });
    }
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

function togglePayloadInput() {
    const checkbox = document.getElementById('enable-payload');
    const container = document.getElementById('payload-options-container');
    const defaultCheckbox = document.getElementById('default-payload');
    const fileContainer = document.getElementById('payload-path-container');
    
    if (checkbox && container) {
        container.style.display = checkbox.checked ? 'block' : 'none';
        if (checkbox.checked && defaultCheckbox && fileContainer) {
            fileContainer.style.display = defaultCheckbox.checked ? 'none' : 'block';
        }
    }
}

function applyMaterialPreset() {
    const preset = document.getElementById('tps-material-preset').value;
    const densityEl = document.getElementById('tps-density');
    const cpEl = document.getElementById('tps-cp');
    const emissEl = document.getElementById('tps-emissivity');
    const maxTempEl = document.getElementById('tps-max-temp');

    const materials = {
        'sic': { rho: 1468.0, cp: 1100.0, eps: 0.75, maxT: 2073.0 },
        'pyrogel': { rho: 110.0, cp: 1000.0, eps: 0.90, maxT: 1373.0 },
        'kapton': { rho: 3100.0, cp: 1090.0, eps: 0.12, maxT: 773.0 }
    };

    const data = materials[preset];
    if (data) {
        densityEl.value = data.rho;
        cpEl.value = data.cp;
        emissEl.value = data.eps;
        maxTempEl.value = data.maxT;
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
        flat_skin: getCheck('flat-skin'),
        payload: getCheck('enable-payload'),
        default_payload: getCheck('default-payload'),
        payload_file: getVal('payload-file')
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
        sparta_gpu: getVal('sparta-gpu'),
        verbose: getCheck('verbose-log'),
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
        grid_factor: getVal('env-grid-factor'),

        env_domain_type: getVal('env-domain-type'),
        // Domain
        env_xmin: getVal('env-xmin'),
        env_xmax: getVal('env-xmax'),
        env_ymax: getVal('env-ymax'),
        env_zthick: getVal('env-zthick'),

        // Payload
        payload: getCheck('enable-payload'),
        default_payload: getCheck('default-payload'),
        payload_file: getVal('payload-file'),

        // Material Properties
        tps_material: getVal('tps-material-preset'),
        tps_density: getVal('tps-density'),
        tps_cp: getVal('tps-cp'),
        tps_emissivity: getVal('tps-emissivity'),
        tps_max_temp: getVal('tps-max-temp'),
        thermal_lag: getVal('thermal-lag')
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
    const viscousModelEl = document.getElementById('env-viscous-model');
    const viscousWarningEl = document.getElementById('viscous-warning');
    
    if (backendEl) {
        const isSparta = (backendEl.value === 'sparta');
        const isOpenFoam = (backendEl.value === 'openfoam');
        remoteVerified = isSparta || isOpenFoam;
        
        if (viscousModelEl) {
            viscousModelEl.disabled = isSparta;
            viscousModelEl.style.opacity = isSparta ? "0.5" : "1";
            viscousModelEl.style.cursor = isSparta ? "not-allowed" : "pointer";
            viscousModelEl.style.background = isSparta ? "rgba(0,0,0,0.1)" : "#f8fafc";
            
            // Auto-select laminar if sparta (purely for visual logic, though setting is ignored)
            if (isSparta) viscousModelEl.value = "laminar";
        }
        
        if (viscousWarningEl) {
            viscousWarningEl.style.display = isSparta ? "block" : "none";
        }

        const spartaGpuContainer = document.getElementById('sparta-gpu-container');
        if (spartaGpuContainer) {
            spartaGpuContainer.style.display = isSparta ? "flex" : "none";
        }

        const remoteViewContainer = document.getElementById('remote-view-container');
        if (remoteViewContainer) {
            remoteViewContainer.style.display = (isOpenFoam || backendEl.value.includes('pyfluent')) ? 'block' : 'none';
        }
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
        } else if (backend === 'openfoam') {
            result = await window.pywebview.api.test_openfoam_readiness();
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
            
            if (backend === 'openfoam') {
                const placeholder = document.getElementById('remote-screen-placeholder');
                if (placeholder) {
                    placeholder.innerHTML = 
                        '<div style="text-align: center; padding: 20px;">' +
                        '<p style="color: #10b981; font-weight: 600; margin-bottom: 10px;">✓ OpenFOAM VNC Server Ready</p>' +
                        '<button onclick="window.open(\'http://localhost:6080/vnc.html\', \'_blank\')" class="btn" style="background: #6366f1; color: white; border: none; padding: 10px 20px; border-radius: 8px; cursor: pointer; font-weight: 600;">Launch OpenFOAM GUI (noVNC)</button>' +
                        '</div>';
                    const remoteImg = document.getElementById('remote-screen-img');
                    if (remoteImg) remoteImg.style.display = 'none';
                }
            }

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
    
    if (backend !== 'pyfluent' && backend !== 'pyfluent_local' && backend !== 'openfoam') return;
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
        viscous: getVal('env-viscous-model'),
        verbose: getCheck('verbose-log')
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
        setCheck('verbose-log', params.verbose !== false);
        onBackendChange();
    } else {
        onBackendChange();
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
const persistFields = ['solver-backend', 'ssh-host', 'ssh-user', 'ssh-pass', 'ssh-key', 'solver-dim', 'solver-gpu', 'sparta-gpu', 'verbose-log', 'solver-bl-layers', 'env-viscous-model'];
persistFields.forEach(id => {
    const el = document.getElementById(id);
    if (el) {
        el.addEventListener('input', saveRemoteParams);
        el.addEventListener('change', saveRemoteParams);
    }
});

// --- AUTOSAVE & DRAFT LOGIC ---
let autosaveInterval = null;

function startAutosave() {
    if (autosaveInterval) return;
    autosaveInterval = setInterval(async () => {
        // Only autosave if we are past the welcome screen (Page 2+)
        if (currentPage < 2) return;
        
        const params = gatherAllParams();
        try {
            await window.pywebview.api.autosave_draft(params, currentPage);
            console.log("Draft autosaved at page " + currentPage);
        } catch (e) { console.error("Autosave failed:", e); }
    }, 10000);
}

function gatherAllParams() {
    const params = {};
    const inputs = document.querySelectorAll('input, select, textarea');
    inputs.forEach(el => {
        if (!el.id) return;
        if (el.type === 'checkbox') {
            params[el.id] = el.checked;
        } else {
            params[el.id] = el.value;
        }
    });
    // Add current session info
    params['draft_name'] = "Session_" + new Date().toISOString().split('T')[0];
    return params;
}

function applyParams(params) {
    if (!params) return;
    Object.keys(params).forEach(id => {
        const el = document.getElementById(id);
        if (!el) return;
        if (el.type === 'checkbox') {
            el.checked = params[id];
        } else {
            el.value = params[id];
        }
    });
    
    // Trigger necessary updates
    if (params['solver-backend']) onBackendChange();
    if (params['env-preset']) toggleMSIS();
}

// Start autosave once DOM is ready and initialized
document.addEventListener('DOMContentLoaded', () => {
    loadRemoteParams();
    const stepsEl = document.getElementById('env-run');
    if (stepsEl) stepsEl.addEventListener('input', onSimStepsChange);
    onSimStepsChange();
    
    // Start the 10s autosave heartbeat
    startAutosave();
});

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

function onPinnAccelChange() {
    const pinnAccel = document.getElementById('pinn-accel');
    const steadyState = document.getElementById('env-steady-state');
    if (!pinnAccel || !steadyState) return;
    
    if (pinnAccel.checked) {
        steadyState.checked = true;
        steadyState.disabled = true;
        steadyState.parentElement.style.opacity = "0.7";
    } else {
        steadyState.disabled = false;
        steadyState.parentElement.style.opacity = "1";
    }
}

function onSteadyStateChange() {
    // If PINN is off, user can toggle this freely.
}

function onSimStepsChange() {
    const stepsEl = document.getElementById('env-run');
    const pinnAccel = document.getElementById('pinn-accel');
    const forcePinn = document.getElementById('force-pinn');
    const pinnWarning = document.getElementById('pinn-fidelity-warning');
    
    if (!stepsEl || !pinnAccel || !forcePinn) return;
    
    const steps = parseInt(stepsEl.value);
    const threshold = 1000;
    
    if (steps < threshold && !forcePinn.checked) {
        pinnAccel.checked = false;
        pinnAccel.disabled = true;
        pinnAccel.style.opacity = "0.5";
        pinnAccel.parentElement.style.opacity = "0.5";
        if (pinnWarning) {
            pinnWarning.style.display = "block";
            pinnWarning.innerText = "⚠️ LOW FIDELITY: Sim steps < 1000. PINN training may be unstable or inaccurate.";
        }
    } else {
        pinnAccel.disabled = false;
        pinnAccel.style.opacity = "1";
        pinnAccel.parentElement.style.opacity = "1";
        if (pinnWarning) {
            if (steps < threshold) {
                pinnWarning.style.display = "block";
                pinnWarning.innerText = "⚠️ LOW FIDELITY: Training with override switch.";
            } else {
                pinnWarning.style.display = "none";
            }
        }
    }
    onPinnAccelChange(); // Sync steady state requirement
}

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
        env_domain_type: getVal('env-domain-type'),
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
    if (textContainer) {
        textContainer.innerHTML = '';
        textContainer.style.display = 'none';
    }
    if (searchInput) searchInput.value = '';
    if (searchCount) searchCount.innerText = '';
    
    try {
        const markdown = await window.pywebview.api.get_manual_content();
        if (textContainer && typeof marked !== 'undefined') {
            // Modern marked configuration (v12+)
            // Use marked.use to merge the custom renderer with defaults
            marked.use({
                renderer: {
                    code(obj) {
                        const code = (typeof obj === 'object' && obj !== null) ? obj.text : arguments[0];
                        const lang = (typeof obj === 'object' && obj !== null) ? obj.lang : arguments[1];
                        
                        if (lang === 'mermaid') {
                            return `<div class="mermaid">${code}</div>`;
                        }
                        return false; // Use default marked renderer
                    }
                },
                breaks: true,
                gfm: true,
                async: false
            });

            textContainer.innerHTML = marked.parse(markdown);
            // Store original HTML for search resetting
            textContainer.dataset.originalHtml = textContainer.innerHTML;
            
            if (loader) loader.style.display = 'none';
            textContainer.style.display = 'block';

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
                try {
                    await mermaid.run();
                } catch (e) {
                    console.error("Mermaid run error:", e);
                }
            }

            // Generate Table of Contents
            generateToc();
        } else if (textContainer) {
            // Fallback if marked is not loaded
            textContainer.innerText = markdown;
            textContainer.style.display = 'block';
            if (loader) loader.style.display = 'none';
        }
    } catch (e) {
        console.error("Error opening manual:", e);
        if (textContainer) {
            textContainer.style.display = 'block';
            textContainer.innerHTML = `<div class="error-msg" style="color: #ef4444; padding: 20px; text-align: center;">
                <h3>Documentation Engine Error</h3>
                <p>${e.message || e}</p>
                <button onclick="openManual()" class="btn-mini-manual" style="margin-top: 10px;">Retry Load</button>
            </div>`;
        }
    } finally {
        if (loader) loader.style.display = 'none';
    }
}

function closeManual() {
    const overlay = document.getElementById('manual-overlay');
    if (overlay) {
        overlay.classList.add('closing');
        setTimeout(() => {
            overlay.style.display = 'none';
            overlay.classList.remove('closing');
        }, 300);
    }
}

function generateToc() {
    const textContainer = document.getElementById('manual-text');
    const tocContainer = document.getElementById('manual-toc');
    if (!textContainer || !tocContainer) return;
    
    tocContainer.innerHTML = '';
    const headers = textContainer.querySelectorAll('h1, h2, h3');
    
    headers.forEach((header, index) => {
        const text = header.innerText;
        const id = 'header-' + index;
        header.id = id;
        
        const item = document.createElement('div');
        item.className = 'toc-item';
        
        // Check if it's a file header (from backend)
        if (text.startsWith('---') && text.endsWith('---')) {
            item.classList.add('toc-file');
            item.innerText = text.replace(/---/g, '').trim();
        } else {
            item.innerText = text;
            if (header.tagName === 'H2') item.classList.add('toc-h2');
            if (header.tagName === 'H3') item.classList.add('toc-h3');
        }
        
        item.onclick = () => {
            header.scrollIntoView({ behavior: 'smooth', block: 'start' });
            document.querySelectorAll('.toc-item').forEach(i => i.classList.remove('active'));
            item.classList.add('active');
        };
        
        tocContainer.appendChild(item);
    });

    // Scroll synchronization
    const mainArea = document.querySelector('.manual-main');
    if (mainArea) {
        mainArea.onscroll = () => {
            let current = "";
            headers.forEach(header => {
                const top = header.offsetTop - mainArea.offsetTop;
                if (mainArea.scrollTop >= top - 20) {
                    current = header.id;
                }
            });
            
            document.querySelectorAll('.toc-item').forEach(item => {
                item.classList.remove('active');
                if (item.onclick.toString().includes(current)) {
                    item.classList.add('active');
                }
            });
        };
    }
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

function checkStructuralValidity() {
    const angle = parseFloat(document.getElementById('ref-angle')?.value || 60);
    const toroids = parseInt(document.getElementById('ref-toroids')?.value || 7);
    const diameter = parseFloat(document.getElementById('ref-diameter')?.value || 3);
    const thickness = parseFloat(document.getElementById('thickness')?.value || 0.025);
    
    let warnings = [];
    if (angle < 40 || angle > 80) warnings.push(`Cone Angle (${angle}°) is outside Rapisarda (2023) stability bounds (40°-80°).`);
    if (toroids > 12) warnings.push(`Toroid Count (${toroids}) exceeds standard manufacturing limits (max 12).`);
    if (diameter > 15) warnings.push(`Extreme Scale: Diameter (${diameter}m) may exceed current inflation system capacity.`);
    if (thickness < 0.005) warnings.push(`TPS Skin (${thickness}m) is too thin for high-Mach aerothermal protection.`);
    
    return warnings;
}

function updateSummary() {
    const summaryDiv = document.getElementById('summary-content');
    if (!summaryDiv) return;

    const structuralWarnings = checkStructuralValidity();
    let warningHtml = "";
    if (structuralWarnings.length > 0) {
        warningHtml = `
            <div style="background: rgba(239, 68, 68, 0.1); border: 1px solid #ef4444; color: #fca5a5; padding: 12px; border-radius: 8px; margin-bottom: 20px; font-size: 0.8rem;">
                <strong style="display: block; margin-bottom: 5px;">⚠️ Structural Integrity Warnings:</strong>
                <ul style="margin: 0; padding-left: 20px;">
                    ${structuralWarnings.map(w => `<li>${w}</li>`).join('')}
                </ul>
            </div>
        `;
    }

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
        ${warningHtml}
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
                    <li>Total Heat Load: <strong>${getVal('target-hload-val')} J/cm²</strong></li>
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
                    <div>Grid Factor: <strong>${getVal('env-grid-factor')}x</strong></div>
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

// --- OPTIMIZATION HISTORY LOGIC ---

let selectedRunId = null;

async function openHistory() {
    document.getElementById('history-modal').style.display = 'flex';
    await loadHistoryList();
}

function closeHistory() {
    const modal = document.getElementById('history-modal');
    if (modal) {
        modal.classList.add('closing');
        setTimeout(() => {
            modal.style.display = 'none';
            modal.classList.remove('closing');
        }, 300);
    }
}

async function loadHistoryList() {
    const listEl = document.getElementById('history-list');
    listEl.innerHTML = '<div style="text-align: center; padding: 20px;">Loading records...</div>';
    
    try {
        const history = await window.pywebview.api.get_optimization_history();
        if (!history || history.length === 0) {
            listEl.innerHTML = '<div style="text-align: center; padding: 40px; color: var(--text-dim);">No history records found.</div>';
            return;
        }

        listEl.innerHTML = '';
        history.forEach(run => {
            const item = document.createElement('div');
            item.className = `history-item ${selectedRunId === run.id ? 'selected' : ''}`;
            item.setAttribute('data-run-id', run.id);
            item.onclick = () => loadRunDetails(run.id);
            
            const date = new Date(run.timestamp).toLocaleString();
            const statusClass = `badge-${run.status || 'running'}`;
            
            item.innerHTML = `
                <div>
                    <div style="font-weight: 700; font-size: 0.9rem;">${run.name}</div>
                    <div style="font-size: 0.75rem; color: var(--text-dim); margin-top: 3px;">${date}</div>
                </div>
                <div class="badge ${statusClass}">${run.status || 'running'}</div>
            `;
            listEl.appendChild(item);
        });
    } catch (e) {
        listEl.innerHTML = `<div style="text-align: center; padding: 20px; color: #f87171;">Error: ${e}</div>`;
    }
}

async function loadRunDetails(runId) {
    selectedRunId = runId;
    
    // Update selection in list without full re-render for better performance
    document.querySelectorAll('.history-item').forEach(el => {
        el.classList.toggle('selected', el.getAttribute('data-run-id') == runId);
    });

    document.getElementById('history-details-empty').style.display = 'none';
    const content = document.getElementById('history-details-content');
    content.style.display = 'block';
    
    try {
        const run = await window.pywebview.api.get_run_details(runId);
        if (!run) return;

        document.getElementById('hist-run-name').innerText = run.name;
        document.getElementById('hist-run-meta').innerText = new Date(run.timestamp).toLocaleString();
        
        const statusEl = document.getElementById('hist-run-status');
        const status = run.status || 'running';
        statusEl.className = `badge badge-${status}`;
        statusEl.innerText = status.toUpperCase();

        document.getElementById('hist-run-goal').innerText = run.goal ? run.goal.toUpperCase() : 'N/A';
        document.getElementById('hist-run-samples').innerText = run.status === 'draft' ? `Draft (Page ${run.last_page})` : `${run.current_sample} / ${run.samples}`;
        document.getElementById('hist-run-best').innerText = run.best_val ? run.best_val.toFixed(4) : 'N/A';

        // Samples timeline
        const samplesList = document.getElementById('hist-samples-list');
        samplesList.innerHTML = '';
        if (run.samples_data && run.samples_data.length > 0) {
            run.samples_data.forEach((s, idx) => {
                const chip = document.createElement('div');
                chip.className = 'sample-chip';
                chip.innerText = `S${idx + 1}`;
                try {
                    const metrics = JSON.parse(s.metrics);
                    if (metrics && metrics[run.goal]) {
                        chip.title = `Metric: ${metrics[run.goal].toFixed(4)}`;
                    }
                } catch(e) {}
                samplesList.appendChild(chip);
            });
        } else {
            samplesList.innerHTML = `<div style="grid-column: 1/-1; text-align: center; color: var(--text-dim); font-size: 0.8rem; padding: 20px;">
                ${run.status === 'draft' ? 'No simulation data yet (Draft Mode)' : 'No samples recorded yet.'}
            </div>`;
        }

        // Resume button visibility: Drafts and Running runs can be resumed
        const resumeBtn = document.getElementById('btn-resume-run');
        if (run.status === 'draft' || run.status === 'running') {
            resumeBtn.style.display = 'block';
            resumeBtn.innerText = run.status === 'draft' ? 'Resume Draft Session' : 'Resume Optimization';
        } else {
            resumeBtn.style.display = 'none';
        }

    } catch (e) {
        console.error("Error loading run details:", e);
    }
}

async function resumeRun() {
    if (!selectedRunId) return;
    
    try {
        const run = await window.pywebview.api.get_run_details(selectedRunId);
        if (!run) return;

        const msg = run.status === 'draft' ? "Resume this session draft?" : "Resume this optimization run?";
        if (confirm(msg)) {
            closeHistory();
            
            // 1. Apply saved parameters to UI
            if (run.parameters) {
                applyParams(JSON.parse(run.parameters));
            }
            
            // 2. Jump to the saved page
            if (run.last_page) {
                jumpToPage(run.last_page);
            }

            // 3. If it was an active optimization, trigger the backend resume
            if (run.status === 'running') {
                await window.pywebview.api.resume_run_from_history(selectedRunId);
            }
        }
    } catch (e) {
        alert("Error resuming: " + e);
    }
}

async function deleteRun() {
    if (!selectedRunId) return;
    if (confirm("Are you sure you want to delete this record? This cannot be undone.")) {
        await window.pywebview.api.delete_run(selectedRunId);
        selectedRunId = null;
        document.getElementById('history-details-content').style.display = 'none';
        document.getElementById('history-details-empty').style.display = 'flex';
        loadHistoryList();
    }
}

async function openLiteracyCredit() {
    const overlay = document.getElementById('manual-overlay');
    const textContainer = document.getElementById('manual-text');
    const titleEl = document.getElementById('manual-title-text');
    const loader = document.getElementById('manual-loader');
    const toc = document.getElementById('manual-toc');
    const search = document.querySelector('.manual-search-box');

    if (!overlay || !textContainer) return;

    overlay.style.display = 'flex';
    if (loader) loader.style.display = 'block';
    if (toc) toc.style.display = 'none'; // Hide TOC for references
    if (search) search.style.display = 'none'; // Hide search for references
    textContainer.style.display = 'none';
    if (titleEl) titleEl.innerText = "Project Bibliography & Literacy Credit";

    try {
        const markdown = await window.pywebview.api.get_references_content();
        if (typeof marked !== 'undefined') {
            let html = marked.parse(markdown);
            // Highlight citations
            html = html.replace(/\[(\d+)\]/g, '<strong style="color: var(--secondary);">[$1]</strong>');
            textContainer.innerHTML = html;
            textContainer.style.display = 'block';
            
            // Re-trigger KaTeX
            if (typeof renderMathInElement !== 'undefined') {
                renderMathInElement(textContainer, {
                    delimiters: [
                        {left: '$$', right: '$$', display: true},
                        {left: '$', right: '$', display: false}
                    ],
                    throwOnError : false
                });
            }
        } else {
            textContainer.innerText = markdown;
            textContainer.style.display = 'block';
        }
    } catch (e) {
        textContainer.innerHTML = `<p style="color: #ef4444;">Error: ${e}</p>`;
        textContainer.style.display = 'block';
    } finally {
        if (loader) loader.style.display = 'none';
    }
}

async function startGridIndependencyTest() {
    // 1. Move to High-Fidelity SBO Page (Terminal)
    jumpToPage(7);
    
    // 2. Gather current parameters
    const getVal = (id) => {
        const el = document.getElementById(id);
        if (!el) return null;
        return (el.type === 'checkbox') ? el.checked : el.value;
    };
    
    const solver = getVal('solver-backend') || 'sparta';
    const steps = parseInt(getVal('grid-test-steps')) || 1100;
    const factorsStr = getVal('grid-test-factors') || "0.3, 0.5, 0.7, 1.0";
    const headless = getVal('grid-test-headless') ?? true;
    const useGpu = getVal('sparta-gpu') || false;

    appendLog("<br><span style='color: #a855f7; font-weight: 800;'>[SYSTEM] INITIALIZING AUTOMATED GRID INDEPENDENCY STUDY...</span>");
    appendLog(`<span style='color: #a855f7;'>[*] Targeting Grid Factors: [${factorsStr}]</span>`);
    appendLog(`[*] Solver Backend: ${solver.toUpperCase()}`);
    appendLog(`[*] Iterations per Test: ${steps}`);
    appendLog(`[*] GPU Acceleration: ${useGpu ? 'ENABLED' : 'DISABLED'}`);
    appendLog(`[*] Mode: ${headless ? 'HEADLESS' : 'INTERACTIVE'}`);
    appendLog("<span style='color: #a855f7;'>[*] ----------------------------------------------------------------</span>");
    
    // 3. Update Progress Bar
    updateProgress(5);

    // 4. Call Python API
    try {
        await window.pywebview.api.run_grid_independency_test(
            solver, 
            steps, 
            false, // skip_diag
            headless,
            useGpu,
            true,  // is_gui
            factorsStr
        );
        
        appendLog("<br><span style='color: #10b981; font-weight: 800;'>[SUCCESS] GRID INDEPENDENCY STUDY COMPLETE.</span>");
        appendLog("[*] Results archived in individual factor subdirectories.");
        appendLog("[*] Reference Comparison Table generated in terminal above.");
        updateProgress(100);
    } catch (e) {
        appendLog(`<br><span style='color: #ef4444; font-weight: 800;'>[ERROR] Grid study failed: ${e}</span>`);
        updateProgress(0);
    }
}

async function runManimDemo() {
    // 1. Move to Reference Physics Page (Page 3) to show terminal logs
    jumpToPage(3);
    
    appendLog("<br><span style='color: #38bdf8; font-weight: 800;'>[VISUAL] INITIALIZING MANIM DSMC WORKFLOW DEMO...</span>");
    appendLog("[*] This process involves rendering high-fidelity animations of the kinetic cycle.");
    appendLog("[*] Target Steps: Preprocessing -> Grid -> Advection -> Collision -> Chemistry -> Post-processing.");
    
    try {
        const res = await window.pywebview.api.run_manim_demo();
        if (res.status === "started") {
            appendLog("<span style='color: #fbbf24;'>[*] Rendering engine dispatched. Tracking progress...</span>");
        }
    } catch (e) {
        appendLog(`<br><span style='color: #ef4444; font-weight: 800;'>[ERROR] Demo engine failed to start: ${e}</span>`);
    }
}

function showDemoVideo(path) {
    appendLog("<br><span style='color: #10b981; font-weight: 800;'>[SUCCESS] DSMC WORKFLOW VISUALIZATION RENDERED.</span>");
    appendLog(`[*] Media Path: ${path}`);
    
    const confirmMsg = "The DSMC Workflow Visualization is ready! Would you like to open it now in your system's default player?";
    if (confirm(confirmMsg)) {
        window.pywebview.api.open_demo_video(path);
    } else {
        appendLog("[*] Click the 'Visual Demo' button again to re-trigger if needed.");
    }
}
