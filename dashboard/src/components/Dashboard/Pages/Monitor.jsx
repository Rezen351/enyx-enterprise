import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Tooltip,
  Legend,
  Filler,
} from 'chart.js';
import {
  Activity,
  RefreshCw,
  AlertTriangle,
  Cpu,
  Gauge,
  CalendarClock,
  Radio,
} from 'lucide-react';
import PageHeader from './PageHeader';
import EnvironmentalOverview from './EnvironmentalOverview';
import { getToken, request, getWsUrl } from '../../../api/client';
import controlApi from '../../../api/control';
import { moduleApi } from '../../../api/module';
import { useModule } from '../../../context/useModule';

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Tooltip, Legend, Filler);

const HEALTH_ROWS = [
  { key: 'auth', label: 'Auth' },
  { key: 'module', label: 'Module' },
  { key: 'control', label: 'Control' },
  { key: 'stream', label: 'Stream' },
  { key: 'analytics', label: 'Analytics' },
  { key: 'wsgateway', label: 'WS-Gateway' },
];

function getByPath(obj, path) {
  if (!obj) return undefined;
  return path.split('.').reduce((acc, k) => (acc == null ? undefined : acc[k]), obj);
}

function numericKeys(obj, prefix = '', out = []) {
  if (obj == null || typeof obj !== 'object') return out;
  for (const [k, v] of Object.entries(obj)) {
    const key = prefix ? `${prefix}.${k}` : k;
    if (v != null && typeof v === 'object') numericKeys(v, key, out);
    else if (typeof v === 'number' && Number.isFinite(v)) out.push(key);
  }
  return out;
}

function fmtCountdown(sec) {
  sec = Math.max(0, Math.floor(sec));
  const h = Math.floor(sec / 3600);
  const m = Math.floor((sec % 3600) / 60);
  const s = sec % 60;
  const p = (n) => String(n).padStart(2, '0');
  return `${p(h)}:${p(m)}:${p(s)}`;
}

function fmtNum(v) {
  if (typeof v !== 'number' || !Number.isFinite(v)) return '—';
  if (Number.isInteger(v)) return String(v);
  return v.toFixed(2);
}

// ── Adapter: map live websocket telemetry → the animated SVG's activeModuleData ──
// Explicit mapping for the current firmware/node telemetry keys:
//   outputs: load1=mist pump, load2=intake pump, load3=valve
//   inputs : input1=laser right, input2=laser left, input3=water level (reservoir)
//            cwrt1=outdoor temp+hum, cwt2=indoor temp+hum
function readTelemetry(payload, ...names) {
  if (!payload || typeof payload !== 'object') return undefined;
  const inputs = payload.telemetry?.inputs || payload.inputs || {};
  for (const n of names) {
    if (inputs?.[n] != null) return inputs[n];
    if (payload?.[n] != null) return payload[n];
  }
  return undefined;
}

// Read a sensor field from a modbus group (e.g. telemetry.modbus.cwt1.temp)
// Also supports top-level npk object (e.g. payload.npk.ph_nutrisi)
function readModbus(payload, group, field, ...fallbackFields) {
  const mb = payload?.telemetry?.modbus || payload?.modbus;
  const g = mb?.[group];
  if (!g) {
    const npk = payload?.npk;
    if (npk) {
      if (npk[field] != null) return npk[field];
      for (const f of fallbackFields) {
        if (npk[f] != null) return npk[f];
      }
    }
    return undefined;
  }
  if (g[field] != null) return g[field];
  for (const f of fallbackFields) {
    if (g[f] != null) return g[f];
  }
  return undefined;
}

function buildActiveModuleData(payload, actuators) {
  const out = payload?.telemetry?.outputs || payload?.outputs || {};

  // Output boolean: prefer live telemetry output value, else actuator last_value
    // Only reflect outputs that are configured (tagged) as actuators for this
    // node/module. Raw firmware output names like "load1" reported in telemetry
    // must not surface for a module that hasn't set up that control.
    const outputOn = (name) => {
      const a = actuators.find((x) => x.source_key === name);
      if (!a) return false;
      if (out?.[name] != null) return Number(out[name]) > 0;
      return Number(a.last_value) > 0;
    };

  const mk = (value) => ({ value: value == null ? null : Math.round(Number(value) * 10) / 10 });
  return {
    isMistPumpOn: outputOn('load1'),
    isInletPumpOn: outputOn('load2'),
    isValveOn: outputOn('load3'),
    isLaserLeftOn: Number(readTelemetry(payload, 'input2', 'laser_kiri', 'laser_left')) > 0,
    isLaserRightOn: Number(readTelemetry(payload, 'input1', 'laser_kanan', 'laser_right')) > 0,
    sensors: {
      reservoir_status: mk(readTelemetry(payload, 'input3', 'waterlevel', 'reservoir', 'level')),
      cwt_dalam_temp: mk(readModbus(payload, 'cwt1', 'temp', 'cwt1_temp', 'temp_dalam', 'temp_in')),
      cwt_dalam_hum: mk(readModbus(payload, 'cwt1', 'hum', 'cwt1_hum', 'hum_dalam', 'hum_in')),
      cwt_luar_temp: mk(readModbus(payload, 'cwt2', 'temp', 'cwt2_temp', 'temp_luar', 'temp_out')),
      cwt_luar_hum: mk(readModbus(payload, 'cwt2', 'hum', 'cwt2_hum', 'hum_luar', 'hum_out')),
      npk_ph: mk(readModbus(payload, 'npk', 'ph_nutrisi')),
      npk_temp_air: mk(readModbus(payload, 'npk', 'temp_nutrisi')),
      npk_ec: mk(readModbus(payload, 'npk', 'ec_nutrisi')),
    },
  };
}

// The scheduler engine dispatches directly and does NOT persist next_run_at,
// so derive a best-effort "next run" from the schedule definition (params).
// Deterministic for time-of-day; approximate (cycle-aligned) for interval/pulse.
function parseParams(s) {
  const p = s?.params;
  if (p == null) return {};
  if (typeof p === 'string') {
    try { return JSON.parse(p); } catch { return {}; }
  }
  return typeof p === 'object' ? p : {};
}

