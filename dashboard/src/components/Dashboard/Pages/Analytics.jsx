import { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { Line, Bar } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  Filler,
} from 'chart.js';
import zoomPlugin from 'chartjs-plugin-zoom';
import {
  BarChart3,
  Activity,
  Loader2,
  AlertTriangle,
  Database,
  LineChart,
  BarChart2,
  Grid3x3,
  ZoomIn,
  ZoomOut,
  Maximize2,
} from 'lucide-react';
import PageHeader from './PageHeader';
import analyticsApi from '../../../api/analytics';
import { moduleApi } from '../../../api/module';
import { useModule } from '../../../context/ModuleContext';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  Filler,
  zoomPlugin
);

const RANGES = [
  { id: '1h', label: '1 HOUR' },
  { id: '6h', label: '6 HOURS' },
  { id: '24h', label: '24 HOURS' },
  { id: '7d', label: '7 DAYS' },
  { id: '30d', label: '30 DAYS' },
];

const PALETTE = [
  '#10b981', '#06b6d4', '#f59e0b', '#a855f7',
  '#f43f5e', '#3b82f6', '#eab308', '#ec4899',
];

function shortId(id) {
  if (!id) return id;
  return id.length > 10 ? `${id.slice(0, 6)}…${id.slice(-4)}` : id;
}

