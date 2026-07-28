import { useState, useEffect, useCallback } from 'react';
import {
  SlidersHorizontal,
  Zap,
  Power,
  Gauge,
  RefreshCw,
  Plus,
  Trash2,
  Clock,
  Play,
  Pause,
  Loader2,
  AlertTriangle,
  CheckCircle2,
  Tags,
  ShieldAlert,
  PlayCircle,
  CircleDot,
  Pencil,
  X,
} from 'lucide-react';
import PageHeader from './PageHeader';
import controlApi from '../../../api/control';
import { moduleApi } from '../../../api/module';
import { useModule } from '../../../context/ModuleContext';

// Schedule type → editable parameters (kept in sync with Control Service).
const SCHEDULE_TYPES = {
  interval:  { label: 'Interval',  fields: ['on_sec', 'off_sec', 'value_on', 'value_off'], defaults: { on_sec: 15, off_sec: 300, value_on: 1, value_off: 0 } },
  duration:  { label: 'Duration',  fields: ['total_sec', 'value_on', 'value_off'], defaults: { total_sec: 60, value_on: 1, value_off: 0 } },
  schedule:  { label: 'Schedule',  fields: ['on_at', 'off_at', 'days', 'value_on', 'value_off'], defaults: { on_at: '06:00', off_at: '18:00', days: '', value_on: 1, value_off: 0 } },
  threshold: { label: 'Threshold', fields: ['source_key', 'threshold_high', 'threshold_low', 'value_on', 'value_off'], defaults: { source_key: '', threshold_high: 30, threshold_low: 25, value_on: 1, value_off: 0 } },
  ramp:      { label: 'Ramp',      fields: ['from', 'to', 'duration_sec', 'steps'], defaults: { from: 0, to: 255, duration_sec: 10, steps: 10 } },
  window_pulse: { label: 'Window + Pulse', fields: ['on_at', 'off_at', 'days', 'on_sec', 'off_sec', 'value_on', 'value_off'], defaults: { on_at: '06:00', off_at: '18:00', days: '', on_sec: 30, off_sec: 30, value_on: 1, value_off: 0 } },
};

function shortId(id) {
  if (!id) return id;
  return id.length > 10 ? `${id.slice(0, 6)}…${id.slice(-4)}` : id;
}

// Actuator tags are dedicated control tags (kind="actuator") the user attaches
// in the node's Tag Mapping. Each maps a chosen firmware output to a friendly
// tag. We reshape them into the target objects the control widgets consume.
function actuatorsToTargets(tags) {
  return (tags || []).map((t) => ({
    node_id: t.node_id,
    source_key: t.source_key, // firmware output name, e.g. "pump"
    tag_name: t.tag_name,
    label: displayOf(t),
    output_type: outputTypeOf(t),
    last_value: t.last_value ?? (t.value ?? 0),
    bypass: false,
  }));
}

function displayOf(t) {
  return t.display_name || t.tag_name || (t.source_key ? t.source_key.replace(/^outputs\./, '') : t.source_key);
}

function outputTypeOf(t) {
  return t.data_type === 'int' ? 'PWM' : 'DIGITAL';
}

function statusColor(status) {
  switch (status) {
    case 'acked':
      return 'text-emerald-400';
    case 'sent':
    case 'pending':
      return 'text-amber-400';
    case 'failed':
    case 'timeout':
    case 'error':
      return 'text-red-400';
    case 'nack':
      return 'text-orange-400';
    default:
      return 'text-slate-400';
  }
}

function Card({ title, icon: Icon, children, right }) {
  return (
    <div className="w-full border border-emerald-500/15 bg-[#030705]/80 backdrop-blur-md p-3 sm:p-4">
      <div className="flex items-center justify-between gap-2 mb-3">
        <div className="flex items-center gap-2 min-w-0">
          {Icon && <Icon className="w-4 h-4 text-emerald-400 shrink-0" />}
          <h3 className="text-xs sm:text-sm font-black uppercase tracking-widest text-emerald-400 truncate">{title}</h3>
        </div>
        {right}
      </div>
      {children}
    </div>
  );
}

