import { create } from 'zustand';
import { kanonApi, type CreateCheckPayload } from '../api/kanon';
import type { KanonCheck } from '../types/models';
import { errorMessage } from '../utils/format';

interface KanonState {
  checks: KanonCheck[];
  current: KanonCheck | null;
  running: boolean;
  loading: boolean;
  error: string | null;
  load: () => Promise<void>;
  run: (payload: CreateCheckPayload) => Promise<KanonCheck | null>;
  refreshCurrent: () => Promise<KanonCheck | null>;
  setCurrent: (check: KanonCheck | null) => void;
}

export const useKanonStore = create<KanonState>((set, get) => ({
  checks: [],
  current: null,
  running: false,
  loading: false,
  error: null,
  load: async () => {
    set({ loading: true, error: null });
    try {
      const response = await kanonApi.list();
      set({
        checks: response.items,
        current: get().current ?? response.items[0] ?? null,
        loading: false,
      });
    } catch (error) {
      set({ loading: false, error: errorMessage(error) });
    }
  },
  run: async (payload) => {
    set({ running: true, error: null });
    try {
      const response = await kanonApi.create(payload);
      set({ current: response.check, running: false, checks: [response.check, ...get().checks] });
      return response.check;
    } catch (error) {
      set({ running: false, error: errorMessage(error) });
      return null;
    }
  },
  refreshCurrent: async () => {
    const current = get().current;
    if (!current) return null;
    try {
      const response = await kanonApi.detail(current.id);
      set({
        current: response.check,
        checks: get().checks.map((item) => (item.id === response.check.id ? response.check : item)),
      });
      return response.check;
    } catch (error) {
      set({ error: errorMessage(error) });
      return null;
    }
  },
  setCurrent: (check) => set({ current: check }),
}));
