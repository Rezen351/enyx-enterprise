import { useState, useEffect, useCallback } from 'react';
import {
  Globe,
  Loader2,
  AlertTriangle,
  ChevronLeft,
  ChevronRight,
  Send,
  Settings2,
  ScrollText,
  Save,
  Mail,
} from 'lucide-react';
import PageHeader from './PageHeader';
import { webhookApi } from '../../../api/webhook';

const PAGE_SIZES = [25, 50, 100];

function isAdmin() {
  try {
    const u = JSON.parse(sessionStorage.getItem('user') || 'null');
    const roles = Array.isArray(u?.roles) ? u.roles : [];
    return roles.includes('admin');
  } catch {
    return false;
  }
}

function fmtTime(d) {
  try {
    return new Date(d).toLocaleString();
  } catch {
    return '';
  }
}

function statusBadge(status = '') {
  switch ((status || '').toLowerCase()) {
    case 'sent':
      return 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30';
    case 'queued':
      return 'bg-sky-500/15 text-sky-300 border-sky-500/30';
    case 'retrying':
      return 'bg-amber-500/15 text-amber-300 border-amber-500/30';
    case 'failed':
      return 'bg-red-500/15 text-red-300 border-red-500/30';
    default:
      return 'bg-slate-500/15 text-slate-300 border-slate-500/30';
  }
}

