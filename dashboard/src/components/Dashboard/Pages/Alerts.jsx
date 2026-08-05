import { useState, useEffect, useCallback, Fragment } from 'react';
import {
  ShieldAlert,
  RefreshCw,
  Search,
  Loader2,
  AlertTriangle,
  ChevronLeft,
  ChevronRight,
  Filter,
  Bell,
  Plus,
  Trash2,
  Pencil,
  Check,
  X,
  ChevronDown,
  ChevronRight as ChevronRightIcon,
  Lock,
} from 'lucide-react';
import PageHeader from './PageHeader';
import {
  listAlerts,
  ackAlert,
  listThresholds,
  createThreshold,
  updateThreshold,
  deleteThreshold,
} from '../../../api/alerts';
import { moduleApi } from '../../../api/module';
import analyticsApi from '../../../api/analytics';

const PAGE_SIZES = [25, 50, 100];

const STATUS_FILTERS = [
  { label: 'All', value: '' },
  { label: 'Active', value: 'active' },
  { label: 'Resolved', value: 'resolved' },
  { label: 'Acked', value: 'acked' },
];

const SEVERITY_FILTERS = [
  { label: 'All', value: '' },
  { label: 'Warning', value: 'warning' },
  { label: 'Critical', value: 'critical' },
];

function getUser() {
  try {
    return JSON.parse(sessionStorage.getItem('user') || 'null');
  } catch {
    return null;
  }
}

function canView() {
  const u = getUser();
  const roles = Array.isArray(u?.roles) ? u.roles : [];
  return roles.length > 0;
}

// Operator/admin may acknowledge; viewer cannot.
function canAck() {
  const u = getUser();
  const roles = Array.isArray(u?.roles) ? u.roles : [];
  return roles.includes('operator') || roles.includes('admin');
}

function formatTime(d) {
  try {
    return new Date(d).toLocaleString();
  } catch {
    return '';
  }
}

function severityBadgeClass(sev = '') {
  if (sev === 'critical') return 'bg-red-500/15 text-red-300 border-red-500/30';
  if (sev === 'warning') return 'bg-amber-500/15 text-amber-300 border-amber-500/30';
  return 'bg-slate-500/15 text-slate-300 border-slate-500/30';
}

function statusBadgeClass(status = '') {
  switch (status) {
    case 'active':
      return 'bg-amber-500/15 text-amber-300 border-amber-500/30';
    case 'resolved':
      return 'bg-sky-500/15 text-sky-300 border-sky-500/30';
    case 'acked':
      return 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30';
    default:
      return 'bg-slate-500/15 text-slate-300 border-slate-500/30';
  }
}

function fmtNum(v) {
  return typeof v === 'number' ? v : (v ?? '—');
}

export default function Alerts() {
  const [tab, setTab] = useState('alerts');

  if (!canView()) {
    return (
      <div className="border border-red-500/20 bg-red-500/5 p-6 text-red-300">
        You do not have permission to view alerts.
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Sub-tabs */}
      <div className="flex items-center gap-1 border-b border-emerald-500/15">
        {[
          { id: 'alerts', label: 'Alerts' },
          { id: 'thresholds', label: 'Thresholds' },
        ].map((t) => {
          const active = tab === t.id;
          return (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              className={`px-4 h-11 text-xs font-black uppercase tracking-widest border-b-2 transition-all cursor-pointer ${
                active
                  ? 'border-emerald-500 text-emerald-400'
                  : 'border-transparent text-slate-500 hover:text-emerald-400'
              }`}
            >
              {t.label}
            </button>
          );
        })}
      </div>

      {tab === 'alerts' ? <AlertsHistory /> : <ThresholdsPanel />}
    </div>
  );
}

