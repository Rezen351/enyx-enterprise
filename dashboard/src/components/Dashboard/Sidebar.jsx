import { useState } from 'react';
import {
  ChevronLeft,
  ChevronRight,
  ChevronDown,
  X,
  User,
  ShieldCheck,
  Server,
  BarChart3,
  SlidersHorizontal,
  Video,
  Camera,
  Activity,
  ScrollText,
  ShieldAlert,
  Download,
  Globe,
  FileWarning
} from 'lucide-react';

function Sidebar({ activeTab, setActiveTab, collapsed, setCollapsed, mobileOpen, setMobileOpen, hidden = false, me = null }) {
  const roles = Array.isArray(me?.roles) ? me.roles : [];

  const mainMenuItems = [
    { id: 'monitor', label: 'MONITOR', icon: Activity, roles: ['admin','operator','viewer'] },
    { id: 'analytics', label: 'ANALYTICS', icon: BarChart3, roles: ['admin','operator','viewer'] },
    { id: 'control', label: 'CONTROL', icon: SlidersHorizontal, roles: ['admin','operator'] },
    { id: 'live', label: 'LIVE', icon: Video, roles: ['admin','operator'] },
    { id: 'snapshot', label: 'GALLERY', icon: Camera, roles: ['admin','operator','viewer'] },
    { id: 'alerts', label: 'ALERTS', icon: ShieldAlert, roles: ['admin','operator'] },
    { id: 'export', label: 'EXPORT', icon: Download, roles: ['admin','operator'] },
    { id: 'module', label: 'MODULE', icon: Server, roles: ['admin','operator'] },
  ];

  // Admin-only tools grouped under a single collapsible "ADMINISTRATOR" tree.
  const adminGroup = {
    id: 'admin-group',
    label: 'ADMINISTRATOR',
    icon: ShieldCheck,
    children: [
      { id: 'audit', label: 'AUDIT', icon: ScrollText, roles: ['admin'] },
      { id: 'dlq', label: 'DLQ', icon: FileWarning, roles: ['admin'] },
      { id: 'webhook', label: 'WEBHOOK', icon: Globe, roles: ['admin'] },
      { id: 'users', label: 'ACCOUNT', icon: User, roles: ['admin'] },
    ],
  };

  const profileItem = { id: 'profile', label: 'PROFILE', icon: User };

  const hasRole = (item) => roles.some(r => item.roles?.includes(r));
  const visibleMainItems = mainMenuItems.filter(hasRole);
  const visibleAdminChildren = adminGroup.children.filter(hasRole);
  const showAdminGroup = visibleAdminChildren.length > 0;

  const adminChildActive = visibleAdminChildren.some((c) => c.id === activeTab);

  // Local collapse state for the admin tree; forced open whenever one of its
  // children is the active tab so the current selection stays visible.
  const [adminOpen, setAdminOpen] = useState(() => adminChildActive);
  const open = adminOpen || adminChildActive;

  const handleSelect = (id) => {
    setActiveTab(id);
    if (setMobileOpen) setMobileOpen(false);
  };

  // Leaf item (flat, used for the main menu, profile and the collapsed tree).
  const renderLeaf = (item, indented = false) => {
    const Icon = item.icon;
    const isActive = activeTab === item.id;

    return (
      <button
        key={item.id}
        onClick={() => handleSelect(item.id)}
        className={`w-full flex items-center transition-all duration-200 group relative ${collapsed ? 'lg:justify-center lg:h-14 lg:px-0 px-4 h-16 gap-5 text-left' : `${indented ? 'h-12 pl-12 pr-5 gap-3' : 'gap-5 px-5 h-16'} text-left`
          } ${isActive
            ? 'bg-emerald-500 text-black font-black border-l-2 border-black'
            : 'text-slate-400 hover:text-emerald-400 hover:bg-emerald-950/20 border border-transparent border-l-2 border-l-transparent'
          }`}
        title={collapsed ? item.label : undefined}
      >
        <Icon
          className={`shrink-0 transition-transform duration-200 group-hover:scale-110 ${isActive ? 'text-black' : 'text-emerald-500'
            } w-6 h-6`}
        />

        <span className={`text-sm font-black tracking-[0.1em] font-display truncate uppercase ${collapsed ? 'lg:hidden inline' : 'inline'
          } ${indented ? 'text-xs' : ''}`}>
          {item.label}
        </span>

        {/* Tooltip for collapsed sidebar */}
        {collapsed && (
          <div className="absolute left-full ml-5 px-3 py-1.5 bg-black/95 border border-emerald-500/30 text-emerald-400 text-[11px] font-black opacity-0 group-hover:opacity-100 pointer-events-none transition-all duration-150 whitespace-nowrap z-50 lg:block hidden uppercase tracking-widest">
            {item.label}
          </div>
        )}
      </button>
    );
  };

  // Collapsible admin group with a downward tree of its children.
  const renderAdminGroup = () => {
    const Icon = adminGroup.icon;
    const isActive = adminChildActive;

    return (
      <div className="space-y-1">
        <button
          onClick={() => setAdminOpen((o) => !o)}
          className={`w-full flex items-center transition-all duration-200 group relative gap-5 px-5 h-16 text-left ${isActive
            ? 'bg-emerald-500/10 text-emerald-400 font-black border-l-2 border-emerald-500'
            : 'text-slate-400 hover:text-emerald-400 hover:bg-emerald-950/20 border border-transparent border-l-2 border-l-transparent'
            }`}
          title={collapsed ? adminGroup.label : undefined}
        >
          <Icon
            className={`shrink-0 transition-transform duration-200 group-hover:scale-110 ${isActive ? 'text-emerald-400' : 'text-emerald-500'
              } w-6 h-6`}
          />
          <span className="text-sm font-black tracking-[0.1em] font-display truncate uppercase">
            {adminGroup.label}
          </span>
          <ChevronDown
            className={`ml-auto w-4 h-4 transition-transform duration-200 ${open ? 'rotate-180' : ''} ${collapsed ? 'lg:hidden' : ''}`}
          />

          {collapsed && (
            <div className="absolute left-full ml-5 px-3 py-1.5 bg-black/95 border border-emerald-500/30 text-emerald-400 text-[11px] font-black opacity-0 group-hover:opacity-100 pointer-events-none transition-all duration-150 whitespace-nowrap z-50 lg:block hidden uppercase tracking-widest">
              {adminGroup.label}
            </div>
          )}
        </button>

        {/* Downward tree of admin tools */}
        {open && (
          <div className={`${collapsed ? 'lg:hidden' : ''} ml-6 border-l border-emerald-500/15 pl-1 space-y-1`}>
            {visibleAdminChildren.map((child) => (
              <div key={child.id} className="relative">
                <span className="absolute -left-[5px] top-1/2 -translate-y-1/2 w-3 h-px bg-emerald-500/20" />
                {renderLeaf(child, true)}
              </div>
            ))}
          </div>
        )}
      </div>
    );
  };

  return (
    <>
      {/* Backdrop for mobile view */}
      {mobileOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm lg:hidden transition-opacity duration-300"
          onClick={() => setMobileOpen(false)}
        />
      )}

      <aside
        className={`fixed lg:sticky top-0 left-0 z-50 h-screen flex flex-col border-r border-emerald-500/15 bg-[#030705] transition-all duration-300 ${hidden ? 'lg:w-0 lg:border-r-0 overflow-hidden' : (collapsed ? 'lg:w-20' : 'lg:w-72')
          } ${mobileOpen ? 'translate-x-0 w-72' : '-translate-x-full lg:translate-x-0'
          }`}
      >
        {/* Top Branding Section */}
        <div className="px-6 border-b border-emerald-500/10 flex items-center justify-between h-14 sm:h-16 lg:h-20">
          {/* Collapsed State Logo (Desktop Only) */}
          <div className={`mx-auto animate-fadeIn ${collapsed ? 'lg:flex hidden' : 'hidden'
            }`}>
            <img src={`${import.meta.env.BASE_URL || '/'}favicon.svg`} className="w-8 h-8 select-none" alt="Smart Farm Icon" />
          </div>

          {/* Full Branding (Mobile always, Desktop only if not collapsed) */}
          <div className={`items-center justify-between w-full ${collapsed ? 'flex lg:hidden' : 'flex'
            }`}>
            <div className="flex items-center animate-fadeIn overflow-hidden select-none">
              <img src={`${import.meta.env.BASE_URL || '/'}Smart Farm Logo.svg`} className="h-10 w-auto object-contain" alt="Smart Farm Logo" />
            </div>

            {/* Close drawer button (Mobile Only) */}
            <button
              onClick={() => setMobileOpen(false)}
              className="lg:hidden p-2  border border-emerald-500/20 text-slate-400 hover:text-emerald-400 hover:bg-emerald-950/20 cursor-pointer transition-all"
            >
              <X className="w-6 h-6" />
            </button>
          </div>
        </div>

        {/* Navigation Menu */}
        <nav className={`flex-1 py-8 flex flex-col justify-between overflow-y-auto ${collapsed ? 'lg:px-3 px-5' : 'px-5'}`}>
          <div className="space-y-4">
            {visibleMainItems.map((item) => renderLeaf(item))}
            {showAdminGroup &&
              (collapsed
                ? visibleAdminChildren.map((item) => renderLeaf(item))
                : renderAdminGroup())}
          </div>

          <div className="mt-auto pt-6 border-t border-emerald-500/10 space-y-4">
            {renderLeaf(profileItem)}
          </div>
        </nav>

        {/* Collapse Toggle Footer */}
        <div className="p-5 border-t border-emerald-500/10 hidden lg:flex justify-center">
          <button
            onClick={() => setCollapsed(!collapsed)}
            className="h-12 w-12 flex items-center justify-center  bg-emerald-950/20 border border-emerald-500/20 text-emerald-500 hover:bg-emerald-500 hover:text-black transition-all duration-200 cursor-pointer  active:scale-[0.95]"
            title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          >
            {collapsed ? <ChevronRight className="w-5 h-5" /> : <ChevronLeft className="w-5 h-5" />}
          </button>
        </div>
      </aside>
    </>
  );
}

export default Sidebar;
