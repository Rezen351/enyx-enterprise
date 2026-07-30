import { createContext, useState, useEffect, useCallback } from 'react';
import { moduleApi } from '../api/module';

const ModuleContext = createContext(null);

export { ModuleContext };

export function ModuleProvider({ children }) {
  const [modules, setModules] = useState([]);
  const [loadingModules, setLoadingModules] = useState(true);

  // Persist selectedModule to localStorage
  const [selectedModule, setSelectedModuleState] = useState(() => {
    try {
      const saved = localStorage.getItem('selectedModule');
      return saved ? JSON.parse(saved) : null;
    } catch {
      return null;
    }
  });

  const setSelectedModule = (module) => {
    setSelectedModuleState(module);
    try {
      if (module) localStorage.setItem('selectedModule', JSON.stringify(module));
      else localStorage.removeItem('selectedModule');
    } catch (err) {
      console.warn('ModuleContext: Failed to save selection', err);
    }
  };

  const fetchModules = useCallback(async () => {
    setLoadingModules(true);
    try {
      const data = await moduleApi.listModules();
      const list = (data?.modules || []).map((m) => ({
        id: m.id,
        name: m.name,
        description: m.description || '',
        config: m.config || '{}',
        createdAt: m.created_at,
        updatedAt: m.updated_at,
      }));
      setModules(list);

      // Keep the current selection if it still exists, otherwise pick the first.
      setSelectedModuleState((prev) => {
        const next = (prev && list.find((m) => m.id === prev.id)) || list[0] || null;
        try {
          if (next) localStorage.setItem('selectedModule', JSON.stringify(next));
          else localStorage.removeItem('selectedModule');
        } catch { /* ignore */ }
        return next;
      });
    } catch (err) {
      console.warn('ModuleContext: Failed to fetch modules', err);
      setModules([]);
      // Do NOT reset selectedModule to null on transient API failure.
      // Keep the persisted localStorage value so the dashboard
      // retains its module selection across service restarts.
    } finally {
      setLoadingModules(false);
    }
  }, []);

  // Retry fetchModules with exponential backoff on failure,
  // so the dashboard eventually recovers when the backend is ready.
  useEffect(() => {
    let cancelled = false;
    let retryCount = 0;
    const maxRetries = 10;
    const baseDelay = 2000;

    const tryFetch = async () => {
      if (cancelled) return;
      try {
        await fetchModules();
      } catch {
        retryCount++;
        if (retryCount < maxRetries) {
          const delay = Math.min(baseDelay * Math.pow(2, retryCount - 1), 30000);
          setTimeout(tryFetch, delay);
        }
      }
    };

    tryFetch();
    return () => { cancelled = true; };
  }, [fetchModules]);

  return (
    <ModuleContext.Provider value={{ modules, selectedModule, setSelectedModule, loadingModules, fetchModules }}>
      {children}
    </ModuleContext.Provider>
  );
}