// ─── Alerts History ───────────────────────────────────────────────────────────
function AlertsHistory() {
  const [alerts, setAlerts] = useState([]);
  const [total, setTotal] = useState(0);
  const [limit, setLimit] = useState(50);
  const [offset, setOffset] = useState(0);
  const [nodeId, setNodeId] = useState('');
  const [metric, setMetric] = useState('');
  const [status, setStatus] = useState('');
  const [severity, setSeverity] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [autoRefresh, setAutoRefresh] = useState(false);
  const [expanded, setExpanded] = useState(null);
  const [busyId, setBusyId] = useState(null);
  const ackAllowed = canAck();

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const data = await listAlerts({ limit, offset, node_id: nodeId, metric, status, severity });
      setAlerts(Array.isArray(data.alerts) ? data.alerts : []);
      setTotal(typeof data.total === 'number' ? data.total : 0);
    } catch (err) {
      setError(err?.message || 'Failed to load alerts');
      setAlerts([]);
    } finally {
      setLoading(false);
    }
  }, [limit, offset, nodeId, metric, status, severity]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    if (!autoRefresh) return;
    const id = setInterval(() => load(), 10000);
    return () => clearInterval(id);
  }, [autoRefresh, load]);

  const page = Math.floor(offset / limit) + 1;
  const totalPages = Math.max(1, Math.ceil(total / limit));
  const goPrev = () => setOffset((o) => Math.max(0, o - limit));
  const goNext = () => setOffset((o) => Math.min(Math.max(0, total - limit), o + limit));

  const handleAck = async (id) => {
    if (!ackAllowed) return;
    setBusyId(id);
    setError('');
    try {
      await ackAlert(id);
      await load();
    } catch (err) {
      setError(err?.message || 'Failed to acknowledge alert');
    } finally {
      setBusyId(null);
    }
  };

  return (
    <>
      <PageHeader
        icon={ShieldAlert}
        title="Alert History"
        subtitle="Threshold-violation events from the Alert Service — streamed live over WebSocket."
      >
        <label className="hidden sm:flex items-center gap-2 text-[11px] font-black uppercase tracking-widest text-slate-400 cursor-pointer select-none">
          <input
            type="checkbox"
            checked={autoRefresh}
            onChange={(e) => setAutoRefresh(e.target.checked)}
            className="accent-emerald-500 w-4 h-4"
          />
          Live
        </label>
        <button
          onClick={load}
          disabled={loading}
          className="flex items-center justify-center gap-2 px-4 h-10 bg-emerald-500 text-black font-black text-xs uppercase tracking-widest hover:bg-emerald-400 transition-all active:scale-95 disabled:opacity-60 cursor-pointer"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </PageHeader>

      {/* Filters */}
      <div className="border border-emerald-500/15 bg-[#030705]/60 p-3 sm:p-4 flex flex-col gap-3">
        <div className="flex flex-col sm:flex-row gap-3">
          <div className="flex-1 flex items-center gap-2 px-3 h-10 bg-black/30 border border-emerald-500/20 focus-within:border-emerald-500/50">
            <Search className="w-4 h-4 text-slate-500 shrink-0" />
            <input
              value={nodeId}
              onChange={(e) => { setNodeId(e.target.value); setOffset(0); }}
              onKeyDown={(e) => { if (e.key === 'Enter') load(); }}
              placeholder="Node ID (or * for all)"
              className="flex-1 bg-transparent outline-none text-sm text-white placeholder:text-slate-600"
            />
          </div>
          <div className="flex-1 flex items-center gap-2 px-3 h-10 bg-black/30 border border-emerald-500/20 focus-within:border-emerald-500/50">
            <Filter className="w-4 h-4 text-slate-500 shrink-0" />
            <input
              value={metric}
              onChange={(e) => { setMetric(e.target.value); setOffset(0); }}
              onKeyDown={(e) => { if (e.key === 'Enter') load(); }}
              placeholder="Metric (e.g. temp, ph)"
              className="flex-1 bg-transparent outline-none text-sm text-white placeholder:text-slate-600"
            />
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {STATUS_FILTERS.map((f) => {
            const active = status === f.value;
            return (
              <button
                key={f.label}
                onClick={() => { setStatus(f.value); setOffset(0); }}
                className={`px-3 h-8 text-[11px] font-black uppercase tracking-widest border transition-all cursor-pointer ${
                  active
                    ? 'bg-emerald-500 text-black border-emerald-500'
                    : 'bg-slate-500/5 text-slate-400 border-slate-500/20 hover:border-emerald-500/40 hover:text-emerald-400'
                }`}
              >
                {f.label}
              </button>
            );
          })}
          <span className="w-px h-5 bg-emerald-500/15 mx-1" />
          {SEVERITY_FILTERS.map((f) => {
            const active = severity === f.value;
            return (
              <button
                key={f.label}
                onClick={() => { setSeverity(f.value); setOffset(0); }}
                className={`px-3 h-8 text-[11px] font-black uppercase tracking-widest border transition-all cursor-pointer ${
                  active
                    ? 'bg-emerald-500 text-black border-emerald-500'
                    : 'bg-slate-500/5 text-slate-400 border-slate-500/20 hover:border-emerald-500/40 hover:text-emerald-400'
                }`}
              >
                {f.label}
              </button>
            );
          })}
        </div>
      </div>

      {error && (
        <div className="flex items-center gap-2 border border-red-500/30 bg-red-500/10 text-red-300 px-4 py-3 text-sm">
          <AlertTriangle className="w-4 h-4 shrink-0" />
          {error}
        </div>
      )}

      {/* Table */}
      <div className="border border-emerald-500/15 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-emerald-500/5 text-[11px] font-black uppercase tracking-widest text-slate-400">
                <th className="text-left px-3 py-3 w-8" />
                <th className="text-left px-4 py-3 whitespace-nowrap">Severity</th>
                <th className="text-left px-4 py-3 whitespace-nowrap">Status</th>
                <th className="text-left px-4 py-3 whitespace-nowrap">Node</th>
                <th className="text-left px-4 py-3 whitespace-nowrap">Metric</th>
                <th className="text-left px-4 py-3 whitespace-nowrap">Value</th>
                <th className="text-left px-4 py-3 whitespace-nowrap">Threshold</th>
                <th className="text-left px-4 py-3">Message</th>
                <th className="text-left px-4 py-3 whitespace-nowrap">Triggered</th>
                <th className="text-left px-4 py-3 whitespace-nowrap">Acked</th>
                <th className="text-right px-4 py-3 whitespace-nowrap">Actions</th>
              </tr>
            </thead>
            <tbody>
              {loading && alerts.length === 0 && (
                <tr>
                  <td colSpan={11} className="px-4 py-12 text-center text-slate-500">
                    <Loader2 className="w-5 h-5 animate-spin inline mr-2" />
                    Loading alerts…
                  </td>
                </tr>
              )}
              {!loading && alerts.length === 0 && (
                <tr>
                  <td colSpan={11} className="px-4 py-12 text-center text-slate-500">
                    No alerts found. Create a threshold first, then push telemetry out of range.
                  </td>
                </tr>
              )}
              {alerts.map((a) => (
                <Fragment key={a.id}>
                  <tr className="border-t border-emerald-500/10 hover:bg-emerald-500/5 align-top">
                    <td className="px-3 py-3">
                      <button
                        onClick={() => setExpanded(expanded === a.id ? null : a.id)}
                        className="p-1 text-slate-500 hover:text-emerald-400 transition-colors cursor-pointer"
                        title={expanded === a.id ? 'Collapse' : 'Expand'}
                      >
                        {expanded === a.id ? <ChevronDown className="w-4 h-4" /> : <ChevronRightIcon className="w-4 h-4" />}
                      </button>
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      <span className={`inline-block px-2 py-1 text-[11px] font-black uppercase tracking-wide border ${severityBadgeClass(a.severity)}`}>
                        {a.severity}
                      </span>
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      <span className={`inline-block px-2 py-1 text-[11px] font-black uppercase tracking-wide border ${statusBadgeClass(a.status)}`}>
                        {a.status}
                      </span>
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-slate-300">{a.node_id}</td>
                    <td className="px-4 py-3 whitespace-nowrap text-slate-300">{a.metric}</td>
                    <td className="px-4 py-3 whitespace-nowrap tabular-nums text-slate-200">{fmtNum(a.value)}</td>
                    <td className="px-4 py-3 whitespace-nowrap tabular-nums text-slate-400">{fmtNum(a.threshold_value)}</td>
                    <td className="px-4 py-3 text-slate-300 max-w-xs truncate" title={a.message}>{a.message}</td>
                    <td className="px-4 py-3 whitespace-nowrap text-slate-400 text-xs">{formatTime(a.triggered_at)}</td>
                    <td className="px-4 py-3 whitespace-nowrap text-slate-400 text-xs">
                      {a.acked_by ? (
                        <span>
                          {a.acked_by}
                          <br />
                          {formatTime(a.acked_at)}
                        </span>
                      ) : (
                        <span className="text-slate-600">—</span>
                      )}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-right">
                      {a.status === 'active' ? (
                        <button
                          onClick={() => handleAck(a.id)}
                          disabled={!ackAllowed || busyId === a.id}
                          title={ackAllowed ? 'Acknowledge alert' : 'Requires operator/admin role'}
                          className="flex items-center gap-1 ml-auto px-3 h-8 border border-emerald-500/30 text-emerald-300 hover:bg-emerald-500/10 disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer text-[11px] font-black uppercase tracking-widest transition-all"
                        >
                          {busyId === a.id ? (
                            <Loader2 className="w-3.5 h-3.5 animate-spin" />
                          ) : ackAllowed ? (
                            <Check className="w-3.5 h-3.5" />
                          ) : (
                            <Lock className="w-3.5 h-3.5" />
                          )}
                          Ack
                        </button>
                      ) : (
                        <span className="text-slate-600 text-xs">—</span>
                      )}
                    </td>
                  </tr>
                  {expanded === a.id && (
                    <tr key={`${a.id}-detail`} className="border-t border-emerald-500/10 bg-black/20">
                      <td colSpan={11} className="px-4 py-4">
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                          <div>
                            <div className="text-[11px] font-black uppercase tracking-widest text-slate-500 mb-1">Message</div>
                            <p className="text-sm text-slate-200 break-words">{a.message}</p>
                            {a.resolved_at && (
                              <p className="mt-2 text-xs text-slate-400">
                                Resolved at: {formatTime(a.resolved_at)}
                              </p>
                            )}
                          </div>
                          <div>
                            <div className="text-[11px] font-black uppercase tracking-widest text-slate-500 mb-1">Raw payload</div>
                            <pre className="text-xs text-slate-400 whitespace-pre-wrap break-all font-mono bg-black/30 border border-emerald-500/10 p-2 max-h-48 overflow-auto">
                              {JSON.stringify(a, null, 2)}
                            </pre>
                          </div>
                        </div>
                      </td>
                    </tr>
                  )}
                </Fragment>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Pagination */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-3">
        <div className="flex items-center gap-3 text-xs text-slate-400">
          <span>
            {total === 0 ? '0 records' : `${offset + 1}–${Math.min(offset + limit, total)} of ${total}`}
          </span>
          <select
            value={limit}
            onChange={(e) => { setLimit(Number(e.target.value)); setOffset(0); }}
            className="bg-black/30 border border-emerald-500/20 text-white px-2 h-8 outline-none"
          >
            {PAGE_SIZES.map((s) => (
              <option key={s} value={s}>{s} / page</option>
            ))}
          </select>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={goPrev}
            disabled={offset === 0}
            className="flex items-center gap-1 px-3 h-9 border border-emerald-500/20 text-slate-300 hover:bg-emerald-500/10 disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer text-xs font-black uppercase tracking-widest"
          >
            <ChevronLeft className="w-4 h-4" /> Prev
          </button>
          <span className="text-xs text-slate-400 px-2">Page {page} / {totalPages}</span>
          <button
            onClick={goNext}
            disabled={offset + limit >= total}
            className="flex items-center gap-1 px-3 h-9 border border-emerald-500/20 text-slate-300 hover:bg-emerald-500/10 disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer text-xs font-black uppercase tracking-widest"
          >
            Next <ChevronRight className="w-4 h-4" />
          </button>
        </div>
      </div>
    </>
  );
}

// ─── Thresholds Management ──────────────────────────────────────────────────
function ThresholdsPanel() {
  const [thresholds, setThresholds] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [formOpen, setFormOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const [busy, setBusy] = useState(false);
  const [nodes, setNodes] = useState([]);
  const [metrics, setMetrics] = useState([]);
  const [loadingNodes, setLoadingNodes] = useState(false);
  const [loadingMetrics, setLoadingMetrics] = useState(false);

  const blankForm = { node_id: '', metric: '', min: '', max: '', enabled: true, severity: 'warning', message: '', duration_sec: '', cooldown_sec: '', hysteresis: '' };
  const [form, setForm] = useState(blankForm);

  const loadNodes = useCallback(async () => {
    setLoadingNodes(true);
    try {
      const [pairedRes, analyticsRes] = await Promise.all([
        moduleApi.listNodes({ paired: true }),
        analyticsApi.listNodes(),
      ]);
      const pairedNodes = (pairedRes?.nodes || []).map((n) => n.node_id).filter(Boolean);
      const analyticsNodeIDs = (analyticsRes?.nodes || []).map((n) => n.node_id).filter(Boolean);
      const unique = Array.from(new Set([...pairedNodes, ...analyticsNodeIDs]));
      setNodes(unique);
    } catch (err) {
      console.error('Failed to load nodes for threshold form', err);
      setNodes([]);
    } finally {
      setLoadingNodes(false);
    }
  }, []);

  const loadMetrics = useCallback(async (nodeId) => {
    if (!nodeId) {
      setMetrics([]);
      return;
    }
    setLoadingMetrics(true);
    try {
      const res = await analyticsApi.getMetrics({ node_id: nodeId, metric: '', interval: '30d' });
      const list = Array.isArray(res?.metrics) ? res.metrics : [];
      setMetrics(list);
    } catch (err) {
      console.error('Failed to load metrics for threshold form', err);
      setMetrics([]);
    } finally {
      setLoadingMetrics(false);
    }
  }, []);

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const data = await listThresholds();
      setThresholds(Array.isArray(data.thresholds) ? data.thresholds : []);
    } catch (err) {
      setError(err?.message || 'Failed to load thresholds');
      setThresholds([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    if (formOpen) {
      loadNodes();
    }
  }, [formOpen, loadNodes]);

  useEffect(() => {
    if (formOpen && form.node_id) {
      loadMetrics(form.node_id);
    }
  }, [formOpen, form.node_id, loadMetrics]);

  const openCreate = () => {
    setEditing(null);
    setForm(blankForm);
    setFormOpen(true);
    setError('');
  };

  const openEdit = (t) => {
    setEditing(t);
    setForm({
      node_id: t.node_id,
      metric: t.metric,
      min: t.min ?? '',
      max: t.max ?? '',
      enabled: t.enabled,
      severity: t.severity || 'warning',
      message: t.message || '',
      duration_sec: t.duration_sec ?? '',
      cooldown_sec: t.cooldown_sec ?? '',
      hysteresis: t.hysteresis ?? '',
    });
    setFormOpen(true);
    setError('');
  };

  const closeForm = () => {
    setFormOpen(false);
    setEditing(null);
    setNodes([]);
    setMetrics([]);
  };

  const submit = async () => {
    setError('');
    if (!form.node_id.trim() || !form.metric.trim()) {
      setError('Node ID and Metric are required.');
      return;
    }
    const min = form.min === '' ? null : Number(form.min);
    const max = form.max === '' ? null : Number(form.max);
    if (min === null && max === null) {
      setError('Provide at least one of Min or Max.');
      return;
    }
    if ((form.min !== '' && Number.isNaN(min)) || (form.max !== '' && Number.isNaN(max))) {
      setError('Min and Max must be numbers.');
      return;
    }
    const durationSec = form.duration_sec === '' ? null : Number(form.duration_sec);
    const cooldownSec = form.cooldown_sec === '' ? null : Number(form.cooldown_sec);
    const hysteresis = form.hysteresis === '' ? null : Number(form.hysteresis);
    setBusy(true);
    try {
      const payload = {
        node_id: form.node_id.trim(),
        metric: form.metric.trim(),
        min,
        max,
        enabled: form.enabled,
        severity: form.severity,
        message: form.message.trim(),
        duration_sec: durationSec,
        cooldown_sec: cooldownSec,
        hysteresis,
      };
      if (editing) {
        await updateThreshold(editing.id, payload);
      } else {
        await createThreshold(payload);
      }
      closeForm();
      await load();
    } catch (err) {
      setError(err?.message || 'Failed to save threshold');
    } finally {
      setBusy(false);
    }
  };

  const remove = async (t) => {
    if (!window.confirm(`Delete threshold for ${t.node_id} / ${t.metric}?`)) return;
    setBusy(true);
    setError('');
    try {
      await deleteThreshold(t.id);
      await load();
    } catch (err) {
      setError(err?.message || 'Failed to delete threshold');
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <PageHeader
        icon={Bell}
        title="Thresholds"
        subtitle="Out-of-range telemetry against these limits creates an alert. Use node_id '*' to apply a metric to every node."
      >
        <button
          onClick={openCreate}
          className="flex items-center justify-center gap-2 px-4 h-10 bg-emerald-500 text-black font-black text-xs uppercase tracking-widest hover:bg-emerald-400 transition-all active:scale-95 cursor-pointer"
        >
          <Plus className="w-4 h-4" />
          New Threshold
        </button>
      </PageHeader>

      {error && (
        <div className="flex items-center gap-2 border border-red-500/30 bg-red-500/10 text-red-300 px-4 py-3 text-sm">
          <AlertTriangle className="w-4 h-4 shrink-0" />
          {error}
        </div>
      )}

      <div className="border border-emerald-500/15 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-emerald-500/5 text-[11px] font-black uppercase tracking-widest text-slate-400">
                <th className="text-left px-4 py-3 whitespace-nowrap">Node</th>
                <th className="text-left px-4 py-3 whitespace-nowrap">Metric</th>
                <th className="text-left px-4 py-3 whitespace-nowrap">Min</th>
                <th className="text-left px-4 py-3 whitespace-nowrap">Max</th>
                <th className="text-left px-4 py-3 whitespace-nowrap">Message</th>
                <th className="text-left px-4 py-3 whitespace-nowrap">Duration</th>
                <th className="text-left px-4 py-3 whitespace-nowrap">Cooldown</th>
                <th className="text-left px-4 py-3 whitespace-nowrap">Hysteresis</th>
                <th className="text-left px-4 py-3 whitespace-nowrap">Severity</th>
                <th className="text-left px-4 py-3 whitespace-nowrap">Enabled</th>
                <th className="text-right px-4 py-3 whitespace-nowrap">Actions</th>
              </tr>
            </thead>
            <tbody>
              {loading && thresholds.length === 0 && (
                <tr>
                  <td colSpan={7} className="px-4 py-12 text-center text-slate-500">
                    <Loader2 className="w-5 h-5 animate-spin inline mr-2" />
                    Loading thresholds…
                  </td>
                </tr>
              )}
              {!loading && thresholds.length === 0 && (
                <tr>
                  <td colSpan={11} className="px-4 py-12 text-center text-slate-500">
                    No thresholds configured. Add one to start generating alerts.
                  </td>
                </tr>
              )}
              {thresholds.map((t) => (
                <tr key={t.id} className="border-t border-emerald-500/10 hover:bg-emerald-500/5">
                  <td className="px-4 py-3 whitespace-nowrap text-slate-300">{t.node_id}</td>
                  <td className="px-4 py-3 whitespace-nowrap text-slate-300">{t.metric}</td>
                  <td className="px-4 py-3 whitespace-nowrap tabular-nums text-slate-200">{t.min ?? '—'}</td>
                  <td className="px-4 py-3 whitespace-nowrap tabular-nums text-slate-200">{t.max ?? '—'}</td>
                  <td className="px-4 py-3 whitespace-nowrap text-slate-300 max-w-[200px] truncate" title={t.message || ''}>{t.message || '—'}</td>
                  <td className="px-4 py-3 whitespace-nowrap tabular-nums text-slate-200">{t.duration_sec ?? 0}s</td>
                  <td className="px-4 py-3 whitespace-nowrap tabular-nums text-slate-200">{t.cooldown_sec ?? 0}s</td>
                  <td className="px-4 py-3 whitespace-nowrap tabular-nums text-slate-200">{t.hysteresis ?? 0}</td>
                  <td className="px-4 py-3 whitespace-nowrap">
                    <span className={`inline-block px-2 py-1 text-[11px] font-black uppercase tracking-wide border ${severityBadgeClass(t.severity)}`}>
                      {t.severity}
                    </span>
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap">
                    <span className={`inline-block px-2 py-1 text-[11px] font-black uppercase tracking-wide border ${
                      t.enabled ? 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30' : 'bg-slate-500/15 text-slate-400 border-slate-500/30'
                    }`}>
                      {t.enabled ? 'On' : 'Off'}
                    </span>
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap text-right">
                    <div className="flex items-center justify-end gap-2">
                      <button
                        onClick={() => openEdit(t)}
                        disabled={busy}
                        className="flex items-center gap-1 px-3 h-8 border border-emerald-500/30 text-emerald-300 hover:bg-emerald-500/10 disabled:opacity-40 cursor-pointer text-[11px] font-black uppercase tracking-widest transition-all"
                      >
                        <Pencil className="w-3.5 h-3.5" />
                        Edit
                      </button>
                      <button
                        onClick={() => remove(t)}
                        disabled={busy}
                        className="flex items-center gap-1 px-3 h-8 border border-red-500/30 text-red-300 hover:bg-red-500/10 disabled:opacity-40 cursor-pointer text-[11px] font-black uppercase tracking-widest transition-all"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                        Delete
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {formOpen && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-slate-950/60 backdrop-blur-md" onClick={closeForm} />
          <div className="relative z-10 w-full max-w-lg border border-emerald-500/20 bg-[#030705] p-5 sm:p-6 space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-black uppercase tracking-wider text-white">
                {editing ? 'Edit Threshold' : 'New Threshold'}
              </h3>
              <button onClick={closeForm} className="p-1 text-slate-500 hover:text-emerald-400 cursor-pointer">
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <Field label="Node ID (use * for all)">
                <select
                  value={form.node_id}
                  onChange={(e) => setForm({ ...form, node_id: e.target.value })}
                  className="w-full h-10 px-3 bg-black/30 border border-emerald-500/20 focus:border-emerald-500/50 outline-none text-sm text-white"
                >
                  <option value="">-- select node --</option>
                  <option value="*">* (all nodes)</option>
                  {nodes.map((n) => (
                    <option key={n} value={n}>{n}</option>
                  ))}
                </select>
              </Field>
              <Field label="Metric">
                <select
                  value={form.metric}
                  onChange={(e) => setForm({ ...form, metric: e.target.value })}
                  disabled={loadingMetrics || !form.node_id}
                  className="w-full h-10 px-3 bg-black/30 border border-emerald-500/20 focus:border-emerald-500/50 outline-none text-sm text-white disabled:opacity-50"
                >
                  <option value="">-- select metric --</option>
                  {metrics.map((m) => (
                    <option key={m} value={m}>{m}</option>
                  ))}
                </select>
              </Field>
              <Field label="Min (optional)">
                <input
                  type="number"
                  step="any"
                  value={form.min}
                  onChange={(e) => setForm({ ...form, min: e.target.value })}
                  placeholder="—"
                  className="w-full h-10 px-3 bg-black/30 border border-emerald-500/20 focus:border-emerald-500/50 outline-none text-sm text-white placeholder:text-slate-600"
                />
              </Field>
              <Field label="Max (optional)">
                <input
                  type="number"
                  step="any"
                  value={form.max}
                  onChange={(e) => setForm({ ...form, max: e.target.value })}
                  placeholder="—"
                  className="w-full h-10 px-3 bg-black/30 border border-emerald-500/20 focus:border-emerald-500/50 outline-none text-sm text-white placeholder:text-slate-600"
                />
              </Field>
              <Field label="Custom Message (optional)">
                <input
                  value={form.message}
                  onChange={(e) => setForm({ ...form, message: e.target.value })}
                  placeholder="Auto-generated if empty"
                  className="w-full h-10 px-3 bg-black/30 border border-emerald-500/20 focus:border-emerald-500/50 outline-none text-sm text-white placeholder:text-slate-600"
                />
              </Field>
              <Field label="Severity">
                <select
                  value={form.severity}
                  onChange={(e) => setForm({ ...form, severity: e.target.value })}
                  className="w-full h-10 px-3 bg-black/30 border border-emerald-500/20 focus:border-emerald-500/50 outline-none text-sm text-white"
                >
                  <option value="warning">warning</option>
                  <option value="critical">critical</option>
                  <option value="info">info</option>
                </select>
              </Field>
              <Field label="Duration (seconds, 0 = instant)">
                <input
                  type="number"
                  min="0"
                  step="1"
                  value={form.duration_sec}
                  onChange={(e) => setForm({ ...form, duration_sec: e.target.value })}
                  placeholder="0"
                  className="w-full h-10 px-3 bg-black/30 border border-emerald-500/20 focus:border-emerald-500/50 outline-none text-sm text-white placeholder:text-slate-600"
                />
              </Field>
              <Field label="Cooldown (seconds, 0 = none)">
                <input
                  type="number"
                  min="0"
                  step="1"
                  value={form.cooldown_sec}
                  onChange={(e) => setForm({ ...form, cooldown_sec: e.target.value })}
                  placeholder="0"
                  className="w-full h-10 px-3 bg-black/30 border border-emerald-500/20 focus:border-emerald-500/50 outline-none text-sm text-white placeholder:text-slate-600"
                />
              </Field>
              <Field label="Hysteresis (optional)">
                <input
                  type="number"
                  step="any"
                  value={form.hysteresis}
                  onChange={(e) => setForm({ ...form, hysteresis: e.target.value })}
                  placeholder="0"
                  className="w-full h-10 px-3 bg-black/30 border border-emerald-500/20 focus:border-emerald-500/50 outline-none text-sm text-white placeholder:text-slate-600"
                />
              </Field>
              <Field label="Enabled">
                <label className="flex items-center gap-2 h-10 px-3 bg-black/30 border border-emerald-500/20 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={form.enabled}
                    onChange={(e) => setForm({ ...form, enabled: e.target.checked })}
                    className="accent-emerald-500 w-4 h-4"
                  />
                  <span className="text-sm text-slate-300">{form.enabled ? 'On' : 'Off'}</span>
                </label>
              </Field>
            </div>

            <div className="flex items-center justify-end gap-2 pt-1">
              <button
                onClick={closeForm}
                className="px-4 h-10 border border-slate-500/30 text-slate-300 hover:bg-slate-500/10 text-xs font-black uppercase tracking-widest cursor-pointer transition-all"
              >
                Cancel
              </button>
              <button
                onClick={submit}
                disabled={busy}
                className="flex items-center gap-2 px-4 h-10 bg-emerald-500 text-black font-black text-xs uppercase tracking-widest hover:bg-emerald-400 disabled:opacity-60 cursor-pointer transition-all"
              >
                {busy && <Loader2 className="w-4 h-4 animate-spin" />}
                {editing ? 'Save' : 'Create'}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

function Field({ label, children }) {
  return (
    <label className="block">
      <span className="block text-[11px] font-black uppercase tracking-widest text-slate-500 mb-1">{label}</span>
      {children}
    </label>
  );
}
