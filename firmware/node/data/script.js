let token = localStorage.getItem('token');

function escapeHtml(str) {
    if (str == null) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

function showFieldError(inputId, message) {
    let input = document.getElementById(inputId);
    if (!input) return;
    let group = input.closest('.form-group');
    if (!group) return;
    let msgEl = group.querySelector('.validation-message');
    if (!msgEl) {
        msgEl = document.createElement('div');
        msgEl.className = 'validation-message error';
        group.appendChild(msgEl);
    }
    msgEl.textContent = message;
    msgEl.className = 'validation-message error';
    input.setAttribute('aria-invalid', 'true');
    input.setAttribute('aria-describedby', msgEl.id || (msgEl.id = 'err-' + inputId));
}

function clearFieldError(inputId) {
    let input = document.getElementById(inputId);
    if (!input) return;
    let group = input.closest('.form-group');
    if (!group) return;
    let msgEl = group.querySelector('.validation-message');
    if (msgEl) msgEl.className = 'validation-message';
    input.removeAttribute('aria-invalid');
    input.removeAttribute('aria-describedby');
}

function validateRequired(inputId) {
    let input = document.getElementById(inputId);
    if (!input) return true;
    let val = input.value.trim();
    if (!val) {
        showFieldError(inputId, 'This field is required');
        return false;
    }
    clearFieldError(inputId);
    return true;
}

let alertTimer;
let modalResolve = null;

// Lacak apakah field password benar-benar diubah user.
// Backend sengaja TIDAK mengembalikan password (security), sehingga field kosong saat refresh.
// Jika tidak dilacak, menyimpan form akan mengirim password kosong & menimpa password tersimpan.
let pwDirty = { cfg_pass: false, cfg_mqtt_p: false, cfg_ent_password: false };
['cfg_pass', 'cfg_mqtt_p', 'cfg_ent_password'].forEach(id => {
    let el = document.getElementById(id);
    if (el) el.addEventListener('input', () => { pwDirty[id] = true; });
});

const PW_PLACEHOLDER = '•••••••• (leave empty to keep current)';

function showMsg(msg, isErr = false) {
    let box = document.getElementById('alert');
    let icon = isErr ? '✕ ' : '✓ ';
    box.innerText = icon + msg;
    box.className = 'alert-box ' + (isErr ? 'alert-error' : 'alert-success');
    box.style.display = 'block';
    clearTimeout(alertTimer);
    alertTimer = setTimeout(() => box.style.display = 'none', 3000);
}

function setButtonLoading(btn, loading, text) {
    if (!btn) return;
    btn.disabled = loading;
    if (loading) {
        btn.dataset.originalText = btn.innerText;
        btn.innerHTML = '<span class="spinner-sm"></span> Loading…';
    } else {
        btn.innerText = text || btn.dataset.originalText || 'Submit';
    }
}

function showModal(title, body) {
    return new Promise(resolve => {
        modalResolve = resolve;
        document.getElementById('modal-title').innerText = title;
        document.getElementById('modal-body').innerText = body;
        document.getElementById('confirm-modal').classList.add('show');
        document.getElementById('modal-confirm-btn').focus();
    });
}

function closeModal() {
    document.getElementById('confirm-modal').classList.remove('show');
    let resolve = modalResolve;
    modalResolve = null;
    if (resolve) resolve(false);
}

function confirmModal() {
    document.getElementById('confirm-modal').classList.remove('show');
    let resolve = modalResolve;
    modalResolve = null;
    if (resolve) resolve(true);
}

document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
        let modal = document.getElementById('confirm-modal');
        if (modal && modal.classList.contains('show')) {
            closeModal();
            return;
        }
        let sidebar = document.getElementById('sidebarMenu');
        if (sidebar && sidebar.classList.contains('show')) {
            toggleMobileMenu();
        }
    }
});

async function api(path, method = 'GET', body = null) {
    // Local testing bypass for UI preview without backend
    if (window.location.hostname === '127.0.0.1' || window.location.hostname === 'localhost' || window.location.protocol === 'file:') {
        console.log(`[MOCK API] ${method} ${path}`, body || '');
        if (path === '/api/status') {
            return {
                status: 'Connected', ip: '192.168.1.104', rssi: -37,
                mqtt_conn: 'Connected', topic_telemetry: 'smartfarm/node-01/telemetry', topic_control: 'smartfarm/actuator/node-01',
                uptime_s: 605, cpu_mhz: 240, heap_free: 201326, heap_total: 325734
            };
        }
        if (path === '/api/fullconfig') {
            return {
                device: { node_id: 'node-01' },
                security: { admin_user: 'admin' },
                protocols: {
                    wifi: { ssid: 'MyWiFi', ent_enabled: false, ent_username: '', wifi_type: 'open' },
                    mqtt: { server: 'broker.emqx.io', port: 1883, topic_prefix: 'smartfarm', telemetry_interval_ms: 5000, mqtt_disconnect_emergency_stop: true }
                },
                hardware: {
                    inputs: [{ pin: 4, type: 'DIGITAL', pull: 'UP', name: 'Water Sensor' }],
                    outputs: [{ pin: 5, type: 'DIGITAL', name: 'Pump Relay' }],
                    modbus: [{
                        name: 'CWT Soil Sensor', slave_id: 1, baudrate: 9600, registers: [
                            { address: 0, type: 'HOLDING', name: 'Moisture', multiplier: 0.1 },
                            { address: 1, type: 'HOLDING', name: 'Temperature', multiplier: 0.1 }
                        ]
                    }],
                    sensors: [
                        { name: 'BME280 Main', protocol: 'I2C', type: 'BME280', address: '0x76' }
                    ],
                    i2c_sda_pin: 21,
                    i2c_scl_pin: 22
                }
            };
        }
        return { success: true };
    }

    try {
        let opts = { method, headers: {} };
        if (token) opts.headers['Authorization'] = 'Bearer ' + token;
        if (body) {
            opts.headers['Content-Type'] = 'application/x-www-form-urlencoded';
            opts.body = body;
        }
        let res = await fetch(path, opts);
        let data = await res.json();
        if (!res.ok) {
            showMsg(data.error || 'Error', true);
            if (res.status === 401) { logout(); }
            return null;
        }
        return data;
    } catch (e) {
        showMsg('Network error', true); return null;
    }
}

function onWifiTypeChange() {
    let type = document.getElementById('cfg_wifi_type').value;
    let passGroup = document.getElementById('wifi-pass-group');
    let entGroup = document.getElementById('wifi-ent-group');

    if (type === 'open') {
        passGroup.style.display = 'none';
        entGroup.style.display = 'none';
        document.getElementById('cfg_pass').value = '';
    } else if (type === 'wpa_personal') {
        passGroup.style.display = 'block';
        entGroup.style.display = 'none';
    } else if (type === 'wpa_enterprise') {
        passGroup.style.display = 'none';
        entGroup.style.display = 'block';
    }
}

let statusTimer = null;

