import { api } from './client';
import type { DatasetColumn, DatasetTable, ScanResult, TableDetail } from '../types/models';
import type { ListResponse } from '../types/api';

export const datasetApi = {
  list: () => api.get<ListResponse<DatasetTable>>('/datasets'),
  detail: (tableId: string) => api.get<TableDetail>(`/datasets/${tableId}`),
  columns: (tableId: string) => api.get<ListResponse<DatasetColumn>>(`/datasets/${tableId}/columns`),
  scan: (tableId: string) => api.post<ScanResult>(`/datasets/${tableId}/scan`, {}),
};
