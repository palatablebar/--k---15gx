import { api } from './client';
import type { ExportRequest } from '../types/models';
import type { ListResponse } from '../types/api';

export const exportApi = {
  list: () => api.get<ListResponse<ExportRequest>>('/exports'),
  create: (payload: { table_id: string; purpose: string; requested_rows: number }) =>
    api.post<{ request: ExportRequest }>('/exports', payload),
  approve: (requestId: string, note: string) =>
    api.post<{ request: ExportRequest }>(`/exports/${requestId}/approve`, { note }),
  reject: (requestId: string, note: string) =>
    api.post<{ request: ExportRequest }>(`/exports/${requestId}/reject`, { note }),
  downloadUrl: (requestId: string) => api.downloadPath(`/exports/${requestId}/download`),
};
