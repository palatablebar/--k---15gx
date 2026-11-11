import { useCallback, useState } from 'react';
import { ApiError } from '../types/api';
import { errorMessage } from '../utils/format';

/** 统一错误展示：优先展示后端 detail，保留 code 方便排查。 */
export const useApiError = () => {
  const [message, setMessage] = useState<string | null>(null);

  const capture = useCallback((error: unknown) => {
    if (error instanceof ApiError) {
      setMessage(`${error.message}${error.detail ? `（${error.detail}）` : ''}`);
      return error;
    }
    setMessage(errorMessage(error));
    return error;
  }, []);

  const clear = useCallback(() => setMessage(null), []);

  return { message, capture, clear, setMessage };
};
