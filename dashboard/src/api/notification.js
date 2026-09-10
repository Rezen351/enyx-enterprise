// ============================================================================
// NOTIFICATION API — unified notification + webhook settings, logs, delivery
// test, and inbound receivers (merged webhook service into notification).
// ----------------------------------------------------------------------------
// Endpoints (Kong → notification-service):
//   GET /notifications/settings      → current channel config (any auth)
//   PUT /notifications/settings      → update channel config (admin)
//   GET /notifications/logs          → delivery log history (any auth)
//   POST /notifications/test         → enqueue test delivery (admin)
//   POST /notifications/receive/*    → inbound webhook receivers (admin)
// ============================================================================

import { request } from './client';

const unwrap = (p) => p.then((r) => (r && r.data !== undefined ? r.data : r));

function qs(params) {
  if (!params) return '';
  const entries = Object.entries(params).filter(([, v]) => v !== undefined && v !== null && v !== '');
  if (entries.length === 0) return '';
  return '?' + entries.map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(v)}`).join('&');
}

export const notificationApi = {
  getSettings: () => unwrap(request(`/notifications/settings`, { auth: true })),
  updateSettings: (body) => unwrap(request(`/notifications/settings`, { method: 'PUT', auth: true, body })),
  listLogs: (params) => unwrap(request(`/notifications/logs${qs(params)}`, { auth: true })),
  testDelivery: (body) => unwrap(request(`/notifications/test`, { method: 'POST', auth: true, body })),
};

export default notificationApi;
