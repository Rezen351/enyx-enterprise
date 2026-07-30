import { useState, useEffect } from 'react';
import {
  Menu,
  Clock,
  LogOut,
  Sun,
  Moon
} from 'lucide-react';

// Isolated clock widget — keeps its own 1s tick state so the rest of the
// dashboard (including Analytics charts) is NOT re-rendered every second.
function ClockWidget() {
  const [now, setNow] = useState(new Date());
  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(id);
  }, []);

  const formatTime = (date) =>
    `${String(date.getHours()).padStart(2, '0')}.${String(date.getMinutes()).padStart(2, '0')}.${String(date.getSeconds()).padStart(2, '0')}`;

  const formatDate = (date) => {
    const months = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
    const days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
    return `${date.getDate()} ${months[date.getMonth()]} ${date.getFullYear()}, ${days[date.getDay()]}`;
  };

  return (
    <div className="hidden sm:flex items-center gap-2 lg:gap-3 px-3 py-1.5 sm:px-4 sm:py-2 lg:py-2.5 border" style={{ backgroundColor: 'var(--bg-card)', borderColor: 'var(--border-main)' }}>
      <div className="flex flex-col items-end">
        <span className="text-xs sm:text-base lg:text-lg font-black font-display tracking-widest text-emerald-400 tabular-nums">
          {formatTime(now)}
        </span>
        <span className="hidden lg:inline text-[11px] font-black uppercase tracking-widest mt-0.5" style={{ color: 'var(--text-muted)' }}>
          {formatDate(now)}
        </span>
      </div>
      <div className="p-1.5 sm:p-2 lg:p-2.5 bg-emerald-500/10 border border-emerald-500/20">
        <Clock className="w-4 h-4 sm:w-5 sm:h-5 lg:w-6 lg:h-6 text-emerald-400 animate-pulse" />
      </div>
    </div>
  );
}
import { useTheme } from '../../context/useTheme';
import { ModuleProvider } from '../../context/ModuleContext';
import Sidebar from './Sidebar';
import ModuleSelector from './ModuleSelector';
import Profile from './Pages/Users';
import UserManagement from './Pages/UserManagement';
import ModuleManagement from './Pages/DeviceManagement';
import NodeConfigPage from './Pages/NodeConfigPage';
import Analytics from './Pages/Analytics';
import ControlPanel from './Pages/ControlPanel';
import LiveView from './Pages/LiveView';
import Snapshot from './Pages/Snapshot';
import Monitor from './Pages/Monitor';
import Audit from './Pages/Audit';
import Alerts from './Pages/Alerts';
import Export from './Pages/Export';
import Webhook from './Pages/Webhook';
import DLQ from './Pages/DLQ';
import NotificationBell from './NotificationBell';