function checkAuth() {
    // Local testing bypass for UI preview without backend
    if (window.location.hostname === '127.0.0.1' || window.location.hostname === 'localhost' || window.location.protocol === 'file:') {
        document.getElementById('login-container').style.display = 'none';
        document.getElementById('app-container').style.display = 'flex';
        loadStatus();
        loadFullConfig();
        if (typeof onWifiTypeChange === 'function') onWifiTypeChange();
        return;
    }

    if (token) {
        document.getElementById('login-container').style.display = 'none';
        document.getElementById('app-container').style.display = 'flex';
        loadStatus();
        loadFullConfig();
        if (typeof onWifiTypeChange === 'function') onWifiTypeChange();
    } else {
        document.getElementById('login-container').style.display = 'flex';
        document.getElementById('app-container').style.display = 'none';
    }
}

async function doLogin() {
    let u = document.getElementById('login_user').value.trim();
    let p = document.getElementById('login_pass').value.trim();
    let btn = document.querySelector('#login-container button[type="submit"]');
    
    let valid = true;
    if (!u) { showFieldError('login_user', 'Username is required'); valid = false; }
    else { clearFieldError('login_user'); }
    if (!p) { showFieldError('login_pass', 'Password is required'); valid = false; }
    else { clearFieldError('login_pass'); }
    if (!valid) return;
    
    setButtonLoading(btn, true, 'Sign In');
    let d = await api('/api/login', 'POST', `user=${u}&pass=${p}`);
    if (d && d.token) {
        token = d.token;
        localStorage.setItem('token', token);
        checkAuth();
    } else {
        setButtonLoading(btn, false, 'Sign In');
    }
}

function logout() { token = null; localStorage.removeItem('token'); checkAuth(); }

function toggleMobileMenu() {
    const header = document.querySelector('.mobile-header');
    if (header) {
        const height = header.offsetHeight;
        document.documentElement.style.setProperty('--mobile-header-height', height + 'px');
    }
    document.getElementById('sidebarMenu').classList.toggle('show');
    document.getElementById('sidebar-backdrop').classList.toggle('show');
}

function switchView(event, id) {
    document.querySelectorAll('.view-section').forEach(e => e.classList.remove('active'));
    document.querySelectorAll('.menu-item').forEach(e => e.classList.remove('active'));
    document.getElementById('view-' + id).classList.add('active');
    event.currentTarget.classList.add('active');
    document.getElementById('sidebarMenu').classList.remove('show');
    document.getElementById('sidebar-backdrop').classList.remove('show');

    if (statusTimer) clearInterval(statusTimer);
    if (id === 'status') {
        loadStatus();
        statusTimer = setInterval(loadStatus, 3000);
    }
}

// Status & Formatters
function formatTime(sec) {
    let h = Math.floor(sec / 3600);
    let m = Math.floor((sec % 3600) / 60);
    let s = Math.floor(sec % 60);
    return `${h}h ${m}m ${s}s`;
}

async function loadStatus() {
    let refreshBtn = document.querySelector('#view-status .card .outline');
    setButtonLoading(refreshBtn, true, 'Refresh');
    let d = await api('/api/status');
    setButtonLoading(refreshBtn, false, 'Refresh');
    if (d) {
        let connEl = document.getElementById('stat_conn');
        if (connEl) {
            connEl.innerText = d.status;
            connEl.className = d.status === 'Connected' ? 'metric-value success' : 'metric-value warn';
        }

        document.getElementById('stat_ip').innerText = d.ip;

        let mqttEl = document.getElementById('stat_mqtt');
        if (mqttEl) {
            mqttEl.innerText = d.mqtt_conn || '-';
            mqttEl.className = d.mqtt_conn === 'Connected' ? 'metric-value success' : 'metric-value warn';
        }

        let tEl = document.getElementById('info_telemetry');
        if (tEl && d.topic_telemetry) tEl.innerText = d.topic_telemetry;

        let cEl = document.getElementById('info_control');
        if (cEl && d.topic_control) cEl.innerText = d.topic_control;

        let rssiEl = document.getElementById('stat_rssi');
        rssiEl.innerText = d.rssi ? d.rssi + ' dBm' : '-';
        if (d.rssi > -60) rssiEl.className = 'metric-value success';
        else if (d.rssi > -80) rssiEl.className = 'metric-value warn';
        else rssiEl.className = 'metric-value';

        document.getElementById('stat_cpu').innerText = d.cpu_mhz ? d.cpu_mhz + ' MHz' : '-';
        document.getElementById('stat_uptime').innerText = d.uptime_s ? formatTime(d.uptime_s) : '-';

        if (d.heap_free && d.heap_total) {
            let freeKB = (d.heap_free / 1024).toFixed(1);
            let totalKB = (d.heap_total / 1024).toFixed(1);
            let p = ((d.heap_free / d.heap_total) * 100).toFixed(0);
            let hEl = document.getElementById('stat_heap');
            hEl.innerText = `${freeKB} KB / ${totalKB} KB (${p}%)`;
            hEl.className = p < 15 ? 'metric-value warn' : 'metric-value';
        }

        let logsContainer = document.getElementById('mqtt_logs_container');
        if (logsContainer && d.mqtt_logs) {
            let validLogs = d.mqtt_logs.filter(log => log !== null && log !== undefined);
            if (validLogs.length === 0) {
                logsContainer.innerHTML = '<div class="text-muted italic">No logs captured yet. Send telemetry or toggle outputs to see activity here.</div>';
            } else {
                logsContainer.innerHTML = validLogs.map(log => {
                    let color = "#10b981";
                    if (log.includes("Pub FAILED") || log.includes("FAILED") || log.includes("failed")) {
                        color = "#ef4444";
                    } else if (log.includes("Attempting") || log.includes("rc=")) {
                        color = "#f59e0b";
                    } else if (log.includes("Sub Recv:")) {
                        color = "#3b82f6";
                    }
                    return `<div class="log-entry" style="color:${color};">${escapeHtml(log)}</div>`;
                }).join('');
                logsContainer.scrollTop = logsContainer.scrollHeight;
            }
        }
    }
}

async function sendDiscovery() {
    let btn = document.getElementById('btn_discovery');
    setButtonLoading(btn, true, 'Send Discovery Signal');

    let d = await api('/api/publish_discovery', 'POST');
    if (d) {
        if (d.success || d.status === "success") {
            showMsg("Discovery signal sent successfully!");
        } else {
            showMsg(d.message || "Failed to send discovery", true);
        }
    }

    setButtonLoading(btn, false, 'Send Discovery Signal');
}

