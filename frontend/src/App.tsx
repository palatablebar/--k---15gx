import { useEffect } from 'react';
import { RouterProvider } from 'react-router-dom';
import { router } from './router';
import { onUnauthorized } from './api/client';
import { useAuthStore } from './stores/authStore';

export const App = () => {
  const loadMe = useAuthStore((state) => state.loadMe);
  const logout = useAuthStore((state) => state.logout);

  useEffect(() => {
    void loadMe();
    onUnauthorized(() => {
      logout();
      window.location.assign('/login');
    });
  }, [loadMe, logout]);

  return <RouterProvider router={router} />;
};
