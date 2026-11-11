import { redirect } from 'react-router-dom';
import { tokenStore } from '../api/client';

/** 未登录直接回登录页，不闪一下空壳。 */
export const requireAuth = () => {
  if (!tokenStore.get()) {
    return redirect('/login');
  }
  return null;
};
