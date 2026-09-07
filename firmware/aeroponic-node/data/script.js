let token = localStorage.getItem('token');
let alertTimer;

// Lacak apakah field password benar-benar diubah user.
// Backend sengaja TIDAK mengembalikan password (security), sehingga field kosong saat refresh.
// Jika tidak dilacak, menyimpan form akan mengirim password kosong & menimpa password tersimpan.
let pwDirty = { cfg_pass: false, cfg_eap_pass: false, cfg_mqtt_p: false };
['cfg_pass', 'cfg_eap_pass', 'cfg_mqtt_p'].forEach(id => {
    let el = document.getElementById(id);
    if (el) el.addEventListener('input', () => { pwDirty[id] = true; });
});

const PW_PLACEHOLDER = '•••••••• (biarkan kosong untuk mempertahankan)';

function showMsg(msg, isErr = false) {
    let box = document.getElementById('alert');
    box.innerText = msg;
    box.className = 'alert-box ' + (isErr ? 'alert-error' : 'alert-success');
    box.style.display = 'block';
    clearTimeout(alertTimer);
    alertTimer = setTimeout(() => box.style.display = 'none', 3000);
}

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
                wifi: { ssid: 'MyWiFi', password: 'pass', eap_identity: '', eap_password: '' },
                mqtt: { server: 'broker.emqx.io', port: 1883, topic_prefix: 'smartfarm', user: '', pass: '', telemetry_interval: 5000 },
                hardware: {
                    inputs: [{ pin: 4, type: 'DIGITAL', pull: 'UP', name: 'Water Sensor' }],
                    outputs: [{ pin: 5, type: 'DIGITAL', name: 'Pump Relay' }],
                    modbus: [{
                        name: 'CWT Soil Sensor', slave_id: 1, baudrate: 9600, registers: [
                            { address: 0, type: 'HOLDING', name: 'Moisture', multiplier: 0.1 },
                            { address: 1, type: 'HOLDING', name: 'Temperature', multiplier: 0.1 }
                        ]
                    }]
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

let statusTimer = null;

function checkAuth() {
    // Local testing bypass for UI preview without backend
    if (window.location.hostname === '127.0.0.1' || window.location.hostname === 'localhost' || window.location.protocol === 'file:') {
        document.getElementById('login-container').style.display = 'none';
        document.getElementById('app-container').style.display = 'flex';
        return;
    }

    if (token) {
        document.getElementById('login-container').style.display = 'none';
        document.getElementById('app-container').style.display = 'flex';
        loadStatus();
        loadFullConfig();
    } else {
        document.getElementById('login-container').style.display = 'flex';
        document.getElementById('app-container').style.display = 'none';
    }
}

async function doLogin() {
    let u = document.getElementById('login_user').value;
    let p = document.getElementById('login_pass').value;
    let d = await api('/api/login', 'POST', `user=${u}&pass=${p}`);
    if (d && d.token) {
        token = d.token;
        localStorage.setItem('token', token);
        checkAuth();
    }
}

function logout() { token = null; localStorage.removeItem('token'); checkAuth(); }

function toggleMobileMenu() {
    document.getElementById('sidebarMenu').classList.toggle('show');
}

function switchView(id) {
    document.querySelectorAll('.view-section').forEach(e => e.classList.remove('active'));
    document.querySelectorAll('.menu-item').forEach(e => e.classList.remove('active'));
    document.getElementById('view-' + id).classList.add('active');
    event.currentTarget.classList.add('active');
    // Hide sidebar on mobile after clicking
    document.getElementById('sidebarMenu').classList.remove('show');

    if (statusTimer) clearInterval(statusTimer);
    if (id === 'status') {
        loadStatus();
        statusTimer = setInterval(loadStatus, 3000);
    }
    if (id === 'local_control') {
        loadLocalControl();
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
    let d = await api('/api/status');
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

        // Render MQTT Logs
        let logsContainer = document.getElementById('mqtt_logs_container');
        if (logsContainer && d.mqtt_logs) {
            let validLogs = d.mqtt_logs.filter(log => log !== null && log !== undefined);
            if (validLogs.length === 0) {
                logsContainer.innerHTML = `<div style="color:var(--text-light); font-style:italic;">No logs captured yet. Send telemetry or toggle outputs to see activity here.</div>`;
            } else {
                logsContainer.innerHTML = validLogs.map(log => {
                    let color = "#10b981"; // default green
                    if (log.includes("Pub FAILED") || log.includes("FAILED") || log.includes("failed")) {
                        color = "#ef4444"; // red
                    } else if (log.includes("Attempting") || log.includes("rc=")) {
                        color = "#f59e0b"; // yellow
                    } else if (log.includes("Sub Recv:")) {
                        color = "#3b82f6"; // blue
                    }
                    return `<div style="color:${color}; margin-bottom:4px;">${log}</div>`;
                }).join('');
                // Auto scroll to bottom
                logsContainer.scrollTop = logsContainer.scrollHeight;
            }
        }
    }
}

async function sendDiscovery() {
    let btn = document.getElementById('btn_discovery');
    btn.disabled = true;
    btn.innerText = "Sending...";

    let d = await api('/api/publish_discovery', 'POST');
    if (d) {
        if (d.success || d.status === "success") {
            showMsg("Discovery signal sent successfully!");
        } else {
            showMsg(d.message || "Failed to send discovery", true);
        }
    } else {
        // Jika d bernilai null, helper api() sudah menampilkan pesan error aslinya (misal "Unauthorized")
        // Jadi kita tidak perlu menimpanya dengan pesan palsu "MQTT not connected".
    }

    btn.disabled = false;
    btn.innerText = "Send Discovery Signal";
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
        if (document.getElementById('cfg_rs485_rts')) {
            document.getElementById('cfg_rs485_rts').value = (d.hardware && d.hardware.rs485_rts != null) ? d.hardware.rs485_rts : 255;
        }
        document.getElementById('cfg_admin_u').value = d.security.admin_user || '';
        document.getElementById('cfg_ssid').value = wifi.ssid || '';
        document.getElementById('cfg_pass').value = wifi.password || '';
        document.getElementById('cfg_pass').placeholder = wifi.password ? PW_PLACEHOLDER : '';
        document.getElementById('cfg_eap_id').value = wifi.eap_identity || '';
        document.getElementById('cfg_eap_pass').value = wifi.eap_password || '';
        document.getElementById('cfg_eap_pass').placeholder = wifi.eap_password ? PW_PLACEHOLDER : '';
        document.getElementById('cfg_mqtt_srv').value = mqtt.server || '';
        document.getElementById('cfg_mqtt_port').value = mqtt.port || '';
        document.getElementById('cfg_mqtt_pre').value = mqtt.topic_prefix || '';
        document.getElementById('cfg_mqtt_u').value = mqtt.user || '';
        document.getElementById('cfg_mqtt_p').value = mqtt.pass || '';
        document.getElementById('cfg_mqtt_p').placeholder = mqtt.pass ? PW_PLACEHOLDER : '';
        document.getElementById('cfg_mqtt_int').value = mqtt.telemetry_interval_ms || '';

        pwDirty.cfg_pass = false;
        pwDirty.cfg_eap_pass = false;
        pwDirty.cfg_mqtt_p = false;

        // Render GPIO (inputs/outputs/modbus) + I2C sensors
        renderGpioRows(d.hardware || { inputs: [], outputs: [] });

        // Load local control rules
        if (d.local_control) {
            localControlRules = d.local_control;
            drawLocalControl();
        }
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

function renderGpioRows(hw) {
    hwInputs = hw.inputs || [];
    hwOutputs = hw.outputs || [];
    hwModbus = hw.modbus || [];
    hwI2C = hw.sensors || [];
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
        if (editInputIdx === idx) {
            html += `
            <div class="hw-row" style="flex-wrap:wrap; gap:8px;">
                <div style="flex:1; min-width:80px;">
                    <label>GPIO Pin</label>
                    <input type="number" min="0" max="48" value="${p.pin}" onchange="hwInputs[${idx}].pin=parseInt(this.value)">
                </div>
                <div style="flex:1; min-width:120px;">
                    <label>Input Type</label>
                    <select onchange="hwInputs[${idx}].type=this.value">
                        <option value="DIGITAL" ${p.type === 'DIGITAL' ? 'selected' : ''}>DIGITAL</option>
                        <option value="ANALOG" ${p.type === 'ANALOG' ? 'selected' : ''}>ANALOG (ADC)</option>
                    </select>
                </div>
                <div style="flex:1; min-width:120px;">
                    <label>Pull Resistor</label>
                    <select onchange="hwInputs[${idx}].pull=this.value">
                        <option value="NONE" ${p.pull === 'NONE' ? 'selected' : ''}>NONE</option>
                        <option value="UP" ${p.pull === 'UP' ? 'selected' : ''}>PULL-UP</option>
                        <option value="DOWN" ${p.pull === 'DOWN' ? 'selected' : ''}>PULL-DOWN</option>
                    </select>
                </div>
                <div style="flex:1; min-width:120px;">
                    <label>Interrupt Mode</label>
                    <select onchange="hwInputs[${idx}].interrupt=this.value">
                        <option value="NONE" ${(p.interrupt||'NONE') === 'NONE' ? 'selected' : ''}>NONE</option>
                        <option value="RISING" ${p.interrupt === 'RISING' ? 'selected' : ''}>RISING</option>
                        <option value="FALLING" ${p.interrupt === 'FALLING' ? 'selected' : ''}>FALLING</option>
                        <option value="CHANGE" ${p.interrupt === 'CHANGE' ? 'selected' : ''}>CHANGE</option>
                    </select>
                </div>
                <div style="flex:1; min-width:100px;">
                    <label>Debounce (ms)</label>
                    <input type="number" min="0" max="5000" value="${p.debounce_ms||0}" onchange="hwInputs[${idx}].debounce_ms=parseInt(this.value)">
                </div>
                <div style="flex:2; min-width:150px;">
                    <label>Name Label</label>
                    <input type="text" value="${p.name}" placeholder="e.g. Water Sensor" onchange="hwInputs[${idx}].name=this.value">
                </div>
                <div style="flex:1; min-width:100px; display:flex; flex-direction:column; justify-content:flex-end;">
                    <label style="margin-bottom:8px;">Invert Logic</label>
                    <label style="display:flex; align-items:center; gap:8px; cursor:pointer; font-weight:normal; margin:0;">
                        <input type="checkbox" ${p.invert ? 'checked' : ''} onchange="hwInputs[${idx}].invert=this.checked" style="width:auto; margin:0;">
                        <span style="font-size:12px;">LOW = Active</span>
                    </label>
                </div>
                <button style="margin-top:24px; background:#10b981; border-color:#10b981; align-self:flex-end;" onclick="editInputIdx=-1; drawInputs();">Done</button>
            </div>
            `;
        } else {
            html += `
            <div class="hw-list-item">
                <div class="hw-info">
                    <span class="hw-name">${p.name || 'Unnamed Input'}</span>
                    <span class="hw-meta">GPIO ${p.pin} | ${p.type} | Pull: ${p.pull} | IRQ: ${p.interrupt||'NONE'} | Debounce: ${p.debounce_ms||0}ms${p.invert ? ' | ⇄ Inverted' : ''}</span>
                </div>
                <div class="hw-actions">
                    <button class="outline" style="padding:6px 12px; font-size:12px;" onclick="editInputIdx=${idx}; drawInputs();">Edit</button>
                    <button class="danger" style="padding:6px 12px; font-size:12px;" onclick="hwInputs.splice(${idx}, 1); if(editInputIdx==${idx}) editInputIdx=-1; else if(editInputIdx > ${idx}) editInputIdx--; drawInputs();">Remove</button>
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
        if (editOutputIdx === idx) {
            html += `
            <div class="hw-row">
                <div style="flex:1; min-width:80px;">
                    <label>GPIO Pin</label>
                    <input type="number" min="0" max="48" value="${p.pin}" onchange="hwOutputs[${idx}].pin=this.value">
                </div>
                <div style="flex:1; min-width:120px;">
                    <label>Output Type</label>
                    <select onchange="hwOutputs[${idx}].type=this.value">
                        <option value="DIGITAL" ${p.type === 'DIGITAL' ? 'selected' : ''}>DIGITAL</option>
                        <option value="PWM" ${p.type === 'PWM' ? 'selected' : ''}>PWM</option>
                    </select>
                </div>
                <div style="flex:2; min-width:150px;">
                    <label>Name Label</label>
                    <input type="text" value="${p.name}" placeholder="e.g. Pump Relay" onchange="hwOutputs[${idx}].name=this.value">
                </div>
                <button style="margin-top:24px; background:#10b981; border-color:#10b981;" onclick="editOutputIdx=-1; drawOutputs();">Done</button>
            </div>
            `;
        } else {
            html += `
            <div class="hw-list-item">
                <div class="hw-info">
                    <span class="hw-name">${p.name || 'Unnamed Output'}</span>
                    <span class="hw-meta">GPIO ${p.pin} | ${p.type}</span>
                </div>
                <div class="hw-actions">
                    <button class="outline" style="padding:6px 12px; font-size:12px;" onclick="editOutputIdx=${idx}; drawOutputs();">Edit</button>
                    <button class="danger" style="padding:6px 12px; font-size:12px;" onclick="hwOutputs.splice(${idx}, 1); if(editOutputIdx==${idx}) editOutputIdx=-1; else if(editOutputIdx > ${idx}) editOutputIdx--; drawOutputs();">Remove</button>
                </div>
            </div>
            `;
        }
    });
    document.getElementById('output-rows').innerHTML = html;
}

function addInputRow() {
    hwInputs.push({ pin: 0, type: 'DIGITAL', pull: 'NONE', name: 'New Input', invert: false, debounce_ms: 0, interrupt: 'NONE' });
    editInputIdx = hwInputs.length - 1;
    drawInputs();
}

function addOutputRow() {
    hwOutputs.push({ pin: 0, type: 'DIGITAL', name: 'New Output' });
    editOutputIdx = hwOutputs.length - 1;
    drawOutputs();
}

function drawModbus() {
    let html = '';
    hwModbus.forEach((m, idx) => {
        if (editModbusIdx === idx) {
            html += `<div class="hw-row" style="flex-direction:column; gap:10px;">
                <div style="display:flex; gap:10px; flex-wrap:wrap;">
                    <div style="flex:2; min-width:150px;"><label>Sensor Name</label><input type="text" value="${m.name}" onchange="hwModbus[${idx}].name=this.value"></div>
                    <div style="flex:1; min-width:80px;"><label>Slave ID</label><input type="number" min="1" max="247" value="${m.slave_id}" onchange="hwModbus[${idx}].slave_id=parseInt(this.value)"></div>
                    <div style="flex:1; min-width:100px;"><label>Baudrate</label><select onchange="hwModbus[${idx}].baudrate=parseInt(this.value)"><option value="4800" ${m.baudrate == 4800 ? 'selected' : ''}>4800</option><option value="9600" ${m.baudrate == 9600 ? 'selected' : ''}>9600</option><option value="19200" ${m.baudrate == 19200 ? 'selected' : ''}>19200</option></select></div>
                </div>
                <div style="margin-top:10px; padding:10px; background:rgba(0,0,0,0.02); border-radius:4px;">
                    <label style="margin-bottom:5px; display:block;">Registers to Read</label>`;

            m.registers.forEach((r, ridx) => {
                html += `<div style="display:flex; gap:6px; margin-bottom:8px; flex-wrap:wrap; background:#fff; padding:6px; border-radius:4px; border:1px solid #ddd; align-items:center;">
                    <input type="number" placeholder="Addr" value="${r.address}" onchange="hwModbus[${idx}].registers[${ridx}].address=parseInt(this.value)" style="flex:1; min-width:60px; font-size:12px; padding:6px; margin:0;">
                    <select onchange="hwModbus[${idx}].registers[${ridx}].type=this.value" style="flex:1.5; min-width:85px; font-size:12px; padding:6px; margin:0;"><option value="HOLDING" ${r.type === 'HOLDING' ? 'selected' : ''}>HOLDING</option><option value="INPUT" ${r.type === 'INPUT' ? 'selected' : ''}>INPUT</option></select>
                    <input type="text" placeholder="Name" value="${r.name}" onchange="hwModbus[${idx}].registers[${ridx}].name=this.value" style="flex:2; min-width:90px; font-size:12px; padding:6px; margin:0;">
                    <input type="number" step="0.01" placeholder="Mult." value="${r.multiplier}" onchange="hwModbus[${idx}].registers[${ridx}].multiplier=parseFloat(this.value)" style="flex:1; min-width:55px; font-size:12px; padding:6px; margin:0;">
                    <button class="danger" style="padding:6px 12px; font-size:12px; min-width:40px; text-align:center;" onclick="hwModbus[${idx}].registers.splice(${ridx}, 1); drawModbus();">X</button>
                </div>`;
            });

            html += `<button class="outline" style="font-size:12px; padding:4px 8px;" onclick="hwModbus[${idx}].registers.push({address:0, type:'HOLDING', name:'new_reg', multiplier:1.0}); drawModbus();">+ Reg</button>
                </div>
                <button style="margin-top:10px; background:#10b981; border-color:#10b981;" onclick="editModbusIdx=-1; drawModbus();">Done</button>
            </div>`;
        } else {
            html += `<div class="hw-list-item">
                <div class="hw-info">
                    <span class="hw-name">${m.name || 'Unnamed Sensor'}</span>
                    <span class="hw-meta">ID: ${m.slave_id} | Baud: ${m.baudrate} | Regs: ${m.registers.length}</span>
                </div>
                <div class="hw-actions">
                    <button class="outline" style="padding:6px 12px; font-size:12px;" onclick="editModbusIdx=${idx}; drawModbus();">Edit</button>
                    <button class="danger" style="padding:6px 12px; font-size:12px;" onclick="hwModbus.splice(${idx}, 1); if(editModbusIdx==${idx}) editModbusIdx=-1; else if(editModbusIdx > ${idx}) editModbusIdx--; drawModbus();">Remove</button>
                </div>
            </div>`;
        }
    });
    document.getElementById('modbus-rows').innerHTML = html;
}

function addModbusSensor() {
    hwModbus.push({ name: 'New RS485 Sensor', slave_id: 1, baudrate: 9600, registers: [] });
    editModbusIdx = hwModbus.length - 1;
    drawModbus();
}

function drawI2C() {
    let html = '';
    hwI2C.forEach((s, idx) => {
        if (editI2CIdx === idx) {
            html += `
            <div class="hw-row" style="flex-wrap:wrap; gap:8px;">
                <div style="flex:1; min-width:120px;">
                    <label>Sensor Name</label>
                    <input type="text" value="${s.name || ''}" onchange="hwI2C[${idx}].name=this.value">
                </div>
                <div style="flex:1; min-width:120px;">
                    <label>Sensor Type</label>
                    <select onchange="hwI2C[${idx}].type=this.value">
                        <option value="INA219" ${(s.type || '') === 'INA219' ? 'selected' : ''}>INA219</option>
                        <option value="BME280" ${(s.type || '') === 'BME280' ? 'selected' : ''}>BME280</option>
                        <option value="DHT12" ${(s.type || '') === 'DHT12' ? 'selected' : ''}>DHT12</option>
                    </select>
                </div>
                <div style="flex:1; min-width:100px;">
                    <label>I2C Address</label>
                    <input type="text" value="${s.address || '0x40'}" onchange="hwI2C[${idx}].address=this.value">
                </div>
                <div style="flex:1; min-width:80px;">
                    <label>SDA Pin</label>
                    <input type="number" min="0" max="48" value="${s.sda_pin || 21}" onchange="hwI2C[${idx}].sda_pin=this.value">
                </div>
                <div style="flex:1; min-width:80px;">
                    <label>SCL Pin</label>
                    <input type="number" min="0" max="48" value="${s.scl_pin || 22}" onchange="hwI2C[${idx}].scl_pin=this.value">
                </div>
                <div style="display:flex; gap:6px; margin-top:8px;">
                    <button class="outline" style="padding:6px 12px; font-size:12px;" onclick="editI2CIdx=-1; drawI2C();">Done</button>
                </div>
            </div>`;
        } else {
            html += `
            <div class="hw-row" style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px;">
                <span class="hw-name">${s.name || 'Unnamed'} (${s.type || '?'}) @ ${s.address || '?'}</span>
                <div style="display:flex; gap:6px;">
                    <button class="outline" style="padding:6px 12px; font-size:12px;" onclick="editI2CIdx=${idx}; drawI2C();">Edit</button>
                    <button class="danger" style="padding:6px 12px; font-size:12px;" onclick="hwI2C.splice(${idx},1); if(editI2CIdx===${idx}) editI2CIdx=-1; else if(editI2CIdx>${idx}) editI2CIdx--; drawI2C();">Remove</button>
                </div>
            </div>`;
        }
    });
    document.getElementById('i2c-rows').innerHTML = html;
}

function addI2CSensor() {
    hwI2C.push({ name: 'New I2C Sensor', type: 'INA219', protocol: 'I2C', address: '0x40', sda_pin: '21', scl_pin: '22' });
    editI2CIdx = hwI2C.length - 1;
    drawI2C();
}

// Scanner logic
async function startScanId() {
    let baud = document.getElementById('scan_baud').value;
    let resDiv = document.getElementById('scan_results');
    resDiv.innerHTML = `<div style="color:var(--primary);">Scanning ID 1-247 on ${baud} baud... Please wait (this may take a few minutes).</div>`;

    try {
        let res = await fetch('/api/modbus/start_scan', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
                'Authorization': 'Bearer ' + token
            },
            body: `baud=${baud}`
        });

        if (!res.ok) {
            resDiv.innerHTML = "<div style='color:var(--danger);'>Failed to start scan or timeout occurred.</div>";
            return;
        }

        let data = await res.json();
        if (data.status === "completed") {
            let ids = data.found_ids || [];
            if (ids.length > 0) {
                resDiv.innerHTML = `<div style="color:var(--success);"><strong>Scan Complete. Found ${ids.length} devices:</strong><br>`;
                ids.forEach(id => {
                    resDiv.innerHTML += `✅ Slave ID ${id} at ${baud} baud<br>`;
                });
                resDiv.innerHTML += "</div>";
            } else {
                resDiv.innerHTML = `<div style="color:var(--warning);">Scan complete. No devices found.</div>`;
            }
        }
    } catch (e) {
        resDiv.innerHTML = `<div style="color:var(--danger);">Network error or timeout. Error: ${e.message}</div>`;
    }
}

async function startScanReg() {
    let id = document.getElementById('scan_id').value;
    let baud = document.getElementById('scan_baud').value;
    let start = parseInt(document.getElementById('scan_reg_start').value);
    let end = parseInt(document.getElementById('scan_reg_end').value);
    let type = document.getElementById('scan_type').value;
    let resDiv = document.getElementById('scan_results');
    resDiv.innerHTML = `Scanning ${type} registers ${start} to ${end} on ID ${id}...<br>`;

    let foundAny = false;
    for (let i = start; i <= end; i++) {
        let res = await fetch(`/api/modbus/scan_reg?scan_reg=${i}&id=${id}&baud=${baud}&type=${type}`, { headers: { 'Authorization': 'Bearer ' + token } });
        if (res.ok) {
            let data = await res.json();
            if (data.success) {
                resDiv.innerHTML += `<div style="color:var(--success);">✅ Reg ${i}: Value = ${data.val}</div>`;
                foundAny = true;
            }
        }
    }
    if (!foundAny) resDiv.innerHTML += "<div style='color:var(--danger);'>No valid registers found in range.</div>";
}

async function saveHardware() {
    let payload = encodeURIComponent(JSON.stringify({ inputs: hwInputs, outputs: hwOutputs, modbus: hwModbus, sensors: hwI2C }));
    let d = await api('/api/hardware', 'POST', `payload=${payload}`);
    if (d) triggerRebootSequence();
}

async function saveDevice() {
    let v = document.getElementById('cfg_node_id').value;
    let d = await api('/api/device', 'POST', `node_id=${v}`);
    if (d) triggerRebootSequence();
}

async function saveRS485() {
    let rx = document.getElementById('cfg_rs485_rx').value;
    let tx = document.getElementById('cfg_rs485_tx').value;
    let de = document.getElementById('cfg_rs485_de').value;
    let rts = document.getElementById('cfg_rs485_rts').value;
    let body = `rs485_rx=${rx}&rs485_tx=${tx}&rs485_de=${de}&rs485_rts=${rts}`;
    let d = await api('/api/device', 'POST', body);
    if (d) triggerRebootSequence();
}

async function saveWifi() {
    let s = document.getElementById('cfg_ssid').value;
    let ei = document.getElementById('cfg_eap_id').value;
    let body = `ssid=${encodeURIComponent(s)}&eap_identity=${encodeURIComponent(ei)}`;
    // Hanya kirim password bila user mengubahnya, agar password tersimpan tidak tertimpa kosong.
    if (pwDirty.cfg_pass) body += `&pass=${encodeURIComponent(document.getElementById('cfg_pass').value)}`;
    if (pwDirty.cfg_eap_pass) body += `&eap_password=${encodeURIComponent(document.getElementById('cfg_eap_pass').value)}`;
    let d = await api('/api/wifi', 'POST', body);
    if (d) triggerRebootSequence();
}

async function saveMqtt() {
    let s = document.getElementById('cfg_mqtt_srv').value;
    let p = document.getElementById('cfg_mqtt_port').value;
    let pre = document.getElementById('cfg_mqtt_pre').value;
    let u = document.getElementById('cfg_mqtt_u').value;
    let int = document.getElementById('cfg_mqtt_int').value;
    let body = `server=${encodeURIComponent(s)}&port=${encodeURIComponent(p)}&topic_prefix=${encodeURIComponent(pre)}&user=${encodeURIComponent(u)}&telemetry_interval=${encodeURIComponent(int)}`;
    if (pwDirty.cfg_mqtt_p) body += `&pass=${encodeURIComponent(document.getElementById('cfg_mqtt_p').value)}`;
    let d = await api('/api/mqtt', 'POST', body);
    if (d) triggerRebootSequence();
}

async function saveAccount() {
    let u = document.getElementById('cfg_admin_u').value;
    let p = document.getElementById('cfg_admin_p').value;
    if (!u || !p) { showMsg('Cannot be empty', true); return; }
    let d = await api('/api/account', 'POST', `user=${u}&pass=${p}`);
    if (d) {
        logout();
        triggerRebootSequence();
    }
}

// ==================== LOCAL CONTROL ====================
let localControlRules = [];
let editLocalControlIdx = -1;

async function loadLocalControl() {
    let d = await api('/api/local_control', 'GET');
    if (d && d.local_control) {
        localControlRules = d.local_control;
        editLocalControlIdx = -1;
        drawLocalControl();
    }
}

function drawLocalControl() {
    let html = '';
    localControlRules.forEach((r, idx) => {
        if (editLocalControlIdx === idx) {
            html += `
            <div class="hw-row">
                <div style="flex:2; min-width:150px;">
                    <label>Rule Name</label>
                    <input type="text" value="${r.name}" onchange="localControlRules[${idx}].name=this.value">
                </div>
                <div style="flex:2; min-width:150px;">
                    <label>Input Sensor</label>
                    <input type="text" value="${r.input_sensor}" onchange="localControlRules[${idx}].input_sensor=this.value">
                </div>
                <div style="flex:2; min-width:150px;">
                    <label>Output Target</label>
                    <input type="text" value="${r.output_target}" onchange="localControlRules[${idx}].output_target=this.value">
                </div>
                <button style="margin-top:24px; background:#10b981; border-color:#10b981;" onclick="editLocalControlIdx=-1; drawLocalControl();">Done</button>
            </div>
            <div class="hw-row" style="margin-top:10px;">
                <div style="flex:1; min-width:100px;">
                    <label>Threshold High (ON)</label>
                    <input type="number" step="0.1" value="${r.threshold_high}" onchange="localControlRules[${idx}].threshold_high=parseFloat(this.value)">
                </div>
                <div style="flex:1; min-width:100px;">
                    <label>Threshold Low (OFF)</label>
                    <input type="number" step="0.1" value="${r.threshold_low}" onchange="localControlRules[${idx}].threshold_low=parseFloat(this.value)">
                </div>
                <div style="flex:1; min-width:100px;">
                    <label>Enabled</label>
                    <select onchange="localControlRules[${idx}].enabled=this.value==='true'">
                        <option value="true" ${r.enabled ? 'selected' : ''}>Yes</option>
                        <option value="false" ${!r.enabled ? 'selected' : ''}>No</option>
                    </select>
                </div>
            </div>
            `;
        } else {
            html += `
            <div class="hw-list-item">
                <div class="hw-info">
                    <span class="hw-name">${r.name || 'Unnamed Rule'}</span>
                    <span class="hw-meta">${r.input_sensor} → ${r.output_target} | High: ${r.threshold_high} | Low: ${r.threshold_low} | ${r.enabled ? 'Enabled' : 'Disabled'}</span>
                </div>
                <div class="hw-actions">
                    <button class="outline" style="padding:6px 12px; font-size:12px;" onclick="editLocalControlIdx=${idx}; drawLocalControl();">Edit</button>
                    <button class="danger" style="padding:6px 12px; font-size:12px;" onclick="localControlRules.splice(${idx}, 1); if(editLocalControlIdx==${idx}) editLocalControlIdx=-1; else if(editLocalControlIdx > ${idx}) editLocalControlIdx--; drawLocalControl();">Remove</button>
                </div>
            </div>
            `;
        }
    });
    document.getElementById('local-control-rows').innerHTML = html;
}

function addLocalControlRow() {
    localControlRules.push({
        name: 'New Rule',
        input_sensor: '',
        output_target: '',
        threshold_high: 30.0,
        threshold_low: 25.0,
        enabled: true
    });
    editLocalControlIdx = localControlRules.length - 1;
    drawLocalControl();
}

async function saveLocalControl() {
    let payload = encodeURIComponent(JSON.stringify({ local_control: localControlRules }));
    let d = await api('/api/local_control', 'POST', `payload=${payload}`);
    if (d) triggerRebootSequence();
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
            showMsg("Failed to download config file", true);
            return;
        }
        let blob = await res.blob();
        let url = URL.createObjectURL(blob);
        let a = document.createElement("a");
        a.href = url;
        a.download = "config.json";
        a.click();
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
    btn.disabled = true;
    btn.innerText = "Restoring...";

    let reader = new FileReader();
    reader.onload = async function (e) {
        let contents = e.target.result;

        // Client-side JSON format check
        try {
            JSON.parse(contents);
        } catch (err) {
            showMsg("Invalid file: File must be a valid JSON configuration", true);
            btn.disabled = false;
            btn.innerText = "Upload & Restore";
            return;
        }

        let d = await api('/api/config/import', 'POST', `payload=${encodeURIComponent(contents)}`);
        if (d && (d.status === "success" || d.success)) {
            showMsg("Config imported successfully! Rebooting...");
            setTimeout(() => triggerRebootSequence(true), 1000);
        } else {
            btn.disabled = false;
            btn.innerText = "Upload & Restore";
        }
    };
    reader.readAsText(file);
}

window.onload = checkAuth;
