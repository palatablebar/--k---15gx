import { create } from 'zustand';
import { datasetApi } from '../api/datasets';
import type { DatasetTable, ScanResult, TableDetail } from '../types/models';
import { errorMessage } from '../utils/format';

interface DatasetState {
  tables: DatasetTable[];
  selectedTableId: string | null;
  detail: TableDetail | null;
  loading: boolean;
  scanning: boolean;
  error: string | null;
  lastScan: ScanResult | null;
  loadTables: () => Promise<void>;
  selectTable: (tableId: string) => Promise<void>;
  scan: () => Promise<ScanResult | null>;
}

export const useDatasetStore = create<DatasetState>((set, get) => ({
  tables: [],
  selectedTableId: null,
  detail: null,
  loading: false,
  scanning: false,
  error: null,
  lastScan: null,
  loadTables: async () => {
    set({ loading: true, error: null });
    try {
      const response = await datasetApi.list();
      const current = get().selectedTableId;
      const nextId = current ?? response.items[0]?.id ?? null;
      set({ tables: response.items, selectedTableId: nextId, loading: false });
      if (nextId) await get().selectTable(nextId);
    } catch (error) {
      set({ loading: false, error: errorMessage(error) });
    }
  },
  selectTable: async (tableId) => {
    set({ selectedTableId: tableId, loading: true, error: null });
    try {
      const detail = await datasetApi.detail(tableId);
      set({ detail, loading: false });
    } catch (error) {
      set({ loading: false, error: errorMessage(error) });
    }
  },
  scan: async () => {
    const tableId = get().selectedTableId;
    if (!tableId) return null;
    set({ scanning: true, error: null });
    try {
      const result = await datasetApi.scan(tableId);
      set({ lastScan: result, scanning: false });
      await get().loadTables();
      await get().selectTable(tableId);
      return result;
    } catch (error) {
      set({ scanning: false, error: errorMessage(error) });
      return null;
    }
  },
}));
