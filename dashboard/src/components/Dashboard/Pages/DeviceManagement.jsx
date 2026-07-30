import { useState } from 'react';
import { Server, Plus, Edit2, Trash2, AlertTriangle, Save, X, Network } from 'lucide-react';
import { useModule } from '../../../context/useModule';
import { moduleApi } from '../../../api/module';
import NodeManagement from './NodeManagement';

function ModuleManagement({ onOpenNodeConfig }) {
  const { modules, fetchModules } = useModule();
  const [isEditing, setIsEditing] = useState(false);
  const [, setEditingModule] = useState(null);
  const [formData, setFormData] = useState({ id: null, name: '', description: '', config: '' });
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState('');
  const [selectedModuleForNodes, setSelectedModuleForNodes] = useState(null);

  const handleSave = async (e) => {
    e.preventDefault();
    if (!formData.name.trim()) {
      setError('Name is required.');
      return;
    }
    // Validate optional JSON config
    if (formData.config && formData.config.trim()) {
      try {
        JSON.parse(formData.config);
      } catch {
        setError('Config must be valid JSON (or leave it empty).');
        return;
      }
    }

    setIsSaving(true);
    setError('');
    try {
      const payload = {
        name: formData.name.trim(),
        description: formData.description.trim(),
        config: formData.config?.trim() || '{}',
      };
      if (formData.id) {
        await moduleApi.updateModule(formData.id, payload);
      } else {
        await moduleApi.createModule(payload);
      }
      await fetchModules();
      setIsEditing(false);
      setEditingModule(null);
    } catch (err) {
      setError(err.message || 'Failed to save module.');
    } finally {
      setIsSaving(false);
    }
  };

  const handleEdit = (mod) => {
    setEditingModule(mod);
    setFormData({
      id: mod.id,
      name: mod.name || '',
      description: mod.description || '',
      config: mod.config && mod.config !== '{}' ? mod.config : '',
    });
    setIsEditing(true);
    setError('');
  };

  const handleAddNew = () => {
    setEditingModule(null);
    setFormData({ id: null, name: '', description: '', config: '' });
    setIsEditing(true);
    setError('');
  };

  const handleDelete = async (mod) => {
    if (!window.confirm(`Delete module "${mod.name}"? Its nodes will be unpaired (not deleted).`)) return;
    try {
      await moduleApi.deleteModule(mod.id);
      await fetchModules();
    } catch (err) {
      alert(err.message || 'Failed to delete module.');
    }
  };

  if (selectedModuleForNodes) {
    return (
      <div className="flex flex-col gap-3 w-full animate-fadeIn">
        <NodeManagement
          selectedModule={selectedModuleForNodes}
          onBack={() => { setSelectedModuleForNodes(null); fetchModules(); }}
          onOpenNodeConfig={onOpenNodeConfig}
        />
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-3 w-full animate-fadeIn">
      <div className="border border-emerald-500/15 bg-[#030705]/80 backdrop-blur-md overflow-hidden">
        <div className="p-3 sm:p-4 border-b border-white/5 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
          <div className="flex items-center gap-3 sm:gap-4 w-full">
            <div className="p-3 sm:p-4 bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 shrink-0">
              <Server className="w-8 h-8 sm:w-10 sm:h-10" />
            </div>
            <div className="min-w-0 flex-1">
              <h2 className="text-xl sm:text-2xl font-black font-display text-white tracking-wide uppercase truncate">Modules</h2>
              <p className="hidden sm:block text-[11px] text-slate-400 mt-0.5">Create modules, then pair ESP32 devices.</p>
            </div>
          </div>
          {!isEditing && (
            <button
              onClick={handleAddNew}
              className="w-full sm:w-auto flex items-center justify-center gap-2 px-3 py-2 text-xs font-bold bg-emerald-500 text-black hover:bg-emerald-400 transition-colors uppercase tracking-wider shrink-0 cursor-pointer"
            >
              <Plus className="w-4 h-4" />
              Add Module
            </button>
          )}
        </div>

        <div className="p-3 sm:p-4">
          {isEditing ? (
            <form onSubmit={handleSave} className="animate-in fade-in slide-in-from-top-4 duration-300">
              <div className="grid grid-cols-1 gap-4 mb-6">
                <div>
                  <label className="block text-[10px] font-black text-emerald-400 uppercase tracking-widest mb-1.5">Module Name</label>
                  <input
                    type="text"
                    value={formData.name}
                    onChange={e => setFormData({ ...formData, name: e.target.value })}
                    className="w-full bg-slate-900/50 border border-slate-700 px-3 py-2 text-sm text-white focus:outline-none focus:border-emerald-500 transition-colors"
                    placeholder="e.g. Greenhouse Zone A"
                    required
                  />
                </div>
                <div>
                  <label className="block text-[10px] font-black text-emerald-400 uppercase tracking-widest mb-1.5">Description</label>
                  <input
                    type="text"
                    value={formData.description}
                    onChange={e => setFormData({ ...formData, description: e.target.value })}
                    className="w-full bg-slate-900/50 border border-slate-700 px-3 py-2 text-sm text-white focus:outline-none focus:border-emerald-500 transition-colors"
                    placeholder="e.g. Rooftop aeroponic zone"
                  />
                </div>
                <div>
                  <label className="block text-[10px] font-black text-emerald-400 uppercase tracking-widest mb-1.5">Config (JSON, optional)</label>
                  <textarea
                    value={formData.config}
                    onChange={e => setFormData({ ...formData, config: e.target.value })}
                    className="w-full bg-slate-900/50 border border-slate-700 px-3 py-2 text-sm text-white focus:outline-none focus:border-emerald-500 transition-colors font-mono h-24 resize-none"
                    placeholder='{"ph_target": 6.0}'
                  />
                  <p className="text-[9px] text-slate-500 mt-1 uppercase">Module settings in JSON format</p>
                </div>
              </div>

              {error && (
                <div className="mb-4 p-3 bg-red-500/10 border border-red-500/20 text-red-400 text-xs flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4" />
                  {error}
                </div>
              )}

              <div className="flex items-center gap-3 justify-end pt-4 border-t border-white/5">
                <button
                  type="button"
                  onClick={() => setIsEditing(false)}
                  className="px-4 py-2 text-xs font-bold text-slate-400 hover:text-white transition-colors uppercase tracking-wider flex items-center gap-2 cursor-pointer"
                >
                  <X className="w-3.5 h-3.5" />
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSaving}
                  className="px-4 py-2 text-xs font-black bg-emerald-500 text-black hover:bg-emerald-400 disabled:opacity-50 transition-colors uppercase tracking-widest flex items-center gap-2 cursor-pointer"
                >
                  <Save className="w-3.5 h-3.5" />
                  {isSaving ? 'Saving...' : (formData.id ? 'Update Module' : 'Save Module')}
                </button>
              </div>
            </form>
            ) : (
              <div>
                <div className="px-4 sm:px-6 py-4 border-b border-emerald-500/10 flex items-center gap-3">
                  <Server className="w-5 h-5 text-emerald-400" />
                  <h3 className="text-sm sm:text-base font-black font-display text-white tracking-widest uppercase">Module List</h3>
                </div>
                <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="border-b border-emerald-500/20 bg-slate-900/50">
                    <th className="py-4 px-4 text-xs font-black uppercase tracking-widest text-slate-300 align-middle leading-normal">Name</th>
                    <th className="py-4 px-4 text-xs font-black uppercase tracking-widest text-slate-300 align-middle leading-normal">Description</th>
                    <th className="py-4 px-4 text-xs font-black uppercase tracking-widest text-slate-300 align-middle leading-normal">Module ID</th>
                    <th className="py-4 px-4 text-xs font-black uppercase tracking-widest text-slate-300 text-right align-middle leading-normal">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {modules.length === 0 ? (
                    <tr>
                      <td colSpan="4" className="py-8 text-center text-slate-500 text-xs">No modules yet. Click "Add Module" to create one.</td>
                    </tr>
                  ) : (
                    modules.map(mod => (
                      <tr key={mod.id} className="border-b border-white/5 last:border-0 hover:bg-white/5 transition-colors group">
                        <td className="py-3 pr-4">
                          <span className="text-sm font-bold text-white">{mod.name || 'Unnamed'}</span>
                        </td>
                        <td className="py-3 pr-4">
                          <span className="text-xs text-slate-400">{mod.description || '-'}</span>
                        </td>
                        <td className="py-3 pr-4">
                          <span className="font-mono text-[11px] text-emerald-400/70">{mod.id.slice(0, 8)}…</span>
                        </td>
                        <td className="py-3 text-right">
                          <div className="flex justify-end gap-2 opacity-50 group-hover:opacity-100 transition-opacity">
                            <button
                              onClick={() => setSelectedModuleForNodes(mod)}
                              className="p-1.5 bg-slate-800 hover:bg-blue-500/20 hover:text-blue-400 text-slate-400 transition-colors cursor-pointer"
                              title="Manage / Pair Nodes"
                            >
                              <Network className="w-3.5 h-3.5" />
                            </button>
                            <button
                              onClick={() => handleEdit(mod)}
                              className="p-1.5 bg-slate-800 hover:bg-emerald-500/20 hover:text-emerald-400 text-slate-400 transition-colors cursor-pointer"
                              title="Edit Module"
                            >
                              <Edit2 className="w-3.5 h-3.5" />
                            </button>
                            <button
                              onClick={() => handleDelete(mod)}
                              className="p-1.5 bg-slate-800 hover:bg-red-500/20 hover:text-red-400 text-slate-400 transition-colors cursor-pointer"
                              title="Delete Module"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}
        </div>
      </div>
    </div>
  );
}

export default ModuleManagement;
