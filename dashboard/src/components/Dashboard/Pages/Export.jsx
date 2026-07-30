import { useState, useEffect, useCallback, useMemo } from 'react';
import {
  Download,
  Loader2,
  AlertTriangle,
  ChevronLeft,
  ChevronRight,
  FileText,
  Table,
  Filter,
} from 'lucide-react';
import PageHeader from './PageHeader';
import { exportApi } from '../../../api/export';
import { useModule } from '../../../context/useModule';

const EXPORT_TABS = [
  { id: 'telemetry', label: 'Telemetry', icon: Table },
  { id: 'nodes', label: 'Nodes', icon: FileText },
];

function toRFC3339(dateStr, timeSuffix) {
  if (!dateStr) return undefined;
  if (dateStr.includes('T')) return dateStr;
  return `${dateStr}T${timeSuffix}`;
}

const FORMATS = [
  { label: 'CSV', value: 'csv' },
  { label: 'JSON', value: 'json' },
  { label: 'Parquet', value: 'parquet' },
  { label: 'Excel', value: 'xlsx' },
];

function extractArray(obj) {
  if (!obj) return [];
  if (Array.isArray(obj)) return obj;
  if (typeof obj === 'object') {
    if (Array.isArray(obj.rows)) return obj.rows;
    if (Array.isArray(obj.nodes)) return obj.nodes;
    if (Array.isArray(obj.alerts)) return obj.alerts;
    if (Array.isArray(obj.commands)) return obj.commands;
    if (Array.isArray(obj.audit)) return obj.audit;
    if (Array.isArray(obj.data)) return extractArray(obj.data);
  }
  return [];
}

function jsonToCsv(items) {
  const arr = extractArray(items);
  if (!Array.isArray(arr) || arr.length === 0) return '';

  // If items contain telemetry fields (metric & value & time), pivot into wide format columns!
  const isTelemetryUnpivoted = arr.length > 0 && arr[0].metric !== undefined && arr[0].value !== undefined && arr[0].time !== undefined;

  if (isTelemetryUnpivoted) {
    const metricSet = new Set();
    const groupMap = new Map();
    const groupKeys = [];

    arr.forEach((item) => {
      if (item.metric) metricSet.add(item.metric);
      const key = `${item.time || ''}___${item.node_id || ''}___${item.module_id || ''}`;
      if (!groupMap.has(key)) {
        const obj = {
          time: item.time || '',
          node_id: item.node_id || '',
          module_id: item.module_id || '',
        };
        groupMap.set(key, obj);
        groupKeys.push(key);
      }
      groupMap.get(key)[item.metric] = item.value;
    });

    const metricList = Array.from(metricSet).sort();
    const headers = ['time', 'node_id', 'module_id', ...metricList];
    const csvRows = [headers.join(',')];

    groupKeys.forEach((key) => {
      const rowObj = groupMap.get(key);
      const row = headers.map((h) => {
        const val = rowObj[h];
        if (val === null || val === undefined) return '""';
        const str = typeof val === 'object' ? JSON.stringify(val) : String(val);
        return `"${str.replace(/"/g, '""')}"`;
      });
      csvRows.push(row.join(','));
    });

    return csvRows.join('\n');
  }

  // Standard JSON array to CSV
  const keys = new Set();
  arr.forEach((item) => {
    if (item && typeof item === 'object') {
      Object.keys(item).forEach((k) => keys.add(k));
    }
  });
  const headers = Array.from(keys);
  if (headers.length === 0) return '';
  const csvRows = [headers.join(',')];
  for (const item of arr) {
    const row = headers.map((h) => {
      const val = item?.[h];
      if (val === null || val === undefined) return '""';
      const str = typeof val === 'object' ? JSON.stringify(val) : String(val);
      return `"${str.replace(/"/g, '""')}"`;
    });
    csvRows.push(row.join(','));
  }
  return csvRows.join('\n');
}

function pivotTelemetryRows(data) {
  if (!Array.isArray(data) || data.length === 0) return [];
  if (data[0].metric === undefined || data[0].value === undefined || data[0].time === undefined) {
    return data;
  }
  const groupMap = new Map();
  const groupKeys = [];

  data.forEach((item) => {
    const key = `${item.time || ''}___${item.node_id || ''}___${item.module_id || ''}`;
    if (!groupMap.has(key)) {
      const obj = {
        time: item.time || '',
        node_id: item.node_id || '',
        module_id: item.module_id || '',
      };
      groupMap.set(key, obj);
      groupKeys.push(key);
    }
    groupMap.get(key)[item.metric] = item.value;
  });

  return groupKeys.map((k) => groupMap.get(k));
}