// ─── Manual target control tile ────────────────────────────────────────────
function TargetTile({ tag, allTargets, onCommand, nodeMode, onToggleBypass }) {
  const allowManual = nodeMode === 'MANUAL' || tag.bypass;
  const isDigital = outputTypeOf(tag) === 'DIGITAL';
  const [busy, setBusy] = useState(false);
  const [level, setLevel] = useState(128);
  const pulseSec = 3;

  // "output" sent to the Control Service is the firmware target = tag source key
  // (e.g. "outputs.pump" → firmware "pump"). The friendly tag_name is recorded.
  const output = tag.source_key;

  const run = async (type, value) => {
    setBusy(true);
    try {
      const body = { node_id: tag.node_id, output, type, targets: allTargets };
      if (tag.bypass) body.bypass = true;
      if (type === 'set_level') body.value = Number(level);
      if (type === 'set_state') body.value = value !== undefined ? Number(value) : (on ? 0 : 1);
      if (type === 'pulse') body.duration_sec = Number(pulseSec);
      await onCommand(body);
    } finally {
      setBusy(false);
    }
  };

  const on = (tag.last_value ?? 0) > 0;

  return (
    <div className="flex flex-col gap-3 p-3 border border-emerald-500/15 bg-[#030705]/60">
      <div className="flex items-center justify-between gap-2">
        <div className="min-w-0">
          <div className="text-sm font-black uppercase tracking-wide text-slate-100 truncate">{displayOf(tag)}</div>
          <div className="text-[9px] font-black uppercase tracking-widest text-slate-500">
            {outputTypeOf(tag)} · {tag.tag_name || '—'}
          </div>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <span
            className={`shrink-0 px-2 py-1 text-[10px] font-black uppercase tracking-widest ${
              on ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30' : 'bg-slate-500/10 text-slate-500 border border-slate-500/20'
            }`}
          >
            {on ? 'ON' : 'OFF'}
          </span>
          {nodeMode === 'AUTO' && (
            <button
              onClick={() => onToggleBypass(tag)}
              title={tag.bypass ? 'Disable bypass' : 'Bypass auto mode'}
              className={`h-7 px-2 flex items-center justify-center border text-[10px] font-black uppercase tracking-widest cursor-pointer disabled:opacity-50 ${
                tag.bypass
                  ? 'bg-amber-500/20 border-amber-500/40 text-amber-300 hover:bg-amber-500/30'
                  : 'bg-slate-500/10 border-slate-500/20 text-slate-400 hover:bg-slate-500/20'
              }`}
            >
              {tag.bypass ? 'BYPASS' : 'BYPASS'}
            </button>
          )}
        </div>
      </div>

      {isDigital ? (
        <div className="flex gap-2">
          <button
            onClick={() => run('set_state')}
            disabled={busy || !allowManual}
            className="flex-1 h-9 flex items-center justify-center gap-2 bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 hover:bg-emerald-500 hover:text-black text-[11px] font-black uppercase tracking-widest cursor-pointer disabled:opacity-50"
          >
            <Power className="w-4 h-4" /> {on ? 'OFF' : 'ON'}
          </button>
          <button
            onClick={() => run('toggle')}
            disabled={busy || !allowManual}
            className="h-9 px-3 flex items-center justify-center bg-slate-500/10 border border-slate-500/20 text-slate-300 hover:bg-slate-500/20 text-[11px] font-black uppercase tracking-widest cursor-pointer disabled:opacity-50"
            title="Toggle"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      ) : (
        <div className="flex flex-col gap-2">
          <div className="flex items-center gap-3">
            <Gauge className="w-4 h-4 text-emerald-400 shrink-0" />
            <input
              type="range"
              min={0}
              max={255}
              value={level}
              onChange={(e) => setLevel(Number(e.target.value))}
              className="flex-1 accent-emerald-500"
            />
            <span className="w-10 text-right text-xs font-black tabular-nums text-slate-200">{level}</span>
          </div>
          <button
            onClick={() => run('set_level')}
            disabled={busy || !allowManual}
            className="h-9 flex items-center justify-center gap-2 bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 hover:bg-emerald-500 hover:text-black text-[11px] font-black uppercase tracking-widest cursor-pointer disabled:opacity-50"
          >
            <Zap className="w-4 h-4" /> Set Level
          </button>
        </div>
      )}

      {!allowManual && (
        <p className="text-[10px] text-slate-500">
          {nodeMode === 'EMERGENCY'
            ? 'Emergency stop active — all outputs forced OFF. Click Resume to re-enable.'
            : 'Automatic Mode — schedule controls outputs. Enable BYPASS on this output for direct override.'}
        </p>
      )}
      {allowManual && tag.bypass && (
        <p className="text-[10px] text-amber-400">Bypass active — this output can be controlled in Automatic mode.</p>
      )}
    </div>
  );
}

