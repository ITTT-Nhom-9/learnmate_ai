import { useCallback } from 'react';
import { authApi } from '../api/authApi';
import { useAuthStore } from '../store/useAuthStore';

/** Hook quản lý trạng thái đăng nhập & phân quyền. */
export function useAuth() {
  const user = useAuthStore((s) => s.user);
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const isInitializing = useAuthStore((s) => s.isInitializing);
  const setSession = useAuthStore((s) => s.setSession);

  /** Đăng nhập và lưu JWT vào Zustand store. Ném lỗi axios để trang tự hiển thị. */
  const login = useCallback(
    async ({ email, password, remember = false }) => {
      const data = await authApi.login({ email, password });
      setSession({
        user: data.user,
        accessToken: data.access_token,
        refreshToken: data.refresh_token,
        remember,
      });
      return data.user;
    },
    [setSession]
  );

  const register = useCallback((payload) => authApi.register(payload), []);
  const logout = useCallback(() => authApi.logout(), []);

  return {
    user,
    isAuthenticated,
    isInitializing,
    isAdmin: user?.role === 'ADMIN',
    login,
    register,
    logout,
  };
}