async function loadFullConfig() {
    let d = await api('/api/fullconfig', 'GET');
    if (d) {
        let wifi = (d.protocols && d.protocols.wifi) || {};
        let mqtt = (d.protocols && d.protocols.mqtt) || {};
        document.getElementById('cfg_node_id').value = d.device.node_id || '';
        if (document.getElementById('cfg_rs485_rx')) {
            document.getElementById('cfg_rs485_rx').value = (d.hardware && d.hardware.rs485_rx != null) ? d.hardware.rs485_rx : 16;
        }
        if (document.getElementById('cfg_rs485_tx')) {
            document.getElementById('cfg_rs485_tx').value = (d.hardware && d.hardware.rs485_tx != null) ? d.hardware.rs485_tx : 17;
        }
        if (document.getElementById('cfg_rs485_de')) {
            document.getElementById('cfg_rs485_de').value = (d.hardware && d.hardware.rs485_de != null) ? d.hardware.rs485_de : 255;
        }
        // I2C global pins
        if (document.getElementById('cfg_i2c_sda')) {
            document.getElementById('cfg_i2c_sda').value = (d.hardware && d.hardware.i2c_sda_pin != null) ? d.hardware.i2c_sda_pin : 21;
        }
        if (document.getElementById('cfg_i2c_scl')) {
            document.getElementById('cfg_i2c_scl').value = (d.hardware && d.hardware.i2c_scl_pin != null) ? d.hardware.i2c_scl_pin : 22;
        }
        document.getElementById('cfg_admin_u').value = (d.security && d.security.admin_user) || '';

        let wifiType = wifi.wifi_type || 'wpa_personal';
        document.getElementById('cfg_wifi_type').value = wifiType;
        onWifiTypeChange();

        document.getElementById('cfg_ssid').value = wifi.ssid || '';
        document.getElementById('cfg_pass').value = '';
        document.getElementById('cfg_pass').placeholder = wifi.password ? PW_PLACEHOLDER : '';
        document.getElementById('cfg_ent_username').value = wifi.ent_username || '';
        document.getElementById('cfg_ent_password').value = '';
        document.getElementById('cfg_ent_password').placeholder = wifi.ent_password ? PW_PLACEHOLDER : '';
        document.getElementById('cfg_mqtt_srv').value = mqtt.server || '';
        document.getElementById('cfg_mqtt_port').value = mqtt.port || '';
        document.getElementById('cfg_mqtt_pre').value = mqtt.topic_prefix || '';
        document.getElementById('cfg_mqtt_u').value = mqtt.user || '';
        document.getElementById('cfg_mqtt_p').value = '';
        document.getElementById('cfg_mqtt_p').placeholder = mqtt.pass ? PW_PLACEHOLDER : '';
        document.getElementById('cfg_mqtt_int').value = mqtt.telemetry_interval_ms || '';
        document.getElementById('cfg_mqtt_emergency_stop').checked = !!mqtt.mqtt_disconnect_emergency_stop;

        pwDirty.cfg_pass = false;
        pwDirty.cfg_mqtt_p = false;
        pwDirty.cfg_ent_password = false;

        renderGpioRows(d.hardware || { inputs: [], outputs: [] });
        renderEmptyStates();
    }
}

function renderEmptyStates() {
    let inputRows = document.getElementById('input-rows');
    let outputRows = document.getElementById('output-rows');
    let modbusRows = document.getElementById('modbus-rows');
    let i2cRows = document.getElementById('i2c-rows');

    if (inputRows && hwInputs.length === 0 && editInputIdx === -1) {
        inputRows.innerHTML = '<div class="empty-state">No inputs configured. Click "+ Add Input" to add one.</div>';
    }
    if (outputRows && hwOutputs.length === 0 && editOutputIdx === -1) {
        outputRows.innerHTML = '<div class="empty-state">No outputs configured. Click "+ Add Output" to add one.</div>';
    }
    if (modbusRows && hwModbus.length === 0 && editModbusIdx === -1) {
        modbusRows.innerHTML = '<div class="empty-state">No Modbus sensors configured. Click "+ Add Modbus Sensor" to add one.</div>';
    }
    if (i2cRows && hwI2C.length === 0 && editI2CIdx === -1) {
        i2cRows.innerHTML = '<div class="empty-state">No I2C sensors configured. Click "+ Add I2C Sensor" to add one.</div>';
    }
}

// GPIO (Hardware) Logic
let hwInputs = [];
let hwOutputs = [];
let hwModbus = [];
let hwI2C = [];
let editInputIdx = -1;
let editOutputIdx = -1;
let editModbusIdx = -1;
let editI2CIdx = -1;

function getUsedGpioPins() {
    let used = new Set();
    hwInputs.forEach(p => {
        if (p.protocol === 'GPIO' || p.protocol === '') used.add(Number(p.pin));
    });
    hwOutputs.forEach(p => {
        if (p.protocol === 'GPIO_OUT' || p.protocol === '') used.add(Number(p.pin));
    });
    return used;
}

function buildGpioPinOptions(currentPin, usedPins) {
    let options = '';
    for (let i = 0; i <= 48; i++) {
        if (!usedPins.has(i) || Number(i) === Number(currentPin)) {
            options += `<option value="${i}" ${Number(i) === Number(currentPin) ? 'selected' : ''}>GPIO ${i}</option>`;
        }
    }
    return options;
}

function refreshGpioViews() {
    drawInputs();
    drawOutputs();
}

function renderGpioRows(hw) {
    hwInputs = hw.inputs || [];
    hwOutputs = hw.outputs || [];
    hwModbus = hw.modbus || [];
    // Strip sda/scl from sensor params — pins are now global
    hwI2C = (hw.sensors || []).map(s => {
        let clean = {};
        for (let k in s) { if (k !== 'sda_pin' && k !== 'scl_pin') clean[k] = s[k]; }
        return clean;
    });
    editInputIdx = -1;
    editOutputIdx = -1;
    editModbusIdx = -1;
    editI2CIdx = -1;
    drawInputs();
    drawOutputs();
    drawModbus();
    drawI2C();
}

