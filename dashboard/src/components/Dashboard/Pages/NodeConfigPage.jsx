import { useEffect, useRef, useState, useCallback } from 'react';
import { ArrowLeft, Activity, Tags, Plus, Trash2, Save, Radio, AlertTriangle, RefreshCw, Wifi, WifiOff, SlidersHorizontal } from 'lucide-react';
import { getToken, getWsUrl } from '../../../api/client';
import { moduleApi } from '../../../api/module';

function safeJson(raw) {
  try { return JSON.parse(raw); }
  catch { return raw; }
}

function prettyPrint(value) {
  try { return JSON.stringify(value, null, 2); }
  catch { return String(value); }
}

function highlight(jsonStr) {
  return jsonStr.split('\n').map((line, i) => {
    let out = line.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    out = out.replace(/("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*")(\s*:)/g, '<span class="text-emerald-400 font-bold">$1</span>$3');
    out = out.replace(/: \s*("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*")/g, ': <span class="text-amber-300">$1</span>');
    out = out.replace(/: \s*(true|false|null|\d+(\.\d+)?)/g, (m, p1) => {
      const color = p1 === 'null' ? 'text-gray-500' : p1 === 'true' || p1 === 'false' ? 'text-violet-400 font-semibold' : 'text-cyan-400';
      return `: <span class="${color}">${p1}</span>`;
    });
    return <div key={i} className="font-mono text-[11px] sm:text-xs leading-relaxed whitespace-pre" dangerouslySetInnerHTML={{ __html: out }} />;
  });
}

function inferType(value) {
  if (typeof value === 'boolean') return 'bool';
  if (typeof value === 'number') return Number.isInteger(value) ? 'int' : 'float';
  return 'float';
}

function collectPaths(obj, prefix, out) {
  for (const [k, v] of Object.entries(obj)) {
    const key = prefix ? `${prefix}.${k}` : k;
    if (v && typeof v === 'object' && !Array.isArray(v)) {
      collectPaths(v, key, out);
    } else if (typeof v === 'number' || typeof v === 'boolean' || typeof v === 'string') {
      out[key] = v;
    }
  }
}

// Collect only controllable outputs from a payload. Firmware publishes outputs
// under `telemetry.outputs.<name>` (or a top-level `outputs.<name>`); we store
// the bare output name (e.g. "load1") because that is exactly the `target`
// the Control Service publishes to MQTT and the firmware matches via hw.name.
function collectOutputPaths(obj, prefix, out) {
  if (!obj || typeof obj !== 'object') return;
  for (const [k, v] of Object.entries(obj)) {
    const key = prefix ? `${prefix}.${k}` : k;
    if (k === 'outputs' && v && typeof v === 'object' && !Array.isArray(v)) {
      for (const [ok, ov] of Object.entries(v)) {
        if (ov && typeof ov === 'object' && !Array.isArray(ov)) {
          collectOutputPaths(ov, ok, out);
        } else if (typeof ov === 'number' || typeof ov === 'boolean' || typeof ov === 'string') {
          out[ok] = ov;
        }
      }
    } else if (v && typeof v === 'object' && !Array.isArray(v)) {
      collectOutputPaths(v, key, out);
    }
  }
}

// Normalize a user-entered key to the bare firmware output name. Accepts
// `telemetry.outputs.load1`, `outputs.load1`, or just `load1` → "load1".
// This bare name is what the firmware expects as the MQTT command target.
function normalizeActuatorKey(raw) {
  let k = (raw || '').trim();
  const i = k.toLowerCase().lastIndexOf('outputs.');
  if (i !== -1) k = k.slice(i + 'outputs.'.length);
  return k;
}