function formatTick(t) {
  const d = new Date(t);
  if (isNaN(d)) return t;
  return d.toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function fmt(v, decimals = 2) {
  if (v === null || v === undefined || isNaN(v)) return '—';
  return Number(v).toFixed(decimals);
}

function statsOf(points) {
  if (!points.length) return { count: 0, min: NaN, max: NaN, avg: NaN, last: NaN };
  let min = Infinity, max = -Infinity, sum = 0, n = 0;
  for (const p of points) {
    const lo = p.min != null ? p.min : p.v;
    const hi = p.max != null ? p.max : p.v;
    const a = p.avg != null ? p.avg : p.v;
    if (lo < min) min = lo;
    if (hi > max) max = hi;
    sum += a;
    n++;
  }
  return { count: points.length, min, max, avg: n ? sum / n : NaN, last: points[points.length - 1].v };
}

// Build a unified, time-sorted x-axis from several per-metric point arrays so
// datasets with different bucket counts (e.g. per-minute digital vs hourly
// analog at the same range) line up by actual timestamp instead of by array
// index — otherwise the series with fewer points gets squashed/truncated.
function buildAxis(pointLists) {
  const set = new Set();
  for (const pts of pointLists) for (const p of pts) set.add(p.t);
  return Array.from(set).sort();
}

// Project one metric's points onto the unified axis; gaps become null so the
// line breaks instead of shifting every subsequent sample out of alignment.
function alignToAxis(axis, pts, pick) {
  const idx = new Map(axis.map((t, i) => [t, i]));
  const out = new Array(axis.length).fill(null);
  for (const p of pts) {
    const i = idx.get(p.t);
    if (i != null) out[i] = pick(p);
  }
  return out;
}

function histogram(values, bins = 10) {
  if (values.length === 0) return { labels: [], counts: [] };
  const min = Math.min(...values);
  const max = Math.max(...values);
  if (min === max) return { labels: [min.toFixed(1)], counts: [values.length] };
  const width = (max - min) / bins;
  const counts = new Array(bins).fill(0);
  for (const v of values) {
    let i = Math.floor((v - min) / width);
    if (i >= bins) i = bins - 1;
    if (i < 0) i = 0;
    counts[i]++;
  }
  const labels = counts.map((_, i) => (min + i * width).toFixed(1));
  return { labels, counts };
}

function pearson(a, b) {
  const n = Math.min(a.length, b.length);
  if (n === 0) return 0;
  let sa = 0, sb = 0;
  for (let i = 0; i < n; i++) { sa += a[i]; sb += b[i]; }
  const ma = sa / n, mb = sb / n;
  let num = 0, da = 0, db = 0;
  for (let i = 0; i < n; i++) {
    const x = a[i] - ma, y = b[i] - mb;
    num += x * y; da += x * x; db += y * y;
  }
  const den = Math.sqrt(da * db);
  return den === 0 ? 0 : num / den;
}

// A metric is treated as a digital/boolean state when every sample is 0 or 1.
function isBooleanMetric(points) {
  if (!points || points.length === 0) return false;
  for (const p of points) {
    if (p.v !== 0 && p.v !== 1) return false;
  }
  return true;
}

function corrColor(v) {
  if (v >= 0) {
    const a = 0.15 + 0.6 * v;
    return `rgba(16,185,129,${a.toFixed(2)})`;
  }
  const a = 0.15 + 0.6 * -v;
  return `rgba(244,63,94,${a.toFixed(2)})`;
}

function Card({ title, icon: Icon, children }) {
  return (
    <div className="w-full border border-emerald-500/15 bg-[#030705]/80 backdrop-blur-md p-3 sm:p-4">
      <div className="flex items-center gap-2 mb-3">
        <Icon className="w-4 h-4 text-emerald-400" />
        <h3 className="text-xs sm:text-sm font-black uppercase tracking-widest text-emerald-400">{title}</h3>
      </div>
      {children}
    </div>
  );
}

function StatChip({ label, value }) {
  return (
    <div className="flex flex-col">
      <span className="text-[9px] font-black uppercase tracking-[0.15em] text-slate-500">{label}</span>
      <span className="text-sm font-black tabular-nums text-slate-200">{value}</span>
    </div>
  );
}

function Analytics() {
  const { selectedModule } = useModule();
  const [nodes, setNodes] = useState([]);
  const [nodeId, setNodeId] = useState('');
  const [range, setRange] = useState('1h');
  const [tags, setTags] = useState([]);

  const [seriesByMetric, setSeriesByMetric] = useState({});
  const [booleanSet, setBooleanSet] = useState(() => new Set());
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [tagsLoaded, setTagsLoaded] = useState(false);
  const trendRef = useRef(null);
  const stateRef = useRef(null);

  useEffect(() => {
    let active = true;
    (async () => {
      try {
        if (!selectedModule) {
          setNodes([]);
          setNodeId('');
          return;
        }
        const [modRes, analyticsRes] = await Promise.all([
          moduleApi.listNodes({ module_id: selectedModule.id }),
          analyticsApi.listNodes(),
        ]);
        if (!active) return;
        const allNodes = analyticsRes?.nodes || [];
        const moduleNodeIds = new Set((modRes?.nodes || []).map((n) => n.node_id));
        // Keep module scoping strict: only show nodes that belong to the
        // selected module. A module with no telemetry stays empty (it must not
        // borrow another module's data).
        const list = allNodes.filter((n) => moduleNodeIds.has(n.node_id));
        setNodes(list);
        if (list.length > 0) setNodeId(list[0].node_id);
        else setNodeId('');
      } catch (err) {
        if (active) setError(err.message || 'Failed to load nodes');
      }
    })();
    return () => { active = false; };
  }, [selectedModule]);

  useEffect(() => {
    if (!nodeId) {
      setTags([]);
      setTagsLoaded(false);
      return;
    }
    let active = true;
    setTagsLoaded(false);
    moduleApi
      .getNodeTags(nodeId)
      .then((data) => {
        if (!active) return;
        setTags(Array.isArray(data?.tags) ? data.tags : []);
        setTagsLoaded(true);
      })
      .catch((err) => {
        console.error('Failed to load node tags for analytics units', err);
        if (active) {
          setTags([]);
          setTagsLoaded(true);
        }
      });
    return () => { active = false; };
  }, [nodeId]);

  const onNodeChange = (id) => setNodeId(id);

  // Only show metrics that are configured (enabled) on the node. Each node tag
  // carries an `enabled` flag; metrics whose tag is disabled or absent are
  // device-internal / not configured and are hidden from charts and legends.
  // DB Tag (`tag_name`) is the single source of truth for TimescaleDB metrics.
  const enabledKeys = useMemo(
    () => new Set(tags.filter((t) => t.enabled).map((t) => t.tag_name).filter(Boolean)),
    [tags]
  );
  const configuredMetrics = useMemo(() => {
    if (!tagsLoaded) return [];
    const all = nodes.find((n) => n.node_id === nodeId)?.metrics || [];
    return all.filter((m) => enabledKeys.has(m));
  }, [nodes, nodeId, tagsLoaded, enabledKeys]);

  // Friendly display name for a metric: use the tag's `label` if set, else the
  // DB tag name (`tag_name`), else the raw telemetry key. Keeps the dashboard clean.
  const tagByKey = useMemo(() => {
    const m = {};
    for (const t of tags) {
      if (t.tag_name) m[t.tag_name] = t;
    }
    return m;
  }, [tags]);
  const displayName = useCallback(
    (metric) => {
      const t = tagByKey[metric];
      if (t) {
        const labelStr = (t.label || '').trim();
        if (labelStr) return labelStr;
        const tagNameStr = (t.tag_name || '').trim();
        if (tagNameStr) return tagNameStr;
      }
      return metric;
    },
    [tagByKey]
  );

  const loadData = useCallback(async () => {
    if (!nodeId || !tagsLoaded) {
      setSeriesByMetric({});
      return;
    }
    const metrics = configuredMetrics;
    if (metrics.length === 0) {
      setSeriesByMetric({});
      return;
    }
    setLoading(true);
    setError(null);
    try {
      // One batched request fetches the whole node's telemetry (all metrics)
      // at once, so we never fire one HTTP call per metric (which tripped
      // Kong's rate limiter and blanked the chart). Digital/state metrics are
      // requested with discrete=true to keep 1-minute resolution at wide ranges.
      const boolMetrics = metrics.filter((m) => booleanSet.has(m));
      const params = { node_id: nodeId, metric: metrics.join(','), interval: range };
      if (boolMetrics.length) params.discrete = boolMetrics.join(',');
      const res = await analyticsApi.getMetrics(params);
      const series = res?.series?.[nodeId] || {};
      const map = {};
      metrics.forEach((m) => { map[m] = series[m] || []; });
      setSeriesByMetric(map);
    } catch (err) {
      setError(err.message || 'Failed to load analytics');
      setSeriesByMetric({});
    } finally {
      setLoading(false);
    }
  }, [nodeId, tagsLoaded, configuredMetrics, range, booleanSet]);

  useEffect(() => { loadData(); }, [loadData]);

  // Classify each metric's *type* from the raw 1h view (range-independent),
  // so a boolean (0/1) metric stays boolean even on aggregated ranges where
  // the hourly/daily cagg would otherwise average it into a fraction (0.33).
  // One batched request fetches every (configured) metric at 1h.
  useEffect(() => {
    let cancelled = false;
    const metrics = configuredMetrics;
    if (!metrics.length) {
      Promise.resolve().then(() => { if (!cancelled) setBooleanSet(new Set()); });
      return;
    }
    analyticsApi
      .getMetrics({ node_id: nodeId, metric: metrics.join(','), interval: '1h' })
      .then((res) => {
        if (cancelled) return;
        const series = res?.series?.[nodeId] || {};
        const set = new Set();
        metrics.forEach((m) => {
          const pts = series[m] || [];
          if (pts.length && pts.every((p) => p.v === 0 || p.v === 1)) set.add(m);
        });
        setBooleanSet(set);
      })
      .catch(() => {});
    return () => { cancelled = true; };
  }, [nodeId, configuredMetrics]);

  const metrics = Object.keys(seriesByMetric);
  const totalPoints = metrics.reduce((s, m) => s + seriesByMetric[m].length, 0);

  // Classify metrics as analog (continuous) or digital/boolean (0/1). The type
  // is decided from the raw 1h view above (booleanSet), so it is stable across
  // every selected range. Fall back to value-based detection until classified.
  const boolMetrics = metrics.filter((m) =>
    booleanSet.size ? booleanSet.has(m) : isBooleanMetric(seriesByMetric[m])
  );
  const analogMetrics = metrics.filter((m) => !boolMetrics.includes(m));
  // Each chart builds its own time axis from the metrics it draws, so mismatched
  // bucket counts (per-minute digital vs hourly analog at the same range) never
  // squash or truncate a series.
  const trendAxis = buildAxis(analogMetrics.map((m) => seriesByMetric[m] || []));
  const trendLabels = trendAxis.map(formatTick);
  const stateAxis = buildAxis(boolMetrics.map((m) => seriesByMetric[m] || []));
  const stateLabels = stateAxis.map(formatTick);

  // Analog trend: each metric draws a min–max envelope (filled band between its
  // low/high bucket values) plus an avg line, so aggregated ranges (7d/30d)
  // keep their full range information instead of a single point. The band
  // datasets are tagged isBand and hidden from the legend/tooltip.
  const trendData = {
    labels: trendLabels,
    datasets: analogMetrics.flatMap((m, i) => {
      const color = PALETTE[i % PALETTE.length];
      const pts = seriesByMetric[m] || [];
      return [
        {
          label: displayName(m),
          data: alignToAxis(trendAxis, pts, (p) => (p.max != null ? p.max : p.v)),
          borderWidth: 0,
          pointRadius: 0,
          pointHoverRadius: 0,
          fill: '+1',
          backgroundColor: color + '22',
          isBand: true,
          order: 1,
        },
        {
          label: displayName(m),
          data: alignToAxis(trendAxis, pts, (p) => (p.min != null ? p.min : p.v)),
          borderWidth: 0,
          pointRadius: 0,
          pointHoverRadius: 0,
          fill: false,
          isBand: true,
          order: 1,
        },
        {
          label: displayName(m),
          data: alignToAxis(trendAxis, pts, (p) => (p.avg != null ? p.avg : p.v)),
          borderColor: color,
          backgroundColor: color + '22',
          borderWidth: 2,
          pointRadius: 0,
          pointHoverRadius: 4,
          tension: 0.3,
          fill: false,
          order: 2,
        },
      ];
    }),
  };

  // Shared zoom/pan config (chartjs-plugin-zoom). Mode 'x' keeps the time axis
  // zoomable while Y stays auto-scaled, so dragging/scrolling drills into a
  // window without distorting the values.
  const zoomCfg = {
    // pan needs a modifier key so a plain left-drag is reserved for box-zoom.
    // Having pan and drag-zoom both trigger on a bare left-drag is a documented
    // conflict in chartjs-plugin-zoom that swallows the hover events, breaking
    // tooltips and legend clicks.
    pan: { enabled: true, mode: 'x', modifierKey: 'shift' },
    zoom: {
      wheel: { enabled: true },
      pinch: { enabled: true },
      drag: { enabled: true, backgroundColor: 'rgba(16,185,129,0.15)', borderColor: 'rgba(16,185,129,0.5)', borderWidth: 1 },
      mode: 'x',
    },
  };

  const trendOptions = {
    responsive: true,
    maintainAspectRatio: false,
    interaction: { mode: 'index', intersect: false },
    plugins: {
      legend: {
        // Each metric is rendered as 3 datasets (max band, min band, avg line)
        // that share one label. The bands are hidden from the legend via
        // `filter`, but toggling a legend item must hide/show all three so the
        // metric appears and disappears as a unit. The default handler only
        // flips the single avg-line dataset, leaving the bands behind — which
        // made the legend look like it could not be re-shown.
        onClick: (e, legendItem, legend) => {
          const ci = legend.chart;
          const mi = Math.floor(legendItem.datasetIndex / 3);
          const indices = [3 * mi, 3 * mi + 1, 3 * mi + 2];
          const hide = ci.isDatasetVisible(legendItem.datasetIndex);
          indices.forEach((i) => (hide ? ci.hide(i) : ci.show(i)));
          ci.update();
        },
        labels: {
          color: 'rgba(148,163,184,0.9)',
          boxWidth: 12,
          font: { size: 10 },
          filter: (item, data) => !data.datasets[item.datasetIndex].isBand,
        },
      },
      tooltip: {
        mode: 'index',
        intersect: false,
        filter: (item) => !item.dataset.isBand,
        callbacks: {
          label: (c) => {
            const m = c.dataset.label;
            const tag = tags.find((t) => t.source_key === m || t.tag_name === m);
            const unit = tag?.unit ? ` ${tag.unit}` : '';
            return `${displayName(m)}: ${fmt(c.parsed.y)}${unit}`;
          },
        },
      },
      zoom: zoomCfg,
    },
    scales: {
      x: { grid: { color: 'rgba(148,163,184,0.08)' }, ticks: { color: 'rgba(148,163,184,0.7)', maxRotation: 0, autoSkip: true, maxTicksLimit: 8 } },
      y: { grid: { color: 'rgba(148,163,184,0.08)' }, ticks: { color: 'rgba(148,163,184,0.7)' } },
    },
  };

  const stateData = {
    labels: stateLabels,
    datasets: boolMetrics.map((m, i) => ({
      label: displayName(m),
      data: alignToAxis(stateAxis, seriesByMetric[m] || [], (p) => p.v),
      borderColor: PALETTE[i % PALETTE.length],
      backgroundColor: PALETTE[i % PALETTE.length] + '22',
      borderWidth: 2,
      pointRadius: 0,
      pointHoverRadius: 4,
      stepped: true,
      fill: false,
    })),
  };

  const stateOptions = {
    responsive: true,
    maintainAspectRatio: false,
    interaction: { mode: 'index', intersect: false },
    plugins: {
      legend: { labels: { color: 'rgba(148,163,184,0.9)', boxWidth: 12, font: { size: 10 } } },
      tooltip: { mode: 'index', intersect: false, callbacks: { label: (c) => `${c.dataset.label}: ${c.parsed.y ? 'ON' : 'OFF'}` } },
      zoom: zoomCfg,
    },
    scales: {
      x: { grid: { color: 'rgba(148,163,184,0.08)' }, ticks: { color: 'rgba(148,163,184,0.7)', maxRotation: 0, autoSkip: true, maxTicksLimit: 8 } },
      y: { min: 0, max: 1, ticks: { color: 'rgba(148,163,184,0.7)', stepSize: 1, callback: (v) => (v === 1 ? 'ON' : 'OFF') } },
    },
  };

  const selectedNode = nodes.find((n) => n.node_id === nodeId);

  const corr = (() => {
    const n = metrics.length;
    if (n < 2) return null;
    const matrix = metrics.map((mi) =>
      metrics.map((mj) => {
        const a = seriesByMetric[mi].map((p) => p.v);
        const b = seriesByMetric[mj].map((p) => p.v);
        const len = Math.min(a.length, b.length);
        return pearson(a.slice(0, len), b.slice(0, len));
      })
    );
    return { metrics, matrix };
  })();

  return (
    <div className="flex flex-col gap-4 w-full animate-fadeIn">
      <PageHeader icon={BarChart3} title="Analytics" subtitle="Aggregated telemetry from the Analytics Service — all metrics, one view.">
        <select
          value={nodeId}
          onChange={(e) => onNodeChange(e.target.value)}
          disabled={nodes.length === 0}
          title={selectedNode?.module_id ? `module: ${selectedNode.module_id}` : undefined}
          className="h-10 px-3 text-xs font-black uppercase tracking-widest bg-[#040e0a] border border-emerald-500/20 text-slate-200 cursor-pointer focus:outline-none focus:border-emerald-500/60"
        >
          {nodes.length === 0 && <option value="">No nodes</option>}
          {nodes.map((n) => (
            <option key={n.node_id} value={n.node_id}>
              {shortId(n.node_id)}{n.module_id ? ` · ${shortId(n.module_id)}` : ''}
            </option>
          ))}
        </select>

        <div className="flex bg-[#040e0a] p-1 border border-emerald-500/20 h-10 items-center shrink-0">
          {RANGES.map((r) => (
            <button
              key={r.id}
              onClick={() => setRange(r.id)}
              className={`h-full flex-1 sm:flex-initial px-3 text-[10px] sm:text-[11px] font-black tracking-widest transition-all duration-200 cursor-pointer select-none ${range === r.id ? 'bg-emerald-500 text-black' : 'text-slate-400 hover:text-slate-200'}`}
            >
              {r.label}
            </button>
          ))}
        </div>
      </PageHeader>

      {error && (
        <div className="flex items-center gap-3 p-4 border border-red-500/30 bg-red-950/15 text-red-400">
          <AlertTriangle className="w-5 h-5 shrink-0" />
          <span className="text-xs sm:text-sm font-bold">{error}</span>
        </div>
      )}

      {loading && (
        <div className="flex items-center justify-center gap-3 min-h-[300px] text-emerald-400">
          <Loader2 className="w-6 h-6 animate-spin" />
          <span className="text-xs font-black tracking-widest uppercase">Loading analytics…</span>
        </div>
      )}

      {!loading && !error && nodes.length === 0 && (
        <div className="flex flex-col items-center justify-center gap-3 min-h-[300px] text-slate-400">
          <Database className="w-10 h-10 opacity-40" />
          <span className="text-sm font-bold">No telemetry yet</span>
          <span className="text-xs text-slate-500 max-w-md text-center">
            Analytics ingests <code>telemetry.batch</code> from the Module Service. Once a paired node
            reports sensor data, it will appear here automatically.
          </span>
        </div>
      )}

      {!loading && !error && nodes.length > 0 && tagsLoaded && configuredMetrics.length === 0 && (
        <div className="flex flex-col items-center justify-center gap-3 min-h-[300px] text-slate-400">
          <Database className="w-10 h-10 opacity-40 text-amber-400" />
          <span className="text-sm font-bold text-amber-300">No Configured Telemetry Fields</span>
          <span className="text-xs text-slate-400 max-w-md text-center">
            No active sensor tags have been configured for this node. Go to the <strong>Node Configuration</strong> page to enable telemetry fields for this node.
          </span>
        </div>
      )}

      {!loading && nodes.length > 0 && configuredMetrics.length > 0 && totalPoints === 0 && (
        <div className="flex flex-col items-center justify-center gap-2 min-h-[300px] text-slate-400">
          <Activity className="w-10 h-10 opacity-40" />
          <span className="text-sm font-bold">No data for this range</span>
          <span className="text-xs text-slate-500">Try a wider time range.</span>
        </div>
      )}

      {!loading && totalPoints > 0 && (
        <>
          {/* Combined trend: analog on the left axis, digital/boolean (step
              "state" lines, 0/1) on the right axis — one chart, not split. */}
          <Card title={`Trends · ${range}`} icon={LineChart}>
            <div className="flex items-center justify-end gap-1.5 mb-2">
              <button type="button" title="Zoom in" onClick={() => trendRef.current?.zoom(1.2)} className="p-1.5 border border-emerald-500/20 text-slate-300 hover:text-emerald-300 hover:border-emerald-500/50 transition-colors cursor-pointer" style={{ lineHeight: 0 }}><ZoomIn className="w-3.5 h-3.5" /></button>
              <button type="button" title="Zoom out" onClick={() => trendRef.current?.zoom(0.8)} className="p-1.5 border border-emerald-500/20 text-slate-300 hover:text-emerald-300 hover:border-emerald-500/50 transition-colors cursor-pointer" style={{ lineHeight: 0 }}><ZoomOut className="w-3.5 h-3.5" /></button>
              <button type="button" title="Reset zoom" onClick={() => trendRef.current?.resetZoom()} className="p-1.5 border border-emerald-500/20 text-slate-300 hover:text-emerald-300 hover:border-emerald-500/50 transition-colors cursor-pointer" style={{ lineHeight: 0 }}><Maximize2 className="w-3.5 h-3.5" /></button>
            </div>
            <div className="h-[360px]">
              <Line ref={trendRef} data={trendData} options={trendOptions} />
            </div>
              <p className="text-[9px] text-slate-500 mt-1.5 uppercase tracking-wider">Scroll to zoom · drag to box-zoom · shift-drag to pan</p>

            </Card>

            {/* Dedicated state graph for boolean/digital metrics, below the trend */}
          {boolMetrics.length > 0 && (
            <Card title={`Digital states · ${range}`} icon={Activity}>
              <div className="flex items-center justify-end gap-1.5 mb-2">
                <button type="button" title="Zoom in" onClick={() => stateRef.current?.zoom(1.2)} className="p-1.5 border border-emerald-500/20 text-slate-300 hover:text-emerald-300 hover:border-emerald-500/50 transition-colors cursor-pointer" style={{ lineHeight: 0 }}><ZoomIn className="w-3.5 h-3.5" /></button>
                <button type="button" title="Zoom out" onClick={() => stateRef.current?.zoom(0.8)} className="p-1.5 border border-emerald-500/20 text-slate-300 hover:text-emerald-300 hover:border-emerald-500/50 transition-colors cursor-pointer" style={{ lineHeight: 0 }}><ZoomOut className="w-3.5 h-3.5" /></button>
                <button type="button" title="Reset zoom" onClick={() => stateRef.current?.resetZoom()} className="p-1.5 border border-emerald-500/20 text-slate-300 hover:text-emerald-300 hover:border-emerald-500/50 transition-colors cursor-pointer" style={{ lineHeight: 0 }}><Maximize2 className="w-3.5 h-3.5" /></button>
              </div>
              <div className="h-[220px]">
                <Line ref={stateRef} data={stateData} options={stateOptions} />
              </div>
                <p className="text-[9px] text-slate-500 mt-1.5 uppercase tracking-wider">Scroll to zoom · drag to box-zoom · shift-drag to pan</p>
              <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3 mt-4">
                {boolMetrics.map((m) => {
                  const pts = seriesByMetric[m];
                  const on = pts.filter((p) => p.v === 1).length;
                  const pct = pts.length ? Math.round((on / pts.length) * 100) : 0;
                  return (
                    <div key={m} className="flex flex-col gap-1 p-3 border border-emerald-500/15 bg-[#030705]/60">
                      <span className="text-[10px] font-black uppercase tracking-widest text-slate-400 truncate">{displayName(m)}</span>
                      <span className="text-sm font-black" style={{ color: on > 0 ? '#10b981' : '#64748b' }}>
                        {on > 0 ? 'ON' : 'OFF'} · {pct}%
                      </span>
                    </div>
                  );
                })}
              </div>
            </Card>
          )}

          {/* Per-metric summary (analog) */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {analogMetrics.map((m) => {
              const s = statsOf(seriesByMetric[m]);
              const tag = tags.find((t) => t.source_key === m || t.tag_name === m);
              const unit = tag?.unit ? ` ${tag.unit}` : '';
              return (
                <Card key={m} title={displayName(m)} icon={Activity}>
                  <div className="grid grid-cols-4 gap-3">
                    <StatChip label="Samples" value={s.count} />
                    <StatChip label="Min" value={fmt(s.min) + unit} />
                    <StatChip label="Avg" value={fmt(s.avg) + unit} />
                    <StatChip label="Max" value={fmt(s.max) + unit} />
                    <StatChip label="Last" value={fmt(s.last) + unit} />
                  </div>
                </Card>
              );
            })}
          </div>

          <Card title="Distributions (histogram per analog metric)" icon={BarChart2}>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 sm:gap-4">
              {analogMetrics.map((m, i) => {
                const h = histogram(seriesByMetric[m].map((p) => p.v));
                const data = {
                  labels: h.labels,
                  datasets: [{
                    label: displayName(m),
                    data: h.counts,
                    backgroundColor: PALETTE[i % PALETTE.length] + 'cc',
                    borderColor: PALETTE[i % PALETTE.length],
                    borderWidth: 1,
                  }],
                };
                const opt = {
                  responsive: true,
                  maintainAspectRatio: false,
                  plugins: { legend: { display: false } },
                  scales: {
                    x: { grid: { color: 'rgba(148,163,184,0.08)' }, ticks: { color: 'rgba(148,163,184,0.7)', maxRotation: 45, autoSkip: true, maxTicksLimit: 6 } },
                    y: { grid: { color: 'rgba(148,163,184,0.08)' }, ticks: { color: 'rgba(148,163,184,0.7)', precision: 0 } },
                  },
                };
                return (
                  <div key={m}>
                    <div className="text-[10px] font-black uppercase tracking-widest mb-2 text-slate-500">{displayName(m)}</div>
                    <div className="h-[180px]">
                      {h.counts.length ? <Bar data={data} options={opt} /> : <div className="text-xs text-slate-500">no data</div>}
                    </div>
                  </div>
                );
              })}
            </div>
          </Card>

          <Card title="Correlation matrix (Pearson)" icon={Grid3x3}>
            {corr ? (
              <div className="overflow-x-auto">
                <table className="border-collapse text-xs">
                  <thead>
                    <tr>
                      <th className="p-2 text-left text-[10px] font-black uppercase tracking-widest text-slate-500">metric</th>
                      {corr.metrics.map((m) => (
                        <th key={m} className="p-2 text-[10px] font-black uppercase tracking-widest text-slate-500">{displayName(m)}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {corr.metrics.map((mi, i) => (
                      <tr key={mi}>
                        <td className="p-2 text-[10px] font-black uppercase tracking-widest whitespace-nowrap text-slate-500">{displayName(mi)}</td>
                        {corr.metrics.map((mj, j) => {
                          const v = corr.matrix[i][j];
                          return (
                            <td
                              key={mj}
                              className="p-2 text-center font-black tabular-nums whitespace-nowrap"
                              style={{ backgroundColor: corrColor(v), color: Math.abs(v) > 0.5 ? '#0b0f0a' : '#e2e8f0' }}
                              title={`${displayName(mi)} ↔ ${displayName(mj)}: ${v.toFixed(2)}`}
                            >
                              {v.toFixed(2)}
                            </td>
                          );
                        })}
                      </tr>
                    ))}
                  </tbody>
                </table>
                <div className="flex items-center gap-3 mt-3 text-[10px] font-black uppercase tracking-widest text-slate-500">
                  <span className="flex items-center gap-1"><span className="w-3 h-3 inline-block" style={{ backgroundColor: 'rgba(244,63,94,0.7)' }} /> -1</span>
                  <span className="flex items-center gap-1"><span className="w-3 h-3 inline-block" style={{ backgroundColor: 'rgba(148,163,184,0.4)' }} /> 0</span>
                  <span className="flex items-center gap-1"><span className="w-3 h-3 inline-block" style={{ backgroundColor: 'rgba(16,185,129,0.7)' }} /> +1</span>
                </div>
              </div>
            ) : (
              <div className="text-xs text-slate-500">Need at least 2 metrics to compute correlation.</div>
            )}
          </Card>
        </>
      )}
    </div>
  );
}

export default Analytics;
