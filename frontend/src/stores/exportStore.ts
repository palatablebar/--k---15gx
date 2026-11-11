import { create } from 'zustand';
import { exportApi } from '../api/exports';
import type { ExportRequest } from '../types/models';
import { errorMessage } from '../utils/format';

interface ExportState {
  items: ExportRequest[];
  loading: boolean;
  busyId: string | null;
  error: string | null;
  load: () => Promise<void>;
  submit: (payload: { table_id: string; purpose: string; requested_rows: number }) => Promise<boolean>;
  approve: (requestId: string, note: string) => Promise<boolean>;
  reject: (requestId: string, note: string) => Promise<boolean>;
}

export const useExportStore = create<ExportState>((set, get) => ({
  items: [],
  loading: false,
  busyId: null,
  error: null,
  load: async () => {
    set({ loading: true, error: null });
    try {
      const response = await exportApi.list();
      set({ items: response.items, loading: false });
    } catch (error) {
      set({ loading: false, error: errorMessage(error) });
    }
  },
  submit: async (payload) => {
    set({ error: null });
    try {
      await exportApi.create(payload);
      await get().load();
      return true;
    } catch (error) {
      set({ error: errorMessage(error) });
      return false;
    }
  },
  approve: async (requestId, note) => {
    set({ busyId: requestId, error: null });
    try {
      await exportApi.approve(requestId, note);
      await get().load();
      set({ busyId: null });
      return true;
    } catch (error) {
      set({ busyId: null, error: errorMessage(error) });
      return false;
    }
  },
  reject: async (requestId, note) => {
    set({ busyId: requestId, error: null });
    try {
      await exportApi.reject(requestId, note);
      await get().load();
      set({ busyId: null });
      return true;
    } catch (error) {
      set({ busyId: null, error: errorMessage(error) });
      return false;
    }
  },
}));
