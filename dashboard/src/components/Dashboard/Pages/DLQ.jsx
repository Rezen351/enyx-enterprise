import { useState, useEffect, useCallback } from 'react';
import {
  ScrollText,
  RefreshCw,
  Search,
  Loader2,
  AlertTriangle,
  ChevronLeft,
  ChevronRight,
  Filter,
} from 'lucide-react';
import PageHeader from './PageHeader';
import { listDLQMessages } from '../../../api/dlq';

const PAGE_SIZES = [25, 50, 100];

function canView() {
  try {
    const u = JSON.parse(sessionStorage.getItem('user') || 'null');
    const roles = Array.isArray(u?.roles) ? u.roles : [];
    return roles.includes('admin');
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

function prettyJSON(value) {
  if (!value) return '';
  try {
    return JSON.stringify(JSON.parse(value), null, 2);
  } catch {
    return value;
  }
}

function reasonBadgeClass(reason = '') {
  if (reason === 'MaxDeliverExceeded') return 'bg-red-500/15 text-red-300 border-red-500/30';
  return 'bg-slate-500/15 text-slate-300 border-slate-500/30';
}

export default function DLQ() {
  const [messages, setMessages] = useState([]);
  const [total, setTotal] = useState(0);
  const [limit, setLimit] = useState(50);
  const [offset, setOffset] = useState(0);
  const [sourceStream, setSourceStream] = useState('');
  const [traceId, setTraceId] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const res = await listDLQMessages({ sourceStream, traceId, limit, offset });
      const payload = res?.data ?? {};
      setMessages(Array.isArray(payload.messages) ? payload.messages : []);
      setTotal(typeof payload.total === 'number' ? payload.total : 0);
    } catch (err) {
      setError(err?.message || 'Failed to load DLQ messages');
      setMessages([]);
    } finally {
      setLoading(false);
    }
  }, [sourceStream, traceId, limit, offset]);

  useEffect(() => {
    load();
  }, [load]);

  const page = Math.floor(offset / limit) + 1;
  const totalPages = Math.max(1, Math.ceil(total / limit));
  const goPrev = () => setOffset((o) => Math.max(0, o - limit));
  const goNext = () => setOffset((o) => Math.min(Math.max(0, total - limit), o + limit));

  if (!canView()) {
    return (
      <div className="border border-red-500/20 bg-red-500/5 p-6 text-red-300">
        You do not have permission to view the dead letter queue.
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <PageHeader
        icon={ScrollText}
        title="Dead Letter Queue"
        subtitle="Failed JetStream messages captured after exceeding MaxDeliver retries."
      >
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
              value={sourceStream}
              onChange={(e) => { setSourceStream(e.target.value); setOffset(0); }}
              onKeyDown={(e) => { if (e.key === 'Enter') load(); }}
              placeholder="Filter by source stream"
              className="flex-1 bg-transparent outline-none text-sm text-white placeholder:text-slate-600"
            />
          </div>
          <div className="flex-1 flex items-center gap-2 px-3 h-10 bg-black/30 border border-emerald-500/20 focus-within:border-emerald-500/50">
            <Filter className="w-4 h-4 text-slate-500 shrink-0" />
            <input
              value={traceId}
              onChange={(e) => { setTraceId(e.target.value); setOffset(0); }}
              onKeyDown={(e) => { if (e.key === 'Enter') load(); }}
              placeholder="Filter by trace ID"
              className="flex-1 bg-transparent outline-none text-sm text-white placeholder:text-slate-600"
            />
          </div>
        </div>
      </div>

      {/* Error */}
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
                <th className="text-left px-4 py-3 whitespace-nowrap">Source Stream</th>
                <th className="text-left px-4 py-3 whitespace-nowrap">Consumer</th>
                <th className="text-left px-4 py-3 whitespace-nowrap">Subject</th>
                <th className="text-left px-4 py-3 whitespace-nowrap">Reason</th>
                <th className="text-left px-4 py-3">Payload</th>
                <th className="text-left px-4 py-3 whitespace-nowrap">Captured At</th>
              </tr>
            </thead>
            <tbody>
              {loading && messages.length === 0 && (
                <tr>
                  <td colSpan={6} className="px-4 py-12 text-center text-slate-500">
                    <Loader2 className="w-5 h-5 animate-spin inline mr-2" />
                    Loading DLQ messages…
                  </td>
                </tr>
              )}
              {!loading && messages.length === 0 && (
                <tr>
                  <td colSpan={6} className="px-4 py-12 text-center text-slate-500">
                    No DLQ messages found.
                  </td>
                </tr>
              )}
              {messages.map((m) => (
                <tr key={m.id} className="border-t border-emerald-500/10 hover:bg-emerald-500/5 align-top">
                  <td className="px-4 py-3 whitespace-nowrap text-slate-200 font-mono text-xs">
                    {m.source_stream}
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap text-slate-400 text-xs">
                    {m.source_consumer}
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap text-slate-300 text-xs">
                    {m.subject}
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap">
                    <span className={`inline-block px-2 py-1 text-[11px] font-black uppercase tracking-wide border ${reasonBadgeClass(m.reason)}`}>
                      {m.reason}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <pre className="text-xs text-slate-300 whitespace-pre-wrap break-all font-mono bg-black/30 border border-emerald-500/10 p-2 max-w-full overflow-x-auto">
                      {prettyJSON(m.payload)}
                    </pre>
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap text-slate-400 text-xs">
                    {formatTime(m.created_at)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Pagination */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-3">
        <div className="flex items-center gap-3 text-xs text-slate-400">
          <span>
            {total === 0 ? '0 messages' : `${offset + 1}–${Math.min(offset + limit, total)} of ${total}`}
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
    </div>
  );
}
