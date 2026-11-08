import axiosClient, { refreshAccessToken } from './axiosClient';
import { useAuthStore } from '../store/useAuthStore';

// Response của Backend là object phẳng (không bọc trong { data }), xem backend/app/schemas/auth.py.
export const authApi = {
  /** API-01 -> { user_id, email, full_name, role, created_at } */
  register: ({ email, password, fullName }) =>
    axiosClient.post('/auth/register', { email, password, full_name: fullName }),

  /** API-02 -> { access_token, refresh_token, token_type, expires_in, user } */
  login: ({ email, password }) => axiosClient.post('/auth/login', { email, password }),

  /**
   * API-04. Luôn xóa phiên phía client dù Backend lỗi.
   * Access Token hết hạn thì refresh trước rồi mới thu hồi, để refresh token không còn hiệu lực trên server.
   */
  async logout() {
    const send = () =>
      axiosClient.post('/auth/logout', { refresh_token: useAuthStore.getState().refreshToken });
    try {
      try {
        await send();
      } catch (error) {
        if (error.response?.status !== 401) throw error;
        await refreshAccessToken();
        await send();
      }
    } catch {
      /* bỏ qua: người dùng vẫn được đăng xuất khỏi giao diện */
    } finally {
      useAuthStore.getState().clearSession();
    }
  },

  /** Khôi phục phiên khi mở lại trang: đổi refresh token đã lưu lấy Access Token mới (nằm trong bộ nhớ). */
  async restoreSession() {
    const { refreshToken, user, clearSession, finishInitializing } = useAuthStore.getState();
    if (!refreshToken || !user) {
      clearSession();
      return false;
    }
    try {
      await refreshAccessToken();
      return true;
    } catch {
      finishInitializing();
      return false;
    }
  },
};
