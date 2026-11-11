import { ApiError } from '../types/api';

export const formatDate = (value: string | null): string => {
  if (!value) return '—';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  const pad = (input: number) => String(input).padStart(2, '0');
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(
    date.getHours(),
  )}:${pad(date.getMinutes())}`;
};

export const formatPercent = (value: number | null | undefined, digits = 1): string => {
  if (value === null || value === undefined || Number.isNaN(value)) return '—';
  return `${(value * 100).toFixed(digits)}%`;
};

export const formatNumber = (value: number | null | undefined): string => {
  if (value === null || value === undefined || Number.isNaN(value)) return '—';
  return value.toLocaleString('en-US');
};

export const shortId = (value: string): string => value.slice(0, 8);

export const errorMessage = (error: unknown): string => {
  if (error instanceof ApiError) return error.message;
  if (error instanceof Error) return error.message;
  return '操作失败，请重试';
};

export const methodParamText = (params: Record<string, unknown>): string => {
  const parts: string[] = [];
  if (params.keep_prefix !== undefined) parts.push(`前 ${String(params.keep_prefix)} 位`);
  if (params.keep_suffix !== undefined) parts.push(`后 ${String(params.keep_suffix)} 位`);
  if (params.digest_len !== undefined) parts.push(`截取 ${String(params.digest_len)} 位`);
  if (params.prefix) parts.push(`前缀 ${String(params.prefix)}`);
  if (params.kind) parts.push(`泛化 ${String(params.kind)}`);
  if (params.width !== undefined) parts.push(`区间 ${String(params.width)} 岁`);
  if (params.keep !== undefined) parts.push(`保留 ${String(params.keep)}`);
  if (params.replacement) parts.push(`替换 ${String(params.replacement)}`);
  return parts.length ? parts.join(' · ') : '默认参数';
};
