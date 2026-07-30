import { createContext, useState, useEffect, useCallback } from 'react';
import { getWsUrl } from '../api/client';

const NotificationContext = createContext();

const MAX_NOTIFICATIONS = 20;

// Categories that count as "actionable" (not just informational pings)
const ACTIONABLE_CATEGORIES = ['alert', 'security', 'vision', 'system'];

// Normalize *any* alert-shaped websocket payload into the internal notification
// object. Handles three producers:
//  - legacy wrapped envelope: { type:'alert', data:{ status, category, timestamp, system, message, module_id } }
//  - Alert Service `system.status`: { type:'alert', level, node_id, metric, value, message, status:'triggered'|'resolved', ts }
//  - raw `alert.triggered`/`alert.resolved`: { severity, node_id, metric, value, message, status:'active'|'resolved', triggered_at }
// Returns null when the payload is not an alert.
function normalizeAlert(parsed) {
  // Legacy wrapped envelope (data.* present)
  if (parsed.data) {
    const d = parsed.data;
    return {
      id: Date.now() + Math.random(),
      status: d.status || 'info',
      timestamp: d.timestamp || new Date().toISOString(),
      system: d.system || 'Aeroponic System',
      message: d.message || 'System Event',
      category: d.category || 'system',
      module_id: d.module_id,
    };
  }

  const hasAlertShape =
    parsed.level !== undefined ||
    parsed.severity !== undefined ||
    parsed.node_id !== undefined ||
    parsed.metric !== undefined;
  if (!hasAlertShape) return null;

  const levelOrSeverity = parsed.level || parsed.severity || 'warning';
  const rawStatus = parsed.status; // 'triggered' | 'active' | 'resolved'

  let status;
  if (rawStatus === 'resolved') status = 'success';
  else if (levelOrSeverity === 'critical') status = 'critical';
  else status = 'warning';

  const ts = parsed.ts ?? parsed.triggered_at;
  const timestamp = ts ? new Date(ts).toISOString() : new Date().toISOString();

  return {
    id: Date.now() + Math.random(),
    status,
    timestamp,
    system: 'Aeroponic System',
    message: parsed.message || 'Alert',
    category: 'alert',
    module_id: parsed.node_id,
  };
}

export function NotificationProvider({ children }) {
  const [notifications, setNotifications] = useState([]);
  const [latestStatus, setLatestStatus] = useState({ status: 'healthy', message: 'System Offline' });
  const [unreadCount, setUnreadCount] = useState(0);

  const pushNotification = useCallback((newNotif) => {
    setNotifications(prev => {
      // De-duplicate: if exact same message & status in last 5s, update timestamp only
      const recent = prev[0];
      if (
        recent &&
        recent.message === newNotif.message &&
        recent.status === newNotif.status &&
        (new Date(newNotif.timestamp) - new Date(recent.timestamp)) < 5000
      ) {
        const updated = [...prev];
        updated[0] = { ...updated[0], timestamp: newNotif.timestamp };
        return updated;
      }
      return [newNotif, ...prev].slice(0, MAX_NOTIFICATIONS);
    });

    // Increment unread for actionable categories
    if (ACTIONABLE_CATEGORIES.includes(newNotif.category) || newNotif.status !== 'info') {
      setUnreadCount(prev => prev + 1);
    }
  }, []);

  useEffect(() => {
    const token = sessionStorage.getItem('token') || '';
    const wsUrl = getWsUrl(`/ws/system-status?token=${encodeURIComponent(token)}`);

    let socket = null;
    let reconnectTimer = null;

    function connect() {
      if (!token) return;
      socket = new WebSocket(wsUrl);

      socket.onopen = () => {
        setLatestStatus(prev => ({ ...prev, message: 'System: Active' }));
      };

      socket.onmessage = (event) => {
        try {
          const parsed = JSON.parse(event.data);
          const msgType = parsed.type || parsed.event;

          // ── Handle generic system health (Agregator heartbeat) ──
          if (msgType === 'system_health') {
            const data = parsed.data || {};
            const newNotif = {
              id: Date.now() + Math.random(),
              status: data.status || 'info',
              timestamp: data.timestamp || new Date().toISOString(),
              system: data.system || 'Aeroponic System',
              message: data.message || 'System Update',
              category: 'system',
            };

            setLatestStatus({ status: newNotif.status, message: newNotif.message });

            // Only push to history if it's NOT a generic "all operational" heartbeat
            const isGenericHealthy = newNotif.status === 'healthy' && newNotif.message === 'All systems operational';
            if (!isGenericHealthy) {
              pushNotification(newNotif);
            }
            return;
          }

          // ── Handle alert events (legacy wrapped, Alert Service system.status, raw alert.*) ──
          const notif = normalizeAlert(parsed);
          if (notif) {
            // Update top-bar status only for actionable alerts
            if (notif.status === 'critical' || notif.status === 'warning') {
              setLatestStatus({ status: notif.status, message: notif.message });
            } else if (notif.status === 'success') {
              // Resolved alerts: briefly show message then revert to healthy
              setLatestStatus({ status: 'healthy', message: notif.message });
            }

            pushNotification(notif);
          }
        } catch (err) {
          console.warn('NotificationContext: Failed to parse WS message', err);
        }
      };

      socket.onclose = () => {
        setLatestStatus({ status: 'warning', message: 'Connection Lost. Reconnecting...' });
        reconnectTimer = setTimeout(connect, 5000);
      };

      socket.onerror = () => {
        socket.close();
      };
    }

    connect();

    return () => {
      if (socket) socket.close();
      if (reconnectTimer) clearTimeout(reconnectTimer);
    };
  }, [pushNotification]);

  const clearUnread = () => setUnreadCount(0);

  return (
    <NotificationContext.Provider value={{ notifications, latestStatus, unreadCount, clearUnread }}>
      {children}
    </NotificationContext.Provider>
  );
}
