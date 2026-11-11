import { api } from './client';
import type { AuditLog } from '../types/models';
import type { ListResponse } from '../types/api';

export const auditApi = {
  logs: (limit = 50) => api.get<ListResponse<AuditLog>>(`/audit/logs?limit=${limit}`),
};
