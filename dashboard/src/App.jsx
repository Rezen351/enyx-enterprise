import { useState, useEffect } from 'react';
import {
  Activity,
  ShieldAlert,
  Video,
  ArrowRight,
  BookOpen,
  Sparkles,
  LogOut,
  User as UserIcon,
  Cpu,
  Database,
  Layers,
  Network,
  Sun,
  Moon,
  Radio,
  Zap,
  BrainCircuit,
  Gauge
} from 'lucide-react';
import heroImage from './assets/aeroponic_hero.png';
import Login from './components/Auth/Login';
import Register from './components/Auth/Register';
import DashboardLayout from './components/Dashboard/DashboardLayout';
import WebSerialClient from './components/WebSerial/WebSerialClient';
import Docs from './components/Docs/Docs';
import { ThemeProvider } from './context/ThemeContext';
import { useTheme } from './context/useTheme';
import { authApi } from './api/auth';
import { registerUnauthorized, registerServerError, clearSession } from './api/client';

// Base path where the dashboard is served via Kong (see vite.config.js -> base).
// All navigation & assets must be relative to this BASE.
const BASE = import.meta.env.BASE_URL || '/';
function stripBase(p) {
  if (BASE !== '/' && p.startsWith(BASE)) {
    return p.slice(BASE.length - 1); // pertahankan leading '/'
  }
  return p;
}

