// ============================================================================
// API CLIENT — same-origin requests (served by nginx in the dashboard
// container). Kong stays on the Docker internal network at :8000 and is
// invisible from the browser. Override with VITE_API_URL only if you need
// to point to an external API gateway.
// ============================================================================

function resolveApiBase() {
  const envUrl = import.meta.env?.VITE_API_URL;
  if (typeof window !== 'undefined') {
    if (typeof envUrl === 'string' && envUrl.trim() !== '' && !envUrl.includes('localhost')) {
      return envUrl;
    }
    if (typeof envUrl === 'string' && envUrl.includes('localhost')) {
      const hostname = window.location.hostname;
      if (hostname === 'localhost' || hostname === '127.0.0.1') {
        return envUrl;
      }
    }
    return '/';
  }
  return envUrl || 'http://localhost:8000';
}

export const API_BASE = resolveApiBase();

export function getWsUrl(path) {
  let proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  let host = window.location.host;

  const base = API_BASE === '/' ? '' : (API_BASE || '');
  if (base.startsWith('http://') || base.startsWith('https://')) {
    try {
      const u = new URL(base);
      proto = u.protocol === 'https:' ? 'wss:' : 'ws:';
      host = u.host;
    } catch (e) {
      console.error('Failed to parse API_BASE for WebSocket URL:', e);
    }
  }

  // Fallback if host is empty (e.g. file:// protocol or Capacitor webview context)
  if (!host) {
    // If window.location.hostname is set but host is somehow empty, use that; otherwise fallback
    host = window.location.hostname || 'localhost:5173';
  }

  // Ensure path starts with a slash
  const cleanPath = path.startsWith('/') ? path : `/${path}`;

  return `${proto}//${host}${cleanPath}`;
}


// ---- Session helpers ------------------------------------------------------
export const getToken = () => sessionStorage.getItem('token');
export const getRefreshToken = () => sessionStorage.getItem('refresh_token');

// Build an absolute, token-authenticated URL for <img>/<video> sources.
// The dashboard loads stored snapshots/detections via the stream service's
// /storage proxy, which requires a JWT. Browsers cannot attach an
// Authorization header to media elements, so we pass the token as a query
// arg (?token=) — the backend accepts it (same pattern as the WS gateway).
// A relative /storage/... path is resolved against API_BASE; already-absolute
// URLs are normalized to API_BASE and the token is (re)attached.
export function withToken(url) {
  if (!url) return '';
  let path = url;
  if (url.startsWith('http')) {
    try {
      const u = new URL(url);
      path = u.pathname + u.search;
    } catch {
      path = url;
    }
  }
  const apiPath = path.startsWith('/v1/') || path === '/v1' ? path : `/v1${path.startsWith('/') ? '' : '/'}${path}`;
  const base = API_BASE === '/' ? '' : (API_BASE || 'http://localhost:8000');
  const sep = apiPath.includes('?') ? '&' : '?';
  const token = getToken();
  return `${base}${apiPath}${token ? `${sep}token=${encodeURIComponent(token)}` : ''}`;
}

export function setSession({ access_token, refresh_token, user }) {
  if (access_token) sessionStorage.setItem('token', access_token);
  if (refresh_token) sessionStorage.setItem('refresh_token', refresh_token);
  if (user) sessionStorage.setItem('user', JSON.stringify(user));
}

export function clearSession() {
  sessionStorage.removeItem('token');
  sessionStorage.removeItem('refresh_token');
  sessionStorage.removeItem('user');
}

// ---- Auto token refresh on 401 (deduplicated) -----------------------------
let refreshInFlight = null;

async function refreshAccessToken() {
  if (!refreshInFlight) {
    refreshInFlight = (async () => {
       try {
         await authApiRefresh();
         return true;
       } catch {
         clearSession();
         onUnauthorized();
         return false;
       } finally {
        refreshInFlight = null;
      }
    })();
  }
  return refreshInFlight;
}

// authApi.refresh dipisah agar tidak circular: mengembalikan promise
let authApiRefresh = async () => {
  throw new Error('refresh not initialized');
};

