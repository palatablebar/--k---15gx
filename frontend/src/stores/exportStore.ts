import { create } from 'zustand';
import { exportApi } from '../api/exports';
import { ApiError } from '../types/api';
import type { ExportRequest, GateGap } from '../types/models';
import { errorMessage } from '../utils/format';

interface ExportState {
  items: ExportRequest[];
  loading: boolean;
  busyId: string | null;
  error: string | null;
  load: () => Promise<void>;
  submit: (payload: { table_id: string; purpose: string; requested_rows: number }) => Promise<boolean>;
  precheck: (requestId: string) => Promise<boolean>;
  approve: (requestId: string, note: string) => Promise<boolean>;
  reject: (requestId: string, note: string) => Promise<boolean>;
}

/** 门禁拦截时把缺口明细拼进错误提示，台账行内也会同步展示。 */
const gateErrorMessage = (error: unknown): string => {
  if (error instanceof ApiError && error.code === 'EXPORT_GATE_BLOCKED') {
    const gaps = (error.extra?.gaps as GateGap[] | undefined) ?? [];
    if (gaps.length) {
      const lines = gaps.map((gap, index) => `${index + 1}. ${gap.message}`).join('\n');
      return `${error.message}（${gaps.length} 项缺口）：\n${lines}`;
    }
  }
  return errorMessage(error);
};

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
  precheck: async (requestId) => {
    set({ busyId: requestId, error: null });
    try {
      await exportApi.precheck(requestId);
      await get().load();
      set({ busyId: null });
      return true;
    } catch (error) {
      set({ busyId: null, error: errorMessage(error) });
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
      // 被门禁拦截时后端已落缺口，刷新台账让行内缺口列表同步显示
      const message = gateErrorMessage(error);
      if (error instanceof ApiError && error.code === 'EXPORT_GATE_BLOCKED') {
        await get().load();
      }
      set({ busyId: null, error: message });
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
