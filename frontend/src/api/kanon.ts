import { api } from './client';
import type { KanonCheck } from '../types/models';
import type { ListResponse } from '../types/api';

export interface CreateCheckPayload {
  table_id: string;
  quasi_identifiers: string[];
  sensitive_column: string;
  target_k: number;
  target_l: number;
}

export const kanonApi = {
  list: () => api.get<ListResponse<KanonCheck>>('/k-anonymity/checks'),
  detail: (checkId: string) => api.get<{ check: KanonCheck }>(`/k-anonymity/checks/${checkId}`),
  create: (payload: CreateCheckPayload) => api.post<{ check: KanonCheck }>('/k-anonymity/checks', payload),
};