function drawInputs() {
    let html = '';
    hwInputs.forEach((p, idx) => {
        let isPcf = p.protocol === 'PCF8575_IN';
        if (editInputIdx === idx) {
            html += `
            <div class="hw-row flex-wrap gap-8">
                <div class="form-field form-field-lg">
                    <label>Interface / Protocol</label>
                    <select onchange="hwInputs[${idx}].protocol=this.value; if(this.value==='PCF8575_IN'){if(!hwInputs[${idx}].i2c_addr)hwInputs[${idx}].i2c_addr='0x20'; if(hwInputs[${idx}].pin>15)hwInputs[${idx}].pin=0;} refreshGpioViews();">
                        <option value="GPIO" ${!isPcf ? 'selected' : ''}>Direct</option>
                        <option value="PCF8575_IN" ${isPcf ? 'selected' : ''}>Expander</option>
                    </select>
                </div>
                ${isPcf ? `
                <div class="form-field">
                    <label>PCF Pin</label>
                    <select onchange="hwInputs[${idx}].pin=parseInt(this.value)">
                        ${Array.from({ length: 16 }, (_, i) => `<option value="${i}" ${p.pin == i ? 'selected' : ''}>P${i}</option>`).join('')}
                    </select>
                </div>
                <div class="form-field form-field-sm">
                    <label>I2C Address</label>
                    <input type="text" value="${escapeHtml(p.i2c_addr || '0x20')}" placeholder="0x20" onchange="hwInputs[${idx}].i2c_addr=this.value.trim()">
                </div>
                ` : `
                <div class="form-field">
                    <label>GPIO Pin</label>
                    <select onchange="hwInputs[${idx}].pin=parseInt(this.value); refreshGpioViews();">
                        ${buildGpioPinOptions(p.pin, getUsedGpioPins())}
                    </select>
                </div>
                <div class="form-field form-field-md">
                    <label>Input Type</label>
                    <select onchange="hwInputs[${idx}].type=this.value">
                        <option value="DIGITAL" ${p.type === 'DIGITAL' ? 'selected' : ''}>DIGITAL</option>
                        <option value="ANALOG" ${p.type === 'ANALOG' ? 'selected' : ''}>ADC</option>
                    </select>
                </div>
                <div class="form-field form-field-md">
                    <label>Pull Resistor</label>
                    <select onchange="hwInputs[${idx}].pull=this.value">
                        <option value="NONE" ${p.pull === 'NONE' ? 'selected' : ''}>NONE</option>
                        <option value="UP" ${p.pull === 'UP' ? 'selected' : ''}>UP</option>
                        <option value="DOWN" ${p.pull === 'DOWN' ? 'selected' : ''}>DOWN</option>
                    </select>
                </div>
                <div class="form-field form-field-md">
                    <label>Interrupt Mode</label>
                    <select onchange="hwInputs[${idx}].interrupt=this.value">
                        <option value="NONE" ${(p.interrupt || 'NONE') === 'NONE' ? 'selected' : ''}>NONE</option>
                        <option value="RISING" ${p.interrupt === 'RISING' ? 'selected' : ''}>RISING</option>
                        <option value="FALLING" ${p.interrupt === 'FALLING' ? 'selected' : ''}>FALLING</option>
                        <option value="CHANGE" ${p.interrupt === 'CHANGE' ? 'selected' : ''}>CHANGE</option>
                    </select>
                </div>
                <div class="form-field form-field-sm">
                    <label>Debounce (ms)</label>
                    <input type="number" min="0" max="5000" value="${p.debounce_ms || 0}" onchange="hwInputs[${idx}].debounce_ms=parseInt(this.value)">
                </div>
                `}
                <div class="form-field form-field-lg">
                    <label>Name Label</label>
                    <input type="text" value="${escapeHtml(p.name)}" placeholder="e.g. Water Sensor" onchange="hwInputs[${idx}].name=this.value">
                </div>
                <div class="form-field form-field-sm flex-col justify-end">
                    <label class="mb-8">Invert Logic</label>
                    <label class="checkbox-label" style="margin:0;">
                        <input type="checkbox" ${p.invert ? 'checked' : ''} onchange="hwInputs[${idx}].invert=this.checked" class="checkbox-input">
                        <span style="font-size:12px;">LOW = Active</span>
                    </label>
                </div>
                <button type="button" class="btn-success" style="margin-top:24px; align-self:flex-end;" onclick="editInputIdx=-1; drawInputs();">Done</button>
            </div>
            `;
        } else {
            let metaDesc = isPcf
                ? `PCF8575 (${escapeHtml(p.i2c_addr || '0x20')}) Pin P${p.pin}${p.invert ? ' | ⇄ Inverted' : ''}`
                : `GPIO ${p.pin} | ${p.type} | Pull: ${p.pull} | IRQ: ${p.interrupt || 'NONE'} | Debounce: ${p.debounce_ms || 0}ms${p.invert ? ' | ⇄ Inverted' : ''}`;
            html += `
            <div class="hw-list-item">
                <div class="hw-info">
                    <span class="hw-name">${escapeHtml(p.name || 'Unnamed Input')}</span>
                    <span class="hw-meta">${metaDesc}</span>
                </div>
                <div class="hw-actions">
                    <button type="button" class="outline btn-touch btn-sm" onclick="editInputIdx=${idx}; drawInputs();">Edit</button>
                    <button type="button" class="danger btn-touch btn-sm" onclick="confirmRemove('Remove this input permanently?', () => { hwInputs.splice(${idx}, 1); if(editInputIdx==${idx}) editInputIdx=-1; else if(editInputIdx > ${idx}) editInputIdx--; drawInputs(); })">Remove</button>
                </div>
            </div>
            `;
        }
    });
    document.getElementById('input-rows').innerHTML = html;
}

function drawOutputs() {
    let html = '';
    hwOutputs.forEach((p, idx) => {
        let isPcf = p.protocol === 'PCF8575_OUT';
        if (editOutputIdx === idx) {
            html += `
            <div class="hw-row flex-wrap gap-8">
                <div class="form-field form-field-lg">
                    <label>Interface / Protocol</label>
                    <select onchange="hwOutputs[${idx}].protocol=this.value; if(this.value==='PCF8575_OUT'){if(!hwOutputs[${idx}].i2c_addr)hwOutputs[${idx}].i2c_addr='0x20'; if(hwOutputs[${idx}].pin>15)hwOutputs[${idx}].pin=0; if(hwOutputs[${idx}].active_low===undefined)hwOutputs[${idx}].active_low=true;} refreshGpioViews();">
                        <option value="GPIO_OUT" ${!isPcf ? 'selected' : ''}>Direct</option>
                        <option value="PCF8575_OUT" ${isPcf ? 'selected' : ''}>Expander</option>
                    </select>
                </div>
                ${isPcf ? `
                <div class="form-field">
                    <label>PCF Pin</label>
                    <select onchange="hwOutputs[${idx}].pin=parseInt(this.value)">
                        ${Array.from({ length: 16 }, (_, i) => `<option value="${i}" ${p.pin == i ? 'selected' : ''}>P${i}</option>`).join('')}
                    </select>
                </div>
                <div class="form-field form-field-sm">
                    <label>I2C Address</label>
                    <input type="text" value="${escapeHtml(p.i2c_addr || '0x20')}" placeholder="0x20" onchange="hwOutputs[${idx}].i2c_addr=this.value.trim()">
                </div>
                <div class="form-field form-field-lg flex-col justify-end">
                    <label class="mb-8">Relay Trigger Mode</label>
                    <label class="checkbox-label" style="margin:0;">
                        <input type="checkbox" ${p.active_low !== false ? 'checked' : ''} onchange="hwOutputs[${idx}].active_low=this.checked" class="checkbox-input">
                        <span style="font-size:12px;">Active LOW (Relay)</span>
                    </label>
                </div>
                ` : `
                <div class="form-field">
                    <label>GPIO Pin</label>
                    <select onchange="hwOutputs[${idx}].pin=parseInt(this.value); refreshGpioViews();">
                        ${buildGpioPinOptions(p.pin, getUsedGpioPins())}
                    </select>
                </div>
                <div class="form-field form-field-md">
                    <label>Output Type</label>
                    <select onchange="hwOutputs[${idx}].type=this.value">
                        <option value="DIGITAL" ${p.type === 'DIGITAL' ? 'selected' : ''}>DIGITAL</option>
                        <option value="PWM" ${p.type === 'PWM' ? 'selected' : ''}>PWM</option>
                    </select>
                </div>
                `}
                <div class="form-field form-field-lg">
                    <label>Name Label</label>
                    <input type="text" value="${escapeHtml(p.name)}" placeholder="e.g. Pump Relay" onchange="hwOutputs[${idx}].name=this.value">
                </div>
                <button type="button" class="btn-success" style="margin-top:24px; align-self:flex-end;" onclick="editOutputIdx=-1; drawOutputs();">Done</button>
            </div>
            `;
        } else {
            let metaDesc = isPcf
                ? `PCF8575 (${escapeHtml(p.i2c_addr || '0x20')}) Pin P${p.pin} | Relay ${p.active_low !== false ? 'Active-LOW' : 'Active-HIGH'}`
                : `GPIO ${p.pin} | ${p.type}`;
            html += `
            <div class="hw-list-item">
                <div class="hw-info">
                    <span class="hw-name">${escapeHtml(p.name || 'Unnamed Output')}</span>
                    <span class="hw-meta">${metaDesc}</span>
                </div>
                <div class="hw-actions">
                    <button type="button" class="outline btn-touch btn-sm" onclick="editOutputIdx=${idx}; drawOutputs();">Edit</button>
                    <button type="button" class="danger btn-touch btn-sm" onclick="confirmRemove('Remove this output permanently?', () => { hwOutputs.splice(${idx}, 1); if(editOutputIdx==${idx}) editOutputIdx=-1; else if(editOutputIdx > ${idx}) editOutputIdx--; drawOutputs(); })">Remove</button>
                </div>
            </div>
            `;
        }
    });
    document.getElementById('output-rows').innerHTML = html;
}

