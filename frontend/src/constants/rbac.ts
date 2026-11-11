import type { Role } from '../types/models';

export type Permission =
  | 'datasets:read'
  | 'datasets:scan'
  | 'pii:read'
  | 'pii:review'
  | 'policies:read'
  | 'policies:write'
  | 'policies:preview'
  | 'kanon:read'
  | 'kanon:run'
  | 'exports:read'
  | 'exports:create'
  | 'exports:approve'
  | 'audit:read';

/** 与后端 src/constants/roles.py::PERMISSIONS 一致 */
export const PERMISSION_MATRIX: Record<Role, Permission[]> = {
  admin: [
    'datasets:read',
    'datasets:scan',
    'pii:read',
    'pii:review',
    'policies:read',
    'policies:write',
    'policies:preview',
    'kanon:read',
    'kanon:run',
    'exports:read',
    'exports:create',
    'exports:approve',
    'audit:read',
  ],
  dpo: [
    'datasets:read',
    'datasets:scan',
    'pii:read',
    'pii:review',
    'policies:read',
    'policies:preview',
    'kanon:read',
    'kanon:run',
    'exports:read',
    'exports:create',
    'exports:approve',
    'audit:read',
  ],
  client: ['datasets:read', 'pii:read', 'policies:read', 'kanon:read', 'exports:read', 'exports:create'],
};