// ─── Node control-mode arbitration card ────────────────────────────────────
const MODE_BADGE = {
  MANUAL:    { label: 'MANUAL',                cls: 'bg-amber-500/15 text-amber-400 border-amber-500/30', Icon: ShieldAlert },
  AUTO:      { label: 'AUTOMATIC · RUNNING NORMALLY', cls: 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30', Icon: PlayCircle },
  EMERGENCY: { label: 'EMERGENCY STOP',        cls: 'bg-red-500/15 text-red-400 border-red-500/30', Icon: AlertTriangle },
};

function ModeControl({ nodeMode, busy, hasTargets, onSetMode, onEmergencyStop, onResume }) {
  const badge = MODE_BADGE[nodeMode] || MODE_BADGE.AUTO;
  const BadgeIcon = badge.Icon;
  const isEmergency = nodeMode === 'EMERGENCY';

  return (
    <Card title="Control Mode" icon={CircleDot}>
      <div className="flex flex-col gap-3">
        <div className="flex items-center justify-between gap-3 flex-wrap">
          <div className={`flex items-center gap-2 px-3 py-2 border ${badge.cls}`}>
            <BadgeIcon className="w-4 h-4" />
            <span className="text-[11px] font-black uppercase tracking-widest">{badge.label}</span>
          </div>
          <span className="text-[10px] font-black uppercase tracking-widest text-slate-500">
            Mode arbitrasi
          </span>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => onSetMode('MANUAL')}
            disabled={busy || isEmergency || nodeMode === 'MANUAL'}
            className={`flex-1 h-9 flex items-center justify-center gap-2 text-[11px] font-black uppercase tracking-widest border cursor-pointer disabled:opacity-50 ${
              nodeMode === 'MANUAL'
                ? 'bg-amber-500 text-black border-amber-500'
                : 'bg-amber-500/10 border-amber-500/30 text-amber-400 hover:bg-amber-500 hover:text-black'
            }`}
          >
            <ShieldAlert className="w-4 h-4" /> Manual
          </button>
          <button
            onClick={() => onSetMode('AUTO')}
            disabled={busy || isEmergency || nodeMode === 'AUTO'}
            className={`flex-1 h-9 flex items-center justify-center gap-2 text-[11px] font-black uppercase tracking-widest border cursor-pointer disabled:opacity-50 ${
              nodeMode === 'AUTO'
                ? 'bg-emerald-500 text-black border-emerald-500'
                : 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400 hover:bg-emerald-500 hover:text-black'
            }`}
          >
            <PlayCircle className="w-4 h-4" /> Automatic
          </button>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={onEmergencyStop}
            disabled={busy || isEmergency || !hasTargets}
            className="flex-1 h-9 flex items-center justify-center gap-2 bg-red-500/10 border border-red-500/30 text-red-400 hover:bg-red-500 hover:text-black text-[11px] font-black uppercase tracking-widest cursor-pointer disabled:opacity-50"
          >
            <Power className="w-4 h-4" /> Emergency Stop
          </button>
          {isEmergency && (
            <button
              onClick={onResume}
              disabled={busy}
              className="flex-1 h-9 flex items-center justify-center gap-2 bg-emerald-500 text-black border border-emerald-500 text-[11px] font-black uppercase tracking-widest hover:bg-emerald-400 cursor-pointer disabled:opacity-50"
            >
              <PlayCircle className="w-4 h-4" /> Resume
            </button>
          )}
        </div>
      </div>
    </Card>
  );
}

