export interface ApiErrorShape {
  code: string;
  message: string;
  detail?: string;
  trace_id?: string | null;
  extra?: Record<string, unknown>;
}

export class ApiError extends Error {
  status: number;
  code: string;
  detail: string;
  traceId: string | null;
  extra: Record<string, unknown>;

  constructor(status: number, payload: ApiErrorShape) {
    super(payload.message || '请求失败');
    this.status = status;
    this.code = payload.code || 'INTERNAL_ERROR';
    this.detail = payload.detail ?? '';
    this.traceId = payload.trace_id ?? null;
    this.extra = payload.extra ?? {};
  }
}

export interface ListResponse<T> {
  items: T[];
}
