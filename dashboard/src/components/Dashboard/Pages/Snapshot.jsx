import { useState, useEffect, useCallback, useMemo } from 'react';
import {
  Camera,
  RefreshCw,
  Trash2,
  Loader2,
  Film,
  AlertTriangle,
  X,
  Sparkles,
  Check,
  Download,
  Search,
  ArrowUpDown,
} from 'lucide-react';
import PageHeader from './PageHeader';
import streamApi from '../../../api/stream';
import mlApi from '../../../api/ml';
import { withToken } from '../../../api/client';
import { useModule } from '../../../context/useModule';

function canManage() {
  try {
    const u = JSON.parse(sessionStorage.getItem('user') || 'null');
    const roles = Array.isArray(u?.roles) ? u.roles : [];
    return roles.includes('admin') || roles.includes('operator');
  } catch {
    return false;
  }
}

function formatTime(d) {
  try {
    return new Date(d).toLocaleString();
  } catch {
    return '';
  }
}

// Format a seconds count as mm:ss for recording durations.
function formatDuration(totalSeconds) {
  const s = Math.max(0, Math.round(totalSeconds || 0));
  const m = Math.floor(s / 60);
  return `${String(m).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`;
}

// Parse a JSON string coming from the backend, tolerating empty/invalid values.
function safeParseJSON(value, fallback) {
  if (!value) return fallback;
  try {
    return JSON.parse(value);
  } catch {
    return fallback;
  }
}

// DetectedObject + bounding box overlay rendered on top of the original frame.
// The backend stores pixel-space boxes (x1,y1,x2,y2) in the captured frame's
// native resolution, so we scale them to the displayed image using its natural
// dimensions (read on load) expressed as percentages.
function DetectionImage({ item, onClick, className = '' }) {
  const detections = safeParseJSON(item.detections, []);
  const [natural, setNatural] = useState({ w: 0, h: 0 });

  return (
    <div
      className={`relative aspect-video bg-black overflow-hidden ${className}`}
      onClick={onClick}
    >
      <img
        src={withToken(item.url)}
        alt={item.stream_name}
        loading="lazy"
        onLoad={(e) => {
          setNatural({ w: e.currentTarget.naturalWidth, h: e.currentTarget.naturalHeight });
        }}
        className="w-full h-full object-cover"
        onError={(e) => {
          e.currentTarget.style.display = 'none';
        }}
      />
      {natural.w > 0 && natural.h > 0 && detections.map((d, i) => {
        const { x1, y1, x2, y2 } = d.bbox || {};
        if ([x1, y1, x2, y2].some((v) => typeof v !== 'number')) return null;
        const left = (x1 / natural.w) * 100;
        const top = (y1 / natural.h) * 100;
        const width = ((x2 - x1) / natural.w) * 100;
        const height = ((y2 - y1) / natural.h) * 100;
        return (
          <div
            key={i}
            className="absolute border-2 border-violet-400 pointer-events-none"
            style={{ left: `${left}%`, top: `${top}%`, width: `${width}%`, height: `${height}%` }}
          >
            <span className="absolute -top-5 left-0 px-1 py-0.5 bg-violet-500/90 text-[9px] font-black uppercase tracking-wider text-white whitespace-nowrap">
              {d.class_name} {(d.confidence * 100).toFixed(0)}%
            </span>
          </div>
        );
      })}
    </div>
  );
}

// Compact summary line of detected classes + counts for a detection tile.
function DetectionSummary({ item }) {
  const detections = safeParseJSON(item.detections, []);
  const counts = {};
  detections.forEach((d) => {
    counts[d.class_name] = (counts[d.class_name] || 0) + 1;
  });
  const parts = Object.entries(counts).map(([cls, n]) => `${cls}·${n}`);
  return (
    <div className="flex flex-wrap gap-1">
      {parts.length === 0 && (
        <span className="text-[10px] text-slate-500 uppercase tracking-widest">No objects</span>
      )}
      {parts.map((p) => (
        <span
          key={p}
          className="px-1.5 py-0.5 bg-violet-500/15 border border-violet-500/30 text-violet-300 text-[10px] font-black uppercase tracking-wider"
        >
          {p}
        </span>
      ))}
    </div>
  );
}