function addInputRow() {
    hwInputs.push({ pin: 0, protocol: 'GPIO', type: 'DIGITAL', pull: 'NONE', name: 'New Input', invert: false, debounce_ms: 0, interrupt: 'NONE', i2c_addr: '0x20' });
    editInputIdx = hwInputs.length - 1;
    drawInputs();
}

function addOutputRow() {
    hwOutputs.push({ pin: 0, protocol: 'GPIO_OUT', type: 'DIGITAL', name: 'New Output', i2c_addr: '0x20', active_low: true });
    editOutputIdx = hwOutputs.length - 1;
    drawOutputs();
}

function drawModbus() {
    let html = '';
    hwModbus.forEach((m, idx) => {
        if (editModbusIdx === idx) {
            let transport = (m.transport || 'RTU').toUpperCase();
            html += `<div class="hw-row flex-col gap-10">
                <div class="flex-wrap gap-10">
                    <div class="form-field form-field-lg"><label>Sensor Name</label><input type="text" value="${escapeHtml(m.name)}" onchange="hwModbus[${idx}].name=this.value"></div>
                    <div class="form-field"><label>Slave ID</label><input type="number" min="1" max="247" value="${m.slave_id}" onchange="hwModbus[${idx}].slave_id=parseInt(this.value)"></div>
                    <div class="form-field form-field-md"><label>Transport</label><select onchange="hwModbus[${idx}].transport=this.value; drawModbus();"><option value="RTU" ${transport === 'RTU' ? 'selected' : ''}>RTU</option><option value="TCP" ${transport === 'TCP' ? 'selected' : ''}>TCP</option></select></div>
                </div>
                <div class="flex-wrap gap-10 mt-10">`;
            if (transport === 'TCP') {
                html += `<div class="form-field form-field-lg"><label>IP Address</label><input type="text" value="${escapeHtml(m.ip_address || '')}" onchange="hwModbus[${idx}].ip_address=this.value" placeholder="192.168.1.100"></div>
                         <div class="form-field"><label>Port</label><input type="number" min="1" max="65535" value="${m.port || 502}" onchange="hwModbus[${idx}].port=parseInt(this.value)"></div>`;
            } else {
                html += `<div class="form-field form-field-md"><label>Baudrate</label><select onchange="hwModbus[${idx}].baudrate=parseInt(this.value)"><option value="4800" ${m.baudrate == 4800 ? 'selected' : ''}>4800</option><option value="9600" ${m.baudrate == 9600 ? 'selected' : ''}>9600</option><option value="19200" ${m.baudrate == 19200 ? 'selected' : ''}>19200</option></select></div>`;
            }
            html += `</div>
                <div class="register-section mt-10">
                    <label class="mb-5 d-block">Registers to Read</label>`;

            m.registers.forEach((r, ridx) => {
                html += `<div class="register-row">
                    <input type="number" placeholder="Register Address" value="${r.address}" onchange="hwModbus[${idx}].registers[${ridx}].address=parseInt(this.value)" class="form-input-sm">
                    <select onchange="hwModbus[${idx}].registers[${ridx}].type=this.value" class="form-select-sm"><option value="HOLDING" ${r.type === 'HOLDING' ? 'selected' : ''}>HOLDING (03)</option><option value="INPUT" ${r.type === 'INPUT' ? 'selected' : ''}>INPUT (04)</option></select>
                    <input type="text" placeholder="Register Name" value="${escapeHtml(r.name)}" onchange="hwModbus[${idx}].registers[${ridx}].name=this.value" class="form-input-sm form-field-lg">
                    <select onchange="hwModbus[${idx}].registers[${ridx}].length=parseInt(this.value)" class="form-select-sm form-field-xs" title="Register Count"><option value="1" ${(r.length || 1) == 1 ? 'selected' : ''}>1 reg</option><option value="2" ${(r.length || 1) == 2 ? 'selected' : ''}>2 reg</option></select>
                    <select onchange="hwModbus[${idx}].registers[${ridx}].data_type=this.value" class="form-select-sm" style="flex:1.5; min-width:90px;" title="Data Type"><option value="UINT16" ${(r.data_type || 'UINT16') === 'UINT16' ? 'selected' : ''}>UINT16</option><option value="INT16" ${(r.data_type || 'UINT16') === 'INT16' ? 'selected' : ''}>INT16</option><option value="FLOAT32" ${(r.data_type || 'UINT16') === 'FLOAT32' ? 'selected' : ''}>FLOAT32</option><option value="INT32" ${(r.data_type || 'UINT32') === 'INT32' ? 'selected' : ''}>INT32</option><option value="UINT32" ${(r.data_type || 'UINT16') === 'UINT32' ? 'selected' : ''}>UINT32</option></select>
                    <input type="number" step="0.01" placeholder="Multiplier" value="${r.multiplier}" onchange="hwModbus[${idx}].registers[${ridx}].multiplier=parseFloat(this.value)" class="form-input-sm form-field-xs">
                    <button type="button" class="danger btn-touch btn-icon" onclick="confirmRemove('Remove this register?', () => { hwModbus[${idx}].registers.splice(${ridx}, 1); drawModbus(); })">X</button>
                </div>`;
            });

            html += `<button type="button" class="outline btn-touch btn-sm mt-10" onclick="hwModbus[${idx}].registers.push({address:0, type:'HOLDING', name:'register_1', length:1, data_type:'UINT16', multiplier:1.0}); drawModbus();">+ Register</button>
                </div>
                <button type="button" class="btn-success mt-10" onclick="editModbusIdx=-1; drawModbus();">Done</button>
            </div>`;
        } else {
            let transport = (m.transport || 'RTU').toUpperCase();
            let meta = `ID: ${m.slave_id}`;
            if (transport === 'TCP') {
                meta += ` | ${escapeHtml(m.ip_address || '?')}:${m.port || 502}`;
            } else {
                meta += ` | Baud: ${m.baudrate}`;
            }
            meta += ` | Regs: ${m.registers.length}`;
            html += `<div class="hw-list-item">
                <div class="hw-info">
                    <span class="hw-name">${escapeHtml(m.name || 'Unnamed Sensor')}</span>
                    <span class="hw-meta">${meta}</span>
                </div>
                <div class="hw-actions">
                    <button type="button" class="outline btn-touch btn-sm" onclick="editModbusIdx=${idx}; drawModbus();">Edit</button>
                    <button type="button" class="danger btn-touch btn-sm" onclick="confirmRemove('Remove this Modbus sensor permanently?', () => { hwModbus.splice(${idx}, 1); if(editModbusIdx==${idx}) editModbusIdx=-1; else if(editModbusIdx > ${idx}) editModbusIdx--; drawModbus(); })">Remove</button>
                </div>
            </div>`;
        }
    });
    document.getElementById('modbus-rows').innerHTML = html;
}