function nextHHMM(hhmm, days, now) {
  const m = /^(\d{1,2}):(\d{2})$/.exec(hhmm || '');
  if (!m) return null;
  const min = Number(m[1]) * 60 + Number(m[2]);
  for (let add = 0; add <= 7 * 24 * 60; add += 24 * 60) {
    const d = new Date(now.getTime() + add * 60000);
    if (days && days.length && !days.includes(d.getDay())) continue;
    const cand = new Date(d);
    cand.setHours(0, 0, 0, 0);
    cand.setMinutes(cand.getMinutes() + min);
    if (cand > now) return cand;
  }
  return null;
}

// Derive the upcoming ON/OFF state changes for a single schedule, so the UI can
// show "load1 → OFF in 30s", "load1 → ON in 30s" rather than the whole schedule.
// Cycle-based schedules (interval/window_pulse with on_sec+off_sec) alternate
// predictably; time-of-day schedules flip at on_at/off_at; duration/ramp end once.
function computeTransitions(s, limit = 8) {
  const p = parseParams(s);
  const now = new Date();
  const nowSec = Math.floor(now.getTime() / 1000);
  const add = (sec) => new Date(now.getTime() + sec * 1000);
  const out = [];
  const push = (to, sec) => {
    if (sec == null || !Number.isFinite(sec)) return;
    out.push({ ts: add(Math.max(0, sec)).getTime(), to, output: s.output_name || '*', node_id: s.node_id });
  };

  const isCycle = (s.type === 'interval' || s.type === 'window_pulse') &&
    Number(p.on_sec) > 0 && Number(p.off_sec) > 0;

  if (isCycle) {
    const on = Number(p.on_sec);
    const off = Number(p.off_sec);
    const cycle = on + off;
    const pos = ((nowSec % cycle) + cycle) % cycle;
    if (pos < on) {
      push('off', on - pos);
      push('on', cycle - pos);
    } else {
      push('on', cycle - pos);
      push('off', cycle - pos + on);
    }
  } else if (s.type === 'schedule' || s.type === 'interval' || s.type === 'window_pulse') {
    if (p.on_at) {
      const t = nextHHMM(p.on_at, p.days, now);
      if (t) push('on', (t - now) / 1000);
    }
    if (p.off_at) {
      const t = nextHHMM(p.off_at, p.days, now);
      if (t) push('off', (t - now) / 1000);
    }
  } else if (s.type === 'duration' && Number(p.total_sec) > 0) {
    push('off', Number(p.total_sec));
  } else if (s.type === 'ramp' && Number(p.duration_sec) > 0) {
    push('off', Number(p.duration_sec));
  }

  out.sort((a, b) => a.ts - b.ts);
  return out.slice(0, limit);
}

// Flatten numeric telemetry readings (excluding hardware outputs, shown
// separately as status) for a compact per-node metrics display.
function extractMetrics(payload, limit = 6) {
  if (!payload || typeof payload !== 'object') return [];
  const keys = numericKeys(payload).filter((k) => !/output/i.test(k));
  const out = [];
  for (const k of keys.slice(0, limit)) {
    out.push({ label: k.split('.').pop(), value: getByPath(payload, k), key: k });
  }
  return out;
}

function AnimatedCircle({ color, size = 16 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" className="shrink-0">
      <circle cx="12" cy="12" r="10" fill="none" stroke={color} strokeWidth="3" strokeDasharray="32 64" strokeLinecap="round">
        <animateTransform attributeName="transform" type="rotate" from="0 12 12" to="360 12 12" dur="1.2s" repeatCount="indefinite" />
      </circle>
    </svg>
  );
}

function PulseCircle({ color, size = 10 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" className="shrink-0">
      <circle cx="12" cy="12" r="10" fill={color}>
        <animate attributeName="r" values="8;12;8" dur="1.5s" repeatCount="indefinite" />
        <animate attributeName="opacity" values="1;0.4;1" dur="1.5s" repeatCount="indefinite" />
      </circle>
    </svg>
  );
}

function StatusDot({ connected }) {
  if (connected) {
    return (
      <div className="w-10 h-10 flex items-center justify-center rounded-full bg-emerald-500/20 border border-emerald-500/40 relative">
        <div className="w-4 h-4 rounded-full bg-emerald-400 animate-pulse shadow-[0_0_8px_rgba(52,211,153,0.6)]" />
        <div className="absolute inset-0 rounded-full border-2 border-emerald-500/30 animate-ping" />
      </div>
    );
  }
  return (
    <div className="w-10 h-10 flex items-center justify-center rounded-full bg-slate-100 dark:bg-slate-700/50 border border-slate-300 dark:border-slate-600/40">
      <div className="w-4 h-4 rounded-full bg-slate-400 dark:bg-slate-500" />
    </div>
  );
}

