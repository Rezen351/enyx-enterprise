import { request } from './client';

// Alert Service — alert history + threshold management API.
// Reads are allowed by any authenticated role (viewer/operator/admin).
// `ack` requires operator/admin (enforced by the backend); the UI disables
// the button for viewers.
//
// The Alert Service returns the standard envelope { success, data, error }
// (AGENTS.md §4.4). `unwrap` peels `data` so callers keep using the
// raw object without changes.

const unwrap = (p) => p.then((r) => (r && r.data !== undefined ? r.data : r));

// List alert history with optional filters.
export async function listAlerts({
  limit = 50,
  offset = 0,
  node_id = '',
  metric = '',
  status = '',
  severity = '',
  from = '',
  to = '',
} = {}) {
  const params = new URLSearchParams();
  params.set('limit', String(limit));
  params.set('offset', String(offset));
  if (node_id) params.set('node_id', node_id);
  if (metric) params.set('metric', metric);
  if (status) params.set('status', status);
  if (severity) params.set('severity', severity);
  if (from) params.set('from', from);
  if (to) params.set('to', to);
  return unwrap(request(`/alerts?${params.toString()}`, { auth: true }));
}

// Acknowledge an active/resolved alert (operator/admin only).
export async function ackAlert(id) {
  return unwrap(request(`/alerts/${id}/ack`, { method: 'PUT', auth: true }));
}

// List threshold configurations (optional filters).
export async function listThresholds({ node_id = '', metric = '' } = {}) {
  const params = new URLSearchParams();
  if (node_id) params.set('node_id', node_id);
  if (metric) params.set('metric', metric);
  return unwrap(request(`/thresholds?${params.toString()}`, { auth: true }));
}

// Create a threshold (node_id `*` applies to every node for that metric).
export async function createThreshold({ node_id, metric, min, max, enabled, severity, message, duration_sec, cooldown_sec, hysteresis }) {
  return unwrap(request('/thresholds', {
    method: 'POST',
    auth: true,
    body: { node_id, metric, min, max, enabled, severity, message, duration_sec, cooldown_sec, hysteresis },
  }));
}

// Patch a threshold configuration.
export async function updateThreshold(id, patch) {
  return unwrap(request(`/thresholds/${id}`, { method: 'PUT', auth: true, body: patch }));
}

// Delete a threshold configuration.
export async function deleteThreshold(id) {
  return unwrap(request(`/thresholds/${id}`, { method: 'DELETE', auth: true }));
}