function addModbusSensor() {
    hwModbus.push({ name: 'New Modbus Sensor', slave_id: 1, transport: 'RTU', baudrate: 9600, ip_address: '', port: 502, registers: [] });
    editModbusIdx = hwModbus.length - 1;
    drawModbus();
}

function drawI2C() {
    let html = '';
    hwI2C.forEach((s, idx) => {
        if (editI2CIdx === idx) {
            html += `
            <div class="hw-row flex-wrap gap-8">
                <div class="form-field">
                    <label>Sensor Name</label>
                    <input type="text" value="${escapeHtml(s.name || '')}" onchange="hwI2C[${idx}].name=this.value">
                </div>
                <div class="form-field">
                    <label>Sensor Type</label>
                    <select onchange="hwI2C[${idx}].type=this.value">
                        <option value="INA219" ${(s.type || '') === 'INA219' ? 'selected' : ''}>INA219</option>
                        <option value="BME280" ${(s.type || '') === 'BME280' ? 'selected' : ''}>BME280</option>
                        <option value="DHT12" ${(s.type || '') === 'DHT12' ? 'selected' : ''}>DHT12</option>
                    </select>
                </div>
                <div class="form-field form-field-sm">
                    <label>I2C Address</label>
                    <input type="text" value="${escapeHtml(s.address || '0x40')}" onchange="hwI2C[${idx}].address=this.value">
                </div>
                <div class="flex gap-6 mt-10">
                    <button type="button" class="outline btn-touch btn-sm" onclick="editI2CIdx=-1; drawI2C();">Done</button>
                </div>
            </div>`;
        } else {
            html += `
            <div class="hw-row flex-wrap gap-8">
                <span class="hw-name">${escapeHtml(s.name || 'Unnamed')} (${escapeHtml(s.type || '?')}) @ ${escapeHtml(s.address || '?')}</span>
                <div class="flex gap-6">
                    <button type="button" class="outline btn-touch btn-sm" onclick="editI2CIdx=${idx}; drawI2C();">Edit</button>
                    <button type="button" class="danger btn-touch btn-sm" onclick="confirmRemove('Remove this I2C sensor permanently?', () => { hwI2C.splice(${idx},1); if(editI2CIdx===${idx}) editI2CIdx=-1; else if(editI2CIdx>${idx}) editI2CIdx--; drawI2C(); })">Remove</button>
                </div>
            </div>`;
        }
    });
    document.getElementById('i2c-rows').innerHTML = html;
}

function addI2CSensor() {
    hwI2C.push({ name: 'New I2C Sensor', type: 'INA219', protocol: 'I2C', address: '0x40' });
    editI2CIdx = hwI2C.length - 1;
    drawI2C();
}

// Scanner logic
let scanPollTimer = null;

async function startScanId() {
    let baudChecks = document.querySelectorAll('input[id^="scan_baud_"]:checked');
    let bauds = Array.from(baudChecks).map(cb => cb.value);
    let resDiv = document.getElementById('scan_results');
    let scanBtn = document.querySelector('button[onclick="startScanId()"]');
    let cancelBtn = document.getElementById('btn_cancel_scan');

    if (bauds.length === 0) {
        resDiv.innerHTML = `<div class="text-danger">Please select at least one baudrate.</div>`;
        return;
    }

    if (scanPollTimer) {
        clearInterval(scanPollTimer);
        scanPollTimer = null;
    }

    setButtonLoading(scanBtn, true, 'Scanning...');
    if (cancelBtn) cancelBtn.style.display = 'none';
    resDiv.innerHTML = `<div style="color:var(--primary);">Starting scan on ${bauds.join(', ')} baud...</div>`;

    try {
        let res = await fetch('/api/modbus/start_scan', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
                'Authorization': 'Bearer ' + token
            },
            body: `bauds=${bauds.join(',')}`
        });

        if (!res.ok) {
            let err = await res.json().catch(() => ({}));
            resDiv.innerHTML = `<div class='text-danger'>Failed to start scan: ${escapeHtml(err.error || 'Unknown error')}</div>`;
            setButtonLoading(scanBtn, false, 'Scan All IDs');
            return;
        }

        let data = await res.json();
        if (data.status !== "started") {
            resDiv.innerHTML = `<div class='text-danger'>Scan did not start: ${escapeHtml(data.error || 'Unknown')}</div>`;
            setButtonLoading(scanBtn, false, 'Scan All IDs');
            return;
        }

        if (cancelBtn) cancelBtn.style.display = 'block';
        resDiv.innerHTML = `<div style="color:var(--primary);">Scanning ID 1-247 on ${bauds.join(', ')} baud... <span id="scan_elapsed">0s</span></div>`;

        scanPollTimer = setInterval(async () => {
            try {
                let statusRes = await fetch('/api/modbus/scan_status', {
                    headers: { 'Authorization': 'Bearer ' + token }
                });
                if (!statusRes.ok) return;
                let status = await statusRes.json();

                let elapsed = status.elapsed_ms ? Math.floor(status.elapsed_ms / 1000) : 0;
                let elapsedEl = document.getElementById('scan_elapsed');
                if (elapsedEl) elapsedEl.textContent = elapsed + 's';

                if (status.scanning === false || status.cancelling === true) {
                    clearInterval(scanPollTimer);
                    scanPollTimer = null;
                    if (cancelBtn) cancelBtn.style.display = 'none';
                    setButtonLoading(scanBtn, false, 'Scan All IDs');

                    let results = [];
                    try { results = JSON.parse(status.results || "[]"); } catch (e) { results = []; }

                    if (results.length > 0) {
                        resDiv.innerHTML = `<div class="text-success"><strong>Scan Complete. Found ${results.length} devices:</strong><br>`;
                        results.forEach(item => {
                            resDiv.innerHTML += `✅ Slave ID ${escapeHtml(item.id)} at ${escapeHtml(item.baud)} baud<br>`;
                        });
                        resDiv.innerHTML += "</div>";
                    } else if (status.cancelling) {
                        resDiv.innerHTML = `<div class='text-warning'>Scan cancelled by user.</div>`;
                    } else {
                        resDiv.innerHTML = `<div class="text-warning">Scan complete. No devices found.</div>`;
                    }
                }
            } catch (e) {
                // network error during poll, keep trying
            }
        }, 500);

    } catch (e) {
        resDiv.innerHTML = `<div style='color:var(--danger);'>Network error. Error: ${escapeHtml(e.message)}</div>`;
        setButtonLoading(scanBtn, false, 'Scan All IDs');
        if (cancelBtn) cancelBtn.style.display = 'none';
    }
}