function NodeTelemetryCard({ node, state }) {
  const connected = state?.status === 'open';
  const ip = node?.ip || node?.address || node?.host || '—';
  const lastSeen = state?.lastTs ? new Date(state.lastTs).toLocaleTimeString() : '—';
  const payload = state?.payload;
  const metrics = extractMetrics(payload, 6);
  const liveOutputs = getByPath(payload, 'telemetry.outputs');
  const outputList = liveOutputs && typeof liveOutputs === 'object' ? Object.entries(liveOutputs) : [];
  const onCount = outputList.filter(([, v]) => Number(v) > 0).length;

  return (
    <div className="border border-emerald-500/15 bg-[#030705]/80 backdrop-blur-md p-4 flex flex-col gap-3 rounded-none hover:border-emerald-400/30 hover:shadow-lg hover:shadow-emerald-500/5 transition-all duration-300">
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-3 min-w-0">
          <StatusDot connected={connected} />
          <div className="min-w-0">
            <div className="text-sm font-black uppercase tracking-wider text-white truncate">
              {node.name || node.node_id}
            </div>
            <div className="text-[11px] text-slate-400 font-mono">{ip}</div>
          </div>
        </div>
        <span className={`flex items-center gap-1.5 px-2 py-1 text-[10px] font-black uppercase tracking-wider border shrink-0 ${
          connected
            ? 'text-emerald-400 border-emerald-500/30 bg-emerald-500/10'
            : 'text-red-400 border-red-500/30 bg-red-500/10'
        }`}>
          {connected ? 'Online' : 'Offline'}
        </span>
      </div>

      <div className="grid grid-cols-2 gap-x-3 gap-y-1 text-[10px] border-t border-slate-100 dark:border-white/5 pt-2">
        <div>
          <span className="text-slate-500">Last seen</span>
          <div className="text-slate-300 font-mono">{lastSeen}</div>
        </div>
        <div>
          <span className="text-slate-500">Status WS</span>
          <div className={`font-bold ${connected ? 'text-emerald-300' : 'text-red-300'}`}>
            {state?.status || 'idle'}
          </div>
        </div>
      </div>

      {metrics.length > 0 && (
        <div className="border-t border-slate-100 dark:border-white/5 pt-2">
          <div className="text-[10px] font-black uppercase tracking-widest text-slate-500 mb-1">Telemetry</div>
          <div className="grid grid-cols-2 gap-x-3 gap-y-0.5">
            {metrics.map((m) => (
              <div key={m.key} className="flex items-center justify-between gap-2 text-[11px]">
                <span className="text-slate-400 truncate">{m.label}</span>
                <span className="text-slate-200 font-mono">{fmtNum(m.value)}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {outputList.length > 0 && (
        <div className="border-t border-slate-100 dark:border-white/5 pt-2 flex items-center justify-between gap-2">
          <span className="text-[10px] font-black uppercase tracking-widest text-slate-500">Outputs</span>
          <span className="text-[10px] font-black uppercase tracking-wider text-emerald-400">
            {onCount}/{outputList.length} ON
          </span>
        </div>
      )}
    </div>
  );
}

function Monitor() {
  const { selectedModule } = useModule();
  const [nodes, setNodes] = useState([]);
  const [telemetry, setTelemetry] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const [health, setHealth] = useState({});
  const [selectedNode, setSelectedNode] = useState('');
  const [mode, setMode] = useState(null);
  const [actuators, setActuators] = useState([]);
  const [nextTransitions, setNextTransitions] = useState([]);
  const [actionMsg, setActionMsg] = useState('');
  const [actionErr, setActionErr] = useState('');

  const [now, setNow] = useState(() => Date.now());
  const [throughput, setThroughput] = useState(0);

  const socketsRef = useRef({});
  const telemetryRef = useRef(telemetry);
  const msgCountRef = useRef(0);

  useEffect(() => { telemetryRef.current = telemetry; }, [telemetry]);

  const loadNodes = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      if (!selectedModule) {
        setNodes([]);
        return;
      }
      const res = await moduleApi.listNodes({ module_id: selectedModule.id });
      setNodes(Array.isArray(res?.nodes) ? res.nodes : []);
    } catch (e) {
      setError(e?.message || 'Failed to load nodes');
      setNodes([]);
    } finally {
      setLoading(false);
    }
  }, [selectedModule]);

  useEffect(() => { loadNodes(); }, [loadNodes]);

  useEffect(() => {
    if (!selectedNode && nodes.length) setSelectedNode(nodes[0].node_id);
  }, [nodes, selectedNode]);

  useEffect(() => {
    const sockets = socketsRef.current;
    for (const id of Object.keys(sockets)) {
      if (!nodes.find((n) => n.node_id === id)) {
        try { sockets[id].close(); } catch { /* ignore */ }
        delete sockets[id];
        setTelemetry((prev) => { const next = { ...prev }; delete next[id]; return next; });
      }
    }

    const token = getToken() || '';
    for (const node of nodes) {
      const id = node.node_id;
      if (sockets[id]) continue;
      const wsUrl = getWsUrl(`/ws/nodes/${encodeURIComponent(id)}/live?token=${encodeURIComponent(token)}`);
      let ws;
      try { ws = new WebSocket(wsUrl); } catch {
        setTelemetry((prev) => ({ ...prev, [id]: { status: 'error', error: 'WS init failed' } }));
        continue;
      }
      sockets[id] = ws;
      setTelemetry((prev) => ({ ...prev, [id]: { status: 'connecting' } }));

      ws.onopen = () => setTelemetry((prev) => ({ ...prev, [id]: { ...prev[id], status: 'open', error: '' } }));
      ws.onerror = () => setTelemetry((prev) => ({ ...prev, [id]: { ...prev[id], status: 'error', error: 'Connection error' } }));
      ws.onclose = (ev) => {
        setTelemetry((prev) => ({ ...prev, [id]: { ...prev[id], status: 'closed' } }));
        if (!ev.wasClean) {
          const delay = 3000 + Math.random() * 2000;
          setTimeout(() => {
            setNodes((curr) => {
              if (!curr.find((n) => n.node_id === id)) return curr;
              try { sockets[id].close(); } catch { /* ignore */ }
              delete sockets[id];
              const token = getToken() || '';
              const wsUrl = getWsUrl(`/ws/nodes/${encodeURIComponent(id)}/live?token=${encodeURIComponent(token)}`);
              let ns;
              try { ns = new WebSocket(wsUrl); } catch { return curr; }
              sockets[id] = ns;
              ns.onopen = () => setTelemetry((prev2) => ({ ...prev2, [id]: { ...prev2[id], status: 'open', error: '' } }));
              ns.onerror = () => setTelemetry((prev2) => ({ ...prev2, [id]: { ...prev2[id], status: 'error', error: 'Connection error' } }));
              ns.onclose = (ev2) => {
                setTelemetry((prev2) => ({ ...prev2, [id]: { ...prev2[id], status: 'closed' } }));
                if (!ev2.wasClean) {
                  setTimeout(() => {
                    setNodes((c) => c.find((n) => n.node_id === id) ? (() => { setTelemetry((p) => ({ ...p, [id]: { ...p[id], status: 'reconnecting' } })); return c; })() : c);
                  }, 3000 + Math.random() * 2000);
                }
              };
              ns.onmessage = (event) => {
                msgCountRef.current += 1;
                try {
                  const outer = JSON.parse(event.data);
                  let payload = outer.payload !== undefined ? outer.payload : outer;
                  if (typeof payload === 'string') {
                    try { payload = JSON.parse(payload); } catch { /* keep string */ }
                  }
                  setTelemetry((prev2) => ({
                    ...prev2,
                    [id]: { status: 'open', lastTs: outer.ts || Date.now(), payload, topic: outer.topic },
                  }));
                } catch {
                  setTelemetry((prev2) => ({
                    ...prev2,
                    [id]: { ...prev2[id], status: 'open', lastTs: Date.now(), payload: event.data },
                  }));
                }
              };
              return curr;
            });
          }, delay);
        }
      };
      ws.onmessage = (event) => {
        msgCountRef.current += 1;
        try {
          const outer = JSON.parse(event.data);
          let payload = outer.payload !== undefined ? outer.payload : outer;
          if (typeof payload === 'string') {
            try { payload = JSON.parse(payload); } catch { /* keep string */ }
          }
          setTelemetry((prev) => ({
            ...prev,
            [id]: { status: 'open', lastTs: outer.ts || Date.now(), payload, topic: outer.topic },
          }));
        } catch {
          setTelemetry((prev) => ({
            ...prev,
            [id]: { ...prev[id], status: 'open', lastTs: Date.now(), payload: event.data },
          }));
        }
      };
    }

    return () => {
      for (const id of Object.keys(sockets)) {
        try { sockets[id].close(); } catch { /* ignore */ }
        delete sockets[id];
      }
    };
  }, [nodes]);

  const pollHealth = useCallback(async () => {
    const checks = [
      { key: 'auth', run: () => request('/health', { auth: true, quiet: true }) },
      { key: 'module', run: () => request('/nodes', { auth: true, quiet: true }) },
      { key: 'control', run: () => request('/control/schedules', { auth: true, quiet: true }) },
      { key: 'stream', run: () => request('/streams', { auth: true, quiet: true }) },
      { key: 'analytics', run: () => request('/analytics/nodes', { auth: true, quiet: true }) },
      { key: 'wsgateway', run: () => {
        const open = Object.values(telemetryRef.current).some((t) => t?.status === 'open');
        return open ? Promise.resolve({}) : Promise.reject(new Error('no live ws'));
      } },
    ];
    await Promise.all(checks.map(async (c) => {
      try {
        await c.run();
        setHealth((h) => ({ ...h, [c.key]: 'up' }));
      } catch {
        setHealth((h) => ({ ...h, [c.key]: 'down' }));
      }
    }));
  }, []);

  useEffect(() => {
    pollHealth();
    const id = setInterval(pollHealth, 5000);
    return () => clearInterval(id);
  }, [pollHealth]);

  const loadSchedules = useCallback(async () => {
    // Only show schedules belonging to the selected module's nodes so the
    // "Upcoming States" timeline matches the module the user picked.
    if (!selectedModule || nodes.length === 0) {
      setNextTransitions([]);
      return;
    }
    try {
      const res = await controlApi.listSchedules();
      const list = Array.isArray(res?.schedules) ? res.schedules : [];
      const moduleNodeIds = new Set(nodes.map((n) => n.node_id));
      const nowMs = Date.now();
      const trans = [];
      for (const s of list) {
        if (s.enabled === false) continue;
        if (s.node_id && !moduleNodeIds.has(s.node_id)) continue;
        trans.push(...computeTransitions(s));
        // Honor a persisted next_run_at (treated as the next ON boundary) if present.
        if (s.next_run_at) {
          const ts = new Date(s.next_run_at).getTime();
          if (!isNaN(ts) && ts >= nowMs - 10000) {
            trans.push({ ts, to: 'on', output: s.output_name || '*', node_id: s.node_id });
          }
        }
      }
      trans.sort((a, b) => a.ts - b.ts);
      setNextTransitions(trans.filter((t) => t.ts >= nowMs - 10000).slice(0, 6));
    } catch {
      setNextTransitions([]);
    }
  }, [selectedModule, nodes]);

  const loadMode = useCallback(async () => {
    if (!selectedNode) { setMode(null); return; }
    try {
      const r = await controlApi.getNodeMode(selectedNode);
      setMode(r?.mode || null);
    } catch {
      setMode(null);
    }
  }, [selectedNode]);

  const loadActuators = useCallback(async () => {
    if (!selectedNode) { setActuators([]); return; }
    try {
      const data = await moduleApi.getActuatorTags(selectedNode);
      const acts = Array.isArray(data?.tags) ? data.tags : [];
      let liveByKey = {};
      try {
        const ctrl = await controlApi.listTargets(selectedNode);
        for (const c of Array.isArray(ctrl?.targets) ? ctrl.targets : []) {
          if (c?.source_key) liveByKey[c.source_key] = c;
        }
      } catch { /* live state optional */ }
      setActuators(acts.map((t) => {
        const sourceKey = t.source_key;
        const label = t.display_name || t.tag_name || (sourceKey ? sourceKey.replace(/^outputs\./, '') : sourceKey);
        return {
          node_id: selectedNode,
          source_key: sourceKey,
          tag_name: t.tag_name,
          label,
          output_type: t.data_type === 'int' ? 'PWM' : 'DIGITAL',
          last_value: liveByKey[sourceKey]?.last_value ?? t.last_value ?? 0,
        };
      }));
    } catch {
      setActuators([]);
    }
  }, [selectedNode]);

  useEffect(() => { loadSchedules(); const id = setInterval(loadSchedules, 10000); return () => clearInterval(id); }, [loadSchedules]);
  useEffect(() => { loadMode(); loadActuators(); }, [loadMode, loadActuators]);

  useEffect(() => {
    const id = setInterval(() => {
      setNow(Date.now());
      const rate = msgCountRef.current;
      msgCountRef.current = 0;
      setThroughput(rate);
    }, 1000);
    return () => clearInterval(id);
  }, []);

  // Status of ALL outputs for the selected node: union of actuator-tagged
  // outputs (with control last_value) and live hardware outputs reported in
  // telemetry.outputs. Live values win so the status reflects the device state.
  const outputStatuses = useMemo(() => {
    if (!selectedNode) return [];
    const live = getByPath(telemetry[selectedNode]?.payload, 'telemetry.outputs');
    const map = new Map();
    for (const a of actuators) {
      map.set(a.source_key, {
        key: a.source_key,
        label: a.label || a.source_key,
        value: a.last_value ?? 0,
        tagged: true,
        live: false,
      });
    }
    if (live && typeof live === 'object') {
      // Only overlay live device state onto outputs that are configured
      // (tagged) for this node. Raw firmware output names like "load1" must
      // not appear for a module that hasn't set up that control yet.
      for (const [name, val] of Object.entries(live)) {
        const cur = map.get(name);
        if (!cur) continue;
        cur.value = typeof val === 'number' ? val : (Number(val) || 0);
        cur.live = true;
        map.set(name, cur);
      }
    }
    return Array.from(map.values());
  }, [actuators, telemetry, selectedNode]);

  const outputOnCount = outputStatuses.filter((o) => Number(o.value) > 0).length;

  // Build the activeModuleData shape the animated SVG expects, from live websocket
  // telemetry (payload.telemetry.outputs / .inputs) and the tagged actuators.
  const activeModuleData = useMemo(
    () => buildActiveModuleData(telemetry[selectedNode]?.payload, actuators),
    [telemetry, selectedNode, actuators]
  );
  const systemHealth = telemetry[selectedNode]?.status === 'open' ? 'healthy' : 'degraded';

  const doAction = async (fn, okMsg) => {
    setActionMsg(''); setActionErr('');
    try {
      await fn();
      setActionMsg(okMsg);
      loadMode();
      loadSchedules();
    } catch (e) {
      setActionErr(e?.message || 'Action failed');
    }
  };

  const setModeAction = (mode) => doAction(
    () => controlApi.setNodeMode(selectedNode, mode),
    `Mode → ${mode}`
  );
  const emergencyStop = () => doAction(
    () => controlApi.sendCommand({ node_id: selectedNode, type: 'emergency_stop' }),
    'Emergency stop sent'
  );
  const resumeNode = () => doAction(
    () => controlApi.resumeNode(selectedNode),
    'Node resumed'
  );
  const sendActuator = async (act, value) => {
    await doAction(
      () => controlApi.sendCommand({
        node_id: act.node_id,
        output: act.source_key,
        type: 'set_state',
        value: Number(value),
      }),
      `${act.label} → ${value ? 'ON' : 'OFF'}`
    );
    loadActuators();
  };

  const upCount = HEALTH_ROWS.filter((s) => health[s.key] === 'up').length;
  const connectedCount = Object.values(telemetry).filter((t) => t?.status === 'open').length;

  return (
    <div className="space-y-4">
      <PageHeader icon={Activity} title="MONITOR" subtitle="System health, live telemetry trend, quick control & next schedule">
        <button
          onClick={() => { loadNodes(); pollHealth(); loadSchedules(); loadMode(); }}
          className="h-10 px-3 flex items-center gap-2 border border-emerald-500/20 text-emerald-400 hover:bg-emerald-500/10 text-xs font-black uppercase tracking-widest cursor-pointer"
          title="Reload"
        >
          <RefreshCw className="w-4 h-4" /> Reload
        </button>
      </PageHeader>

      {error && (
        <div className="flex items-center gap-3 p-3 border border-amber-500/30 bg-amber-500/10 text-amber-300 text-xs font-black uppercase tracking-widest animate-pulse">
          <AlertTriangle className="w-4 h-4" /> {error}
        </div>
      )}

      {/* ── Symmetrical 3-Column Layout: Left (0.5) · Center (Overview, 1.0) · Right (0.5) ── */}
      <div className="grid grid-cols-1 lg:grid-cols-[1fr_2fr_1fr] gap-3 sm:gap-4 items-start">
        {/* ── LEFT COLUMN (narrow, 1fr): System Metrics ── */}
        <div className="flex flex-col gap-3 sm:gap-4">
          {/* Card 1: System Health */}
          <div className="border border-emerald-500/15 bg-[#030705]/80 backdrop-blur-md p-4 flex flex-col gap-3 rounded-none relative overflow-hidden transition-all duration-300 hover:border-emerald-400/30 hover:shadow-lg hover:shadow-emerald-500/5">
            <div className="flex items-center justify-between gap-2 border-b border-slate-100 dark:border-white/5 pb-2">
              <div className="flex items-center gap-2 min-w-0">
                <PulseCircle color="#34d399" size={18} />
                <span className="text-xs font-black uppercase tracking-wider text-white">System Health</span>
              </div>
              <span className={`text-[10px] font-black uppercase tracking-wider px-2 py-0.5 border ${
                upCount === HEALTH_ROWS.length ? 'text-emerald-400 border-emerald-500/30 bg-emerald-500/10' : upCount > 0 ? 'text-amber-400 border-amber-500/30 bg-amber-500/10' : 'text-red-400 border-red-500/30 bg-red-500/10'
              }`}>
                {upCount}/{HEALTH_ROWS.length} UP
              </span>
            </div>
            
            <div className="grid grid-cols-3 gap-2 text-[10px]">
              {HEALTH_ROWS.map((s) => {
                const st = health[s.key];
                const up = st === 'up';
                return (
                  <div key={s.key} className={`flex items-center gap-1.5 px-2 py-1.5 border transition-all duration-200 bg-slate-50/40 dark:bg-black/20 ${
                    up ? 'border-emerald-500/20 text-emerald-600 dark:text-emerald-400' : st === 'down' ? 'border-red-500/20 text-red-600 dark:text-red-400' : 'border-slate-200 dark:border-white/5 text-slate-500'
                  }`}>
                    <span className={`w-2 h-2 rounded-full shrink-0 ${
                      up ? 'bg-emerald-400 shadow-[0_0_6px_rgba(52,211,153,0.6)] animate-pulse' : st === 'down' ? 'bg-red-400 shadow-[0_0_6px_rgba(239,68,68,0.6)] animate-pulse' : 'bg-slate-500'
                    }`} />
                    <span className="font-bold truncate" title={s.label}>{s.label}</span>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Card 2: Upcoming State Changes (Timeline) */}
          <div className="border border-emerald-500/15 bg-[#030705]/80 backdrop-blur-md p-4 flex flex-col gap-3 rounded-none relative overflow-hidden justify-between transition-all duration-300 hover:border-emerald-400/30 hover:shadow-lg hover:shadow-emerald-500/5">
            <div className="flex items-center gap-2 border-b border-slate-100 dark:border-white/5 pb-2">
              <AnimatedCircle color="#34d399" size={18} />
              <span className="text-xs font-black uppercase tracking-wider text-white">Upcoming States</span>
            </div>

            {nextTransitions.length > 0 ? (
              <div className="flex flex-col gap-3 relative pl-3.5 border-l border-dashed border-slate-200 dark:border-slate-800 ml-1.5 py-1">
                {nextTransitions.slice(0, 4).map((t, i) => {
                  const rem = Math.max(0, (t.ts - now) / 1000);
                  const isFirst = i === 0;
                  const isOn = t.to === 'on';
                  return (
                    <div key={`${t.node_id}-${t.output}-${i}`} className="flex flex-col relative gap-0.5">
                      {/* Timeline dot */}
                      <span className={`absolute -left-[18.5px] top-1.5 w-2 h-2 rounded-full border transition-all duration-300 ${
                        isFirst
                          ? (isOn 
                              ? 'bg-emerald-400 border-emerald-500 shadow-[0_0_8px_rgba(52,211,153,0.5)] animate-pulse' 
                              : 'bg-red-400 border-red-500 shadow-[0_0_8px_rgba(239,68,68,0.5)] animate-pulse')
                          : 'bg-slate-400 dark:bg-slate-600 border-slate-300 dark:border-slate-800'
                      }`} />

                      <div className="flex items-center justify-between gap-2">
                        <div className="min-w-0">
                          <div className="text-[10px] text-slate-500 font-black uppercase tracking-widest leading-none truncate">
                            {t.node_id}
                          </div>
                          <div className="text-[11px] font-mono text-slate-800 dark:text-slate-300 font-bold mt-1.5 flex items-center gap-1.5 leading-none">
                            <span className="truncate">{t.output || '*'}</span>
                            <span className={`text-[9px] font-black uppercase px-1 border shrink-0 ${
                              isOn 
                                ? 'text-emerald-500 border-emerald-500/20 bg-emerald-500/5' 
                                : 'text-red-500 border-red-500/20 bg-red-500/5'
                            }`}>
                              {isOn ? 'ON' : 'OFF'}
                            </span>
                          </div>
                        </div>
                        <div className="text-right shrink-0">
                          <div className={`font-mono text-xs tabular-nums ${
                            isFirst ? 'text-base font-black text-emerald-500' : 'text-slate-400'
                          }`}>
                            {fmtCountdown(rem)}
                          </div>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="flex items-center justify-center text-slate-600 gap-2 py-4">
                <CalendarClock className="w-5 h-5 text-slate-600" />
                <span className="text-[11px] font-bold uppercase tracking-wider">No Active Schedule</span>
              </div>
            )}
          </div>

          {/* Card 3: Metrics & Network Stats */}
          <div className="border border-emerald-500/15 bg-[#030705]/80 backdrop-blur-md p-4 flex flex-col gap-3 rounded-none relative overflow-hidden justify-between transition-all duration-300 hover:border-emerald-400/30 hover:shadow-lg hover:shadow-emerald-500/5">
            <div className="flex items-center gap-2 border-b border-slate-100 dark:border-white/5 pb-2">
              <Radio className="w-4 h-4 text-emerald-400" />
              <span className="text-xs font-black uppercase tracking-wider text-white">Network Stats</span>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="flex flex-col">
                <span className="text-[10px] font-black uppercase tracking-widest text-slate-500">Active Nodes</span>
                <div className="text-2xl font-black text-white mt-1 flex items-baseline gap-1">
                  {connectedCount}
                  <span className="text-xs text-slate-500 font-normal">/ {nodes.length}</span>
                </div>
                {/* Live progress indicator */}
                <div className="h-1 w-full bg-slate-200 dark:bg-black/40 mt-2 overflow-hidden relative">
                  <div
                    className="absolute top-0 bottom-0 left-0 bg-emerald-400 transition-all duration-500"
                    style={{ width: `${nodes.length > 0 ? (connectedCount / nodes.length) * 100 : 0}%` }}
                  />
                </div>
              </div>
              <div className="flex flex-col">
                <span className="text-[10px] font-black uppercase tracking-widest text-slate-500">Throughput</span>
                <div className="text-2xl font-black text-emerald-400 mt-1 flex items-baseline gap-1">
                  {throughput}
                  <span className="text-xs text-slate-500 font-normal">msg/s</span>
                </div>
                {/* Live progress indicator */}
                <div className="h-1 w-full bg-slate-200 dark:bg-black/40 mt-2 overflow-hidden relative">
                  <div
                    className="absolute top-0 bottom-0 left-0 bg-emerald-500 transition-all duration-300"
                    style={{ width: `${Math.min(100, (throughput / 10) * 100)}%` }}
                  />
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* ── CENTER COLUMN (wide, 2fr): Overview & Nodes Grid ── */}
        <div className="flex flex-col gap-3 sm:gap-4">
          {/* Live Animated System Schematic + live telemetry trend (driven by websocket telemetry) */}
          {selectedNode && (
            <EnvironmentalOverview
              selectedModule={selectedModule}
              payload={telemetry[selectedNode]?.payload}
              systemHealth={{ status: systemHealth }}
              activeModuleData={activeModuleData}
            />
          )}

          {/* Node Telemetry Grid */}
          <div>
            <div className="text-xs font-black uppercase tracking-wider text-slate-400 mb-2.5">
              Nodes Telemetry Monitor
            </div>
            {loading ? (
              <div className="flex items-center justify-center gap-3 py-20 text-slate-400 border border-emerald-500/10 bg-[#030705]/60">
                <RefreshCw className="w-6 h-6 animate-spin text-emerald-400" />
                <span className="text-xs font-black uppercase tracking-widest">Loading nodes...</span>
              </div>
            ) : nodes.length === 0 ? (
              <div className="flex flex-col items-center justify-center gap-4 py-20 border border-emerald-500/10 bg-[#030705]/60">
                <Cpu className="w-12 h-12 text-slate-600" />
                <div className="text-center">
                  {selectedModule ? (
                    <>
                      <div className="text-sm font-black uppercase tracking-widest text-slate-300">No Nodes Paired</div>
                      <div className="text-xs text-slate-500 mt-1">Pair a node in Module “{selectedModule.name}” to see live telemetry here.</div>
                    </>
                  ) : (
                    <>
                      <div className="text-sm font-black uppercase tracking-widest text-slate-300">No Module Selected</div>
                      <div className="text-xs text-slate-500 mt-1">Select a module from the top bar to view its telemetry.</div>
                    </>
                  )}
                </div>
              </div>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 sm:gap-4">
                {nodes.map((node) => (
                  <NodeTelemetryCard key={node.node_id} node={node} state={telemetry[node.node_id]} />
                ))}
              </div>
            )}
          </div>
        </div>

        {/* ── RIGHT COLUMN (narrow, 1fr): Unified Node Controller ── */}
        <div className="flex flex-col gap-3 sm:gap-4">
          <div className="border border-emerald-500/15 bg-[#030705]/80 backdrop-blur-md p-4 flex flex-col gap-4 transition-all duration-300 hover:border-emerald-400/30 hover:shadow-lg hover:shadow-emerald-500/5">
            <div className="flex items-center justify-between gap-2 pb-2 border-b border-slate-100 dark:border-white/5">
              <div className="flex items-center gap-2">
                <Gauge className="w-4 h-4 text-emerald-400" />
                <span className="text-xs font-black uppercase tracking-wider text-white">Node Controller</span>
              </div>
              <span className={`text-[10px] font-black uppercase tracking-wider px-2 py-0.5 border ${
                telemetry[selectedNode]?.status === 'open'
                  ? 'text-emerald-400 border-emerald-500/30 bg-emerald-500/10'
                  : 'text-red-400 border-red-500/30 bg-red-500/10'
              }`}>
                {telemetry[selectedNode]?.status === 'open' ? 'Online' : 'Offline'}
              </span>
            </div>

            {/* Selector */}
            <div className="flex flex-col gap-1.5">
              <label className="text-[10px] font-black uppercase tracking-widest text-slate-400">Target Node</label>
              <select
                value={selectedNode}
                onChange={(e) => setSelectedNode(e.target.value)}
                className="h-10 bg-black/40 border border-emerald-500/20 text-slate-200 text-xs px-2 outline-none focus:border-emerald-400 cursor-pointer"
              >
                {nodes.length === 0 && <option value="">— No Nodes —</option>}
                {nodes.map((n) => (
                  <option key={n.node_id} value={n.node_id}>{n.name || n.node_id}</option>
                ))}
              </select>
            </div>

            {/* Mode Indicator & Action Controls */}
            <div className="flex flex-col gap-2.5">
              <div className="flex items-center justify-between text-[11px] font-black uppercase tracking-widest">
                <span className="text-slate-400">Current Mode:</span>
                <div className="flex items-center gap-1.5">
                  <span className={`w-2 h-2 rounded-full ${
                    mode === 'EMERGENCY' ? 'bg-red-400 shadow-[0_0_6px_rgba(239,68,68,0.6)] animate-ping'
                      : mode === 'AUTO' ? 'bg-emerald-400 shadow-[0_0_6px_rgba(52,211,153,0.6)] animate-pulse'
                      : mode === 'MANUAL' ? 'bg-amber-400 shadow-[0_0_6px_rgba(217,119,6,0.6)] animate-pulse'
                      : 'bg-slate-600'
                  }`} />
                  <span className={`px-2 py-0.5 border ${
                    mode === 'EMERGENCY' ? 'text-red-400 border-red-500/30 bg-red-500/10 font-black'
                      : mode === 'AUTO' ? 'text-emerald-400 border-emerald-500/30 bg-emerald-500/10 font-black'
                      : mode === 'MANUAL' ? 'text-amber-400 border-amber-500/30 bg-amber-500/10 font-black'
                      : 'text-slate-400 border-slate-200 dark:border-white/10'
                  }`}>{mode || '—'}</span>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-2">
                <button onClick={() => setModeAction('MANUAL')}
                  disabled={!selectedNode}
                  className={`h-9 border text-[11px] font-black uppercase tracking-widest transition-all duration-200 cursor-pointer disabled:opacity-40 ${
                    mode === 'MANUAL'
                      ? 'bg-emerald-500 border-emerald-500 text-black shadow-[0_0_12px_rgba(16,185,129,0.35)]'
                      : 'border-slate-200 dark:border-emerald-500/20 text-slate-700 dark:text-emerald-400 hover:bg-emerald-500/10'
                  }`}>
                  Manual
                </button>
                <button onClick={() => setModeAction('AUTO')}
                  disabled={!selectedNode}
                  className={`h-9 border text-[11px] font-black uppercase tracking-widest transition-all duration-200 cursor-pointer disabled:opacity-40 ${
                    mode === 'AUTO'
                      ? 'bg-emerald-500 border-emerald-500 text-black shadow-[0_0_12px_rgba(16,185,129,0.35)]'
                      : 'border-slate-200 dark:border-emerald-500/20 text-slate-700 dark:text-emerald-400 hover:bg-emerald-500/10'
                  }`}>
                  Auto
                </button>
                <button onClick={emergencyStop}
                  disabled={!selectedNode}
                  className={`h-9 border text-[11px] font-black uppercase tracking-widest transition-all duration-200 cursor-pointer disabled:opacity-40 col-span-2 ${
                    mode === 'EMERGENCY'
                      ? 'bg-red-500 border-red-500 text-white shadow-[0_0_12px_rgba(239,68,68,0.4)] animate-pulse'
                      : 'border-red-500/30 text-red-500 hover:bg-red-500/10'
                  }`}>
                  Emergency Stop
                </button>
                <button onClick={resumeNode}
                  disabled={!selectedNode}
                  className={`h-9 border text-[11px] font-black uppercase tracking-widest transition-all duration-200 cursor-pointer disabled:opacity-40 col-span-2 ${
                    mode === 'EMERGENCY'
                      ? 'border-emerald-500 text-emerald-400 bg-emerald-500/10 shadow-[0_0_10px_rgba(16,185,129,0.2)] font-black'
                      : 'border-emerald-500/20 text-emerald-400 hover:bg-emerald-500/10'
                  }`}>
                  Resume Node
                </button>
              </div>
            </div>

            {/* Actuator Controls (MANUAL mode only) */}
            {mode === 'MANUAL' && (
              <div className="flex flex-col gap-2 border-t border-slate-100 dark:border-white/5 pt-3 animate-in fade-in slide-in-from-top-1 duration-200">
                <label className="text-[10px] font-black uppercase tracking-widest text-slate-400 mb-1">Actuators Control</label>
                {actuators.length === 0 ? (
                  <div className="text-[10px] text-slate-500 text-center py-2">No Tagged Actuators.</div>
                ) : (
                  <div className="grid grid-cols-2 gap-2">
                    {actuators.map((a) => {
                      const on = (a.last_value ?? 0) > 0;
                      return (
                        <button
                          key={a.source_key}
                          onClick={() => sendActuator(a, on ? 0 : 1)}
                          disabled={!selectedNode}
                          title={`${a.output_type} · ${a.tag_name || a.source_key}`}
                          className={`h-9 flex items-center justify-center gap-1.5 border text-[11px] font-black uppercase tracking-widest disabled:opacity-40 cursor-pointer transition-all duration-200 ${
                            on
                              ? 'border-emerald-500 bg-emerald-500/10 text-emerald-400 shadow-[0_0_8px_rgba(16,185,129,0.15)] font-black'
                              : 'border-slate-200 dark:border-white/10 text-slate-600 dark:text-slate-400 bg-slate-50/30 dark:bg-transparent hover:border-slate-300 dark:hover:border-white/20'
                          }`}
                        >
                          <span className="truncate">{a.label}</span>
                          <span className={`shrink-0 px-1 border ${on ? 'border-emerald-500/30 text-emerald-400' : 'border-slate-500/30 text-slate-500'}`}>
                            {on ? 'ON' : 'OFF'}
                          </span>
                        </button>
                      );
                    })}
                  </div>
                )}
              </div>
            )}

            {/* Live Outputs Status list (Visual feedback) */}
            {selectedNode && (
              <div className="flex flex-col gap-2 border-t border-slate-100 dark:border-white/5 pt-3">
                <div className="flex items-center justify-between gap-2 mb-1">
                  <span className="text-[10px] font-black uppercase tracking-widest text-slate-400">Live Outputs Status</span>
                  <span className={`text-[10px] font-black uppercase tracking-widest ${
                    outputOnCount > 0 ? 'text-emerald-400' : 'text-slate-500'
                  }`}>
                    {outputOnCount}/{outputStatuses.length} ON
                  </span>
                </div>

                {outputStatuses.length === 0 ? (
                  <div className="py-3 text-center text-[10px] text-slate-500 uppercase tracking-wider">
                    No Live Outputs Detected.
                  </div>
                ) : (
                  <div className="grid grid-cols-2 gap-2">
                    {outputStatuses.map((o) => {
                      const on = Number(o.value) > 0;
                      const pwm = Number(o.value) > 1;
                      return (
                        <div
                          key={o.key}
                          className={`flex items-center justify-between gap-2 px-2 py-1.5 border transition-all duration-200 ${
                            on 
                              ? 'border-emerald-500/30 bg-emerald-500/5 text-emerald-400' 
                              : 'border-slate-200 dark:border-white/5 bg-slate-50/30 dark:bg-transparent'
                          }`}
                          title={o.tagged ? 'Tagged Actuator' : 'Live Hardware Output'}
                        >
                          <span className="text-[11px] text-slate-200 truncate">{o.label}</span>
                          <span className={`shrink-0 px-1.5 py-0.5 text-[9px] font-black uppercase tracking-wider border ${
                            on
                              ? 'text-emerald-400 border-emerald-500/30 bg-emerald-500/10'
                              : 'text-slate-500 border-slate-600/30'
                          }`}>
                            {on ? (pwm ? `ON ${o.value}` : 'ON') : 'OFF'}
                          </span>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            )}

            {/* Feedback messages */}
            {(actionMsg || actionErr) && (
              <div className="border-t border-slate-100 dark:border-white/5 pt-2 flex flex-col gap-1">
                {actionMsg && <div className="text-[10px] font-black uppercase tracking-widest text-emerald-400">{actionMsg}</div>}
                {actionErr && <div className="text-[10px] font-black uppercase tracking-widest text-red-400">{actionErr}</div>}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default Monitor;
