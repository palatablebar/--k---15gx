import { useEffect, useRef } from 'react';
import type { KanonCheck } from '../types/models';

/** k-匿名由 worker 异步计算：完成后台轮询直到 succeeded / failed。 */
export const useCheckPolling = (
  check: KanonCheck | null,
  refresh: () => Promise<KanonCheck | null>,
  intervalMs = 1200,
) => {
  const timer = useRef<number | null>(null);

  useEffect(() => {
    if (!check) return undefined;
    const pending = check.status === 'queued' || check.status === 'running';
    if (!pending) return undefined;
    timer.current = window.setTimeout(() => {
      void refresh();
    }, intervalMs);
    return () => {
      if (timer.current) window.clearTimeout(timer.current);
    };
  }, [check, refresh, intervalMs]);
};