async function cancelScanId() {
    let cancelBtn = document.getElementById('btn_cancel_scan');
    let scanBtn = document.querySelector('button[onclick="startScanId()"]');
    if (cancelBtn) cancelBtn.style.display = 'none';
    if (scanBtn) setButtonLoading(scanBtn, false, 'Scan All IDs');

    try {
        let res = await fetch('/api/modbus/cancel_scan', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
                'Authorization': 'Bearer ' + token
            }
        });

        if (!res.ok) {
            document.getElementById('scan_results').innerHTML = "<div style='color:var(--danger);'>Failed to send cancel.</div>";
        }
    } catch (e) {
        document.getElementById('scan_results').innerHTML = `<div style='color:var(--danger);'>Network error. Error: ${escapeHtml(e.message)}</div>`;
    }
}

async function startScanReg() {
    let id = document.getElementById('scan_id').value;
    let baudChecks = document.querySelectorAll('input[id^="scan_baud_"]:checked');
    let baud = baudChecks.length > 0 ? baudChecks[0].value : '9600';
    let start = parseInt(document.getElementById('scan_reg_start').value);
    let end = parseInt(document.getElementById('scan_reg_end').value);
    let type = document.getElementById('scan_type').value;
    let length = parseInt(document.getElementById('scan_length').value) || 1;
    let resDiv = document.getElementById('scan_results');
    let scanRegBtn = document.querySelector('button[onclick="startScanReg()"]');
    setButtonLoading(scanRegBtn, true, 'Scan Regs');
    resDiv.innerHTML = `Batch scanning ${type} registers ${start} to ${end} on ID ${id} at ${baud} baud...<br>`;

    try {
        let body = `id=${id}&baud=${baud}&type=${type}&start_reg=${start}&end_reg=${end}&length=${length}`;
        let res = await fetch('/api/modbus/scan_reg_batch', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
                'Authorization': 'Bearer ' + token
            },
            body: body
        });

        if (!res.ok) {
            resDiv.innerHTML += "<div class='text-danger'>Failed to start batch scan.</div>";
            return;
        }

        let data = await res.json();
        if (data.status === "completed" && data.results) {
            let foundAny = false;
        data.results.forEach(item => {
                    if (item.success) {
                        resDiv.innerHTML += `<div class="text-success">✅ Reg ${escapeHtml(item.reg)}: Value = ${escapeHtml(item.val)}</div>`;
                        foundAny = true;
                    }
                });
                if (!foundAny) resDiv.innerHTML += "<div class='text-danger'>No valid registers found in range.</div>";
        }
    } catch (e) {
        resDiv.innerHTML += `<div class='text-danger'>Error: ${e.message}</div>`;
    } finally {
        setButtonLoading(scanRegBtn, false, 'Scan Regs');
    }
}

async function saveHardware() {
    if (!await showModal('Confirm', 'Save hardware config and reboot?')) return;
    let btn = document.querySelector('#view-gpio button[type="submit"]');
    setButtonLoading(btn, true, 'Save & Reboot');
    let i2cSda = document.getElementById('cfg_i2c_sda') ? document.getElementById('cfg_i2c_sda').value : 21;
    let i2cScl = document.getElementById('cfg_i2c_scl') ? document.getElementById('cfg_i2c_scl').value : 22;
    let hwPayload = { inputs: hwInputs, outputs: hwOutputs, modbus: hwModbus, sensors: hwI2C, i2c_sda_pin: parseInt(i2cSda), i2c_scl_pin: parseInt(i2cScl) };
    let payload = encodeURIComponent(JSON.stringify(hwPayload));
    let d = await api('/api/hardware', 'POST', `payload=${payload}`);
    setButtonLoading(btn, false, 'Save & Reboot');
    if (d) {
        await loadFullConfig();
        showMsg('Hardware configuration applied.');
    }
}

async function saveDevice() {
    if (!await showModal('Confirm', 'Save device config and reboot?')) return;
    let btn = document.querySelector('#view-device button[type="submit"]');
    setButtonLoading(btn, true, 'Save & Reboot');
    let v = document.getElementById('cfg_node_id').value;
    let d = await api('/api/device', 'POST', `node_id=${v}`);
    setButtonLoading(btn, false, 'Save & Reboot');
    if (d) triggerRebootSequence();
}

async function saveRS485() {
    if (!await showModal('Confirm', 'Save RS485 config and reboot?')) return;
    let btn = document.querySelector('#view-modbus button[type="submit"]');
    setButtonLoading(btn, true, 'Save & Reboot');
    let rx = document.getElementById('cfg_rs485_rx').value;
    let tx = document.getElementById('cfg_rs485_tx').value;
    let de = document.getElementById('cfg_rs485_de').value;
    let body = `rs485_rx=${encodeURIComponent(rx)}&rs485_tx=${encodeURIComponent(tx)}&rs485_de=${encodeURIComponent(de)}`;
    let d = await api('/api/device', 'POST', body);
    setButtonLoading(btn, false, 'Save & Reboot');
    if (d) triggerRebootSequence();
}

async function saveWifi() {
    if (!await showModal('Confirm', 'Save WiFi config and reboot?')) return;
    let btn = document.querySelector('#view-wifi button[type="submit"]');
    setButtonLoading(btn, true, 'Save & Reboot');
    let s = document.getElementById('cfg_ssid').value;
    let type = document.getElementById('cfg_wifi_type').value;
    let p = document.getElementById('cfg_pass').value;
    let entUser = document.getElementById('cfg_ent_username').value;
    let entPass = document.getElementById('cfg_ent_password').value;

    let body = `ssid=${encodeURIComponent(s)}`;
    if (type === 'open') {
        body += `&pass=`;
    } else if (type === 'wpa_personal') {
        body += `&pass=${encodeURIComponent(p)}`;
    } else if (type === 'wpa_enterprise') {
        body += `&ent_enabled=true&ent_username=${encodeURIComponent(entUser)}`;
        if (pwDirty.cfg_ent_password) body += `&ent_password=${encodeURIComponent(entPass)}`;
    }

    let d = await api('/api/wifi', 'POST', body);
    setButtonLoading(btn, false, 'Save & Reboot');
    if (d) triggerRebootSequence();
}

async function saveMqtt() {
    if (!await showModal('Confirm', 'Save MQTT config and reboot?')) return;
    let btn = document.querySelector('#view-mqtt button[type="submit"]');
    setButtonLoading(btn, true, 'Save & Reboot');
    let s = document.getElementById('cfg_mqtt_srv').value;
    let p = document.getElementById('cfg_mqtt_port').value;
    let pre = document.getElementById('cfg_mqtt_pre').value;
    let u = document.getElementById('cfg_mqtt_u').value;
    let int = document.getElementById('cfg_mqtt_int').value;
    let body = `server=${encodeURIComponent(s)}&port=${encodeURIComponent(p)}&topic_prefix=${encodeURIComponent(pre)}&user=${encodeURIComponent(u)}&telemetry_interval_ms=${encodeURIComponent(int)}&mqtt_disconnect_emergency_stop=${document.getElementById('cfg_mqtt_emergency_stop').checked}`;
    if (pwDirty.cfg_mqtt_p) body += `&pass=${encodeURIComponent(document.getElementById('cfg_mqtt_p').value)}`;
    let d = await api('/api/mqtt', 'POST', body);
    setButtonLoading(btn, false, 'Save & Reboot');
    if (d) triggerRebootSequence();
}

