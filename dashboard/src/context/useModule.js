import { useContext } from 'react';
import { ModuleContext } from './ModuleContext';

export function useModule() {
  const ctx = useContext(ModuleContext);
  if (!ctx) throw new Error('useModule must be used inside ModuleProvider');
  return ctx;
}