function canExport() {
  try {
    const u = JSON.parse(sessionStorage.getItem('user') || 'null');
    const roles = Array.isArray(u?.roles) ? u.roles : [];
    return roles.length > 0;
  } catch {
    return false;
  }
}

function fmtDate(d) {
  if (!d) return '';
  const dt = new Date(d);
  if (isNaN(dt.getTime())) return d;
  return dt.toISOString().slice(0, 10);
}

export default function Export() {
  const { selectedModule } = useModule();
  const [tab, setTab] = useState('telemetry');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [discover, setDiscover] = useState(null);

  const [format, setFormat] = useState('csv');
  const [nodeId, setNodeId] = useState('*');
  const [metric, setMetric] = useState('*');
  const [moduleId, setModuleId] = useState('');
  const [from, setFrom] = useState(() => {
    const d = new Date();
    d.setDate(d.getDate() - 7);
    return fmtDate(d);
  });
  const [to, setTo] = useState(() => fmtDate(new Date()));
  const [limit] = useState(10000);
  const [offset, setOffset] = useState(0);
  const [event, setEvent] = useState('');
  const [search, setSearch] = useState('');
  const [sort, setSort] = useState('time');
  const [order, setOrder] = useState('desc');

  const [preview, setPreview] = useState([]);
  const [total, setTotal] = useState(0);

  // Load all nodes with their telemetry metadata (metrics, module mapping)
  const [allNodesData, setAllNodesData] = useState([]);
  const [loadingNodes, setLoadingNodes] = useState(false);

  useEffect(() => {
    let active = true;
    const fetchAllNodes = async () => {
      setLoadingNodes(true);
      try {
        const res = await exportApi.listNodes();
        if (!active) return;
        setAllNodesData(res?.nodes || []);
      } catch (err) {
        console.error('Failed to load nodes & metrics list for export dropdowns:', err);
      } finally {
        if (active) setLoadingNodes(false);
      }
    };
    fetchAllNodes();
    return () => { active = false; };
  }, []);

  // Filter nodes by globally selected module (if any)
  const moduleNodes = useMemo(() => {
    if (!selectedModule) return allNodesData;
    return allNodesData.filter((n) => n.module_id === selectedModule.id);
  }, [allNodesData, selectedModule]);

  // Sync selectedModule with moduleId and auto-select/reset nodeId
  useEffect(() => {
    if (selectedModule) {
      setModuleId(selectedModule.id);
      const nodesOfModule = allNodesData.filter((n) => n.module_id === selectedModule.id);
      if (nodesOfModule.length > 0) {
        setNodeId(nodesOfModule[0].node_id);
      } else {
        setNodeId('*');
      }
    } else {
      setModuleId('');
      setNodeId('*');
    }
    setOffset(0);
  }, [selectedModule, allNodesData]);

  // Compute available metrics for selected node (or current module if "all nodes" selected)
  const availableMetrics = useMemo(() => {
    if (!nodeId || nodeId === '*') {
      const set = new Set();
      moduleNodes.forEach((n) => {
        if (Array.isArray(n.metrics)) {
          n.metrics.forEach((m) => set.add(m));
        }
      });
      return Array.from(set).sort();
    }
    const nodeObj = moduleNodes.find((n) => n.node_id === nodeId);
    return nodeObj?.metrics || [];
  }, [nodeId, moduleNodes]);

  // Default metric to '*' (All Metrics) if not explicitly set
  useEffect(() => {
    if (!metric) {
      setMetric('*');
    }
  }, [metric]);

  const loadDiscover = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const res = await exportApi.discover();
      setDiscover(res || null);
    } catch (err) {
      setError(err?.message || 'Failed to load schema');
      setDiscover(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (tab === 'discover') {
      loadDiscover();
    }
  }, [tab, loadDiscover]);

  const buildParams = useCallback(() => {
    const p = {
      format,
      from: toRFC3339(from, '00:00:00Z'),
      to: toRFC3339(to, '23:59:59Z'),
      limit: tab === 'discover' ? undefined : limit,
      offset: tab === 'discover' ? undefined : offset,
      sort: tab === 'telemetry' || tab === 'aggregate' ? sort : undefined,
      order: tab === 'telemetry' || tab === 'aggregate' ? order : undefined,
    };
    if (['aggregate'].includes(tab)) p.bucket = 'hour';
    if (['telemetry', 'aggregate'].includes(tab)) {
      if (nodeId) p.node_id = nodeId;
      if (metric) p.metric = metric;
      if (moduleId) p.module_id = moduleId;
    }
    if (tab === 'alerts') {
      if (nodeId) p.node_id = nodeId;
      if (metric) p.metric = metric;
    }
    if (tab === 'commands') {
      if (nodeId) p.node_id = nodeId;
    }
    if (tab === 'audit') {
      if (event) p.event = event;
      if (search) p.search = search;
    }
    return p;
  }, [tab, format, nodeId, metric, moduleId, from, to, limit, offset, event, search, sort, order]);

  const loadPreview = useCallback(async () => {
    if (tab === 'discover') return;
    setLoading(true);
    setError('');
    try {
      const params = buildParams();
      if (!params.node_id) params.node_id = '*';
      if (!params.metric) params.metric = '*';
      params.format = 'json';
      params.limit = 100;
      const apiMap = {
        telemetry: exportApi.listTelemetry,
        aggregate: exportApi.listTelemetryAggregate,
        nodes: exportApi.listNodes,
        alerts: exportApi.listAlerts,
        commands: exportApi.listCommands,
        audit: exportApi.listAudit,
      };
      const fn = apiMap[tab];
      if (!fn) throw new Error('Unknown export tab');
      const res = await fn(params);
      if (typeof res === 'string') {
        const lines = res.trim().split('\n').filter(Boolean);
        if (lines.length > 1) {
          const headers = lines[0].split(',').map((h) => h.trim().replace(/^"|"$/g, ''));
          const rows = lines.slice(1).map((line) => {
            const vals = line.split(',').map((v) => v.trim().replace(/^"|"$/g, ''));
            const obj = {};
            headers.forEach((h, idx) => { obj[h] = vals[idx] ?? ''; });
            return obj;
          });
          setPreview(rows.slice(0, 10));
          setTotal(rows.length);
        } else {
          setPreview([]);
          setTotal(0);
        }
      } else {
        const payload = res?.data || res;
        const rawData = Array.isArray(payload)
          ? payload
          : (payload.rows || payload.nodes || payload.alerts || payload.commands || payload.data || []);
        const data = (tab === 'telemetry' || tab === 'aggregate') ? pivotTelemetryRows(rawData) : rawData;
        const previewRows = Array.isArray(data) ? data.slice(0, 10) : [];
        setPreview(previewRows);
        setTotal(typeof payload.total === 'number' ? payload.total : (Array.isArray(data) ? data.length : previewRows.length));
      }
    } catch (err) {
      setError(err?.message || 'Failed to load export preview');
      setPreview([]);
    } finally {
      setLoading(false);
    }
  }, [tab, buildParams, nodeId, metric]);

  useEffect(() => {
    if (tab !== 'discover') {
      loadPreview();
    }
  }, [tab, loadPreview, format, nodeId, metric, moduleId, from, to, limit, offset, event, search, sort, order]);

  if (!canExport()) {
    return (
      <div className="border border-red-500/20 bg-red-500/5 p-6 text-red-300">
        You do not have permission to export data.
      </div>
    );
  }

  const download = async (downloadFormat) => {
    setLoading(true);
    setError('');
    try {
      const params = buildParams();
      params.format = downloadFormat;
      const apiMap = {
        telemetry: exportApi.listTelemetry,
        aggregate: exportApi.listTelemetryAggregate,
        nodes: exportApi.listNodes,
        alerts: exportApi.listAlerts,
        commands: exportApi.listCommands,
        audit: exportApi.listAudit,
      };
      const fn = apiMap[tab];
      if (!fn) throw new Error('Unknown export tab');
      const res = await fn(params);

      let content = '';
      if (downloadFormat === 'csv') {
        if (typeof res === 'string') {
          content = res;
        } else {
          content = jsonToCsv(res);
        }
      } else {
        content = typeof res === 'string' ? res : JSON.stringify(res, null, 2);
      }

      const mimeType = downloadFormat === 'csv' ? 'text/csv;charset=utf-8;' : (downloadFormat === 'json' ? 'application/json' : 'application/octet-stream');
      const blob = new Blob([content], { type: mimeType });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `export-${tab}-${Date.now()}.${downloadFormat === 'xlsx' ? 'xlsx' : downloadFormat}`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(err?.message || 'Failed to download export');
    } finally {
      setLoading(false);
    }
  };

  const page = Math.floor(offset / limit) + 1;
  const totalPages = Math.max(1, Math.ceil(total / limit));
  const goPrev = () => setOffset((o) => Math.max(0, o - limit));
  const goNext = () => setOffset((o) => Math.min(Math.max(0, total - limit), o + limit));

  const previewRows = Array.isArray(preview) ? preview : [];
  const columns = previewRows.length > 0 ? Object.keys(previewRows[0]) : [];

  return (
    <div className="space-y-4">
      <PageHeader
        icon={Download}
        title="Data Export"
        subtitle="Query and download system data in CSV, JSON, Parquet, or Excel."
      >
        <button
          onClick={() => download(format)}
          disabled={loading || tab === 'discover' || (['telemetry', 'aggregate'].includes(tab) && (!nodeId || !metric))}
          className="flex items-center justify-center gap-2 px-4 h-10 bg-emerald-500 text-black font-black text-xs uppercase tracking-widest hover:bg-emerald-400 transition-all active:scale-95 disabled:opacity-60 cursor-pointer"
        >
          {loading ? <Loader2 className={`w-4 h-4 animate-spin`} /> : <Download className="w-4 h-4" />}
          Download {format.toUpperCase()}
        </button>
      </PageHeader>

      {/* Tabs */}
      <div className="flex items-center gap-1 border-b border-emerald-500/15 overflow-x-auto">
        {EXPORT_TABS.map((t) => {
          const active = tab === t.id;
          return (
            <button
              key={t.id}
              onClick={() => { setTab(t.id); setOffset(0); setPreview([]); setDiscover(null); }}
              className={`flex items-center gap-2 px-3 py-2.5 text-xs font-black uppercase tracking-widest transition-all whitespace-nowrap cursor-pointer ${
                active
                  ? 'border-b-2 border-emerald-500 text-emerald-400'
                  : 'text-slate-400 hover:text-emerald-400 border-b-2 border-transparent'
              }`}
            >
              <t.icon className="w-4 h-4" />
              {t.label}
            </button>
          );
        })}
      </div>

      {error && (
        <div className="border border-red-500/20 bg-red-500/5 p-4 text-red-300 text-xs font-black uppercase tracking-widest flex items-center gap-2">
          <AlertTriangle className="w-4 h-4" />
          {error}
        </div>
      )}

      {tab === 'discover' ? (
        <div className="border border-emerald-500/10 bg-[#030705] p-6">
          <h3 className="text-sm font-black uppercase tracking-widest text-slate-300 mb-4">Available Tables & Columns</h3>
          {loading && !discover && (
            <div className="flex items-center gap-2 text-slate-400 text-xs">
              <Loader2 className="w-4 h-4 animate-spin" /> Loading schema...
            </div>
          )}
          {discover && Array.isArray(discover) && discover.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {discover.map((tbl) => (
                <div key={tbl.table || tbl.name} className="border border-emerald-500/10 p-4 space-y-2">
                  <div className="text-xs font-black uppercase tracking-widest text-emerald-400">
                    {tbl.table || tbl.name}
                  </div>
                  <div className="text-[11px] text-slate-400 font-mono">
                    {(Array.isArray(tbl.columns) ? tbl.columns : []).map((c) => (
                      <div key={c.name || c} className="truncate">
                        <span className="text-slate-500">{c.type || ''}</span> {c.name || c}
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-xs text-slate-500">No schema information available.</div>
          )}
        </div>
      ) : (
        <>
          {/* Filters */}
          <div className="border border-emerald-500/10 bg-[#030705] p-4 md:p-6 space-y-4">
            <div className="flex items-center gap-2 text-xs font-black uppercase tracking-widest text-slate-400">
              <Filter className="w-4 h-4" />
              Filters
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              {['telemetry', 'aggregate', 'alerts', 'commands'].includes(tab) && (
                <label className="space-y-1">
                  <span className="text-[10px] font-black uppercase tracking-widest text-slate-500">Node ID</span>
                  {loadingNodes ? (
                    <div className="flex items-center h-10 px-3 bg-slate-900/80 border border-emerald-500/20 text-slate-500 text-xs">
                      <Loader2 className="w-3.5 h-3.5 animate-spin mr-2" /> Loading…
                    </div>
                  ) : moduleNodes.length > 0 ? (
                    <select
                      value={nodeId}
                      onChange={(e) => { setNodeId(e.target.value); setOffset(0); }}
                      className="w-full h-10 px-3 bg-slate-900/80 border border-emerald-500/20 text-emerald-50 text-xs focus:outline-none focus:border-emerald-500/60 cursor-pointer"
                    >
                      <option value="*">All Nodes (*)</option>
                      {moduleNodes.map((n) => (
                        <option key={n.node_id} value={n.node_id}>
                          {n.node_id}
                        </option>
                      ))}
                    </select>
                  ) : (
                    <input
                      value={nodeId}
                      onChange={(e) => { setNodeId(e.target.value); setOffset(0); }}
                      placeholder="* or node id"
                      className="w-full h-10 px-3 bg-slate-900/80 border border-emerald-500/20 text-emerald-50 text-xs placeholder-slate-600 focus:outline-none focus:border-emerald-500/60"
                    />
                  )}
                </label>
              )}
              {['telemetry', 'aggregate'].includes(tab) && (
                <label className="space-y-1">
                  <span className="text-[10px] font-black uppercase tracking-widest text-slate-500">Metric</span>
                  <select
                    value={metric || '*'}
                    onChange={(e) => { setMetric(e.target.value); setOffset(0); }}
                    className="w-full h-10 px-3 bg-slate-900/80 border border-emerald-500/20 text-emerald-50 text-xs focus:outline-none focus:border-emerald-500/60 cursor-pointer"
                  >
                    <option value="*">All Metrics (*)</option>
                    {availableMetrics.map((m) => (
                      <option key={m} value={m}>
                        {m}
                      </option>
                    ))}
                  </select>
                </label>
              )}
              {['telemetry', 'aggregate'].includes(tab) && (
                <label className="space-y-1">
                  <span className="text-[10px] font-black uppercase tracking-widest text-slate-500">Module ID</span>
                  <input
                    value={moduleId || 'Global / All'}
                    disabled
                    className="w-full h-10 px-3 bg-slate-900/40 border border-emerald-500/10 text-slate-400 text-xs focus:outline-none cursor-not-allowed select-none"
                    title="Synced with selected header module"
                  />
                </label>
              )}
              <label className="space-y-1">
                <span className="text-[10px] font-black uppercase tracking-widest text-slate-500">Format</span>
                <select
                  value={format}
                  onChange={(e) => setFormat(e.target.value)}
                  className="w-full h-10 px-3 bg-slate-900/80 border border-emerald-500/20 text-emerald-50 text-xs focus:outline-none focus:border-emerald-500/60"
                >
                  {FORMATS.map((f) => (
                    <option key={f.value} value={f.value}>{f.label}</option>
                  ))}
                </select>
              </label>
              <label className="space-y-1">
                <span className="text-[10px] font-black uppercase tracking-widest text-slate-500">From</span>
                <input
                  type="date"
                  value={from}
                  onChange={(e) => { setFrom(e.target.value); setOffset(0); }}
                  className="w-full h-10 px-3 bg-slate-900/80 border border-emerald-500/20 text-emerald-50 text-xs focus:outline-none focus:border-emerald-500/60"
                />
              </label>
              <label className="space-y-1">
                <span className="text-[10px] font-black uppercase tracking-widest text-slate-500">To</span>
                <input
                  type="date"
                  value={to}
                  onChange={(e) => { setTo(e.target.value); setOffset(0); }}
                  className="w-full h-10 px-3 bg-slate-900/80 border border-emerald-500/20 text-emerald-50 text-xs focus:outline-none focus:border-emerald-500/60"
                />
              </label>
              {tab === 'audit' && (
                <label className="space-y-1">
                  <span className="text-[10px] font-black uppercase tracking-widest text-slate-500">Event</span>
                  <input
                    value={event}
                    onChange={(e) => { setEvent(e.target.value); setOffset(0); }}
                    placeholder="e.g. auth, module"
                    className="w-full h-10 px-3 bg-slate-900/80 border border-emerald-500/20 text-emerald-50 text-xs placeholder-slate-600 focus:outline-none focus:border-emerald-500/60"
                  />
                </label>
              )}
              {tab === 'audit' && (
                <label className="space-y-1">
                  <span className="text-[10px] font-black uppercase tracking-widest text-slate-500">Search</span>
                  <input
                    value={search}
                    onChange={(e) => { setSearch(e.target.value); setOffset(0); }}
                    placeholder="payload search"
                    className="w-full h-10 px-3 bg-slate-900/80 border border-emerald-500/20 text-emerald-50 text-xs placeholder-slate-600 focus:outline-none focus:border-emerald-500/60"
                  />
                </label>
              )}
              {['telemetry', 'aggregate'].includes(tab) && (
                <label className="space-y-1">
                  <span className="text-[10px] font-black uppercase tracking-widest text-slate-500">Sort</span>
                  <div className="flex gap-2">
                    <select
                      value={sort}
                      onChange={(e) => setSort(e.target.value)}
                      className="flex-1 h-10 px-3 bg-slate-900/80 border border-emerald-500/20 text-emerald-50 text-xs focus:outline-none focus:border-emerald-500/60"
                    >
                      <option value="time">Time</option>
                      <option value="node_id">Node</option>
                      <option value="metric">Metric</option>
                      <option value="value">Value</option>
                    </select>
                    <select
                      value={order}
                      onChange={(e) => setOrder(e.target.value)}
                      className="w-20 h-10 px-3 bg-slate-900/80 border border-emerald-500/20 text-emerald-50 text-xs focus:outline-none focus:border-emerald-500/60"
                    >
                      <option value="desc">Desc</option>
                      <option value="asc">Asc</option>
                    </select>
                  </div>
                </label>
              )}
            </div>
          </div>

          {/* Preview table */}
          {loading ? (
            <div className="flex items-center justify-center gap-2 text-slate-400 text-xs py-12">
              <Loader2 className="w-4 h-4 animate-spin" /> Loading preview...
            </div>
          ) : previewRows.length > 0 ? (
            <div className="border border-emerald-500/10 bg-[#030705] overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead>
                    <tr className="border-b border-emerald-500/15 bg-emerald-500/5">
                      <th className="px-4 py-3 text-[10px] font-black uppercase tracking-widest text-slate-400">#</th>
                      {columns.map((c) => (
                        <th key={c} className="px-4 py-3 text-[10px] font-black uppercase tracking-widest text-slate-400 whitespace-nowrap">
                          {c}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {previewRows.map((row, idx) => (
                      <tr key={idx} className="border-b border-emerald-500/10 hover:bg-emerald-500/5 transition-colors">
                        <td className="px-4 py-2.5 text-slate-500 tabular-nums">{offset + idx + 1}</td>
                        {columns.map((c) => (
                          <td key={c} className="px-4 py-2.5 text-slate-300 whitespace-nowrap max-w-[260px] truncate" title={String(row[c] ?? '')}>
                            {typeof row[c] === 'object' ? JSON.stringify(row[c]) : String(row[c] ?? '')}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div className="flex items-center justify-between px-4 py-3 border-t border-emerald-500/15 bg-slate-900/40">
                <div className="text-[11px] font-black uppercase tracking-widest text-slate-500">
                  {total.toLocaleString()} {total === 1 ? 'record' : 'records'}
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={goPrev}
                    disabled={page <= 1}
                    className="flex items-center gap-1 px-3 h-8 border border-emerald-500/20 text-emerald-400 hover:bg-emerald-500/10 disabled:opacity-40 transition-all cursor-pointer"
                  >
                    <ChevronLeft className="w-4 h-4" />
                  </button>
                  <span className="text-[11px] font-black uppercase tracking-widest text-slate-400 tabular-nums">
                    {page} / {totalPages}
                  </span>
                  <button
                    onClick={goNext}
                    disabled={page >= totalPages}
                    className="flex items-center gap-1 px-3 h-8 border border-emerald-500/20 text-emerald-400 hover:bg-emerald-500/10 disabled:opacity-40 transition-all cursor-pointer"
                  >
                    <ChevronRight className="w-4 h-4" />
                  </button>
                </div>
              </div>
            </div>
          ) : (
            <div className="border border-emerald-500/10 bg-[#030705] p-8 text-center">
              <div className="text-xs font-black uppercase tracking-widest text-slate-500">
                {loading
                  ? 'Loading preview...'
                  : (['telemetry', 'aggregate'].includes(tab) && (!nodeId || !metric))
                  ? 'Please enter a Node ID and Metric to load telemetry preview.'
                  : 'No data found for the selected filters.'}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