async function saveAccount() {
    if (!await showModal('Confirm', 'Update admin credentials and reboot?')) return;
    let btn = document.querySelector('#view-account button[type="submit"]');
    setButtonLoading(btn, true, 'Update Credentials & Reboot');
    let u = document.getElementById('cfg_admin_u').value;
    let p = document.getElementById('cfg_admin_p').value;
    if (!u || !p) { showMsg('Cannot be empty', true); setButtonLoading(btn, false, 'Update Credentials & Reboot'); return; }
    let d = await api('/api/account', 'POST', `user=${encodeURIComponent(u)}&pass=${encodeURIComponent(p)}`);
    setButtonLoading(btn, false, 'Update Credentials & Reboot');
    if (d) {
        logout();
        triggerRebootSequence();
    }
}

function confirmRemove(message, callback) {
    showModal('Confirm', message).then(confirmed => {
        if (confirmed) callback();
    });
}

function confirmAction(message, callback) {
    showModal('Confirm', message).then(confirmed => {
        if (confirmed) callback();
    });
}

// --- Reboot & Auto-Reconnect Sequence ---
function triggerRebootSequence(isImport = false) {
    let overlay = document.getElementById('reboot-overlay');
    if (overlay) overlay.style.display = 'flex';

    if (isImport) {
        let msgEl = document.getElementById('reboot-msg');
        let submsgEl = document.getElementById('reboot-submsg');
        if (msgEl) msgEl.innerText = "Configuration Uploaded!";
        if (submsgEl) submsgEl.innerText = "Device is rebooting and please refresh this browser.";
        return; // Skip automatic reconnect pinging as the IP is likely changing
    }

    // Start pinging after 3 seconds
    setTimeout(() => {
        let pingInterval = setInterval(async () => {
            try {
                let opts = { headers: {} };
                if (token) opts.headers['Authorization'] = 'Bearer ' + token;
                let res = await fetch('/api/status', opts);
                if (res.ok) {
                    clearInterval(pingInterval);
                    window.location.reload();
                }
            } catch (e) {
                // Ignore network errors while rebooting
            }
        }, 2000);
    }, 3000);
}

// --- OTA Update ---
async function startOtaUpdate() {
    let fileInput = document.getElementById('ota_file');
    let file = fileInput.files[0];
    if (!file) {
        showMsg("Please select a .bin file first", true);
        return;
    }

    let btn = document.getElementById('ota_btn');
    let progressCont = document.getElementById('ota_progress_container');
    let progressBar = document.getElementById('ota_progress');
    let statusText = document.getElementById('ota_status');

    btn.disabled = true;
    progressCont.style.display = 'block';
    statusText.innerText = "Uploading Firmware...";
    progressBar.style.width = '0%';

    let xhr = new XMLHttpRequest();
    xhr.open('POST', '/api/ota', true);
    if (token) xhr.setRequestHeader('Authorization', 'Bearer ' + token);

    xhr.upload.onprogress = function (e) {
        if (e.lengthComputable) {
            let p = Math.round((e.loaded / e.total) * 100);
            progressBar.style.width = p + '%';
            if (p === 100) statusText.innerText = "Writing to flash, do NOT power off...";
        }
    };

    xhr.onload = function () {
        if (xhr.status === 200) {
            statusText.innerText = "Update successful! Rebooting...";
            statusText.style.color = "var(--accent)";
            setTimeout(triggerRebootSequence, 1000);
        } else {
            let err = "Update failed";
            try { err = JSON.parse(xhr.responseText).error || err; } catch (e) { }
            statusText.innerText = "Error: " + err;
            statusText.style.color = "var(--danger)";
            btn.disabled = false;
        }
    };

    xhr.onerror = function () {
        statusText.innerText = "Network error during upload.";
        statusText.style.color = "var(--danger)";
        btn.disabled = false;
    };

    let formData = new FormData();
    formData.append("update", file, file.name);
    xhr.send(formData);
}

async function exportConfig() {
    // Local testing bypass
    if (window.location.hostname === '127.0.0.1' || window.location.hostname === 'localhost' || window.location.protocol === 'file:') {
        let dummy = { device: { node_id: "mock-node" } };
        let blob = new Blob([JSON.stringify(dummy, null, 2)], { type: "application/json" });
        let url = URL.createObjectURL(blob);
        let a = document.createElement("a");
        a.href = url;
        a.download = "config.json";
        a.click();
        return;
    }

    try {
        let opts = { headers: {} };
        if (token) opts.headers['Authorization'] = 'Bearer ' + token;
        let res = await fetch('/api/config/export', opts);
        if (!res.ok) {
            if (res.status === 401) {
                showMsg("Session expired. Please sign in again.", true);
                logout();
            } else {
                showMsg(`Failed to download config file (${res.status})`, true);
            }
            return;
        }
        let blob = await res.blob();
        let url = URL.createObjectURL(blob);
        let a = document.createElement("a");
        a.href = url;
        a.download = "config.json";
        document.body.appendChild(a);
        a.click();
        a.remove();
        URL.revokeObjectURL(url);
    } catch (e) {
        showMsg("Network error during config export", true);
    }
}

async function importConfig() {
    let fileInput = document.getElementById('import_file');
    let file = fileInput.files[0];
    if (!file) {
        showMsg("Please select a config .json file first", true);
        return;
    }

    let btn = document.getElementById('import_btn');
    setButtonLoading(btn, true, 'Upload & Restore');

    let reader = new FileReader();
    reader.onload = async function (e) {
        let contents = e.target.result;

        try {
            JSON.parse(contents);
        } catch (err) {
            showMsg("Invalid file: File must be a valid JSON configuration", true);
            setButtonLoading(btn, false, 'Upload & Restore');
            return;
        }

        let opts = { method: 'POST', headers: { 'Content-Type': 'application/json' } };
        if (token) opts.headers['Authorization'] = 'Bearer ' + token;
        let response = await fetch('/api/config/import', opts);
        let d = await response.json();
        if (!response.ok) {
            showMsg(d.error || `Config import failed (${response.status})`, true);
            setButtonLoading(btn, false, 'Upload & Restore');
            if (response.status === 401) logout();
            return;
        }
        if (d && (d.status === "success" || d.success)) {
            showMsg("Config imported successfully!");
            setTimeout(() => triggerRebootSequence(true), 1000);
        } else {
            setButtonLoading(btn, false, 'Upload & Restore');
        }
    };
    reader.readAsText(file);
}

window.onload = checkAuth;

document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
        document.getElementById('sidebarMenu').classList.remove('show');
        document.getElementById('sidebar-backdrop').classList.remove('show');
        let modal = document.getElementById('confirm-modal');
        if (modal && modal.classList.contains('show')) {
            closeModal();
        }
    }
});