// ─── Schedule editor row ───────────────────────────────────────────────────
function ScheduleRow({ sched, onEdit, onDelete, onToggle, busy }) {
  const type = SCHEDULE_TYPES[sched.type] || { label: sched.type, fields: [] };
  const params = sched.params || {};
  const chip = (k) => {
    const v = params[k];
    if (v === undefined || v === '' || v === null) return null;
    return (
      <span key={k} className="px-2 py-0.5 text-[9px] font-black uppercase tracking-widest bg-slate-500/10 border border-slate-500/20 text-slate-400">
        {k}: {String(v)}
      </span>
    );
  };

  return (
    <div className="flex flex-col gap-2 p-3 border border-emerald-500/15 bg-[#030705]/60">
      <div className="flex items-center justify-between gap-2">
        <div className="min-w-0">
          <div className="text-sm font-black uppercase tracking-wide text-slate-100 truncate">
            {sched.output_name || '—'}
          </div>
          <div className="text-[9px] font-black uppercase tracking-widest text-emerald-400">{type.label}</div>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <button
            onClick={() => onToggle(sched)}
            disabled={busy}
            className={`h-8 w-8 flex items-center justify-center border cursor-pointer disabled:opacity-50 ${
              sched.enabled
                ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400 hover:bg-emerald-500 hover:text-black'
                : 'bg-slate-500/10 border-slate-500/20 text-slate-400 hover:bg-slate-500/20'
            }`}
            title={sched.enabled ? 'Disable' : 'Enable'}
          >
            {sched.enabled ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
          </button>
          <button
            onClick={() => onEdit(sched)}
            disabled={busy}
            className="h-8 w-8 flex items-center justify-center bg-sky-500/10 border border-sky-500/20 text-sky-300 hover:bg-sky-500 hover:text-black cursor-pointer disabled:opacity-50"
            title="Edit"
          >
            <Pencil className="w-4 h-4" />
          </button>
          <button
            onClick={() => onDelete(sched)}
            disabled={busy}
            className="h-8 w-8 flex items-center justify-center bg-red-500/10 border border-red-500/20 text-red-400 hover:bg-red-500 hover:text-black cursor-pointer disabled:opacity-50"
            title="Delete"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        </div>
      </div>
      <div className="flex flex-wrap gap-1.5">
        {type.fields.map(chip)}
        {sched.node_id && (
          <span className="px-2 py-0.5 text-[9px] font-black uppercase tracking-widest bg-emerald-500/10 border border-emerald-500/20 text-emerald-300">
            {shortId(sched.node_id)}
          </span>
        )}
      </div>
    </div>
  );
}

function ScheduleForm({ nodeId, targets, onCreate, onUpdate, busy, editSched, onCancelEdit }) {
  const isEdit = !!editSched;
  const initType = editSched?.type || 'interval';
  const initOutput = editSched?.output_name || '';
  const initParams = { ...(SCHEDULE_TYPES[editSched?.type]?.defaults || {}), ...(editSched?.params || {}) };

  const [type, setType] = useState(initType);
  const [output, setOutput] = useState(initOutput);
  const [params, setParams] = useState(initParams);

  const outputs = targets;

  const onTypeChange = (t) => {
    setType(t);
    setParams({ ...SCHEDULE_TYPES[t].defaults });
  };

  const setField = (k, v) => setParams((p) => ({ ...p, [k]: v }));

  const numFields = ['on_sec', 'off_sec', 'total_sec', 'value_on', 'value_off', 'threshold_high', 'threshold_low', 'from', 'to', 'duration_sec', 'steps'];
  const daysField = ['days'];

  const submit = async () => {
    const sel = outputs.find((o) => o.source_key === output);
    if (!sel) return;
    const body = {
      node_id: nodeId,
      output_name: output || sel.source_key,
      type,
      params,
      enabled: isEdit ? (editSched.enabled ?? true) : true,
    };
    let ready = { ...params };
    for (const f of SCHEDULE_TYPES[type].fields) {
      if (numFields.includes(f)) ready[f] = Number(params[f]);
      if (daysField.includes(f)) ready[f] = Array.isArray(params[f]) ? params[f] : (params[f] === '' ? [] : String(params[f]).split(',').map(Number));
    }
    body.params = ready;
    if (isEdit) await onUpdate(body);
    else await onCreate(body);
  };

  return (
    <div className={`flex flex-col gap-3 p-3 border bg-[#030705]/40 ${isEdit ? 'border-amber-500/40' : 'border-emerald-500/20'}`}>
      {isEdit && (
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-2 text-[10px] font-black uppercase tracking-widest text-amber-400">
            <Pencil className="w-3.5 h-3.5" /> Edit Schedule
          </div>
          <button
            onClick={onCancelEdit}
            disabled={busy}
            className="h-7 px-2 flex items-center gap-1 bg-slate-500/10 border border-slate-500/20 text-slate-300 hover:bg-slate-500/20 text-[10px] font-black uppercase tracking-widest cursor-pointer disabled:opacity-50"
          >
            <X className="w-3.5 h-3.5" /> Cancel
          </button>
        </div>
      )}
      <div className="grid grid-cols-2 gap-2">
        <select
          value={output}
          onChange={(e) => setOutput(e.target.value)}
          className="h-9 px-2 text-xs font-black uppercase tracking-widest bg-[#040e0a] border border-emerald-500/20 text-slate-200 cursor-pointer focus:outline-none focus:border-emerald-500/60"
        >
          <option value="">Output…</option>
          {outputs.map((o) => (
            <option key={o.source_key} value={o.source_key}>{o.label || o.source_key}</option>
          ))}
        </select>
        <select
          value={type}
          onChange={(e) => onTypeChange(e.target.value)}
          className="h-9 px-2 text-xs font-black uppercase tracking-widest bg-[#040e0a] border border-emerald-500/20 text-slate-200 cursor-pointer focus:outline-none focus:border-emerald-500/60"
        >
          {Object.entries(SCHEDULE_TYPES).map(([k, v]) => (
            <option key={k} value={k}>{v.label}</option>
          ))}
        </select>
      </div>

      <div className="grid grid-cols-2 gap-2">
        {SCHEDULE_TYPES[type].fields.map((f) => (
          <label key={f} className="flex flex-col gap-1">
            <span className="text-[9px] font-black uppercase tracking-widest text-slate-500">{f}</span>
            {f === 'days' ? (
              <input
                type="text"
                value={Array.isArray(params[f]) ? params[f].join(',') : (params[f] ?? '')}
                onChange={(e) => setField(f, e.target.value === '' ? [] : e.target.value.split(',').map((n) => Number(n)).filter((n) => !isNaN(n)))}
                className="h-9 px-2 text-xs bg-[#040e0a] border border-emerald-500/20 text-slate-200 focus:outline-none focus:border-emerald-500/60"
                placeholder="e.g. 1,2,3,4,5"
              />
            ) : (
              <input
                type={numFields.includes(f) ? 'number' : 'text'}
                min={0}
                value={params[f] ?? ''}
                onChange={(e) => setField(f, e.target.value)}
                className="h-9 px-2 text-xs bg-[#040e0a] border border-emerald-500/20 text-slate-200 focus:outline-none focus:border-emerald-500/60"
                placeholder={f}
              />
            )}
          </label>
        ))}
      </div>

      <button
        onClick={submit}
        disabled={busy || !output}
        className={`h-9 flex items-center justify-center gap-2 text-[11px] font-black uppercase tracking-widest cursor-pointer disabled:opacity-50 ${
          isEdit
            ? 'bg-amber-500 text-black hover:bg-amber-400'
            : 'bg-emerald-500 text-black hover:bg-emerald-400'
        }`}
      >
        {isEdit ? <><CheckCircle2 className="w-4 h-4" /> Update Schedule</> : <><Plus className="w-4 h-4" /> Add Schedule</>}
      </button>
    </div>
  );
}

// ─── Main page ─────────────────────────────────────────────────────────────
function ControlPanel() {
  const { selectedModule } = useModule();
  const [nodes, setNodes] = useState([]);
  const [nodeId, setNodeId] = useState('');
  const [targets, setTargets] = useState([]);     // actuator tags (filtered)
  const [schedules, setSchedules] = useState([]);
  const [commands, setCommands] = useState([]);
  const [loading, setLoading] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const [toast, setToast] = useState(null);
  const [nodeMode, setNodeMode] = useState('AUTO'); // MANUAL | AUTO | EMERGENCY
  const [editId, setEditId] = useState(null);
  const [page, setPage] = useState(1);
  const PAGE_SIZE = 4;
  const [cmdPage, setCmdPage] = useState(1);
  const CMD_PAGE_SIZE = 10;
  const editSched = schedules.find((s) => s.id === editId) || null;

  useEffect(() => {
    let active = true;
    (async () => {
      try {
        if (!selectedModule) {
          setNodes([]);
          setNodeId('');
          return;
        }
        const data = await moduleApi.listNodes({ paired: true, module_id: selectedModule.id });
        if (!active) return;
        const list = data?.nodes || [];
        setNodes(list);
        if (list.length > 0) setNodeId(list[0].node_id);
        else setNodeId('');
      } catch (err) {
        if (active) setError(err.message || 'Failed to load nodes');
      }
    })();
    return () => { active = false; };
  }, [selectedModule]);

  const flash = (msg, ok = true) => {
    setToast({ msg, ok });
    setTimeout(() => setToast(null), 2500);
  };

  const loadTags = useCallback(async (id) => {
    if (!id) { setTargets([]); return; }
    // Dedicated actuator tags (kind="actuator") — separate from sensor telemetry.
    const data = await moduleApi.getActuatorTags(id);
    const acts = Array.isArray(data?.tags) ? data.tags : [];
    // Merge the live actuator state (last_value) from the Control Service so the
    // ON/OFF tile reflects the actually-commanded state, not just the tag def.
    let liveByKey = {};
    try {
      const ctrl = await controlApi.listTargets(id);
      for (const c of Array.isArray(ctrl?.targets) ? ctrl.targets : []) {
        if (c?.source_key) liveByKey[c.source_key] = c;
      }
    } catch { /* live state is optional; fall back to tag def */ }
    setTargets(actuatorsToTargets(acts.map((t) => ({
      ...t, node_id: id,
      last_value: liveByKey[t.source_key]?.last_value ?? t.last_value,
      // Preserve bypass state across reloads; default to false for new targets.
      bypass: liveByKey[t.source_key]?.bypass ?? false,
    }))));
  }, []);

  const loadAll = useCallback(async () => {
    if (!nodeId) {
      setSchedules([]); setCommands([]);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      await loadTags(nodeId);
      let mode = 'AUTO';
      try { const m = await controlApi.getNodeMode(nodeId); mode = m?.mode || 'AUTO'; } catch { /* mode optional */ }
      setNodeMode(mode);
      const [s, c] = await Promise.all([
        controlApi.listSchedules(nodeId),
        controlApi.listCommands({ node_id: nodeId, limit: Math.max(100, CMD_PAGE_SIZE) }),
      ]);
      setSchedules(s?.schedules || []);
      setCommands(c?.commands || []);
    } catch (err) {
      setError(err.message || 'Failed to load control data');
    } finally {
      setLoading(false);
    }
  }, [nodeId, loadTags]);

  useEffect(() => { loadAll(); }, [loadAll]);

  const handleNodeChange = (id) => {
    setNodeId(id);
    setPage(1);
    setCmdPage(1);
    setEditId(null);
  };

  const handleUpdateSchedule = async (body) => {
    if (!editId) return;
    setBusy(true);
    try {
      await controlApi.updateSchedule(editId, body);
      flash('Schedule updated');
      setEditId(null);
      await loadAll();
    } catch (err) {
      flash(err.message || 'Update failed', false);
    } finally {
      setBusy(false);
    }
  };

  const handleEditSchedule = (s) => {
    const idx = schedules.findIndex((x) => x.id === s.id);
    if (idx >= 0) setPage(Math.floor(idx / PAGE_SIZE) + 1);
    setEditId(s.id);
  };

  const handleCommand = async (body) => {
    setBusy(true);
    try {
      await controlApi.sendCommand(body);
      flash(`${body.output} · ${body.type} sent`);
      await loadAll();
    } catch (err) {
      flash(err.message || 'Command failed', false);
    } finally {
      setBusy(false);
    }
  };

  const handleToggleBypass = async (tag) => {
    setBusy(true);
    try {
      const newBypass = !tag.bypass;
      // Persist bypass state in the target's local state for UI feedback.
      // The actual bypass behavior is sent per-command via the `bypass` flag.
      setTargets((prev) => prev.map((t) => (t.source_key === tag.source_key ? { ...t, bypass: newBypass } : t)));
      flash(newBypass ? 'Bypass enabled for this output' : 'Bypass disabled');
    } catch (err) {
      flash(err.message || 'Toggle bypass failed', false);
    } finally {
      setBusy(false);
    }
  };

  const handleSetMode = async (mode) => {
    setBusy(true);
    try {
      await controlApi.setNodeMode(nodeId, mode);
      flash(mode === 'MANUAL' ? 'Manual mode active' : 'Automatic mode active');
      await loadAll();
    } catch (err) {
      flash(err.message || 'Set mode failed', false);
    } finally {
      setBusy(false);
    }
  };

  const handleEmergencyStop = async () => {
    setBusy(true);
    try {
      await controlApi.sendCommand({
        node_id: nodeId,
        output: '',
        type: 'emergency_stop',
        targets: targets.map((t) => ({
          node_id: t.node_id, source_key: t.source_key, tag_name: t.tag_name, label: displayOf(t), output_type: outputTypeOf(t),
        })),
      });
      flash('Emergency stop active');
      await loadAll();
    } catch (err) {
      flash(err.message || 'Emergency stop failed', false);
    } finally {
      setBusy(false);
    }
  };

  const handleResume = async () => {
    setBusy(true);
    try {
      const res = await controlApi.resumeNode(nodeId);
      const restored = res?.mode || 'AUTO';
      flash(restored === 'MANUAL' ? 'Control resumed · Manual' : 'Control resumed · Automatic');
      await loadAll();
    } catch (err) {
      flash(err.message || 'Resume failed', false);
    } finally {
      setBusy(false);
    }
  };

  const handleCreateSchedule = async (body) => {
    setBusy(true);
    try {
      await controlApi.createSchedule(body);
      flash('Schedule created');
      await loadAll();
    } catch (err) {
      flash(err.message || 'Create failed', false);
    } finally {
      setBusy(false);
    }
  };

  const handleToggleSchedule = async (sched) => {
    setBusy(true);
    try {
      if (sched.enabled) await controlApi.disableSchedule(sched.id);
      else await controlApi.enableSchedule(sched.id);
      await loadAll();
    } catch (err) {
      flash(err.message || 'Toggle failed', false);
    } finally {
      setBusy(false);
    }
  };

  const handleDeleteSchedule = async (sched) => {
    setBusy(true);
    setBusy(true);
    try {
      await controlApi.deleteSchedule(sched.id);
      flash('Schedule deleted');
      await loadAll();
    } catch (err) {
      flash(err.message || 'Delete failed', false);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flex flex-col gap-4 w-full animate-fadeIn relative">
      <PageHeader icon={SlidersHorizontal} title="Control" subtitle="Attach telemetry tags in the tag editor, then drive those actuator outputs here.">
          <select
            value={nodeId}
            onChange={(e) => handleNodeChange(e.target.value)}
            disabled={nodes.length === 0}
          className="h-10 px-3 text-xs font-black uppercase tracking-widest bg-[#040e0a] border border-emerald-500/20 text-slate-200 cursor-pointer focus:outline-none focus:border-emerald-500/60"
        >
          {nodes.length === 0 && <option value="">No nodes</option>}
          {nodes.map((n) => (
            <option key={n.node_id} value={n.node_id}>{shortId(n.node_id)}</option>
          ))}
        </select>
        <button
          onClick={loadAll}
          disabled={loading || !nodeId}
          className="h-10 w-10 flex items-center justify-center bg-slate-500/10 border border-emerald-500/20 text-emerald-400 hover:bg-emerald-500 hover:text-black cursor-pointer disabled:opacity-50"
          title="Refresh"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
        </button>
      </PageHeader>

      {toast && (
        <div className={`flex items-center gap-2 p-3 border text-xs font-bold ${toast.ok ? 'border-emerald-500/30 bg-emerald-950/15 text-emerald-400' : 'border-red-500/30 bg-red-950/15 text-red-400'}`}>
          {toast.ok ? <CheckCircle2 className="w-4 h-4 shrink-0" /> : <AlertTriangle className="w-4 h-4 shrink-0" />}
          {toast.msg}
        </div>
      )}

      {error && (
        <div className="flex items-center gap-3 p-4 border border-red-500/30 bg-red-950/15 text-red-400">
          <AlertTriangle className="w-5 h-5 shrink-0" />
          <span className="text-xs sm:text-sm font-bold">{error}</span>
        </div>
      )}

      {loading && (
        <div className="flex items-center justify-center gap-3 min-h-[200px] text-emerald-400">
          <Loader2 className="w-6 h-6 animate-spin" />
          <span className="text-xs font-black tracking-widest uppercase">Loading control…</span>
        </div>
      )}

      {!loading && nodes.length === 0 && (
        <div className="flex flex-col items-center justify-center gap-3 min-h-[200px] text-slate-400">
          <SlidersHorizontal className="w-10 h-10 opacity-40" />
          <span className="text-sm font-bold">No paired nodes</span>
          <span className="text-xs text-slate-500 max-w-md text-center">Pair a node in the Module page first, then control its outputs here.</span>
        </div>
      )}

      {!loading && nodeId && (
        <>
          <ModeControl
            nodeMode={nodeMode}
            busy={busy}
            hasTargets={targets.length > 0}
            onSetMode={handleSetMode}
            onEmergencyStop={handleEmergencyStop}
            onResume={handleResume}
          />

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {/* Manual targets (from tag-mapping) */}
            <Card title="Manual Outputs" icon={Zap} right={
              <span className="text-[10px] font-black uppercase tracking-widest text-slate-500">{targets.length} tagged</span>
            }>
              {targets.length === 0 ? (
                <div className="text-xs text-slate-500 flex items-start gap-2">
                  <Tags className="w-4 h-4 mt-0.5 shrink-0" />
                  <span>
                    No actuator tags yet. Open this node's <b>Tag Mapping</b> (in the Module page), select the
                    <b> Actuator</b> tab, then choose a firmware output (e.g. <code>pump</code>) and name the tag.
                    Tagged outputs will appear here as control targets.
                  </span>
                </div>
              ) : (
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {targets.map((t) => (
                    <TargetTile
                      key={`${t.node_id}:${t.source_key}`}
                      tag={t}
                      allTargets={targets.map((x) => ({
                        node_id: x.node_id, source_key: x.source_key, tag_name: x.tag_name, label: displayOf(x), output_type: outputTypeOf(x),
                      }))}
                      onCommand={handleCommand}
                      nodeMode={nodeMode}
                      onToggleBypass={handleToggleBypass}
                    />
                  ))}
                </div>
              )}
            </Card>

            {/* Schedules */}
            <Card title="Automatic Schedules" icon={Clock} right={
              <span className="text-[10px] font-black uppercase tracking-widest text-slate-500">{schedules.length} rules</span>
            }>
              <div className="flex flex-col gap-3">
                <ScheduleForm
                  key={editId ? `edit-${editId}` : 'new'}
                  nodeId={nodeId}
                  targets={targets}
                  onCreate={handleCreateSchedule}
                  onUpdate={handleUpdateSchedule}
                  busy={busy}
                  editSched={editSched}
                  onCancelEdit={() => setEditId(null)}
                />
                {schedules.length === 0 ? (
                  <div className="text-xs text-slate-500">No schedules. Add one to drive this output automatically.</div>
                ) : (
                  <>
                    {schedules
                      .slice((Math.min(page, Math.max(1, Math.ceil(schedules.length / PAGE_SIZE))) - 1) * PAGE_SIZE, Math.min(page, Math.max(1, Math.ceil(schedules.length / PAGE_SIZE))) * PAGE_SIZE)
                      .map((s) => (
                        <ScheduleRow key={s.id} sched={s} onEdit={handleEditSchedule} onDelete={handleDeleteSchedule} onToggle={handleToggleSchedule} busy={busy} />
                      ))}
                    {Math.ceil(schedules.length / PAGE_SIZE) > 1 && (
                      <div className="flex items-center justify-between gap-2 pt-1">
                        <button
                          onClick={() => setPage((p) => Math.max(1, p - 1))}
                          disabled={busy || page <= 1}
                          className="h-8 px-3 flex items-center gap-1 bg-slate-500/10 border border-emerald-500/20 text-emerald-400 hover:bg-emerald-500 hover:text-black text-[10px] font-black uppercase tracking-widest cursor-pointer disabled:opacity-50"
                        >
                          ‹ Prev
                        </button>
                        <span className="text-[10px] font-black uppercase tracking-widest text-slate-500">
                          {Math.min(page, Math.max(1, Math.ceil(schedules.length / PAGE_SIZE)))} / {Math.ceil(schedules.length / PAGE_SIZE)}
                        </span>
                        <button
                          onClick={() => setPage((p) => Math.min(Math.ceil(schedules.length / PAGE_SIZE), p + 1))}
                          disabled={busy || page >= Math.ceil(schedules.length / PAGE_SIZE)}
                          className="h-8 px-3 flex items-center gap-1 bg-slate-500/10 border border-emerald-500/20 text-emerald-400 hover:bg-emerald-500 hover:text-black text-[10px] font-black uppercase tracking-widest cursor-pointer disabled:opacity-50"
                        >
                          Next ›
                        </button>
                      </div>
                    )}
                  </>
                )}
              </div>
            </Card>
          </div>
        </>
      )}

      {/* Command log */}
      {!loading && nodeId && (
        <Card title="Command Log" icon={CheckCircle2} right={
          <span className="text-[10px] font-black uppercase tracking-widest text-slate-500">{commands.length} entries</span>
        }>
          {commands.length === 0 ? (
            <div className="text-xs text-slate-500">No commands sent yet.</div>
          ) : (
            <div className="flex flex-col gap-3">
              <div className="overflow-x-auto">
                <table className="w-full text-xs">
                  <thead>
                    <tr className="text-[10px] font-black uppercase tracking-widest text-slate-500 border-b border-emerald-500/10">
                      <th className="text-left p-2">Output</th>
                      <th className="text-left p-2">Type</th>
                      <th className="text-left p-2">Value</th>
                      <th className="text-left p-2">Status</th>
                      <th className="text-left p-2">Time</th>
                    </tr>
                  </thead>
                  <tbody>
                    {commands
                      .slice((Math.min(cmdPage, Math.max(1, Math.ceil(commands.length / CMD_PAGE_SIZE))) - 1) * CMD_PAGE_SIZE, Math.min(cmdPage, Math.max(1, Math.ceil(commands.length / CMD_PAGE_SIZE))) * CMD_PAGE_SIZE)
                      .map((c) => (
                        <tr key={c.id} className="border-b border-emerald-500/5">
                          <td className="p-2 font-black uppercase tracking-wide text-slate-200">{c.tag_name || c.target || '—'}</td>
                          <td className="p-2 uppercase text-slate-400">{c.control_type}</td>
                          <td className="p-2 tabular-nums text-slate-300">{c.value ?? '—'}</td>
                          <td className="p-2" style={{ color: undefined }}>
                            <span className={statusColor(c.status)}>{c.status}</span>
                          </td>
                          <td className="p-2 text-slate-500">{c.created_at ? new Date(c.created_at).toLocaleTimeString() : '—'}</td>
                        </tr>
                      ))}
                  </tbody>
                </table>
              </div>
              {Math.ceil(commands.length / CMD_PAGE_SIZE) > 1 && (
                <div className="flex items-center justify-between gap-2 pt-1">
                  <button
                    onClick={() => setCmdPage((p) => Math.max(1, p - 1))}
                    disabled={busy || cmdPage <= 1}
                    className="h-8 px-3 flex items-center gap-1 bg-slate-500/10 border border-emerald-500/20 text-emerald-400 hover:bg-emerald-500 hover:text-black text-[10px] font-black uppercase tracking-widest cursor-pointer disabled:opacity-50"
                  >
                    ‹ Prev
                  </button>
                  <span className="text-[10px] font-black uppercase tracking-widest text-slate-500">
                    {Math.min(cmdPage, Math.max(1, Math.ceil(commands.length / CMD_PAGE_SIZE)))} / {Math.ceil(commands.length / CMD_PAGE_SIZE)}
                  </span>
                  <button
                    onClick={() => setCmdPage((p) => Math.min(Math.ceil(commands.length / CMD_PAGE_SIZE), p + 1))}
                    disabled={busy || cmdPage >= Math.ceil(commands.length / CMD_PAGE_SIZE)}
                    className="h-8 px-3 flex items-center gap-1 bg-slate-500/10 border border-emerald-500/20 text-emerald-400 hover:bg-emerald-500 hover:text-black text-[10px] font-black uppercase tracking-widest cursor-pointer disabled:opacity-50"
                  >
                    Next ›
                  </button>
                </div>
              )}
            </div>
          )}
        </Card>
      )}
    </div>
  );
}

export default ControlPanel;
