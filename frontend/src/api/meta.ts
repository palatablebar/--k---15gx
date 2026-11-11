import { api } from './client';

export interface MetaEnums {
  pii_types: Record<string, string>;
  mask_methods: Record<string, string>;
  sensitivity_levels: Record<string, string>;
  export_statuses: Record<string, string>;
  column_roles: Record<string, string>;
  roles: Record<string, string>;
  permissions: Record<string, string[]>;
  generalize_kinds: string[];
  algorithm_versions: Record<string, string>;
  params: Record<string, unknown>;
}

export interface HealthResponse {
  status: string;
  service: string;
  version: string;
  db: boolean;
  redis: boolean;
  worker: { heartbeat_age_seconds: number | null; alive: boolean };
  algorithm_versions: Record<string, string>;
}

export const metaApi = {
  enums: () => api.get<MetaEnums>('/meta/enums'),
  health: () => api.get<HealthResponse>('/health'),
};