function NodeConfigPage({ node, onBack }) {
  const [messages, setMessages] = useState([]);
  const [connState, setConnState] = useState('connecting');
  const [wsError, setWsError] = useState('');
  const wsRef = useRef(null);
  const scrollRef = useRef(null);
  const listRef = useRef([]);

  const [tags, setTags] = useState([]);
  const [draft, setDraft] = useState({ source_key: '', tag_name: '', display_name: '', label: '', unit: '', data_type: 'float' });
  const [isSaving, setIsSaving] = useState(false);
  const [tagError, setTagError] = useState('');
  const [detecting, setDetecting] = useState(false);

  // Actuator (control output) tags
  const [actuatorTags, setActuatorTags] = useState([]);
  const [actDraft, setActDraft] = useState({ source_key: '', tag_name: '', display_name: '', unit: '', data_type: 'int' });
  const [actBusy, setActBusy] = useState(false);
  const [detectingOutputs, setDetectingOutputs] = useState(false);

  const nodeId = node.node_id;

  const closeWs = useCallback(() => {
    const ws = wsRef.current;
    if (ws) {
      try { ws.onclose = null; ws.close(); } catch { /* ignore */ }
      wsRef.current = null;
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    let started = false;
    const wsUrl = getWsUrl(`/ws/nodes/${encodeURIComponent(nodeId)}/live?token=${encodeURIComponent(getToken() || '')}`);

    // Defer socket creation a few ticks so React StrictMode's dev-only double
    // mount/unmount finishes before we open the WebSocket. Opening it during
    // the first (discarded) mount and then tearing it down mid-handshake is
    // what produced the "WebSocket is closed before the connection is
    // established" warning.
    const timer = setTimeout(() => {
      if (cancelled) return;
      started = true;
      let ws;
      try { ws = new WebSocket(wsUrl); }
      catch {
        setConnState('error');
        setWsError('Failed to open live monitor connection.');
        return;
      }
      wsRef.current = ws;

      ws.onopen = () => { if (!cancelled) setConnState('open'); };
      ws.onerror = () => { if (!cancelled) { setConnState('error'); setWsError('Connection lost. The device may be offline or the WebSocket may be unavailable.'); } };
      ws.onclose = () => { if (!cancelled) setConnState('closed'); };
      ws.onmessage = (event) => {
        if (cancelled) return;
        try {
          const data = JSON.parse(event.data);
          const payload = typeof data.payload === 'string' ? safeJson(data.payload) : data.payload;
          const entry = { id: `${data.ts}-${Math.random().toString(36).slice(2, 7)}`, topic: data.topic, payload, ts: data.ts };
          listRef.current = [...listRef.current, entry].slice(-200);
          setMessages(listRef.current);
        } catch (err) { console.warn('monitor: bad frame', err); }
      };
    }, 120);

    return () => {
      cancelled = true;
      clearTimeout(timer);
      if (started && wsRef.current) {
        try { wsRef.current.onclose = null; wsRef.current.close(); } catch { /* ignore */ }
        wsRef.current = null;
      }
    };
  }, [nodeId, closeWs]);

  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [messages]);

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        const data = await moduleApi.getNodeTags(nodeId);
        if (!cancelled) setTags(Array.isArray(data?.tags) ? data.tags : []);
      } catch (err) {
        if (!cancelled) setTagError(err.message || 'Failed to load tag mapping');
      }
    };
    load();
    return () => { cancelled = true; };
  }, [nodeId]);

  useEffect(() => {
    let cancelled = false;
    const loadAct = async () => {
      try {
        const d = await moduleApi.getActuatorTags(nodeId);
        if (!cancelled) setActuatorTags(Array.isArray(d?.tags) ? d.tags : []);
      } catch { if (!cancelled) setActuatorTags([]); }
    };
    loadAct();
    return () => { cancelled = true; };
  }, [nodeId]);

  const handleDetect = () => {
    setDetecting(true);
    setTagError('');
    const wsUrl = getWsUrl(`/ws/nodes/${encodeURIComponent(nodeId)}/live?token=${encodeURIComponent(getToken() || '')}`);
    let ws;
    try { ws = new WebSocket(wsUrl); }
    catch { setTagError('Failed to open live stream for detection.'); setDetecting(false); return; }
    const found = {};
    const timer = setTimeout(() => {
      try { ws.close(); } catch { /* ignore */ }
      setDetecting(false);
      setTags(prev => {
        const existing = new Set(prev.map(t => t.source_key));
        const additions = Object.keys(found).filter(k => !existing.has(k)).map(k => ({
          source_key: k, tag_name: k, display_name: k, label: '', unit: '', data_type: inferType(found[k]), enabled: true,
        }));
        return [...prev, ...additions];
      });
    }, 5000);
    ws.onmessage = (ev) => {
      try {
        const msg = JSON.parse(ev.data);
        const payload = typeof msg.payload === 'string' ? JSON.parse(msg.payload) : msg.payload;
        if (payload && typeof payload === 'object') collectPaths(payload, '', found);
      } catch { /* ignore */ }
    };
    ws.onerror = () => { setTagError('Live stream error during detection.'); setDetecting(false); clearTimeout(timer); };
  };

  const handleAdd = () => {
    if (!draft.source_key.trim()) { setTagError('Source key (MQTT telemetry key) is required.'); return; }
    setTags(prev => [...prev, {
      source_key: draft.source_key.trim(), tag_name: draft.tag_name.trim() || draft.source_key.trim(),
      display_name: draft.display_name.trim(), label: draft.label.trim(), unit: draft.unit.trim(), data_type: draft.data_type, enabled: true,
    }]);
    setDraft({ source_key: '', tag_name: '', display_name: '', label: '', unit: '', data_type: 'float' });
    setTagError('');
  };

  const handleUpdate = (idx, field, value) => {
    setTags(prev => prev.map((t, i) => i === idx ? { ...t, [field]: value } : t));
  };

  const handleRemove = (idx) => {
    setTags(prev => prev.filter((_, i) => i !== idx));
  };

  const handleSave = async () => {
    setIsSaving(true);
    setTagError('');
    try {
      await moduleApi.saveNodeTags(nodeId, tags.map(t => ({
        id: t.id, source_key: t.source_key, tag_name: t.tag_name, display_name: t.display_name,
        label: t.label, unit: t.unit, data_type: t.data_type, enabled: t.enabled,
      })));
      const data = await moduleApi.getNodeTags(nodeId);
      setTags(Array.isArray(data?.tags) ? data.tags : []);
    } catch (err) {
      setTagError(err.message || 'Failed to save tag mapping');
    } finally {
      setIsSaving(false);
    }
  };

  // ─── Actuator tag handlers ─────────────────────────────────────────────
  const handleCreateActuator = async () => {
    if (!actDraft.source_key.trim()) { setTagError('Source key (e.g. telemetry.outputs.load1) is required.'); return; }
    setActBusy(true);
    setTagError('');
    try {
      const sourceKey = normalizeActuatorKey(actDraft.source_key);
      await moduleApi.createActuatorTag(nodeId, {
        source_key: sourceKey,
        tag_name: actDraft.tag_name.trim() || sourceKey.replace(/^outputs\./, ''),
        display_name: actDraft.display_name.trim(),
        unit: actDraft.unit.trim(),
        data_type: actDraft.data_type,
      });
      setActDraft({ source_key: '', tag_name: '', display_name: '', unit: '', data_type: 'int' });
      const d = await moduleApi.getActuatorTags(nodeId);
      setActuatorTags(Array.isArray(d?.tags) ? d.tags : []);
    } catch (err) {
      setTagError(err.message || 'Failed to create actuator mapping');
    } finally {
      setActBusy(false);
    }
  };

  const handleDeleteActuator = async (id) => {
    setActBusy(true);
    setTagError('');
    try {
      await moduleApi.deleteActuatorTag(nodeId, id);
      const d = await moduleApi.getActuatorTags(nodeId);
      setActuatorTags(Array.isArray(d?.tags) ? d.tags : []);
    } catch (err) {
      setTagError(err.message || 'Failed to delete actuator mapping');
    } finally {
      setActBusy(false);
    }
  };

  // Edit a field of an existing actuator mapping (local state; persisted via Save).
  const handleUpdateActuator = (idx, field, value) => {
    setActuatorTags(prev => prev.map((t, i) => i === idx ? { ...t, [field]: value } : t));
  };

  // Persist every actuator mapping (upsert by id). Lets the user re-edit the
  // type / tag / label / unit produced by "Detect Outputs".
  const handleSaveActuators = async () => {
    setActBusy(true);
    setTagError('');
    try {
      for (const t of actuatorTags) {
        await moduleApi.createActuatorTag(nodeId, {
          id: t.id,
          source_key: normalizeActuatorKey(t.source_key),
          tag_name: t.tag_name?.trim() || normalizeActuatorKey(t.source_key).replace(/^outputs\./, ''),
          display_name: t.display_name?.trim() || '',
          unit: t.unit?.trim() || '',
          data_type: t.data_type,
        });
      }
      const d = await moduleApi.getActuatorTags(nodeId);
      setActuatorTags(Array.isArray(d?.tags) ? d.tags : []);
    } catch (err) {
      setTagError(err.message || 'Failed to save actuator mapping');
    } finally {
      setActBusy(false);
    }
  };

  // Detect controllable outputs (telemetry.outputs.*) from the live MQTT stream.
  const handleDetectOutputs = () => {
    setDetectingOutputs(true);
    setTagError('');
    const wsUrl = getWsUrl(`/ws/nodes/${encodeURIComponent(nodeId)}/live?token=${encodeURIComponent(getToken() || '')}`);
    let ws;
    try { ws = new WebSocket(wsUrl); }
    catch { setTagError('Failed to open live stream for output detection.'); setDetectingOutputs(false); return; }
    const found = {};
    const timer = setTimeout(async () => {
      try { ws.close(); } catch { /* ignore */ }
      setDetectingOutputs(false);
      const keys = Object.keys(found);
      if (keys.length === 0) {
        setTagError('No output detected within 5 seconds. Ensure the device is sending telemetry.outputs.*');
        return;
      }
      for (const k of keys) {
        const sourceKey = normalizeActuatorKey(k);
        try {
          await moduleApi.createActuatorTag(nodeId, {
            source_key: sourceKey,
            tag_name: sourceKey.replace(/^outputs\./, ''),
            display_name: '',
            unit: '',
            data_type: inferType(found[k]),
          });
        } catch { /* skip duplicates — backend upserts */ }
      }
      const d = await moduleApi.getActuatorTags(nodeId);
      setActuatorTags(Array.isArray(d?.tags) ? d.tags : []);
    }, 5000);
    ws.onmessage = (ev) => {
      try {
        const msg = JSON.parse(ev.data);
        const payload = typeof msg.payload === 'string' ? JSON.parse(msg.payload) : msg.payload;
        if (payload && typeof payload === 'object') collectOutputPaths(payload, '', found);
      } catch { /* ignore */ }
    };
    ws.onerror = () => { setTagError('Live stream error during output detection.'); setDetectingOutputs(false); clearTimeout(timer); };
  };

  return (
    <div className="min-h-screen flex flex-col" style={{ backgroundColor: 'var(--bg-main)' }}>
      {/* Header */}
      <div className="p-3 sm:p-4 border-b flex items-center justify-between gap-2 sm:gap-3" style={{ backgroundColor: 'var(--bg-main)', borderColor: 'var(--border-main)' }}>
        <div className="flex items-center gap-2 min-w-0">
          <button onClick={onBack} className="p-1.5 sm:p-2 bg-slate-900 border border-slate-700 text-slate-400 hover:text-white hover:bg-slate-800 transition-colors cursor-pointer shrink-0">
            <ArrowLeft className="w-4 h-4 sm:w-5 sm:h-5" />
          </button>
          <div className="min-w-0">
            <h3 className="text-xs sm:text-sm font-black uppercase tracking-wider text-white truncate">
              Config: <span className="text-emerald-400 font-mono">{nodeId}</span>
            </h3>
            <p className="text-[9px] sm:text-[10px] text-slate-400 font-black uppercase tracking-wider mt-0.5 truncate">
              {node.name || node.node_id} • {node.ip || 'DHCP'} • FW {node.fw_version || '-'}
            </p>
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-3 sm:p-4 lg:p-6 space-y-4 sm:space-y-6">
        {/* ─── LIVE MQTT MONITOR ─── */}
        <div>
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 sm:gap-3 mb-2 sm:mb-3">
            <h4 className="text-[10px] sm:text-xs font-black uppercase tracking-widest text-emerald-400 flex items-center gap-1.5 sm:gap-2">
              <Activity className="w-3.5 h-3.5 sm:w-4 sm:h-4" /> Live MQTT Monitor
            </h4>
            <span className={`flex items-center gap-1 px-1.5 py-0.5 sm:px-2 sm:py-1 text-[9px] sm:text-[10px] font-black uppercase tracking-wider border ${
              connState === 'open' ? 'text-emerald-400 border-emerald-500/30 bg-emerald-500/10'
                : connState === 'error' || connState === 'closed' ? 'text-red-400 border-red-500/30 bg-red-500/10'
                : 'text-amber-400 border-amber-500/30 bg-amber-500/10'
            }`}>
              {connState === 'open' ? <Wifi className="w-2.5 h-2.5 sm:w-3 sm:h-3" /> : <WifiOff className="w-2.5 h-2.5 sm:w-3 sm:h-3" />}
              {connState}
            </span>
          </div>
          <div ref={scrollRef} className="h-48 sm:h-56 lg:h-64 overflow-y-auto border border-slate-800 bg-[#040806] p-2 sm:p-3 space-y-2">
            {connState !== 'open' && messages.length === 0 && (
              <div className="h-full flex flex-col items-center justify-center text-center gap-2 sm:gap-3 text-slate-500">
                {connState === 'error' || connState === 'closed' ? (
                  <><AlertTriangle className="w-6 h-6 sm:w-8 sm:h-8 text-red-400/70" /><p className="text-[10px] sm:text-xs font-bold uppercase tracking-wider">{wsError || 'Connection closed'}</p></>
                ) : (
                  <><div className="w-8 h-8 sm:w-10 sm:h-10 border-2 border-emerald-500 border-t-transparent rounded-full animate-spin" /><p className="text-[10px] sm:text-[11px] font-bold uppercase tracking-wider animate-pulse">Waiting for payload...</p></>
                )}
              </div>
            )}
            {messages.length === 0 && connState === 'open' && (
              <div className="py-8 sm:py-12 flex flex-col items-center justify-center text-slate-500 gap-2">
                <Radio className="w-5 h-5 sm:w-6 sm:h-6 text-emerald-400/70 animate-pulse" />
                <p className="text-[10px] sm:text-[11px] font-bold uppercase tracking-wider">Listening for live MQTT payload...</p>
              </div>
            )}
            {messages.map((m) => (
              <div key={m.id} className="border border-slate-800 bg-black/40 hover:border-emerald-500/30 transition-colors">
                <div className="flex items-center justify-between gap-2 px-2 sm:px-3 py-1 sm:py-1.5 border-b border-slate-800 bg-slate-950/60">
                  <span className="font-mono text-[10px] sm:text-[11px] text-emerald-400 truncate">{m.topic}</span>
                  <span className="text-[9px] sm:text-[10px] text-slate-500 font-black shrink-0">{m.ts ? new Date(m.ts).toLocaleTimeString() : ''}</span>
                </div>
                <div className="p-2 sm:p-3 overflow-x-auto text-slate-300">{highlight(prettyPrint(m.payload))}</div>
              </div>
            ))}
          </div>
          <div className="mt-1.5 sm:mt-2 flex items-center justify-between">
            <span className="text-[9px] sm:text-[10px] text-slate-500 font-black uppercase tracking-wider">{messages.length} payload(s)</span>
            <button onClick={() => { listRef.current = []; setMessages([]); }} className="flex items-center gap-1 px-2 py-1 text-[9px] sm:text-[10px] font-black uppercase tracking-wider text-slate-400 border border-slate-700 hover:text-red-400 hover:border-red-500/40 transition-colors cursor-pointer">
              <Trash2 className="w-3 h-3" /> Clear
            </button>
          </div>
        </div>

        {/* ─── TAG MAPPING ─── */}
        <div>
          <h4 className="text-[10px] sm:text-xs font-black uppercase tracking-widest text-emerald-400 flex items-center gap-1.5 sm:gap-2 mb-2 sm:mb-3">
            <Tags className="w-3.5 h-3.5 sm:w-4 sm:h-4" /> Telemetry Mapping
          </h4>
          {tagError && (
            <div className="mb-2 sm:mb-3 p-2 sm:p-3 bg-red-500/10 border border-red-500/20 text-red-400 text-[10px] sm:text-xs flex items-center gap-1.5 sm:gap-2">
              <AlertTriangle className="w-3.5 h-3.5 sm:w-4 sm:h-4" /> {tagError}
            </div>
          )}
          <div className="p-2.5 sm:p-3 border border-emerald-500/15 bg-emerald-500/5 space-y-2 sm:space-y-3 mb-2 sm:mb-3">
            <div className="flex items-center gap-1.5 text-[9px] sm:text-[10px] font-black text-emerald-400 uppercase tracking-widest">
              <Plus className="w-3 h-3 sm:w-3.5 sm:h-3.5" /> Attach new tag
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-5 gap-2 sm:gap-3">
              <input value={draft.source_key} onChange={e => setDraft({ ...draft, source_key: e.target.value })} placeholder="MQTT key" className="bg-slate-900/50 border border-slate-700 px-2 py-1.5 text-[10px] sm:text-xs text-white focus:outline-none focus:border-emerald-500" />
              <input value={draft.tag_name} onChange={e => setDraft({ ...draft, tag_name: e.target.value })} placeholder="DB tag" className="bg-slate-900/50 border border-slate-700 px-2 py-1.5 text-[10px] sm:text-xs text-white focus:outline-none focus:border-emerald-500" />
              <input value={draft.label} onChange={e => setDraft({ ...draft, label: e.target.value })} placeholder="Label" className="bg-slate-900/50 border border-slate-700 px-2 py-1.5 text-[10px] sm:text-xs text-white focus:outline-none focus:border-emerald-500" />
              <input value={draft.unit} onChange={e => setDraft({ ...draft, unit: e.target.value })} placeholder="Unit" className="bg-slate-900/50 border border-slate-700 px-2 py-1.5 text-[10px] sm:text-xs text-white focus:outline-none focus:border-emerald-500" />
              <select value={draft.data_type} onChange={e => setDraft({ ...draft, data_type: e.target.value })} className="bg-slate-900/50 border border-slate-700 px-2 py-1.5 text-[10px] sm:text-xs text-white focus:outline-none focus:border-emerald-500 cursor-pointer">
                <option value="float">float</option><option value="int">int</option><option value="bool">bool</option>
              </select>
            </div>
            <button onClick={handleAdd} className="flex items-center gap-1 px-2.5 py-1.5 text-[10px] font-black uppercase tracking-wider text-black bg-emerald-500 hover:bg-emerald-400 transition-colors cursor-pointer">
              <Plus className="w-3 h-3" /> Add Row
            </button>
          </div>
          <button onClick={handleDetect} disabled={detecting} className="flex items-center gap-1.5 px-2.5 py-1.5 text-[10px] font-black uppercase tracking-wider text-amber-400 border border-amber-500/30 bg-amber-500/5 hover:bg-amber-500/10 disabled:opacity-50 transition-colors cursor-pointer mb-2 sm:mb-3">
            {detecting ? <RefreshCw className="w-3 h-3 animate-spin" /> : <Radio className="w-3 h-3" />}
            {detecting ? 'Detecting...' : 'Detect keys'}
          </button>
          {tags.length === 0 ? (
            <p className="text-[10px] sm:text-xs text-slate-500 italic text-center py-4 sm:py-6 border border-dashed border-slate-800">No tag mapping. Click "Detect" or add manually.</p>
          ) : (
            <div className="overflow-x-auto border border-white/5">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="border-b border-white/5">
                    <th className="py-2.5 px-1.5 sm:py-3 sm:px-2 text-[9px] sm:text-[10px] font-black uppercase tracking-widest text-slate-500 align-middle leading-normal">MQTT Key</th>
                    <th className="py-2.5 px-1.5 sm:py-3 sm:px-2 text-[9px] sm:text-[10px] font-black uppercase tracking-widest text-slate-500 align-middle leading-normal">DB Tag</th>
                    <th className="py-2.5 px-1.5 sm:py-3 sm:px-2 text-[9px] sm:text-[10px] font-black uppercase tracking-widest text-slate-500 align-middle leading-normal">Label</th>
                    <th className="py-2.5 px-1.5 sm:py-3 sm:px-2 text-[9px] sm:text-[10px] font-black uppercase tracking-widest text-slate-500 align-middle leading-normal">Unit</th>
                    <th className="py-2.5 px-1.5 sm:py-3 sm:px-2 text-[9px] sm:text-[10px] font-black uppercase tracking-widest text-slate-500 align-middle leading-normal">Type</th>
                    <th className="py-2.5 px-1.5 sm:py-3 sm:px-2 text-[9px] sm:text-[10px] font-black uppercase tracking-widest text-slate-500 align-middle leading-normal">On</th>
                    <th className="py-2.5 px-1.5 sm:py-3 sm:px-2 align-middle leading-normal"></th>
                  </tr>
                </thead>
                <tbody>
                  {tags.map((t, idx) => (
                    <tr key={t.id || idx} className="border-b border-white/5 last:border-0">
                      <td className="py-1.5 px-1.5 sm:py-2 sm:px-2"><input value={t.source_key} onChange={e => handleUpdate(idx, 'source_key', e.target.value)} className="w-full bg-slate-900/50 border border-slate-700 px-1.5 py-1 text-[10px] sm:text-xs text-emerald-400 font-mono focus:outline-none focus:border-emerald-500" /></td>
                      <td className="py-1.5 px-1.5 sm:py-2 sm:px-2"><input value={t.tag_name} onChange={e => handleUpdate(idx, 'tag_name', e.target.value)} className="w-full bg-slate-900/50 border border-slate-700 px-1.5 py-1 text-[10px] sm:text-xs text-white focus:outline-none focus:border-emerald-500" /></td>
                      <td className="py-1.5 px-1.5 sm:py-2 sm:px-2"><input value={t.label || ''} onChange={e => handleUpdate(idx, 'label', e.target.value)} placeholder={t.tag_name || t.source_key} className="w-28 sm:w-32 bg-slate-900/50 border border-slate-700 px-1.5 py-1 text-[10px] sm:text-xs text-white focus:outline-none focus:border-emerald-500" /></td>
                      <td className="py-1.5 px-1.5 sm:py-2 sm:px-2"><input value={t.unit} onChange={e => handleUpdate(idx, 'unit', e.target.value)} className="w-16 sm:w-20 bg-slate-900/50 border border-slate-700 px-1.5 py-1 text-[10px] sm:text-xs text-white focus:outline-none focus:border-emerald-500" /></td>
                      <td className="py-1.5 px-1.5 sm:py-2 sm:px-2">
                        <select value={t.data_type} onChange={e => handleUpdate(idx, 'data_type', e.target.value)} className="bg-slate-900/50 border border-slate-700 px-1.5 py-1 text-[10px] sm:text-xs text-white focus:outline-none focus:border-emerald-500 cursor-pointer">
                          <option value="float">float</option><option value="int">int</option><option value="bool">bool</option>
                        </select>
                      </td>
                      <td className="py-1.5 px-1.5 sm:py-2 sm:px-2 text-center"><input type="checkbox" checked={t.enabled} onChange={e => handleUpdate(idx, 'enabled', e.target.checked)} className="accent-emerald-500 w-3.5 h-3.5 sm:w-4 sm:h-4 cursor-pointer" /></td>
                      <td className="py-1.5 px-1.5 sm:py-2 sm:px-2 text-right">
                        <button onClick={() => handleRemove(idx)} className="p-1 sm:p-1.5 bg-slate-800 hover:bg-red-500/20 hover:text-red-400 text-slate-400 transition-colors cursor-pointer">
                          <Trash2 className="w-3 h-3 sm:w-3.5 sm:h-3.5" />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          <div className="mt-2 sm:mt-3 flex justify-end">
            <button onClick={handleSave} disabled={isSaving} className="flex items-center gap-1.5 px-3 sm:px-4 py-1.5 sm:py-2 text-[10px] sm:text-xs font-black bg-emerald-500 text-black hover:bg-emerald-400 disabled:opacity-50 transition-colors uppercase tracking-widest cursor-pointer">
              <Save className="w-3 h-3 sm:w-3.5 sm:h-3.5" /> {isSaving ? 'Saving...' : 'Save Mapping'}
            </button>
          </div>
        </div>

        {/* ─── ACTUATOR MAPPING (control outputs) ─── */}
        <div>
          <h4 className="text-[10px] sm:text-xs font-black uppercase tracking-widest text-emerald-400 flex items-center gap-1.5 sm:gap-2 mb-2 sm:mb-3">
            <SlidersHorizontal className="w-3.5 h-3.5 sm:w-4 sm:h-4" /> Actuator Mapping
            <span className="text-[9px] font-normal text-slate-500 normal-case tracking-normal">— control output → shown on the Control page</span>
          </h4>
          <p className="text-[10px] sm:text-xs text-slate-400 mb-2 sm:mb-3">
            Firmware publishes outputs as <b className="text-emerald-300 font-mono">telemetry.outputs.&lt;name&gt;</b> (e.g. <b className="text-emerald-300 font-mono">telemetry.outputs.load1</b>). Map them to a control tag — the stored key is the raw output name (<b className="text-emerald-300 font-mono">load1</b>) sent back to the firmware. Mapped outputs appear as targets in the <b>Control</b> menu. Use <b>Detect Outputs</b> to auto-scan from live MQTT.
          </p>
          <div className="p-2.5 sm:p-3 border border-emerald-500/15 bg-emerald-500/5 space-y-2 sm:space-y-3 mb-2 sm:mb-3">
            <div className="flex items-center gap-1.5 text-[9px] sm:text-[10px] font-black text-emerald-400 uppercase tracking-widest">
              <Plus className="w-3 h-3 sm:w-3.5 sm:h-3.5" /> Attach actuator
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-5 gap-2 sm:gap-3">
              <input
                value={actDraft.source_key}
                onChange={e => setActDraft({ ...actDraft, source_key: e.target.value })}
                placeholder="load1"
                className="bg-slate-900/50 border border-slate-700 px-2 py-1.5 text-[10px] sm:text-xs text-white focus:outline-none focus:border-emerald-500 font-mono"
              />
              <input
                value={actDraft.tag_name}
                onChange={e => setActDraft({ ...actDraft, tag_name: e.target.value })}
                placeholder="Database tag"
                className="bg-slate-900/50 border border-slate-700 px-2 py-1.5 text-[10px] sm:text-xs text-white focus:outline-none focus:border-emerald-500"
              />
              <input
                value={actDraft.display_name}
                onChange={e => setActDraft({ ...actDraft, display_name: e.target.value })}
                placeholder="Label"
                className="bg-slate-900/50 border border-slate-700 px-2 py-1.5 text-[10px] sm:text-xs text-white focus:outline-none focus:border-emerald-500"
              />
              <input
                value={actDraft.unit}
                onChange={e => setActDraft({ ...actDraft, unit: e.target.value })}
                placeholder="Unit"
                className="bg-slate-900/50 border border-slate-700 px-2 py-1.5 text-[10px] sm:text-xs text-white focus:outline-none focus:border-emerald-500"
              />
              <select
                value={actDraft.data_type}
                onChange={e => setActDraft({ ...actDraft, data_type: e.target.value })}
                className="bg-slate-900/50 border border-slate-700 px-2 py-1.5 text-[10px] sm:text-xs text-white focus:outline-none focus:border-emerald-500 cursor-pointer"
              >
                <option value="int">int (PWM/level)</option>
                <option value="bool">bool (ON/OFF)</option>
                <option value="float">float</option>
              </select>
            </div>
            <button
              onClick={handleCreateActuator}
              disabled={actBusy}
              className="flex items-center gap-1 px-2.5 py-1.5 text-[10px] font-black uppercase tracking-wider text-black bg-emerald-500 hover:bg-emerald-400 transition-colors cursor-pointer disabled:opacity-50"
            >
              <Plus className="w-3 h-3" /> Add Actuator
            </button>
          </div>
          <button onClick={handleDetectOutputs} disabled={detectingOutputs} className="flex items-center gap-1.5 px-2.5 py-1.5 text-[10px] font-black uppercase tracking-wider text-amber-400 border border-amber-500/30 bg-amber-500/5 hover:bg-amber-500/10 disabled:opacity-50 transition-colors cursor-pointer mb-2 sm:mb-3">
            {detectingOutputs ? <RefreshCw className="w-3 h-3 animate-spin" /> : <Radio className="w-3 h-3" />}
            {detectingOutputs ? 'Detecting...' : 'Detect Outputs'}
          </button>

          {actuatorTags.length === 0 ? (
            <p className="text-[10px] sm:text-xs text-slate-500 italic text-center py-4 sm:py-6 border border-dashed border-slate-800">No actuator mapping yet. Enter a key or use Detect Outputs.</p>
          ) : (
            <div className="overflow-x-auto border border-white/5">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="border-b border-white/5">
                    <th className="py-2.5 px-1.5 sm:py-3 sm:px-2 text-[9px] sm:text-[10px] font-black uppercase tracking-widest text-slate-500 align-middle leading-normal">Output Key</th>
                    <th className="py-2.5 px-1.5 sm:py-3 sm:px-2 text-[9px] sm:text-[10px] font-black uppercase tracking-widest text-slate-500 align-middle leading-normal">Tag</th>
                    <th className="py-2.5 px-1.5 sm:py-3 sm:px-2 text-[9px] sm:text-[10px] font-black uppercase tracking-widest text-slate-500 align-middle leading-normal">Label</th>
                    <th className="py-2.5 px-1.5 sm:py-3 sm:px-2 text-[9px] sm:text-[10px] font-black uppercase tracking-widest text-slate-500 align-middle leading-normal">Unit</th>
                    <th className="py-2.5 px-1.5 sm:py-3 sm:px-2 text-[9px] sm:text-[10px] font-black uppercase tracking-widest text-slate-500 align-middle leading-normal">Type</th>
                    <th className="py-2.5 px-1.5 sm:py-3 sm:px-2 align-middle leading-normal"></th>
                  </tr>
                </thead>
                <tbody>
                  {actuatorTags.map((t, idx) => (
                    <tr key={t.id || idx} className="border-b border-white/5 last:border-0">
                      <td className="py-1.5 px-1.5 sm:py-2 sm:px-2"><input value={t.source_key} onChange={e => handleUpdateActuator(idx, 'source_key', e.target.value)} className="w-full bg-slate-900/50 border border-slate-700 px-1.5 py-1 text-[10px] sm:text-xs text-emerald-400 font-mono focus:outline-none focus:border-emerald-500" /></td>
                      <td className="py-1.5 px-1.5 sm:py-2 sm:px-2"><input value={t.tag_name} onChange={e => handleUpdateActuator(idx, 'tag_name', e.target.value)} className="w-full bg-slate-900/50 border border-slate-700 px-1.5 py-1 text-[10px] sm:text-xs text-white focus:outline-none focus:border-emerald-500" /></td>
                      <td className="py-1.5 px-1.5 sm:py-2 sm:px-2"><input value={t.display_name} onChange={e => handleUpdateActuator(idx, 'display_name', e.target.value)} placeholder="(optional)" className="w-full bg-slate-900/50 border border-slate-700 px-1.5 py-1 text-[10px] sm:text-xs text-white focus:outline-none focus:border-emerald-500" /></td>
                      <td className="py-1.5 px-1.5 sm:py-2 sm:px-2"><input value={t.unit} onChange={e => handleUpdateActuator(idx, 'unit', e.target.value)} placeholder="-" className="w-14 sm:w-20 bg-slate-900/50 border border-slate-700 px-1.5 py-1 text-[10px] sm:text-xs text-white focus:outline-none focus:border-emerald-500" /></td>
                      <td className="py-1.5 px-1.5 sm:py-2 sm:px-2">
                        <select value={t.data_type} onChange={e => handleUpdateActuator(idx, 'data_type', e.target.value)} className="bg-slate-900/50 border border-slate-700 px-1.5 py-1 text-[10px] sm:text-xs text-white focus:outline-none focus:border-emerald-500 cursor-pointer">
                          <option value="int">int (PWM/level)</option>
                          <option value="bool">bool (ON/OFF)</option>
                          <option value="float">float</option>
                        </select>
                      </td>
                      <td className="py-1.5 px-1.5 sm:py-2 sm:px-2 text-right">
                        <button onClick={() => handleDeleteActuator(t.id)} disabled={actBusy}
                          className="p-1 sm:p-1.5 bg-slate-800 hover:bg-red-500/20 hover:text-red-400 text-slate-400 transition-colors cursor-pointer disabled:opacity-50">
                          <Trash2 className="w-3 h-3 sm:w-3.5 sm:h-3.5" />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          {actuatorTags.length > 0 && (
            <div className="mt-2 sm:mt-3 flex justify-end">
              <button onClick={handleSaveActuators} disabled={actBusy} className="flex items-center gap-1.5 px-3 sm:px-4 py-1.5 sm:py-2 text-[10px] sm:text-xs font-black bg-emerald-500 text-black hover:bg-emerald-400 disabled:opacity-50 transition-colors uppercase tracking-widest cursor-pointer">
                <Save className="w-3 h-3 sm:w-3.5 sm:h-3.5" /> {actBusy ? 'Saving...' : 'Save Mapping'}
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default NodeConfigPage;