function DashboardContent({ onLogout }) {
  const { theme, toggleTheme } = useTheme();
  const [activeTab, setActiveTab] = useState(() => {
    try {
      return sessionStorage.getItem('dashboard_active_tab') || 'monitor';
    } catch {
      return 'monitor';
    }
  });
  const [nodeConfig, setNodeConfig] = useState(null);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [sidebarHidden, setSidebarHidden] = useState(false);
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);

  // Current user (from session) — used for admin-only UI
  const me = (() => {
    try {
      return JSON.parse(sessionStorage.getItem('user') || 'null');
    } catch {
      return null;
    }
  })();
  const isAdmin = Array.isArray(me?.roles) && me.roles.includes('admin');

  // Clock tick is isolated in <ClockWidget /> so its 1s interval does not
  // re-render the rest of the dashboard (charts, tables, etc.).

  // Switching tabs from the sidebar must also exit the Node Config page,
  // otherwise nodeConfig stays truthy and renderContent() keeps showing it.
  const handleSetActiveTab = (tab) => {
    setNodeConfig(null);
    setActiveTab(tab);
    try { sessionStorage.setItem('dashboard_active_tab', tab); } catch { /* ignore */ }
  };

  const renderContent = () => {
    if (nodeConfig) {
      return <NodeConfigPage node={nodeConfig} onBack={() => { setNodeConfig(null); setActiveTab('module'); try { sessionStorage.setItem('dashboard_active_tab', 'module'); } catch { /* ignore */ } }} />;
    }
    switch (activeTab) {
      case 'profile':
        return <Profile onLogout={onLogout} />;
      case 'module':
        return <ModuleManagement onOpenNodeConfig={setNodeConfig} />;
      case 'control':
        return <ControlPanel />;
      case 'analytics':
        return <Analytics />;
      case 'live':
        return <LiveView />;
      case 'monitor':
        return <Monitor />;
      case 'snapshot':
        return <Snapshot />;
      case 'audit':
        return <Audit />;
      case 'alerts':
        return <Alerts />;
      case 'export':
        return <Export />;
      case 'webhook':
        return <Webhook />;
      case 'dlq':
        return <DLQ />;
      case 'users':
        return isAdmin ? <UserManagement /> : <Profile onLogout={onLogout} />;
      default:
        return <Profile onLogout={onLogout} />;
    }
  };

  return (
    <div className="h-screen flex relative overflow-hidden transition-colors duration-300" style={{ backgroundColor: 'var(--bg-main)', color: 'var(--text-main)' }}>
      {/* Background Glows */}
      <div className="absolute inset-0 z-0 overflow-hidden pointer-events-none">
        <div className="absolute top-[10%] right-[5%] w-[40%] h-[40%]  opacity-40 blur-[130px]" style={{ backgroundColor: 'var(--radial-glow-1)' }} />
        <div className="absolute bottom-[10%] left-[10%] w-[40%] h-[40%]  opacity-40 blur-[130px]" style={{ backgroundColor: 'var(--radial-glow-2)' }} />
      </div>

      {/* Sidebar Navigation */}
      <Sidebar
        activeTab={activeTab}
        setActiveTab={handleSetActiveTab}
        collapsed={sidebarCollapsed}
        setCollapsed={setSidebarCollapsed}
        mobileOpen={mobileSidebarOpen}
        setMobileOpen={setMobileSidebarOpen}
        hidden={sidebarHidden}
        me={me}
      />

      {/* Main Layout Area */}
      <div className="flex-1 flex flex-col min-w-0 z-10 relative h-screen overflow-hidden">
        <header className={`shrink-0 transition-all duration-300 border-b flex items-center justify-between gap-2 backdrop-blur-md h-14 sm:h-16 lg:h-20 px-3 sm:px-4 lg:px-8 compact-mobile-header ${sidebarHidden ? 'lg:left-0' : (sidebarCollapsed ? 'lg:left-20' : 'lg:left-72')
          }`} style={{ backgroundColor: 'var(--bg-main)CC', borderColor: 'var(--border-main)' }}>
          {/* Header Left Actions */}
          <div className="flex items-center gap-2 md:gap-3 shrink-0">
            <button
              onClick={() => setMobileSidebarOpen(true)}
              className="lg:hidden p-2.5  border border-emerald-500/20 bg-slate-500/5 text-emerald-400 hover:bg-emerald-500 hover:text-black transition-all duration-200 cursor-pointer"
              title="Open Navigation"
            >
              <Menu className="w-5 h-5" />
            </button>

            <button
              onClick={() => setSidebarHidden(!sidebarHidden)}
              className="hidden lg:flex p-2.5  border border-emerald-500/20 bg-slate-500/5 text-emerald-400 hover:bg-emerald-500 hover:text-black transition-all duration-200 cursor-pointer"
              title={sidebarHidden ? "Show Sidebar" : "Hide Sidebar"}
            >
              <Menu className="w-5 h-5" />
            </button>
          </div>

          {/* Header Right widgets */}
          <div className="flex items-center gap-2 lg:gap-5 shrink-0">
            {/* Module Selector (only for data-bound pages) */}
            {!nodeConfig && ['monitor', 'analytics', 'control', 'live', 'snapshot'].includes(activeTab) && (
              <ModuleSelector />
            )}

            {/* Theme Toggle Button */}
            <button
              onClick={toggleTheme}
              className="h-10 w-10 flex items-center justify-center  transition-all duration-300 border border-emerald-500/10 bg-slate-500/5 hover:bg-emerald-500/10 cursor-pointer"
              title={theme === 'light' ? 'Switch to Dark Mode' : 'Switch to Light Mode'}
            >
              {theme === 'light' ? (
                <Moon className="w-5 h-5 text-slate-600" />
              ) : (
                <Sun className="w-5 h-5 text-emerald-400" />
              )}
            </button>

            {/* Live Clock Card — isolated 1s tick, does not re-render the page */}
            <ClockWidget />

            {/* Notification Bell (real-time alerts from the Alert Service) */}
            <NotificationBell />

            {/* Logout */}
            <button
              onClick={onLogout}
              className="flex items-center gap-2 px-3 py-2 sm:px-4 sm:py-2.5 lg:px-5 lg:py-3  bg-red-500/5 hover:bg-red-500/20 border border-red-500/20 hover:border-red-500/40 text-red-400 hover:text-red-300 font-display font-bold text-xs sm:text-sm tracking-wider transition-all duration-200 cursor-pointer"
              title="Logout from Session"
            >
              <LogOut className="w-4 h-4 sm:w-5 sm:h-5 lg:w-5 lg:h-5" />
              <span className="hidden sm:inline">LOGOUT</span>
            </button>
          </div>
        </header>

        {/* Content Page View */}
        <main className="flex-1 overflow-y-auto pt-2 sm:pt-2 lg:pt-2 main-content-area">
          <div className="p-3 sm:p-4 lg:p-6">
            {renderContent()}
          </div>
        </main>
      </div>
    </div>
  );
}

function DashboardLayout({ onLogout }) {
  return (
    <ModuleProvider>
      <DashboardContent onLogout={onLogout} />
    </ModuleProvider>
  );
}

export default DashboardLayout;