// Dipanggil sekali dari auth.js agar client tahu cara me-refresh token
export function registerRefresh(fn) {
  authApiRefresh = fn;
}

// ---- Global unauth handler (redirect ke logout saat sesi invalid) --------
let onUnauthorized = () => {};

// Dipanggil dari App agar client bisa me-reset sesi & redirect saat 401
// tidak bisa di-refresh (token expired/invalid).
export function registerUnauthorized(fn) {
  onUnauthorized = fn;
}

// ---- Global server-error handler (5xx / network down) ---------------------
// Berbeda dengan onUnauthorized: ini BUKAN sesi invalid, jadi tidak boleh
// memicu logout. Dipakai agar UI bisa menampilkan toast "backend down".
let onServerError = () => {};
let lastServerErrorAt = 0;

export function registerServerError(fn) {
  onServerError = fn;
}

// Beri tahu UI soal error server, di-throttle 5 detik agar tidak spam.
function notifyServerError(msg) {
  const now = Date.now();
  if (now - lastServerErrorAt < 5000) return;
  lastServerErrorAt = now;
  onServerError(msg);
}

export async function request(path, { method = 'GET', body, auth = false, headers = {}, quiet = false } = {}, _isRetry = false) {
  const finalHeaders = { 'Content-Type': 'application/json', ...headers };
  if (auth) {
    const token = getToken();
    if (token) finalHeaders.Authorization = `Bearer ${token}`;
  }

  const apiPath = path.startsWith('/v1/') || path === '/v1' ? path : `/v1${path.startsWith('/') ? '' : '/'}${path}`;
  const base = API_BASE === '/' ? '' : (API_BASE || 'http://localhost:8000');

  let res;
  try {
    res = await fetch(`${base}${apiPath}`, {
      method,
      headers: finalHeaders,
      body: body != null ? JSON.stringify(body) : undefined,
    });
  } catch (netErr) {
    // Network failure (server down, 504 dari gateway, CORS, dll). Ini BUKAN
    // sesi invalid → jangan logout. Beri tahu UI lewat onServerError.
    const err = new Error('Unable to reach server');
    err.status = 0;
    err.type = 'network';
    err.cause = netErr;
    if (!quiet) notifyServerError(err.message);
    throw err;
  }

  const raw = await res.text();
  const contentType = res.headers.get('content-type') || '';
  let data = null;
  if (raw) {
    if (contentType.includes('text/csv') || raw.startsWith('time,') || raw.startsWith('node_id,')) {
      return raw;
    }
    try {
      data = JSON.parse(raw);
    } catch {
      data = raw;
    }
  }

  if (!res.ok) {
    // Coba refresh token sekali bila expired/invalid, lalu ulangi request.
    if (res.status === 401 && auth && !_isRetry) {
      const ok = await refreshAccessToken();
      if (ok) {
        return request(path, { method, body, auth, headers, quiet }, true);
      }
    }

    // Klasifikasi error agar UI tahu apa yang terjadi.
    if (res.status >= 500 && !quiet) {
      // data.error may be an object { code, message } — always extract a string.
      const serverErrMsg =
        (data?.error && typeof data.error === 'object'
          ? data.error.message
          : data?.error) ||
        data?.message ||
        `Server error (${res.status})`;
      notifyServerError(serverErrMsg);
    }

    const rawMessage =
      (data?.error && typeof data.error === 'object'
        ? data.error.message
        : data?.error) ||
      (data?.data?.error && typeof data.data.error === 'object'
        ? data.data.error.message
        : data?.data?.error) ||
      data?.message;

    const message =
      rawMessage && rawMessage.toLowerCase() !== 'unauthorized'
        ? rawMessage
        : res.status === 401
        ? 'Invalid email or password'
        : `Request failed (${res.status})`;
    const err = new Error(message);
    err.status = res.status;
    err.type = res.status === 401 ? 'unauthorized' : res.status >= 500 ? 'server' : 'client';
    err.data = data;
    throw err;
  }

  return data;
}