export default function Webhook() {
  const [tab, setTab] = useState('settings');
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const [settings, setSettings] = useState({
    telegram: { enabled: false, target: '', secret: '' },
    email: { enabled: false, target: '', secret: '' },
    webhook: { enabled: false, target: '', secret: '' },
  });

  const [logs, setLogs] = useState([]);
  const [total, setTotal] = useState(0);
  const [limit, setLimit] = useState(50);
  const [offset, setOffset] = useState(0);
  const [logFilter, setLogFilter] = useState({ channel: '', status: '' });

  const [testChannel, setTestChannel] = useState('');

  const loadSettings = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const res = await Promise.race([
        webhookApi.getSettings(),
        new Promise((_, reject) => setTimeout(() => reject(new Error('Timeout loading webhook settings')), 5000))
      ]);
      if (res) {
        const payload = res.data ?? res;
        setSettings((prev) => ({
          telegram: { ...prev.telegram, ...(payload.telegram || {}) },
          email: { ...prev.email, ...(payload.email || {}) },
          webhook: { ...prev.webhook, ...(payload.webhook || {}) },
        }));
      }
    } catch (err) {
      setError(err?.message || 'Failed to load webhook settings');
    } finally {
      setLoading(false);
    }
  }, []);

  const loadLogs = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const params = { limit, offset };
      if (logFilter.channel) params.channel = logFilter.channel;
      if (logFilter.status) params.status = logFilter.status;
      const res = await Promise.race([
        webhookApi.listLogs(params),
        new Promise((_, reject) => setTimeout(() => reject(new Error('Timeout loading webhook logs')), 5000))
      ]);
      const payload = res?.data ?? res ?? {};
      setLogs(Array.isArray(payload.logs) ? payload.logs : []);
      setTotal(typeof payload.total === 'number' ? payload.total : 0);
    } catch (err) {
      setError(err?.message || 'Failed to load webhook logs');
      setLogs([]);
    } finally {
      setLoading(false);
    }
  }, [limit, offset, logFilter]);

  useEffect(() => {
    if (!isAdmin()) return;
    if (tab === 'settings') loadSettings();
    if (tab === 'logs') loadLogs();
  }, [tab, loadSettings, loadLogs]);

  if (!isAdmin()) {
    return (
      <div className="border border-red-500/20 bg-red-500/5 p-6 text-red-300">
        You do not have permission to manage webhooks.
      </div>
    );
  }

  const saveSettings = async () => {
    setSaving(true);
    setError('');
    setSuccess('');
    try {
      await webhookApi.updateSettings(settings);
      setSuccess('Webhook settings saved successfully.');
    } catch (err) {
      setError(err?.message || 'Failed to save webhook settings');
    } finally {
      setSaving(false);
    }
  };

  const runTest = async () => {
    if (testChannel == null) return;
    setTesting(true);
    setError('');
    setSuccess('');
    try {
      const res = await webhookApi.testDelivery({ channel: testChannel || undefined });
      setSuccess(res?.message || `Test delivery queued for ${testChannel || 'all channels'}.`);
    } catch (err) {
      setError(err?.message || 'Failed to enqueue test delivery');
    } finally {
      setTesting(false);
    }
  };

  const page = Math.floor(offset / limit) + 1;
  const totalPages = Math.max(1, Math.ceil(total / limit));
  const goPrev = () => setOffset((o) => Math.max(0, o - limit));
  const goNext = () => setOffset((o) => Math.min(Math.max(0, total - limit), o + limit));

  const updateChannel = (channel, field, value) => {
    setSettings((s) => ({
      ...s,
      [channel]: { ...s[channel], [field]: value },
    }));
  };

  return (
    <div className="space-y-4">
      <PageHeader
        icon={Globe}
        title="Webhooks"
        subtitle="Configure external delivery channels and inspect dispatch logs."
      >
        {tab === 'settings' && (
          <button
            onClick={saveSettings}
            disabled={saving || loading}
            className="flex items-center justify-center gap-2 px-4 h-10 bg-emerald-500 text-black font-black text-xs uppercase tracking-widest hover:bg-emerald-400 transition-all active:scale-95 disabled:opacity-60 cursor-pointer"
          >
            {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
            Save Settings
          </button>
        )}
      </PageHeader>

      {error && (
        <div className="border border-red-500/20 bg-red-500/5 p-4 text-red-300 text-xs font-black uppercase tracking-widest flex items-center gap-2">
          <AlertTriangle className="w-4 h-4" />
          {error}
        </div>
      )}

      {success && (
        <div className="border border-emerald-500/20 bg-emerald-500/5 p-4 text-emerald-300 text-xs font-black uppercase tracking-widest">
          {success}
        </div>
      )}

      {/* Tabs */}
      <div className="flex items-center gap-1 border-b border-emerald-500/15">
        {[
          { id: 'settings', label: 'Settings', icon: Settings2 },
          { id: 'logs', label: 'Delivery Logs', icon: ScrollText },
          { id: 'test', label: 'Test', icon: Send },
        ].map((t) => {
          const active = tab === t.id;
          return (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
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

      {tab === 'settings' && (
        <div className="border border-emerald-500/10 bg-[#030705] p-4 md:p-6 space-y-6">
          {loading ? (
            <div className="flex items-center gap-2 text-slate-400 text-xs">
              <Loader2 className="w-4 h-4 animate-spin" /> Loading settings...
            </div>
          ) : (
            <>
              {/* Telegram */}
              <div className="space-y-3">
                <div className="flex items-center gap-2 text-xs font-black uppercase tracking-widest text-sky-300">
                  <Send className="w-4 h-4" />
                  Telegram
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                  <label className="flex items-center gap-3 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={settings.telegram?.enabled || false}
                      onChange={(e) => updateChannel('telegram', 'enabled', e.target.checked)}
                      className="accent-emerald-500 w-4 h-4"
                    />
                    <span className="text-xs font-black uppercase tracking-widest text-slate-300">Enabled</span>
                  </label>
                  <label className="space-y-1">
                    <span className="text-[10px] font-black uppercase tracking-widest text-slate-500">Chat ID</span>
                    <input
                      value={settings.telegram?.target || ''}
                      onChange={(e) => updateChannel('telegram', 'target', e.target.value)}
                      placeholder="123456789"
                      className="w-full h-10 px-3 bg-slate-900/80 border border-emerald-500/20 text-emerald-50 text-xs placeholder-slate-600 focus:outline-none focus:border-emerald-500/60"
                    />
                  </label>
                  <label className="space-y-1">
                    <span className="text-[10px] font-black uppercase tracking-widest text-slate-500">Bot Token</span>
                    <input
                      type="password"
                      value={settings.telegram?.secret || ''}
                      onChange={(e) => updateChannel('telegram', 'secret', e.target.value)}
                      placeholder="encrypted / plain"
                      className="w-full h-10 px-3 bg-slate-900/80 border border-emerald-500/20 text-emerald-50 text-xs placeholder-slate-600 focus:outline-none focus:border-emerald-500/60"
                    />
                  </label>
                </div>
              </div>

              {/* Email */}
              <div className="space-y-3">
                <div className="flex items-center gap-2 text-xs font-black uppercase tracking-widest text-amber-300">
                  <Mail className="w-4 h-4" />
                  Email
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                  <label className="flex items-center gap-3 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={settings.email?.enabled || false}
                      onChange={(e) => updateChannel('email', 'enabled', e.target.checked)}
                      className="accent-emerald-500 w-4 h-4"
                    />
                    <span className="text-xs font-black uppercase tracking-widest text-slate-300">Enabled</span>
                  </label>
                  <label className="space-y-1">
                    <span className="text-[10px] font-black uppercase tracking-widest text-slate-500">Recipient</span>
                    <input
                      value={settings.email?.target || ''}
                      onChange={(e) => updateChannel('email', 'target', e.target.value)}
                      placeholder="admin@example.com"
                      className="w-full h-10 px-3 bg-slate-900/80 border border-emerald-500/20 text-emerald-50 text-xs placeholder-slate-600 focus:outline-none focus:border-emerald-500/60"
                    />
                  </label>
                  <label className="space-y-1">
                    <span className="text-[10px] font-black uppercase tracking-widest text-slate-500">SMTP Password</span>
                    <input
                      type="password"
                      value={settings.email?.secret || ''}
                      onChange={(e) => updateChannel('email', 'secret', e.target.value)}
                      placeholder="encrypted / plain"
                      className="w-full h-10 px-3 bg-slate-900/80 border border-emerald-500/20 text-emerald-50 text-xs placeholder-slate-600 focus:outline-none focus:border-emerald-500/60"
                    />
                  </label>
                </div>
              </div>
            </>
          )}
        </div>
      )}

      {tab === 'logs' && (
        <div className="space-y-4">
          <div className="border border-emerald-500/10 bg-[#030705] p-4 md:p-6 space-y-4">
            <div className="flex items-center gap-2 text-xs font-black uppercase tracking-widest text-slate-400">
              <ScrollText className="w-4 h-4" />
              Filters
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              <label className="space-y-1">
                <span className="text-[10px] font-black uppercase tracking-widest text-slate-500">Channel</span>
                <select
                  value={logFilter.channel}
                  onChange={(e) => { setLogFilter((f) => ({ ...f, channel: e.target.value })); setOffset(0); }}
                  className="w-full h-10 px-3 bg-slate-900/80 border border-emerald-500/20 text-emerald-50 text-xs focus:outline-none focus:border-emerald-500/60"
                >
                  <option value="">All</option>
                  <option value="telegram">Telegram</option>
                  <option value="email">Email</option>
                </select>
              </label>
              <label className="space-y-1">
                <span className="text-[10px] font-black uppercase tracking-widest text-slate-500">Status</span>
                <select
                  value={logFilter.status}
                  onChange={(e) => { setLogFilter((f) => ({ ...f, status: e.target.value })); setOffset(0); }}
                  className="w-full h-10 px-3 bg-slate-900/80 border border-emerald-500/20 text-emerald-50 text-xs focus:outline-none focus:border-emerald-500/60"
                >
                  <option value="">All</option>
                  <option value="queued">Queued</option>
                  <option value="retrying">Retrying</option>
                  <option value="sent">Sent</option>
                  <option value="failed">Failed</option>
                </select>
              </label>
              <label className="space-y-1">
                <span className="text-[10px] font-black uppercase tracking-widest text-slate-500">Limit</span>
                <select
                  value={limit}
                  onChange={(e) => { setLimit(Number(e.target.value)); setOffset(0); }}
                  className="w-full h-10 px-3 bg-slate-900/80 border border-emerald-500/20 text-emerald-50 text-xs focus:outline-none focus:border-emerald-500/60"
                >
                  {PAGE_SIZES.map((s) => (
                    <option key={s} value={s}>{s}</option>
                  ))}
                </select>
              </label>
            </div>
          </div>

          {loading ? (
            <div className="flex items-center justify-center gap-2 text-slate-400 text-xs py-12">
              <Loader2 className="w-4 h-4 animate-spin" /> Loading logs...
            </div>
          ) : logs.length > 0 ? (
            <div className="border border-emerald-500/10 bg-[#030705] overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead>
                    <tr className="border-b border-emerald-500/15 bg-emerald-500/5">
                      <th className="px-4 py-3 text-[10px] font-black uppercase tracking-widest text-slate-400">#</th>
                      <th className="px-4 py-3 text-[10px] font-black uppercase tracking-widest text-slate-400">Channel</th>
                      <th className="px-4 py-3 text-[10px] font-black uppercase tracking-widest text-slate-400">Target</th>
                      <th className="px-4 py-3 text-[10px] font-black uppercase tracking-widest text-slate-400">Subject</th>
                      <th className="px-4 py-3 text-[10px] font-black uppercase tracking-widest text-slate-400">Status</th>
                      <th className="px-4 py-3 text-[10px] font-black uppercase tracking-widest text-slate-400">Attempts</th>
                      <th className="px-4 py-3 text-[10px] font-black uppercase tracking-widest text-slate-400">Error</th>
                      <th className="px-4 py-3 text-[10px] font-black uppercase tracking-widest text-slate-400">Created</th>
                    </tr>
                  </thead>
                  <tbody>
                    {logs.map((row, idx) => (
                      <tr key={row.id || idx} className="border-b border-emerald-500/10 hover:bg-emerald-500/5 transition-colors">
                        <td className="px-4 py-2.5 text-slate-500 tabular-nums">{offset + idx + 1}</td>
                        <td className="px-4 py-2.5 text-slate-300 capitalize">{row.channel}</td>
                        <td className="px-4 py-2.5 text-slate-300 max-w-[200px] truncate" title={row.target}>{row.target}</td>
                        <td className="px-4 py-2.5 text-slate-300 max-w-[260px] truncate" title={row.subject}>{row.subject}</td>
                        <td className="px-4 py-2.5">
                          <span className={`px-2 py-0.5 border text-[10px] font-black uppercase tracking-widest ${statusBadge(row.status)}`}>
                            {row.status}
                          </span>
                        </td>
                        <td className="px-4 py-2.5 text-slate-300 tabular-nums">{row.attempts}</td>
                        <td className="px-4 py-2.5 text-red-300 max-w-[220px] truncate" title={row.error}>{row.error}</td>
                        <td className="px-4 py-2.5 text-slate-400 tabular-nums">{fmtTime(row.created_at)}</td>
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
                {loading ? 'Loading logs...' : 'No delivery logs found.'}
              </div>
            </div>
          )}
        </div>
      )}

      {tab === 'test' && (
        <div className="border border-emerald-500/10 bg-[#030705] p-4 md:p-6 space-y-4">
          <div className="text-xs font-black uppercase tracking-widest text-slate-400">
            Send a test delivery to verify the channel configuration.
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <label className="space-y-1">
              <span className="text-[10px] font-black uppercase tracking-widest text-slate-500">Channel</span>
              <select
                value={testChannel}
                onChange={(e) => setTestChannel(e.target.value)}
                className="w-full h-10 px-3 bg-slate-900/80 border border-emerald-500/20 text-emerald-50 text-xs focus:outline-none focus:border-emerald-500/60"
              >
                <option value="">All channels</option>
                <option value="telegram">Telegram</option>
                <option value="email">Email</option>
              </select>
            </label>
            <div className="flex items-end">
              <button
                onClick={runTest}
                disabled={testing || loading}
                className="flex items-center justify-center gap-2 px-4 h-10 bg-emerald-500 text-black font-black text-xs uppercase tracking-widest hover:bg-emerald-400 transition-all active:scale-95 disabled:opacity-60 cursor-pointer"
              >
                {testing ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
                Send Test
              </button>
            </div>
          </div>
          <div className="text-[11px] text-slate-500">
            Test delivery enqueues a synthetic event through the same dispatch pipeline as live alerts, including retry/backoff behavior.
          </div>
        </div>
      )}
    </div>
  );
}
