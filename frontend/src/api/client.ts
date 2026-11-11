import { ApiError, type ApiErrorShape } from '../types/api';

const TOKEN_KEY = 'maskguard.access_token';
const REFRESH_KEY = 'maskguard.refresh_token';

export const tokenStore = {
  get: () => localStorage.getItem(TOKEN_KEY),
  getRefresh: () => localStorage.getItem(REFRESH_KEY),
  set: (access: string, refresh?: string) => {
    localStorage.setItem(TOKEN_KEY, access);
    if (refresh) localStorage.setItem(REFRESH_KEY, refresh);
  },
  clear: () => {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(REFRESH_KEY);
  },
};

let unauthorizedHandler: (() => void) | null = null;
export const onUnauthorized = (handler: () => void) => {
  unauthorizedHandler = handler;
};

const BASE = '/api';

interface RequestOptions {
  method?: string;
  body?: unknown;
  auth?: boolean;
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = 'GET', body, auth = true } = options;
  const headers: Record<string, string> = {};
  if (body !== undefined) headers['Content-Type'] = 'application/json';
  const token = tokenStore.get();
  if (auth && token) headers.Authorization = `Bearer ${token}`;

  const response = await fetch(`${BASE}${path}`, {
    method,
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
  });

  if (!response.ok) {
    let payload: ApiErrorShape = { code: 'INTERNAL_ERROR', message: response.statusText, detail: '' };
    try {
      payload = (await response.json()) as ApiErrorShape;
    } catch {
      /* 非 JSON 错误体 */
    }
    if (response.status === 401 && auth) {
      tokenStore.clear();
      unauthorizedHandler?.();
    }
    throw new ApiError(response.status, payload);
  }

  if (response.status === 204) return undefined as T;
  const contentType = response.headers.get('content-type') ?? '';
  if (contentType.includes('application/json')) return (await response.json()) as T;
  return (await response.text()) as unknown as T;
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body?: unknown) => request<T>(path, { method: 'POST', body }),
  patch: <T>(path: string, body?: unknown) => request<T>(path, { method: 'PATCH', body }),
  del: <T>(path: string) => request<T>(path, { method: 'DELETE' }),
  postAnonymous: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: 'POST', body, auth: false }),
  downloadPath: (path: string) => `${BASE}${path}`,
};
