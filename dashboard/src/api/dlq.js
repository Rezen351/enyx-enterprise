import { request } from './client';

export async function listDLQMessages({ sourceStream = '', traceId = '', limit = 50, offset = 0 } = {}) {
  const params = new URLSearchParams();
  params.set('limit', String(limit));
  params.set('offset', String(offset));
  if (sourceStream) params.set('source_stream', sourceStream);
  if (traceId) params.set('trace_id', traceId);
  return request(`/dlq/messages?${params.toString()}`, { auth: true });
}
