import { create } from 'zustand';
import { authApi } from '../api/auth';
import { tokenStore } from '../api/client';
import type { User } from '../types/models';
import { PERMISSION_MATRIX, type Permission } from '../constants/rbac';

interface AuthState {
  user: User | null;
  token: string | null;
  loading: boolean;
  error: string | null;
  login: (email: string, password: string) => Promise<User>;
  logout: () => void;
  loadMe: () => Promise<User | null>;
  can: (permission: Permission) => boolean;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  user: null,
  token: tokenStore.get(),
  loading: false,
  error: null,
  login: async (email, password) => {
    set({ loading: true, error: null });
    try {
      const response = await authApi.login(email, password);
      tokenStore.set(response.access_token, response.refresh_token);
      set({ user: response.user, token: response.access_token, loading: false });
      return response.user;
    } catch (error) {
      set({ loading: false, error: error instanceof Error ? error.message : '登录失败' });
      throw error;
    }
  },
  logout: () => {
    tokenStore.clear();
    set({ user: null, token: null });
  },
  loadMe: async () => {
    if (!tokenStore.get()) return null;
    try {
      const response = await authApi.me();
      set({ user: response.user, token: tokenStore.get() });
      return response.user;
    } catch {
      set({ user: null });
      return null;
    }
  },
  can: (permission) => {
    const role = get().user?.role;
    if (!role) return false;
    return PERMISSION_MATRIX[role].includes(permission);
  },
}));
