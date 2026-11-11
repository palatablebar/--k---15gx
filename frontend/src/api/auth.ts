import { api } from './client';
import type { User } from '../types/models';

interface LoginResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  user: User;
}

export const authApi = {
  login: (email: string, password: string) =>
    api.postAnonymous<LoginResponse>('/auth/login', { email, password }),
  me: () => api.get<{ user: User }>('/auth/me'),
  users: () => api.get<{ items: User[] }>('/auth/users'),
};
