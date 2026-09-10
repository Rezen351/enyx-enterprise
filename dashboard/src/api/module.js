// ============================================================================
// MODULE API — real calls to the Module Service via Kong Gateway
// ----------------------------------------------------------------------------
// Endpoints (Kong → module-service):
//   Modules: GET/POST /modules   GET/PUT/DELETE /modules/{id}
//   Nodes:   GET /nodes   GET /nodes/discovered   GET /nodes/{node_id}
//            POST /nodes/{node_id}/pair   POST /nodes/{node_id}/unpair
//            DELETE /nodes/{node_id}
// ----------------------------------------------------------------------------
// Onboarding flow: firmware auto-broadcasts `discovery` → nodes appear in
// /nodes/discovered (unpaired) → user pairs a node into a module.
// ============================================================================
// The Module Service returns the standard envelope { success, data, error }
// (AGENTS.md §4.4). `unwrap` peels `data` so pages keep using the raw
// object without changes.

import { request } from './client';

const unwrap = (p) => p.then((r) => (r && r.data !== undefined ? r.data : r));

function qs(params) {
  if (!params) return '';
  const entries = Object.entries(params).filter(([, v]) => v !== undefined && v !== null && v !== '');
  if (entries.length === 0) return '';
  return '?' + entries.map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(v)}`).join('&');
}

export const moduleApi = {
  // ─── Modules ──────────────────────────────────────────────────────────
  listModules: () => unwrap(request('/modules', { auth: true })),
  getModule: (id) => unwrap(request(`/modules/${id}`, { auth: true })),
  createModule: ({ name, description }) =>
    unwrap(request('/modules', { method: 'POST', auth: true, body: { name, description } })),
  updateModule: (id, body) => unwrap(request(`/modules/${id}`, { method: 'PUT', auth: true, body })),
  deleteModule: (id) => unwrap(request(`/modules/${id}`, { method: 'DELETE', auth: true })),

  // ─── Nodes (onboarding) ───────────────────────────────────────────────
  // params: { paired: true|false, module_id, status }
  listNodes: (params) => unwrap(request(`/nodes${qs(params)}`, { auth: true })),
  listDiscovered: () => unwrap(request('/nodes/discovered', { auth: true })),
  getNode: (nodeId) => unwrap(request(`/nodes/${nodeId}`, { auth: true })),
  getNodeTags: (nodeId) => unwrap(request(`/nodes/${nodeId}/tags`, { auth: true })),
  saveNodeTag: (nodeId, tag) =>
    unwrap(request(`/nodes/${nodeId}/tags`, { method: 'POST', auth: true, body: tag })),
  saveNodeTags: (nodeId, tags) =>
    unwrap(request(`/nodes/${nodeId}/tags`, { method: 'PUT', auth: true, body: tags })),
  deleteNodeTag: (nodeId, id) =>
    unwrap(request(`/nodes/${nodeId}/tags/${id}`, { method: 'DELETE', auth: true })),
  // Actuator tags — separate from sensor telemetry tags. The user maps a
  // firmware output (chosen from a node's discovered outputs) to a friendly
  // control tag; these drive the Control page.
  getActuatorTags: (nodeId) => unwrap(request(`/nodes/${nodeId}/actuators`, { auth: true })),
  createActuatorTag: (nodeId, body) =>
    unwrap(request(`/nodes/${nodeId}/actuators`, { method: 'POST', auth: true, body })),
  deleteActuatorTag: (nodeId, id) =>
    unwrap(request(`/nodes/${nodeId}/actuators/${id}`, { method: 'DELETE', auth: true })),
  pairNode: (nodeId, { module_id, name }) =>
    unwrap(request(`/nodes/${nodeId}/pair`, { method: 'POST', auth: true, body: { module_id, name } })),
  unpairNode: (nodeId) => unwrap(request(`/nodes/${nodeId}/unpair`, { method: 'POST', auth: true })),
  deleteNode: (nodeId) => unwrap(request(`/nodes/${nodeId}`, { method: 'DELETE', auth: true })),
};

export default moduleApi;
