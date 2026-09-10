import { useState, useEffect, useCallback } from 'react';
import { Network, Trash2, ArrowLeft, AlertTriangle, Radio, RefreshCw, Wifi, WifiOff, Check, Settings } from 'lucide-react';
import { moduleApi } from '../../../api/module';

function timeAgo(iso, nowMs) {
  if (!iso) return 'Never';
  const d = new Date(iso);
  const s = Math.floor((nowMs - d.getTime()) / 1000);
  if (s < 60) return `${s}s ago`;
  if (s < 3600) return `${Math.floor(s / 60)}m ago`;
  if (s < 86400) return `${Math.floor(s / 3600)}h ago`;
  return d.toLocaleString();
}

function StatusPill({ status }) {
  const online = status === 'online';
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-black uppercase tracking-wider ${
      online ? 'bg-emerald-500/20 text-emerald-400' : 'bg-slate-800 text-slate-400'
    }`}>
      {online ? <Wifi className="w-3 h-3" /> : <WifiOff className="w-3 h-3" />}
      {status || 'unknown'}
    </span>
  );
}

function NodeManagement({ selectedModule, onBack, onOpenNodeConfig }) {
  const [pairedNodes, setPairedNodes] = useState([]);
  const [discoveredNodes, setDiscoveredNodes] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [busyId, setBusyId] = useState(null);
  const [error, setError] = useState('');
  const [nowMs, setNowMs] = useState(() => Date.now());

  const isNodeLive = (node, nowMs) => {
    if (!node?.last_seen_at) return false;
    const diff = nowMs - new Date(node.last_seen_at).getTime();
    return diff < 10000;
  };

  // Staleness threshold (ms) for deriving a node's *effective* status from its
  // last_seen_at. The persisted status can lag (it is only flipped to "offline"
  // by the backend sweep every ~30s), so the UI downgrades a stale "online"
  // node to "offline" immediately instead of showing it as active when no
  // device is actually reporting. Mirrors the backend NODE_OFFLINE_AFTER_SEC.
  const OFFLINE_AFTER_MS = 120000;
  const effectiveStatus = (node, nowMs) => {
    const status = node?.status || 'unknown';
    if (status === 'online' && node?.last_seen_at) {
      const diff = nowMs - new Date(node.last_seen_at).getTime();
      if (diff > OFFLINE_AFTER_MS) return 'offline';
    }
    return status;
  };

  const fetchData = useCallback(async () => {
    try {
      const [pairedRes, discoveredRes] = await Promise.all([
        moduleApi.listNodes({ module_id: selectedModule.id, paired: true }),
        moduleApi.listDiscovered(),
      ]);
      setPairedNodes(pairedRes?.nodes || []);
      setDiscoveredNodes(discoveredRes?.nodes || []);
      setError('');
    } catch (err) {
      setError(err.message || 'Failed to load nodes');
    } finally {
      setIsLoading(false);
    }
  }, [selectedModule.id]);

  // Tick a "now" clock once per second so live-status / time-ago reflect the
  // current time without calling Date.now() during render (keeps render pure).
  useEffect(() => {
    const t = setInterval(() => setNowMs(Date.now()), 1000);
    return () => clearInterval(t);
  }, []);

  // Initial load + poll every 4s so newly-discovered devices appear automatically.
  useEffect(() => {
    fetchData();
    const t = setInterval(fetchData, 4000);
    return () => clearInterval(t);
  }, [fetchData]);

  const handlePair = async (node) => {
    setBusyId(node.node_id);
    setError('');
    try {
      await moduleApi.pairNode(node.node_id, { module_id: selectedModule.id, name: node.name || node.node_id });
      await fetchData();
    } catch (err) {
      setError(err.message || 'Failed to pair node');
    } finally {
      setBusyId(null);
    }
  };

  const handleUnpair = async (node) => {
    if (!window.confirm(`Unpair node ${node.node_id} from this module?`)) return;
    setBusyId(node.node_id);
    setError('');
    try {
      await moduleApi.unpairNode(node.node_id);
      await fetchData();
    } catch (err) {
      setError(err.message || 'Failed to unpair node');
    } finally {
      setBusyId(null);
    }
  };

  const handleDelete = async (node) => {
    if (!window.confirm(`Delete node record ${node.node_id}? The node will reappear if the device sends a discovery message.`)) return;
    setBusyId(node.node_id);
    setError('');
    try {
      await moduleApi.deleteNode(node.node_id);
      await fetchData();
    } catch (err) {
      setError(err.message || 'Failed to delete node');
    } finally {
      setBusyId(null);
    }
  };

  return (
    <div className="border border-emerald-500/15 bg-[#030705]/80 backdrop-blur-md animate-fadeIn">
      {/* Header */}
      <div className="p-3 sm:p-4 border-b border-white/5 flex flex-col xl:flex-row xl:items-center justify-between gap-3">
        <div className="flex items-center gap-3 sm:gap-4 w-full">
          <div className="p-3 sm:p-4 bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 shrink-0">
            <Network className="w-8 h-8 sm:w-10 sm:h-10" />
          </div>
          <div className="min-w-0 flex-1">
            <h2 className="text-xl sm:text-2xl font-black font-display text-white tracking-wide uppercase truncate">
              Nodes: <span className="text-emerald-400">{selectedModule.name}</span>
            </h2>
            <p className="hidden sm:block text-[11px] text-slate-400 mt-0.5">Pair discovered devices to this module.</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={onBack}
            className="h-10 sm:h-11 px-3 sm:px-4 text-xs font-bold text-slate-400 border border-slate-700 hover:text-white hover:border-slate-500 transition-colors cursor-pointer uppercase tracking-wider flex items-center gap-2"
          >
            <ArrowLeft className="w-4 h-4" />
            <span className="hidden sm:inline">Back</span>
          </button>
          <button
            onClick={fetchData}
            className="h-10 sm:h-11 px-3 sm:px-4 text-xs font-bold bg-slate-800 border border-slate-700 text-slate-300 hover:text-emerald-400 hover:border-emerald-500/40 transition-colors uppercase tracking-wider cursor-pointer flex items-center gap-2"
            title="Refresh"
          >
            <RefreshCw className="w-4 h-4" />
            <span className="hidden sm:inline">Refresh</span>
          </button>
        </div>
      </div>

      <div className="p-4 sm:p-6">
        {error && (
          <div className="mb-4 p-3 bg-red-500/10 border border-red-500/20 text-red-400 text-xs sm:text-sm font-black flex items-center gap-2">
            <AlertTriangle className="w-4 h-4" />
            {error}
          </div>
        )}

        {/* SECTION: AUTO-DISCOVERY (unpaired devices) */}
        <div className="mb-6 p-4 border border-amber-500/25 bg-amber-500/5">
          <div className="flex items-center gap-2 mb-3">
            <Radio className="w-4 h-4 text-amber-500 animate-pulse" />
            <span className="text-xs sm:text-sm font-black text-amber-400 uppercase tracking-widest">
              Auto-Discovery — Unpaired ({discoveredNodes.length})
            </span>
          </div>

          {discoveredNodes.length === 0 ? (
            <p className="text-[11px] sm:text-xs text-slate-500 italic p-4 border border-dashed border-amber-500/20 text-center">
              No new devices. Power on ESP32 or send discovery.
            </p>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {discoveredNodes.map(node => (
                <div key={node.node_id} className="p-3.5 bg-slate-950/70 border border-amber-500/20 hover:border-amber-500/50 flex flex-col justify-between transition-all">
                  <div>
                    <div className="flex justify-between items-center mb-2">
                      <span className="text-[11px] font-black uppercase text-slate-400 tracking-wider">Found</span>
                      <StatusPill status={effectiveStatus(node, nowMs)} />
                    </div>
                    <div className="space-y-1 text-xs font-black text-slate-400 font-mono">
                      <div className="flex justify-between gap-2">
                        <span>Node ID:</span>
                        <span className="text-white truncate">{node.node_id}</span>
                      </div>
                      <div className="flex justify-between gap-2">
                        <span>MAC:</span>
                        <span className="text-white truncate">{node.mac || '-'}</span>
                      </div>
                      <div className="flex justify-between gap-2">
                        <span>IP:</span>
                        <span className="text-white">{node.ip || '—'}</span>
                      </div>
                      <div className="flex justify-between gap-2">
                        <span>FW:</span>
                        <span className="text-white">{node.fw_version || '-'}</span>
                      </div>
                    </div>
                  </div>
                  <button
                    type="button"
                    disabled={busyId === node.node_id}
                    onClick={() => handlePair(node)}
                    className="mt-3 w-full h-11 text-xs font-black uppercase tracking-wider text-black bg-amber-500 hover:bg-amber-400 disabled:opacity-50 rounded transition-all cursor-pointer flex items-center justify-center gap-1.5"
                  >
                    <Check className="w-4 h-4" />
                    {busyId === node.node_id ? 'Pairing...' : 'Pair'}
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* SECTION: PAIRED NODES */}
        <h4 className="text-xs sm:text-sm font-black text-emerald-400 uppercase tracking-widest mb-4">
          Paired ({pairedNodes.length})
        </h4>
        {isLoading ? (
          <div className="py-8 text-center text-slate-500 text-sm">Loading nodes...</div>
        ) : pairedNodes.length === 0 ? (
          <div className="py-8 text-center text-slate-500 text-sm bg-slate-900/50 border border-slate-800">
            No paired nodes yet.
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {pairedNodes.map(node => (
              <div key={node.node_id} className="p-4 bg-slate-900/80 border border-slate-700 hover:border-emerald-500/50 transition-all duration-200 group relative">
                <div className="flex justify-between items-center mb-3.5">
                  <div className="flex items-center gap-2 min-w-0">
                    <Network className="w-5 h-5 text-emerald-400 shrink-0" />
                    <span className="text-sm font-black uppercase text-white truncate">{node.name || node.node_id}</span>
                  </div>
                  <StatusPill status={node.status} />
                </div>

                <div className="space-y-1.5 text-xs sm:text-sm text-slate-400 font-mono">
                  <div className="flex justify-between gap-2">
                    <span className="text-slate-500 font-black">Node ID</span>
                    <span className="text-white font-black truncate">{node.node_id}</span>
                  </div>
                  <div className="flex justify-between gap-2">
                    <span className="text-slate-500 font-black">IP</span>
                    <span className="text-white font-black">{node.ip || '—'}</span>
                  </div>
                  <div className="flex justify-between gap-2">
                    <span className="text-slate-500 font-black">FW</span>
                    <span className="text-white font-black">{node.fw_version || '-'}</span>
                  </div>
                  <div className="flex justify-between gap-2">
                    <span className="text-slate-500 font-black">Last Seen</span>
                    <span className="text-white font-black flex items-center gap-1.5">
                      {isNodeLive(node, nowMs) && <span className="relative flex h-2 w-2">
                        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                        <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
                      </span>}
                      {timeAgo(node.last_seen_at, nowMs)}
                    </span>
                  </div>
                </div>

                <div className="mt-3 pt-2.5 border-t border-white/5 flex flex-wrap justify-end gap-2">
                  <button
                    onClick={() => onOpenNodeConfig && onOpenNodeConfig(node)}
                    disabled={busyId === node.node_id}
                    className="flex items-center gap-1 px-2 py-1.5 bg-slate-800 border border-slate-700 hover:border-emerald-500/50 hover:text-emerald-400 text-slate-400 text-[10px] font-black uppercase tracking-wider transition-colors cursor-pointer disabled:opacity-50"
                  >
                    <Settings className="w-3 h-3" /> Configure
                  </button>
                  <button
                    onClick={() => handleUnpair(node)}
                    disabled={busyId === node.node_id}
                    className="px-2 py-1.5 bg-slate-800 border border-slate-700 hover:border-amber-500/50 hover:text-amber-400 text-slate-400 text-[10px] font-black uppercase tracking-wider transition-colors cursor-pointer disabled:opacity-50"
                  >
                    Unpair
                  </button>
                  <button
                    onClick={() => handleDelete(node)}
                    disabled={busyId === node.node_id}
                    className="p-1.5 bg-slate-800 border border-slate-700 hover:border-red-500/50 hover:text-red-400 text-slate-400 transition-colors cursor-pointer disabled:opacity-50"
                    title="Delete node record"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default NodeManagement;
