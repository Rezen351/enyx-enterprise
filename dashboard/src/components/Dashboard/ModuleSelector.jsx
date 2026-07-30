import { Server, ChevronDown, Loader2 } from 'lucide-react';
import { useModule } from '../../context/useModule';

function ModuleSelector() {
  const { modules, selectedModule, setSelectedModule, loadingModules } = useModule();

  const handleChange = (e) => {
    const id = e.target.value;
    const next = modules.find((m) => m.id === id) || null;
    setSelectedModule(next);
  };

  return (
    <div className="flex items-center gap-2 shrink-0">
      <div className="hidden md:flex items-center gap-1.5 text-[10px] font-black uppercase tracking-widest text-slate-400">
        <Server className="w-3.5 h-3.5 text-emerald-400" />
        Module
      </div>
      <div className="relative">
        <select
          value={selectedModule?.id || ''}
          onChange={handleChange}
          disabled={loadingModules || modules.length === 0}
          className="h-10 pl-3 pr-8 appearance-none bg-black/40 border border-emerald-500/20 text-slate-200 text-xs font-bold uppercase tracking-wider outline-none focus:border-emerald-400 hover:border-emerald-400/60 transition-colors cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed max-w-[160px] sm:max-w-[200px]"
          title="Select module to view"
        >
          {loadingModules && <option value="">Loading…</option>}
          {!loadingModules && modules.length === 0 && <option value="">No module</option>}
          {!loadingModules &&
            modules.map((m) => (
              <option key={m.id} value={m.id} className="bg-[#030705] text-slate-200 normal-case">
                {m.name}
              </option>
            ))}
        </select>
        <div className="absolute right-2 top-1/2 -translate-y-1/2 pointer-events-none text-emerald-400">
          {loadingModules ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <ChevronDown className="w-4 h-4" />
          )}
        </div>
      </div>
    </div>
  );
}

export default ModuleSelector;