function AppContent() {
  const { theme, toggleTheme } = useTheme();
  const [showAuth, setShowAuth] = useState(false);
  const [authMode, setAuthMode] = useState('login'); // 'login' or 'register'
  // Initialize user synchronously from localStorage
  const [user, setUser] = useState(() => {
    const savedUser = sessionStorage.getItem('user');
    try {
      return savedUser ? JSON.parse(savedUser) : null;
    } catch {
      return null;
    }
  });

  // Initialize view based on current path and user session
  const [view, setView] = useState(() => {
    const rel = stripBase(window.location.pathname);
    const savedUser = sessionStorage.getItem('user');
    if (rel === '/dashboard' && savedUser) {
      return 'dashboard';
    }
    return 'landing';
  });

  // Session validation on boot: if a user exists in sessionStorage, the session
  // should be checked before showing the dashboard.
  const [validating, setValidating] = useState(() =>
    !!sessionStorage.getItem('user')
  );

  // Toast for "session expired" triggered by a 401 (not a manual logout).
  const [sessionExpired, setSessionExpired] = useState(false);

  // Register the unauthorized handler SYNCHRONOUSLY (during render), not in
  // useEffect. A parent's useEffect runs AFTER child effects, so on first load
  // an authed call (e.g. /modules from ModuleProvider) could return 401 while
  // onUnauthorized is still a no-op → no redirect. Registering it here makes the
  // handler active before the child mounts.
  registerUnauthorized(() => {
    setUser(null);
    setView('landing');
    setValidating(false);
    setSessionExpired(true);
  });

  // Sync state changes to browser URL (base-aware: /app)
  useEffect(() => {
    const rel = stripBase(window.location.pathname);
    if (view === 'dashboard' && user) {
      if (rel !== '/dashboard') {
        window.history.pushState(null, '', BASE + 'dashboard');
      }
    } else if (view === 'webserial') {
      if (rel !== '/configurator') {
        window.history.pushState(null, '', BASE + 'configurator');
      }
    } else {
      if (rel !== '/') {
        window.history.pushState(null, '', BASE === '/' ? '/' : BASE);
      }
    }
  }, [view, user]);

  // Handle browser back/forward buttons (popstate)
  useEffect(() => {
    const handlePopState = () => {
      const rel = stripBase(window.location.pathname);
      const savedUser = sessionStorage.getItem('user');
      if (rel === '/dashboard' && savedUser) {
        setView('dashboard');
      } else if (rel === '/configurator') {
        setView('webserial');
      } else {
        setView('landing');
      }
    };
    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  }, []);

  // Toast for "backend unavailable" on 5xx/network failures.
  const [backendDown, setBackendDown] = useState(false);

  // Register the server-error handler (5xx/network) so App can show a toast
  // without treating the session as invalid (504 ≠ logout). Throttling is in client.
  registerServerError((msg) => {
    setBackendDown(true);
    if (msg) console.warn('[api] backend error:', msg);
  });

  // Auto-hide the "session expired" & "backend down" toasts.
  useEffect(() => {
    if (!sessionExpired && !backendDown) return;
    const t = setTimeout(() => {
      setSessionExpired(false);
      setBackendDown(false);
    }, 6000);
    return () => clearTimeout(t);
  }, [sessionExpired, backendDown]);

  // Session validation on boot: if a user exists in sessionStorage, call /auth/me.
  // On failure (a 401 that can't be refreshed), onUnauthorized already resets the
  // session & redirects. On success, show the dashboard.
  useEffect(() => {
    if (!validating) return;
    let active = true;
    authApi.me()
      .catch(() => {})
      .finally(() => { if (active) setValidating(false); });
    return () => { active = false; };
  }, [validating]);

  // Logout must still clean up the LOCAL session even if the backend is 504/down.
  const handleLogout = async () => {
    try {
      await authApi.logout();
    } catch {
      /* ignore — local session is still cleared in finally */
    } finally {
      clearSession();
      setUser(null);
      setView('landing');
      setValidating(false);
    }
  };

  const handleLoginSuccess = (userData) => {
    setUser(userData);
    setShowAuth(false);
    setView('dashboard');
    setValidating(false);
  };

  const primaryBtn = "px-10 h-16 bg-gradient-to-r from-emerald-500 to-teal-500 hover:from-emerald-400 hover:to-teal-400 text-black font-black transition-all duration-300 active:scale-95 flex items-center justify-center gap-3 cursor-pointer uppercase tracking-widest text-sm shadow-[0_8px_30px_-10px_rgba(16,185,129,0.6)] w-full sm:w-auto";

  // Global toast for session expired / backend unavailable.
  const authToast = sessionExpired ? (
    <div className="fixed top-4 left-1/2 -translate-x-1/2 z-[120] px-5 py-3 bg-red-500/15 border border-red-500/30 backdrop-blur-xl  text-red-300 text-xs font-black uppercase tracking-widest flex items-center gap-2">
      <LogOut className="w-4 h-4" /> Session expired, please sign in again
    </div>
  ) : backendDown ? (
    <div className="fixed top-4 left-1/2 -translate-x-1/2 z-[120] px-5 py-3 bg-amber-500/15 border border-amber-500/30 backdrop-blur-xl  text-amber-200 text-xs font-black uppercase tracking-widest flex items-center gap-2">
      <Database className="w-4 h-4" /> Backend unavailable
    </div>
  ) : null;

  // On boot with a session from sessionStorage, show a loading state first until
  // the /auth/me validation finishes (success → dashboard, 401 failure → redirect).
  if (validating) {
    return (
      <div className="min-h-screen flex items-center justify-center" style={{ backgroundColor: 'var(--bg-main)', color: 'var(--text-muted)' }}>
        <span className="text-xs font-black uppercase tracking-[0.3em] animate-pulse">Verifying session…</span>
      </div>
    );
  }

  if (view === 'dashboard' && user) {
    return (
      <>
        {authToast}
        <DashboardLayout onExit={() => setView('landing')} onLogout={handleLogout} />
      </>
    );
  }

  if (view === 'webserial') {
    return (
      <div className="min-h-screen font-sans selection:bg-emerald-500/30 overflow-x-hidden relative" style={{ backgroundColor: 'var(--bg-main)' }}>
        <nav className="relative z-50 border-b border-emerald-500/10 bg-inherit/80 backdrop-blur-xl sticky top-0" style={{ borderColor: 'var(--border-main)' }}>
          <div className="max-w-7xl mx-auto px-6 py-4 flex justify-between items-center compact-mobile-px">
            <div className="flex items-center cursor-pointer group" onClick={() => setView('landing')}>
              <img src={`${BASE}Smart Farm Logo.svg`} className="h-9 sm:h-10 w-auto object-contain" alt="Smart Farm Logo" />
            </div>
            <button onClick={() => setView('landing')} className="text-emerald-500 hover:text-emerald-400 font-bold uppercase tracking-widest text-xs flex items-center gap-2">
              <LogOut className="w-4 h-4 rotate-180" /> Back to Home
            </button>
          </div>
        </nav>
        <WebSerialClient />
      </div>
    );
  }

  if (view === 'docs') {
    return (
      <Docs onBack={() => setView('landing')} theme={theme} />
    );
  }

  return (
    <div className="min-h-screen font-sans selection:bg-emerald-500/30 overflow-x-hidden relative">
      {authToast}

      {/* Background Radial Glows */}
      <div className="fixed inset-0 z-0 overflow-hidden pointer-events-none">
        <div className="absolute top-[-10%] left-[-10%] w-[50%] h-[50%]  opacity-40 blur-[150px]" style={{ backgroundColor: 'var(--radial-glow-1)' }} />
        <div className="absolute bottom-[-10%] right-[-10%] w-[50%] h-[50%]  opacity-40 blur-[150px]" style={{ backgroundColor: 'var(--radial-glow-2)' }} />
        <div className="absolute top-1/3 left-1/2 -translate-x-1/2 w-[60%] h-[40%] opacity-20 blur-[160px]" style={{ backgroundColor: '#10b981' }} />
      </div>

      {/* Auth Modal Overlay */}
      {showAuth && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center p-6">
          <div 
            className="absolute inset-0 bg-slate-950/60 backdrop-blur-md"
            onClick={() => setShowAuth(false)}
          />
          <div className="relative z-10 w-full flex justify-center animate-in fade-in zoom-in duration-300">
            {authMode === 'login' ? (
              <Login 
                onLoginSuccess={handleLoginSuccess} 
                onToggleMode={() => setAuthMode('register')} 
              />
            ) : (
              <Register 
                onRegisterSuccess={() => setAuthMode('login')} 
                onToggleMode={() => setAuthMode('login')} 
              />
            )}
          </div>
        </div>
      )}

      {/* Navigation Header */}
      <nav className="relative z-50 border-b border-emerald-500/10 bg-[#030705]/70 backdrop-blur-xl sticky top-0" style={{ borderColor: 'var(--border-main)' }}>
        <div className="max-w-7xl mx-auto px-6 py-4 flex justify-between items-center compact-mobile-px">
          <div className="flex items-center cursor-pointer group select-none" onClick={() => window.scrollTo({top: 0, behavior: 'smooth'})}>
            <img src="/favicon.svg" className={`sm:hidden h-8 w-8 object-contain ${theme === 'light' ? 'invert opacity-80' : ''}`} alt="Aeroponik" />
            <img src="/Smart Farm Logo.svg" className="hidden sm:block h-9 sm:h-10 w-auto object-contain" alt="Smart Farm Logo" />
          </div>

          <div className="hidden lg:flex items-center gap-5 xl:gap-8 text-[11px] font-black uppercase tracking-[0.2em]" style={{ color: 'var(--text-muted)' }}>
            <a href="#hero" className="hover:text-emerald-400 transition-colors">Home</a>
            <a href="#how" className="hover:text-emerald-400 transition-colors">How it works</a>
            <a href="#features" className="hover:text-emerald-400 transition-colors">Platform</a>
            <a href="#architecture" className="hover:text-emerald-400 transition-colors">Architecture</a>
          </div>

          <div className="flex items-center gap-2 sm:gap-4">
            {/* Documentation */}
            <button
              onClick={() => setView('docs')}
              title="Documentation"
              className="flex items-center gap-2 h-10 px-3 border border-emerald-500/20 text-emerald-400 hover:bg-emerald-500/10 transition-colors cursor-pointer"
            >
              <BookOpen className="w-5 h-5" />
              <span className="hidden sm:inline text-[11px] font-black uppercase tracking-widest">Docs</span>
            </button>

            {/* Theme Toggle Button */}
            <button
              onClick={toggleTheme}
              className="h-10 w-10 flex items-center justify-center transition-all duration-300 border border-emerald-500/10 hover:bg-emerald-500/5 cursor-pointer"
              title={theme === 'light' ? 'Switch to Dark Mode' : 'Switch to Light Mode'}
            >
              {theme === 'light' ? (
                <Moon className="w-5 h-5 text-slate-600" />
              ) : (
                <Sun className="w-5 h-5 text-emerald-400" />
              )}
            </button>

            {user ? (
              <div className="flex items-center gap-2 sm:gap-4">
                <div className="hidden lg:flex items-center gap-2 px-4 h-10 bg-emerald-500/10 border border-emerald-500/20">
                  <UserIcon className="w-4 h-4 text-emerald-400" />
                  <span className="text-xs font-black text-emerald-400 uppercase tracking-wider">{user.username}</span>
                </div>
                <button
                  onClick={() => setView('dashboard')}
                  className="px-4 sm:px-6 h-10 bg-emerald-500 text-black font-black text-xs uppercase tracking-widest transition-all duration-300 hover:bg-emerald-400 active:scale-95 cursor-pointer"
                >
                  Dashboard
                </button>
                <button
                  onClick={handleLogout}
                  className="h-10 w-10 flex items-center justify-center text-slate-500 hover:text-red-400 transition-colors cursor-pointer border border-white/5 hover:bg-red-500/5"
                  title="Logout"
                >
                  <LogOut className="w-5 h-5" />
                </button>
              </div>
            ) : (
              <button
                onClick={() => { setAuthMode('login'); setShowAuth(true); }}
                className="px-4 sm:px-6 h-11 bg-gradient-to-r from-emerald-500 to-teal-500 hover:from-emerald-400 hover:to-teal-400 text-black font-black text-xs uppercase tracking-widest transition-all duration-300 active:scale-95"
              >
                Login
              </button>
            )}
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section id="hero" className="max-w-7xl mx-auto px-6 pt-20 pb-24 grid grid-cols-1 lg:grid-cols-12 gap-16 items-center relative z-10 compact-mobile-px">
        <div className="lg:col-span-7 flex flex-col items-start text-left">
          <div className="inline-flex items-center gap-2.5 px-4 py-1.5 bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-[10px] font-black tracking-[0.2em] uppercase mb-8">
            <Sparkles className="w-3.5 h-3.5 animate-pulse" />
            Aeroponic IoT Platform
          </div>
          <h1 className="text-4xl sm:text-5xl lg:text-7xl font-black font-display leading-[1.02] tracking-tighter mb-6 uppercase" style={{ color: 'var(--text-main)' }}>
            The Control Tower <br />
            for <span className="bg-gradient-to-r from-emerald-400 via-green-400 to-teal-400 bg-clip-text text-transparent">Aeroponic Farms</span>
          </h1>
          <p className="text-lg sm:text-xl max-w-2xl leading-relaxed mb-10 font-medium" style={{ color: 'var(--text-muted)' }}>
            Real-time telemetry, on-device AI vision, and automated actuator control — unified by a resilient microservice backbone. Purpose-built for the Aeroponik precision potato-seedling system.
            {user ? <span className="text-emerald-400"> Welcome back, {user.username}.</span> : ''}
          </p>

          <div className="flex flex-wrap gap-4 mb-12">
            {user ? (
              <button
                onClick={() => setView('dashboard')}
                className={`group ${primaryBtn}`}
              >
                Launch Dashboard <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
              </button>
            ) : (
              <button
                onClick={() => { setAuthMode('login'); setShowAuth(true); }}
                className={`group ${primaryBtn}`}
              >
                Get Started <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
              </button>
            )}
            <a href="#features" className="px-10 h-16 border bg-slate-500/5 hover:bg-slate-500/10 font-black transition-all duration-300 active:scale-95 uppercase tracking-widest text-sm flex items-center justify-center w-full sm:w-auto" style={{ borderColor: 'var(--border-main)', color: 'var(--text-main)' }}>
              Explore Platform
            </a>
          </div>

          <div className="flex items-center gap-6 sm:gap-8 lg:gap-12 flex-wrap">
            {[
              { v: '15s', l: 'Misting Cycle' },
              { v: '98.4%', l: 'AI Accuracy' },
              { v: '24/7', l: 'Uptime' },
              { v: '<50ms', l: 'Command Latency' },
            ].map((s) => (
              <div key={s.l} className="flex flex-col gap-1">
                <span className="text-2xl sm:text-3xl font-black tabular-nums bg-gradient-to-r from-emerald-400 to-teal-400 bg-clip-text text-transparent">{s.v}</span>
                <span className="text-[10px] font-black uppercase tracking-widest text-slate-500">{s.l}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="lg:col-span-5 relative flex justify-center lg:justify-end">
          <div className="relative w-full max-w-[480px] aspect-[4/5] overflow-hidden border border-emerald-500/10 group shadow-[0_0_80px_-20px_rgba(16,185,129,0.45)]">
            <div className="absolute inset-0 bg-gradient-to-t from-black/30 via-transparent to-transparent z-10" />
            <div className="absolute inset-0 bg-emerald-500/5 mix-blend-overlay z-10" />
            <img src={heroImage} alt="Aeroponics" className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-1000" />

            {/* Overlay Status Card */}
            <div className="absolute bottom-6 left-6 right-6 z-20 p-5 backdrop-blur-md border" style={{ backgroundColor: 'var(--bg-card)', borderColor: 'var(--border-main)' }}>
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                  <span className="w-2 h-2 bg-emerald-400 animate-pulse" />
                  <span className="text-[10px] font-black text-emerald-400 uppercase tracking-widest">Node-01 Active</span>
                </div>
                <span className="text-[10px] font-black uppercase" style={{ color: 'var(--text-muted)' }}>12:30:15 UTC</span>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-1">
                  <div className="text-[9px] font-black uppercase" style={{ color: 'var(--text-muted)' }}>Air Temp</div>
                  <div className="text-lg font-black" style={{ color: 'var(--text-main)' }}>18.4°C</div>
                </div>
                <div className="space-y-1">
                  <div className="text-[9px] font-black uppercase" style={{ color: 'var(--text-muted)' }}>Humidity</div>
                  <div className="text-lg font-black" style={{ color: 'var(--text-main)' }}>82%</div>
                </div>
              </div>
              <div className="mt-4 flex items-end gap-1 h-8">
                {[40, 65, 50, 80, 60, 92, 70, 55, 78, 64].map((h, i) => (
                  <div key={i} className="flex-1 bg-gradient-to-t from-emerald-500/40 to-emerald-400/80" style={{ height: `${h}%` }} />
                ))}
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Trust Strip */}
      <section className="border-y relative z-10" style={{ borderColor: 'var(--border-main)', backgroundColor: 'var(--bg-card)' }}>
        <div className="max-w-7xl mx-auto px-6 py-6 flex flex-col sm:flex-row items-center justify-between gap-4 compact-mobile-px">
          <span className="text-[10px] font-black uppercase tracking-[0.3em] text-slate-500">Powered by a resilient stack</span>
          <div className="flex flex-wrap items-center gap-6 text-xs font-black uppercase tracking-widest text-slate-400">
            <span>ESP32</span><span className="text-slate-600">·</span>
            <span>Go</span><span className="text-slate-600">·</span>
            <span>Kong</span><span className="text-slate-600">·</span>
            <span>NATS</span><span className="text-slate-600">·</span>
            <span>MQTT</span><span className="text-slate-600">·</span>
            <span>MariaDB</span><span className="text-slate-600">·</span>
            <span>MinIO</span><span className="text-slate-600">·</span>
            <span>YOLOv8</span>
          </div>
        </div>
      </section>

      {/* How it works — Pipeline */}
      <section id="how" className="max-w-7xl mx-auto px-6 py-28 relative z-10 compact-mobile-px">
        <div className="text-center max-w-3xl mx-auto mb-16">
          <h2 className="text-xs font-black text-emerald-500 uppercase tracking-[0.3em] mb-4">The Data Loop</h2>
          <h3 className="text-4xl sm:text-5xl font-black uppercase tracking-tight leading-tight" style={{ color: 'var(--text-main)' }}>From Sensor to Actuator in Real Time</h3>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
          {[
            { n: '01', icon: Radio, t: 'Sense', d: 'ESP32 nodes capture pH, EC, climate and root imagery at the edge.' },
            { n: '02', icon: Zap, t: 'Stream', d: 'Kong routes every request and live WebSocket, while MQTT and NATS carry device telemetry across the mesh.' },
            { n: '03', icon: BrainCircuit, t: 'Analyze', d: 'The Analytics Service and ML vision (YOLOv8) surface trends and anomalies from raw telemetry.' },
            { n: '04', icon: Gauge, t: 'Actuate', d: 'The Control panel drives pumps, relays and misting on your terms.' },
          ].map((step, i, arr) => (
            <div key={step.n} className="relative p-8 border transition-all duration-500 group hover:-translate-y-1" style={{ backgroundColor: 'var(--bg-card)', borderColor: 'var(--border-main)' }}>
              <div className="flex items-center justify-between mb-6">
                <div className="p-3 bg-emerald-500/10 group-hover:bg-emerald-500/20 transition-colors">
                  <step.icon className="w-7 h-7 text-emerald-400" />
                </div>
                <span className="text-3xl font-black text-emerald-500/20 group-hover:text-emerald-500/40 transition-colors">{step.n}</span>
              </div>
              <h4 className="text-lg font-black uppercase tracking-wider mb-2" style={{ color: 'var(--text-main)' }}>{step.t}</h4>
              <p className="text-sm leading-relaxed font-medium" style={{ color: 'var(--text-muted)' }}>{step.d}</p>
              {i < arr.length - 1 && (
                <span className="hidden lg:block absolute -right-3 top-1/2 -translate-y-1/2 text-emerald-500/40 text-2xl">→</span>
              )}
            </div>
          ))}
        </div>
      </section>

      {/* Features Section */}
      <section id="features" className="max-w-7xl mx-auto px-6 py-28 border-t relative z-10 compact-mobile-px" style={{ borderColor: 'var(--border-main)' }}>
        <div className="text-center max-w-3xl mx-auto mb-16">
          <h2 className="text-xs font-black text-emerald-500 uppercase tracking-[0.3em] mb-4">Core Capabilities</h2>
          <h3 className="text-4xl sm:text-5xl font-black uppercase tracking-tight leading-tight" style={{ color: 'var(--text-main)' }}>One Platform, Total Visibility</h3>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {[
            { icon: Activity, t: 'Live Telemetry', d: 'Sub-second sensor streams from every node. Watch pH, EC, temperature and humidity the instant they change.' },
            { icon: Video, t: 'AI Vision', d: 'On-device YOLOv8 models grade root and leaf health, flagging stress long before the human eye can.' },
            { icon: ShieldAlert, t: 'Edge Protection', d: 'Hardware failsafes cut power to pumps and relays the moment a threshold is breached.' },
          ].map((f) => (
            <div key={f.t} className="relative p-10 border overflow-hidden transition-all duration-500 group hover:-translate-y-1" style={{ backgroundColor: 'var(--bg-card)', borderColor: 'var(--border-main)' }}>
              <div className="absolute -top-16 -right-16 w-40 h-40 bg-emerald-500/10 blur-2xl group-hover:bg-emerald-500/20 transition-colors" />
              <div className="p-4 bg-emerald-500/10 w-fit mb-8 group-hover:scale-110 transition-transform duration-300">
                <f.icon className="w-8 h-8 text-emerald-400" />
              </div>
              <h4 className="text-xl font-black mb-4 uppercase tracking-wider" style={{ color: 'var(--text-main)' }}>{f.t}</h4>
              <p className="leading-relaxed font-medium" style={{ color: 'var(--text-muted)' }}>{f.d}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Architecture Section */}
      <section id="architecture" className="max-w-7xl mx-auto px-6 py-28 border-t relative z-10 overflow-hidden compact-mobile-px" style={{ borderColor: 'var(--border-main)' }}>
         <div className="grid grid-cols-1 lg:grid-cols-2 gap-20 items-center">
            <div className="order-2 lg:order-1 grid grid-cols-2 gap-4">
                <div className="space-y-4 pt-12">
                    <div className="p-5 sm:p-6 border" style={{ backgroundColor: 'var(--bg-card)', borderColor: 'var(--border-main)' }}>
                        <Cpu className="w-6 h-6 text-emerald-400 mb-3" />
                        <span className="block text-[10px] font-black uppercase tracking-widest mb-1" style={{ color: 'var(--text-muted)' }}>Compute</span>
                        <span className="text-sm font-black uppercase" style={{ color: 'var(--text-main)' }}>Go Microservices</span>
                    </div>
                    <div className="p-5 sm:p-6 border" style={{ backgroundColor: 'var(--bg-card)', borderColor: 'var(--border-main)' }}>
                        <Database className="w-6 h-6 text-emerald-400 mb-3" />
                        <span className="block text-[10px] font-black uppercase tracking-widest mb-1" style={{ color: 'var(--text-muted)' }}>Persistence</span>
                        <span className="text-sm font-black uppercase" style={{ color: 'var(--text-main)' }}>MariaDB + TimescaleDB</span>
                    </div>
                </div>
                <div className="space-y-4">
                    <div className="p-5 sm:p-6 border" style={{ backgroundColor: 'var(--bg-card)', borderColor: 'var(--border-main)' }}>
                        <Network className="w-6 h-6 text-emerald-400 mb-3" />
                        <span className="block text-[10px] font-black uppercase tracking-widest mb-1" style={{ color: 'var(--text-muted)' }}>Traffic</span>
                        <span className="text-sm font-black uppercase" style={{ color: 'var(--text-main)' }}>Kong API Gateway</span>
                    </div>
                    <div className="p-5 sm:p-6 border" style={{ backgroundColor: 'var(--bg-card)', borderColor: 'var(--border-main)' }}>
                        <Layers className="w-6 h-6 text-emerald-400 mb-3" />
                        <span className="block text-[10px] font-black uppercase tracking-widest mb-1" style={{ color: 'var(--text-muted)' }}>Messaging</span>
                        <span className="text-sm font-black uppercase" style={{ color: 'var(--text-main)' }}>NATS + MQTT</span>
                    </div>
                </div>
            </div>
            <div className="order-1 lg:order-2">
                <h2 className="text-xs font-black text-emerald-500 uppercase tracking-[0.3em] mb-4">The Backbone</h2>
                <h3 className="text-4xl font-black uppercase tracking-tight leading-tight mb-8" style={{ color: 'var(--text-main)' }}>Production-Grade <br />Infrastructure</h3>
                <p className="text-lg leading-relaxed font-medium mb-10" style={{ color: 'var(--text-muted)' }}>
                   Every service runs isolated in Docker, scales on demand, and is exposed through a Kong API gateway over an SSL-secured tunnel. NATS and MQTT move telemetry between nodes and services — no single point of failure.
                </p>
                <ul className="space-y-4">
                    {['WebSocket + MQTT Streams', 'MinIO Object Storage', 'Prometheus + Grafana', 'Encrypted Handshake'].map((item) => (
                        <li key={item} className="flex items-center gap-3 font-black uppercase tracking-widest text-[11px]" style={{ color: 'var(--text-main)' }}>
                            <span className="w-1.5 h-1.5 bg-emerald-400" />
                            {item}
                        </li>
                    ))}
                </ul>
            </div>
         </div>
      </section>

      {/* CTA Band */}
      <section className="relative z-10 px-6 pb-28 compact-mobile-px">
        <div className="max-w-5xl mx-auto border p-10 sm:p-16 text-center relative overflow-hidden" style={{ backgroundColor: 'var(--bg-card)', borderColor: 'var(--border-main)' }}>
          <div className="absolute inset-0 bg-gradient-to-br from-emerald-500/10 via-transparent to-teal-500/10 pointer-events-none" />
          <div className="relative">
            <h3 className="text-3xl sm:text-5xl font-black uppercase tracking-tight mb-4" style={{ color: 'var(--text-main)' }}>Wire Up Your Farm</h3>
            <p className="text-base sm:text-lg max-w-xl mx-auto mb-8 font-medium" style={{ color: 'var(--text-muted)' }}>
              Pair your first ESP32 node and watch telemetry flow in minutes. Free for single-module pilots.
            </p>
            {user ? (
              <button onClick={() => setView('dashboard')} className={`group mx-auto ${primaryBtn}`}>
                Launch Dashboard <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
              </button>
            ) : (
              <button onClick={() => { setAuthMode('login'); setShowAuth(true); }} className={`group mx-auto ${primaryBtn}`}>
                Get Started <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
              </button>
            )}
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t py-16 text-center relative z-10" style={{ backgroundColor: 'var(--bg-main)', borderColor: 'var(--border-main)' }}>
        <div className="flex justify-center items-center mb-8 opacity-60 select-none">
            <img src={`${BASE}Smart Farm Logo.svg`} className="h-8 w-auto object-contain" alt="Smart Farm Logo" />
        </div>
        <p className="text-sm font-black uppercase tracking-[0.2em] mb-6" style={{ color: 'var(--text-main)' }}>Aeroponik — Precision Aeroponic Control</p>
        <div className="flex justify-center gap-10 text-[10px] font-black uppercase tracking-[0.2em] mb-10" style={{ color: 'var(--text-muted)' }}>
            <a href="#" className="hover:text-emerald-400 transition-colors">Safety Logs</a>
            <button type="button" onClick={() => setView('docs')} className="hover:text-emerald-400 transition-colors cursor-pointer bg-transparent border-0 p-0 font-[inherit] text-[inherit]">Documentation</button>
            <a href="#" className="hover:text-emerald-400 transition-colors">API Status</a>
        </div>
        <p className="text-[10px] font-black uppercase tracking-widest" style={{ color: 'var(--text-muted)' }}>© 2026 Aeroponik. Built for scale.</p>
      </footer>

    </div>
  );
}

function App() {
  return (
    <ThemeProvider>
      <AppContent />
    </ThemeProvider>
  );
}

export default App;
