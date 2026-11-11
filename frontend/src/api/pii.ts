import { api } from './client';
import type { DatasetColumn, DatasetTable, PiiFinding } from '../types/models';
import type { ListResponse } from '../types/api';

export interface ColumnEvidenceResponse {
  column: DatasetColumn;
  table: DatasetTable;
  finding: PiiFinding;
}

export const piiApi = {
  findings: (tableId?: string) =>
    api.get<ListResponse<PiiFinding>>(`/pii/findings${tableId ? `?table_id=${tableId}` : ''}`),
  columnEvidence: (columnId: string) => api.get<ColumnEvidenceResponse>(`/pii/columns/${columnId}`),
};
