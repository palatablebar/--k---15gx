import { create } from 'zustand';
import { policyApi } from '../api/policies';
import type { MaskingPolicy, PolicyPreview } from '../types/models';
import { errorMessage } from '../utils/format';

interface PolicyState {
  policies: MaskingPolicy[];
  selectedId: string | null;
  preview: PolicyPreview | null;
  loading: boolean;
  previewing: boolean;
  error: string | null;
  load: () => Promise<void>;
  select: (policyId: string) => void;
  runPreview: () => Promise<PolicyPreview | null>;
}

export const usePolicyStore = create<PolicyState>((set, get) => ({
  policies: [],
  selectedId: null,
  preview: null,
  loading: false,
  previewing: false,
  error: null,
  load: async () => {
    set({ loading: true, error: null });
    try {
      const response = await policyApi.list();
      const selected = get().selectedId ?? response.items[0]?.id ?? null;
      set({ policies: response.items, selectedId: selected, loading: false });
    } catch (error) {
      set({ loading: false, error: errorMessage(error) });
    }
  },
  select: (policyId) => set({ selectedId: policyId, preview: null, error: null }),
  runPreview: async () => {
    const policyId = get().selectedId;
    if (!policyId) return null;
    set({ previewing: true, error: null });
    try {
      const preview = await policyApi.preview(policyId);
      set({ preview, previewing: false });
      return preview;
    } catch (error) {
      set({ previewing: false, error: errorMessage(error), preview: null });
      return null;
    }
  },
}));
