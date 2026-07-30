import { useEffect, useRef, useState, useCallback } from 'react';
import { createPortal } from 'react-dom';
import { Activity, X, Radio, Trash2, AlertTriangle, Wifi, WifiOff } from 'lucide-react';
import { getToken, getWsUrl } from '../../api/client';

function safeJson(raw) {
  try {
    return JSON.parse(raw);
  } catch {
    return raw;
  }
}

function prettyPrint(value) {
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}

function highlight(jsonStr) {
  return jsonStr.split('\n').map((line, i) => {
    let out = line
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');
    out = out.replace(/("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*")(\s*:)/g, '<span class="text-emerald-400 font-bold">$1</span>$3');
    out = out.replace(/: \s*("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*")/g, ': <span class="text-amber-300">$1</span>');
    out = out.replace(/: \s*(true|false|null|\d+(\.\d+)?)/g, (m, p1) => {
      const color = p1 === 'null' ? 'text-gray-500' : p1 === 'true' || p1 === 'false' ? 'text-violet-400 font-semibold' : 'text-cyan-400';
      return `: <span class="${color}">${p1}</span>`;
    });
    return (
      <div key={i} className="font-mono text-[11px] sm:text-xs leading-relaxed whitespace-pre" dangerouslySetInnerHTML={{ __html: out }} />
    );
  });
}

function NodeMonitorModal({ node, onClose }) {
  const [messages, setMessages] = useState([]);
  const [connState, setConnState] = useState('connecting'); // connecting | open | closed | error
  const [error, setError] = useState('');
  const wsRef = useRef(null);
  const scrollRef = useRef(null);
  const listRef = useRef([]);

  const nodeId = node.node_id;

  const closeWs = useCallback(() => {
    if (wsRef.current) {
      try { wsRef.current.onclose = null; wsRef.current.close(); } catch { /* ignore */ }
      wsRef.current = null;
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    const wsUrl = getWsUrl(`/ws/nodes/${encodeURIComponent(nodeId)}/live?token=${encodeURIComponent(getToken() || '')}`);
    let ws;
    try {
      ws = new WebSocket(wsUrl);
    } catch {
      setConnState('error');
      setError('Failed to open live monitor connection.');
      return;
    }
    wsRef.current = ws;

    ws.onopen = () => { if (!cancelled) setConnState('open'); };
    ws.onerror = () => { if (!cancelled) { setConnState('error'); setError('Connection lost. The device may be offline or the WebSocket may be unavailable.'); } };
    ws.onclose = () => { if (!cancelled) setConnState('closed'); };
    ws.onmessage = (event) => {
      if (cancelled) return;
      try {
        const data = JSON.parse(event.data);
        const payload = typeof data.payload === 'string' ? safeJson(data.payload) : data.payload;
        const entry = {
          id: `${data.ts}-${Math.random().toString(36).slice(2, 7)}`,
          topic: data.topic,
          payload,
          ts: data.ts,
        };
        listRef.current = [...listRef.current, entry].slice(-200);
        setMessages(listRef.current);
      } catch (err) {
        console.warn('monitor: bad frame', err);
      }
    };

    return () => {
      cancelled = true;
      closeWs();
    };
  }, [nodeId, closeWs]);

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  return createPortal(
    <div className="fixed inset-0 z-[100] flex flex-col bg-[#030705] animate-fadeIn">
        {/* Header */}
        <div className="p-4 border-b border-white/5 flex items-center justify-between gap-3 bg-[#050b08]/40">
          <div className="flex items-center gap-2 min-w-0">
            <Activity className="w-5 h-5 text-emerald-400 shrink-0" />
            <div className="min-w-0">
              <h3 className="text-sm sm:text-base font-black uppercase tracking-wider text-white truncate">
                Live MQTT — <span className="text-emerald-400 font-mono">{nodeId}</span>
              </h3>
              <p className="text-[10px] text-slate-400 font-black uppercase tracking-wider mt-0.5 truncate">
                All payloads from the device (telemetry / actuator / diagnostics / alert / status)
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            <span className={`flex items-center gap-1.5 px-2 py-1 text-[10px] font-black uppercase tracking-wider border ${
              connState === 'open'
                ? 'text-emerald-400 border-emerald-500/30 bg-emerald-500/10'
                : connState === 'error' || connState === 'closed'
                  ? 'text-red-400 border-red-500/30 bg-red-500/10'
                  : 'text-amber-400 border-amber-500/30 bg-amber-500/10'
            }`}>
              {connState === 'open' ? <Wifi className="w-3 h-3" /> : <WifiOff className="w-3 h-3" />}
              {connState}
            </span>
            <button
              onClick={onClose}
              className="p-1.5 bg-slate-900 border border-slate-700 text-slate-400 hover:text-white hover:bg-slate-800 transition-colors cursor-pointer"
              title="Close"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Body */}
        <div ref={scrollRef} className="flex-1 overflow-y-auto p-4 space-y-3 bg-[#040806]">
          {connState !== 'open' && messages.length === 0 && (
            <div className="h-full flex flex-col items-center justify-center text-center gap-3 text-slate-500">
              {connState === 'error' || connState === 'closed' ? (
                <>
                  <AlertTriangle className="w-8 h-8 text-red-400/70" />
                  <p className="text-xs font-bold uppercase tracking-wider">{error || 'Connection closed'}</p>
                </>
              ) : (
                <>
                  <div className="w-10 h-10 border-2 border-emerald-500 border-t-transparent rounded-full animate-spin" />
                  <p className="text-[11px] font-bold uppercase tracking-wider animate-pulse">Waiting for payload from device...</p>
                </>
              )}
            </div>
          )}

          {messages.length === 0 && connState === 'open' && (
            <div className="py-16 flex flex-col items-center justify-center text-slate-500 gap-2">
              <Radio className="w-6 h-6 text-emerald-400/70 animate-pulse" />
              <p className="text-[11px] font-bold uppercase tracking-wider">Listening for live MQTT payload...</p>
            </div>
          )}

          {messages.map((m) => (
            <div key={m.id} className="border border-slate-800 bg-black/40 hover:border-emerald-500/30 transition-colors">
              <div className="flex items-center justify-between gap-2 px-3 py-1.5 border-b border-slate-800 bg-slate-950/60">
                <span className="font-mono text-[11px] text-emerald-400 truncate">{m.topic}</span>
                <span className="text-[10px] text-slate-500 font-black shrink-0">
                  {m.ts ? new Date(m.ts).toLocaleTimeString() : ''}
                </span>
              </div>
              <div className="p-3 overflow-x-auto text-slate-300">
                {highlight(prettyPrint(m.payload))}
              </div>
            </div>
          ))}
        </div>

        {/* Footer */}
        <div className="p-3 border-t border-white/5 flex items-center justify-between bg-[#050b08]/40">
          <span className="text-[10px] text-slate-500 font-black uppercase tracking-wider">
            {messages.length} payload(s) diterima
          </span>
          <button
            onClick={() => { listRef.current = []; setMessages([]); }}
            className="flex items-center gap-1.5 px-3 py-1.5 text-[10px] font-black uppercase tracking-wider text-slate-400 border border-slate-700 hover:text-red-400 hover:border-red-500/40 transition-colors cursor-pointer"
          >
            <Trash2 className="w-3 h-3" /> Clear
          </button>
        </div>
    </div>
  , document.body
  );
}

export default NodeMonitorModal;
