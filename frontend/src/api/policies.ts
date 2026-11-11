import { api } from './client';
import type { MaskingPolicy, PolicyPreview } from '../types/models';
import type { ListResponse } from '../types/api';

export const policyApi = {
  list: () => api.get<ListResponse<MaskingPolicy>>('/policies'),
  preview: (policyId: string) => api.post<PolicyPreview>(`/policies/${policyId}/preview`, {}),
  create: (payload: Record<string, unknown>) => api.post<{ policy: MaskingPolicy }>('/policies', payload),
  update: (policyId: string, payload: Record<string, unknown>) =>
    api.patch<{ policy: MaskingPolicy }>(`/policies/${policyId}`, payload),
};
