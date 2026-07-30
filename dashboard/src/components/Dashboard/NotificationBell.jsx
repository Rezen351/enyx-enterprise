import { useState, useRef, useEffect } from 'react';
import { Bell, BellOff, ShieldAlert, X } from 'lucide-react';
import { useNotification } from '../../context/useNotification';

function relativeTime(ts) {
  try {
    const diff = Date.now() - new Date(ts).getTime();
    if (Number.isNaN(diff)) return '';
    const s = Math.floor(diff / 1000);
    if (s < 60) return `${s}s ago`;
    const m = Math.floor(s / 60);
    if (m < 60) return `${m}m ago`;
    const h = Math.floor(m / 60);
    if (h < 24) return `${h}h ago`;
    const d = Math.floor(h / 24);
    return `${d}d ago`;
  } catch {
    return '';
  }
}

function severityDotClass(status = 'info') {
  switch (status) {
    case 'critical':
      return 'bg-red-500';
    case 'warning':
      return 'bg-amber-500';
    case 'success':
      return 'bg-emerald-500';
    default:
      return 'bg-slate-500';
  }
}

function severityTextClass(status = 'info') {
  switch (status) {
    case 'critical':
      return 'text-red-300 border-red-500/30 bg-red-500/10';
    case 'warning':
      return 'text-amber-300 border-amber-500/30 bg-amber-500/10';
    case 'success':
      return 'text-emerald-300 border-emerald-500/30 bg-emerald-500/10';
    default:
      return 'text-slate-300 border-slate-500/30 bg-slate-500/10';
  }
}

export default function NotificationBell() {
  const { notifications, unreadCount, clearUnread } = useNotification();
  const [open, setOpen] = useState(false);
  const ref = useRef(null);

  useEffect(() => {
    if (!open) return;
    const onDoc = (e) => {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false);
    };
    document.addEventListener('mousedown', onDoc);
    return () => document.removeEventListener('mousedown', onDoc);
  }, [open]);

  const toggle = () => {
    const next = !open;
    setOpen(next);
    if (next) clearUnread();
  };

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={toggle}
        className="relative h-10 w-10 flex items-center justify-center transition-all duration-300 border border-emerald-500/10 bg-slate-500/5 hover:bg-emerald-500/10 cursor-pointer"
        title="Notifications"
      >
        <Bell className="w-5 h-5 text-emerald-400" />
        {unreadCount > 0 && (
          <span className="absolute -top-1.5 -right-1.5 min-w-[18px] h-[18px] px-1 flex items-center justify-center rounded-full bg-red-500 text-[10px] font-black text-white border-2 border-[#030705]">
            {unreadCount > 99 ? '99+' : unreadCount}
          </span>
        )}
      </button>

      {open && (
        <div className="absolute right-0 mt-2 w-80 sm:w-96 z-50 border border-emerald-500/20 bg-[#030705]/95 backdrop-blur-xl shadow-2xl">
          <div className="flex items-center justify-between px-4 py-3 border-b border-emerald-500/15">
            <div className="flex items-center gap-2 text-emerald-400">
              <ShieldAlert className="w-4 h-4" />
              <span className="text-xs font-black uppercase tracking-widest">Notifications</span>
            </div>
            <button
              onClick={() => setOpen(false)}
              className="p-1 text-slate-500 hover:text-emerald-400 transition-colors cursor-pointer"
              title="Close"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          <div className="max-h-[60vh] overflow-y-auto">
            {notifications.length === 0 ? (
              <div className="flex flex-col items-center gap-2 py-12 text-slate-500 text-sm">
                <BellOff className="w-6 h-6" />
                No notifications yet.
              </div>
            ) : (
              notifications.map((n) => (
                <div
                  key={n.id}
                  className="px-4 py-3 border-b border-emerald-500/10 hover:bg-emerald-500/5"
                >
                  <div className="flex items-start gap-3">
                    <span className={`mt-1.5 w-2 h-2 shrink-0 rounded-full ${severityDotClass(n.status)}`} />
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center justify-between gap-2">
                        <span className={`inline-block px-2 py-0.5 text-[10px] font-black uppercase tracking-wide border ${severityTextClass(n.status)}`}>
                          {n.status}
                        </span>
                        <span className="text-[10px] text-slate-500 shrink-0">{relativeTime(n.timestamp)}</span>
                      </div>
                      <p className="mt-1.5 text-sm text-slate-200 break-words">{n.message}</p>
                      <p className="mt-1 text-[11px] text-slate-500">
                        {n.module_id ? `${n.module_id}` : 'Aeroponic System'}
                        {n.category ? ` · ${n.category}` : ''}
                      </p>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}