// ─── mlbucket (external cctv-capture cron) helpers ──────────────────────────
function parseKey(key) {
  const parts = (key || '').split('/');
  const stream = parts[1] || 'unknown';
  const file = parts[parts.length - 1] || '';
  const stem = file.replace(/\.[^.]+$/, '');
  return { stream, file, stem };
}
function resultJsonUrl(frameUrl) {
  return frameUrl.replace('/frames/', '/results/').replace(/\.jpg$/i, '.json');
}
function annotatedUrl(frameUrl) {
  return withToken(frameUrl.replace('/frames/', '/annotated/'));
}
// Normalize an ml object into the same shape used by the gallery grid.
function normalizeCapture(raw) {
  const { stream, stem } = parseKey(raw.key);
  return {
    id: raw.key,
    key: raw.key,
    url: raw.url,
    kind: 'capture',
    captureType: raw.kind, // 'frame' | 'annotated'
    stream_name: stream,
    title: stem,
    created_at: raw.last_modified || '',
    source: 'capture',
    size: raw.size,
  };
}

function triggerDownload(u, name) {
  const a = document.createElement('a');
  a.href = withToken(u);
  a.download = name || '';
  document.body.appendChild(a);
  a.click();
  a.remove();
}


export default function Snapshot() {
  const { selectedModule } = useModule();
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [filter, setFilter] = useState('snapshot'); // 'snapshot' | 'recording' | 'ai'
  const [busyId, setBusyId] = useState(null);
  const [preview, setPreview] = useState(null); // lightbox item
  const [captureDetail, setCaptureDetail] = useState(null); // mlbucket result JSON

  // Local search + filter controls
  const [query, setQuery] = useState('');
  const [sort, setSort] = useState('newest'); // 'newest' | 'oldest'
  const [streamFilter, setStreamFilter] = useState('all');

  const streamOptions = useMemo(() => {
    const set = new Set(items.map((i) => i.stream_name).filter(Boolean));
    return Array.from(set).sort((a, b) => a.localeCompare(b));
  }, [items]);

  const filtered = useMemo(() => {
    let list = items;
    const q = query.trim().toLowerCase();
    if (q) {
      list = list.filter((i) => {
        const hay = [
          i.stream_name,
          i.title,
          i.id,
          ...safeParseJSON(i.detections, []).map((d) => d.class_name),
        ]
          .filter(Boolean)
          .join(' ')
          .toLowerCase();
        return hay.includes(q);
      });
    }
    if (streamFilter !== 'all') {
      list = list.filter((i) => i.stream_name === streamFilter);
    }
    return [...list].sort((a, b) => {
      const ta = new Date(a.created_at).getTime() || 0;
      const tb = new Date(b.created_at).getTime() || 0;
      return sort === 'newest' ? tb - ta : ta - tb;
    });
  }, [items, query, streamFilter, sort]);

  // File-management (select / download / delete)
  const [selectMode, setSelectMode] = useState(false);
  const [selected, setSelected] = useState({}); // id -> true
  const [actionBusy, setActionBusy] = useState(false);

  const manage = canManage();

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      if (filter === 'ai') {
        // AI Detection: only show results for the selected module.
        // If no module is selected, the gallery stays empty so the user
        // cannot see detection results from unrelated modules.
        if (!selectedModule) {
          setItems([]);
          return;
        }
        const data = await streamApi.list({ module_id: selectedModule.id }).catch(() => null);
        const names = new Set((data?.streams || []).map((s) => s.name));
        if (!names.size) {
          setItems([]);
          return;
        }
        const [framesRes, annotatedRes] = await Promise.all([
          mlApi.listResults('frames').catch(() => null),
          mlApi.listResults('annotated').catch(() => null),
        ]);
        const frames = framesRes?.items || (Array.isArray(framesRes) ? framesRes : []);
        const annotated = annotatedRes?.items || (Array.isArray(annotatedRes) ? annotatedRes : []);
        const a = frames.map(normalizeCapture);
        const b = annotated.map(normalizeCapture);
        const list = [...a, ...b].filter((it) => names.has(it.stream_name));
        setItems(list);
      } else if (filter === 'snapshot' || filter === 'recording') {
        const data = await streamApi.listSnapshots({ kind: filter, module_id: selectedModule?.id || '' });
        setItems(Array.isArray(data?.snapshots) ? data.snapshots : []);
      } else {
        setItems([]);
      }
    } catch (e) {
      setError(e?.message || 'Failed to load gallery');
      setItems([]);
    } finally {
      setLoading(false);
    }
  }, [filter, selectedModule]);

  useEffect(() => {
    load();
    setSelected({});
  }, [load]);

  const openPreview = async (item) => {
    setPreview(item);
    setCaptureDetail(null);
    if (item.source === 'capture' && item.captureType === 'frame') {
      try {
        const res = await fetch(resultJsonUrl(item.url));
        if (res.ok) setCaptureDetail(await res.json());
      } catch {
        /* ignore — show images only */
      }
    }
  };

  const toggleSelect = (id) => {
    setSelected((prev) => {
      const next = { ...prev };
      if (next[id]) delete next[id];
      else next[id] = true;
      return next;
    });
  };

  const selectedItems = items.filter((i) => selected[i.id]);

  const handleDownload = (item) => {
    const name = (item.stream_name || 'file') + '_' + (item.title || item.id || '');
    triggerDownload(item.url, name);
  };

  const handleDownloadSelected = () => {
    selectedItems.forEach((it, idx) => {
      setTimeout(() => handleDownload(it), idx * 250);
    });
  };

  const handleDelete = async (item) => {
    if (!confirm('Delete this file?')) return;
    setBusyId(item.id);
    try {
      if (item.source === 'capture') {
        await mlApi.deleteResult(item.key);
      } else {
        await streamApi.deleteSnapshot(item.id);
      }
      setPreview(null);
      await load();
    } catch (e) {
      setError(e?.message || 'Failed to delete');
    } finally {
      setBusyId(null);
    }
  };

  const handleDeleteSelected = async () => {
    if (!confirm(`Delete ${selectedItems.length} selected file(s)?`)) return;
    setActionBusy(true);
    setError('');
    try {
      for (const it of selectedItems) {
        if (it.source === 'capture') await mlApi.deleteResult(it.key);
        else await streamApi.deleteSnapshot(it.id);
      }
      setSelected({});
      setSelectMode(false);
      await load();
    } catch (e) {
      setError(e?.message || 'Failed to delete');
    } finally {
      setActionBusy(false);
    }
  };

  const tabs = [
    { id: 'snapshot', label: 'SNAPSHOT', icon: Camera },
    { id: 'recording', label: 'RECORDING', icon: Film },
    { id: 'ai', label: 'AI DETECTION', icon: Sparkles },
  ];

  return (
    <div className="space-y-4">
      <PageHeader icon={Camera} title="GALLERY" subtitle="File manager for CCTV captures, recordings, AI detections, and periodic cron captures (mlbucket bucket). Select, download, or delete.">
        <div className="flex items-center gap-2">
          <button
            onClick={load}
            className="h-10 px-3 flex items-center gap-2 border border-emerald-500/20 text-emerald-400 hover:bg-emerald-500/10 text-xs font-black uppercase tracking-widest"
            title="Refresh"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} /> Refresh
          </button>
          <button
            onClick={() => { setSelectMode((v) => !v); setSelected({}); }}
            className={`h-10 px-3 flex items-center gap-2 border text-xs font-black uppercase tracking-widest transition-all ${selectMode ? 'bg-emerald-500 text-black border-emerald-500' : 'border-emerald-500/15 text-slate-300 hover:text-emerald-400 hover:bg-emerald-500/10'}`}
            title="Select files"
          >
            <Check className="w-4 h-4" /> {selectMode ? 'Cancel' : 'Select'}
          </button>
        </div>
      </PageHeader>

      {/* Filter tabs */}
      <div className="flex gap-2 flex-wrap">
        {tabs.map((t) => {
          const Icon = t.icon;
          const active = filter === t.id;
          return (
            <button
              key={t.id}
              onClick={() => setFilter(t.id)}
              className={`flex items-center gap-2 px-4 h-10 border text-xs font-black uppercase tracking-widest transition-all ${active ? 'bg-emerald-500 text-black border-emerald-500' : 'border-emerald-500/15 text-slate-300 hover:text-emerald-400 hover:bg-emerald-500/10'}`}
            >
              <Icon className="w-4 h-4" />
              {t.label}
              {active && (
                <span className="ml-1 px-1.5 py-0.5 rounded text-[10px] bg-black/20">
                  {items.length}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* Search + filter bar */}
      <div className="flex flex-col sm:flex-row gap-2 flex-wrap">
        <div className="relative flex-1 min-w-[200px]">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search by stream, title, or detected object…"
            className="w-full h-10 pl-9 pr-3 bg-[#030705]/80 border border-emerald-500/15 text-xs text-white placeholder:text-slate-500 uppercase tracking-wide outline-none focus:border-emerald-400"
          />
        </div>
        <select
          value={streamFilter}
          onChange={(e) => setStreamFilter(e.target.value)}
          className="h-10 px-3 bg-[#030705]/80 border border-emerald-500/15 text-xs text-white uppercase tracking-wide outline-none focus:border-emerald-400 cursor-pointer"
        >
          <option value="all">All streams</option>
          {streamOptions.map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>
        <button
          onClick={() => setSort((v) => (v === 'newest' ? 'oldest' : 'newest'))}
          className="h-10 px-3 flex items-center gap-2 border border-emerald-500/15 text-xs font-black uppercase tracking-widest text-slate-300 hover:text-emerald-400 hover:bg-emerald-500/10"
          title="Toggle sort order"
        >
          <ArrowUpDown className="w-4 h-4" />
          {sort === 'newest' ? 'Newest' : 'Oldest'}
        </button>
      </div>

      {error && (
        <div className="flex items-center gap-2 text-red-400 text-sm font-bold border border-red-500/30 bg-red-500/10 px-4 py-3">
          <AlertTriangle className="w-4 h-4" /> {error}
        </div>
      )}

      {loading ? (
        <div className="flex items-center justify-center gap-3 py-20 text-slate-400">
          <Loader2 className="w-6 h-6 animate-spin text-emerald-400" />
          <span className="text-xs font-black uppercase tracking-widest">Loading gallery…</span>
        </div>
      ) : filtered.length === 0 ? (
        <div className="flex flex-col items-center justify-center gap-4 py-20 border border-emerald-500/10 bg-[#030705]/60">
          <Camera className="w-12 h-12 text-slate-600" />
          <div className="text-center">
            {query || streamFilter !== 'all' ? (
              <>
                <div className="text-sm font-black uppercase tracking-widest text-slate-300">No matches</div>
                <div className="text-xs text-slate-500 mt-1">No gallery items match the current search or filter.</div>
              </>
            ) : (
              <>
                <div className="text-sm font-black uppercase tracking-widest text-slate-300">Gallery Empty</div>
                <div className="text-xs text-slate-500 mt-1">Use the camera (SNAPSHOT) on the LIVE page for a plain frame, or AI Detect for a detection. AI DETECTION shows every ML result (cron routine + live captures) from the mlbucket bucket.</div>
              </>
            )}
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {filtered.map((s) => {
            const isDetection = s.kind === 'detection';
            const isCapture = s.source === 'capture';
            const isAI = isDetection || isCapture;
            const isRecording = s.kind === 'recording';
            const checked = !!selected[s.id];
            return (
            <div key={s.id} className={`border border-emerald-500/15 bg-[#030705]/80 backdrop-blur-md overflow-hidden flex flex-col ${checked ? 'ring-2 ring-emerald-400' : ''}`}>
              <div className="relative aspect-video bg-black">
                {isDetection ? (
                  <DetectionImage item={s} onClick={() => !selectMode && openPreview(s)} />
                ) : isRecording ? (
                  <video
                    src={withToken(s.url)}
                    controls
                    preload="metadata"
                    className="w-full h-full object-contain bg-black"
                    onError={(e) => {
                      e.currentTarget.style.display = 'none';
                    }}
                  />
                ) : (
                  <img
                    src={withToken(s.url)}
                    alt={s.stream_name}
                    loading="lazy"
                    onClick={() => selectMode ? toggleSelect(s.id) : openPreview(s)}
                    className="w-full h-full object-cover cursor-pointer hover:opacity-90 transition-opacity"
                    onError={(e) => {
                      e.currentTarget.style.display = 'none';
                    }}
                  />
                )}
                <span className={`absolute top-2 left-2 inline-flex items-center gap-1 px-2 py-0.5 text-[10px] font-black uppercase tracking-widest border ${
                  s.kind === 'recording'
                    ? 'bg-red-500/20 border-red-500/30 text-red-400'
                    : isAI
                      ? 'bg-violet-500/20 border-violet-500/30 text-violet-300'
                      : 'bg-emerald-500/20 border-emerald-500/30 text-emerald-400'
                }`}>
                  {s.kind === 'recording' ? <Film className="w-3 h-3" /> : isAI ? <Sparkles className="w-3 h-3" /> : <Camera className="w-3 h-3" />}
                  {isCapture ? s.captureType : s.kind}
                </span>
                {selectMode && (
                  <button
                    onClick={() => toggleSelect(s.id)}
                    className={`absolute top-2 right-2 h-6 w-6 flex items-center justify-center border ${checked ? 'bg-emerald-500 text-black border-emerald-500' : 'bg-black/50 border-white/30 text-white'}`}
                    title="Select"
                  >
                    <Check className="w-3.5 h-3.5" />
                  </button>
                )}
              </div>

              <div className="px-3 py-2 flex items-center justify-between gap-2">
                <div className="min-w-0">
                  <div className="text-xs font-black uppercase tracking-wide text-white truncate">{s.stream_name}</div>
                  <div className="text-[10px] text-slate-500 truncate">
                    {formatTime(s.created_at)}{isRecording && s.duration ? ` · ${formatDuration(s.duration)}` : ''}
                  </div>
                  {isDetection && (
                    <div className="mt-1">
                      <DetectionSummary item={s} />
                    </div>
                  )}
                </div>
                {!selectMode && (
                  <div className="flex items-center gap-1.5 shrink-0">
                    <button
                      onClick={() => handleDownload(s)}
                      className="h-8 w-8 flex items-center justify-center border border-emerald-500/20 text-emerald-400 hover:bg-emerald-500/10"
                      title="Download"
                    >
                      <Download className="w-4 h-4" />
                    </button>
                    {manage && (
                      <button
                        onClick={() => handleDelete(s)}
                        disabled={busyId === s.id}
                        className="h-8 w-8 flex items-center justify-center border border-red-500/20 text-red-400 hover:bg-red-500/10 disabled:opacity-50"
                        title="Delete"
                      >
                        {busyId === s.id ? <Loader2 className="w-4 h-4 animate-spin" /> : <Trash2 className="w-4 h-4" />}
                      </button>
                    )}
                  </div>
                )}
              </div>
            </div>
            );
          })}
        </div>
      )}

      {/* Bulk action bar (selection mode) */}
      {selectMode && (
        <div className="sticky bottom-4 z-30 flex items-center justify-between gap-3 border border-emerald-500/30 bg-[#030705]/95 backdrop-blur-md px-4 py-3">
          <span className="text-xs font-black uppercase tracking-widest text-emerald-300">
            {selectedItems.length} selected
          </span>
          <div className="flex items-center gap-2">
            <button
              onClick={handleDownloadSelected}
              disabled={selectedItems.length === 0 || actionBusy}
              className="h-9 px-3 flex items-center gap-2 border border-emerald-500/20 text-emerald-400 hover:bg-emerald-500/10 text-xs font-black uppercase tracking-widest disabled:opacity-50"
            >
              <Download className="w-4 h-4" /> Download
            </button>
            {manage && (
              <button
                onClick={handleDeleteSelected}
                disabled={selectedItems.length === 0 || actionBusy}
                className="h-9 px-3 flex items-center gap-2 border border-red-500/30 text-red-400 hover:bg-red-500/10 text-xs font-black uppercase tracking-widest disabled:opacity-50"
              >
                {actionBusy ? <Loader2 className="w-4 h-4 animate-spin" /> : <Trash2 className="w-4 h-4" />} Delete
              </button>
            )}
          </div>
        </div>
      )}

      {/* Lightbox — click a tile to enlarge */}
      {preview && (
        <div
          className="fixed inset-0 z-[200] bg-black/85 backdrop-blur-sm flex items-center justify-center p-6"
          onClick={() => { setPreview(null); setCaptureDetail(null); }}
        >
          <button
            className="absolute top-4 right-4 h-10 w-10 flex items-center justify-center border border-white/20 text-white hover:bg-white/10"
            onClick={() => { setPreview(null); setCaptureDetail(null); }}
            title="Close"
          >
            <X className="w-5 h-5" />
          </button>
          <div className="max-w-5xl w-full flex flex-col items-center gap-3" onClick={(e) => e.stopPropagation()}>
            {preview.source === 'capture' ? (
              <>
                {preview.captureType === 'frame' ? (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3 w-full">
                    <img src={withToken(preview.url)} alt="frame" className="max-h-[70vh] w-full object-contain border border-sky-500/20" />
                    <img src={withToken(annotatedUrl(preview.url))} alt="annotated" className="max-h-[70vh] w-full object-contain border border-sky-500/20" onError={(e) => { e.currentTarget.style.display = 'none'; }} />
                  </div>
                ) : (
                  <img src={withToken(preview.url)} alt="annotated" className="max-h-[80vh] w-auto object-contain border border-sky-500/20" />
                )}
                {captureDetail?.detection && (
                  <div className="w-full border border-sky-500/20 bg-[#030705]/90 p-4 text-xs font-black uppercase tracking-widest text-slate-200 space-y-1">
                    <div>Stream: <span className="text-sky-300">{captureDetail.stream}</span></div>
                    <div>Captured: <span className="text-sky-300">{captureDetail.captured_at}</span></div>
                    <div>Detections: <span className="text-sky-300">{captureDetail.detection.num_detections}</span> — {(captureDetail.detection.classes || []).join(', ') || 'none'}</div>
                    <div>Condition: pump_off={String(captureDetail.condition?.pump_off)} load_zero={String(captureDetail.condition?.load_zero)}</div>
                  </div>
                )}
              </>
            ) : preview.kind === 'detection' ? (
              <div className="w-full max-w-5xl border border-violet-500/20">
                <DetectionImage item={preview} />
              </div>
            ) : preview.kind === 'recording' ? (
              <video
                src={withToken(preview.url)}
                controls
                className="max-h-[80vh] w-auto max-w-full bg-black border border-red-500/20"
              />
            ) : (
              <img
                src={withToken(preview.url)}
                alt={preview.stream_name}
                className="max-h-[80vh] w-auto object-contain border border-emerald-500/20"
              />
            )}
            <div className="flex flex-wrap items-center justify-center gap-3 text-xs font-black uppercase tracking-widest text-slate-200">
              <span className={`inline-flex items-center gap-1 px-2 py-0.5 border ${
                preview.kind === 'recording'
                  ? 'border-red-500/30 text-red-400'
                  : preview.kind === 'detection' || preview.source === 'capture'
                    ? 'border-violet-500/30 text-violet-300'
                    : 'border-emerald-500/30 text-emerald-400'
              }`}>
                {preview.kind === 'recording' ? <Film className="w-3 h-3" /> : preview.kind === 'detection' || preview.source === 'capture' ? <Sparkles className="w-3 h-3" /> : <Camera className="w-3 h-3" />}
                {preview.source === 'capture' ? preview.captureType : preview.kind}
              </span>
              <span>{preview.stream_name}</span>
              <span className="text-slate-500">{formatTime(preview.created_at)}</span>
              {preview.kind === 'recording' && preview.duration ? (
                <span className="text-red-300">Duration {formatDuration(preview.duration)}</span>
              ) : null}
              {preview.kind === 'detection' && (
                <>
                  <span className="text-violet-300">{preview.model_name || preview.model_id}</span>
                  <span className="text-slate-500">{preview.num_detections} obj</span>
                  {typeof preview.confidence_avg === 'number' && (
                    <span className="text-slate-500">avg {(preview.confidence_avg * 100).toFixed(0)}%</span>
                  )}
                </>
              )}
              <button
                onClick={() => handleDownload(preview)}
                className="h-8 px-3 flex items-center gap-2 border border-emerald-500/20 text-emerald-400 hover:bg-emerald-500/10"
              >
                <Download className="w-4 h-4" /> Download
              </button>
              {manage && !preview.source && (
                <button
                  onClick={() => handleDelete(preview)}
                  disabled={busyId === preview.id}
                  className="h-8 px-3 flex items-center gap-2 border border-red-500/20 text-red-400 hover:bg-red-500/10 disabled:opacity-50"
                >
                  {busyId === preview.id ? <Loader2 className="w-4 h-4 animate-spin" /> : <Trash2 className="w-4 h-4" />} Delete
                </button>
              )}
            </div>
            {preview.kind === 'detection' && (
              <div className="w-full max-w-5xl">
                <DetectionSummary item={preview} />
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
