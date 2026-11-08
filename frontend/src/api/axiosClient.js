import axios from 'axios';
import { useAuthStore } from '../store/useAuthStore';

const baseURL = import.meta.env.VITE_API_URL || 'http://localhost:8080/api/v1';
const jsonHeaders = { 'Content-Type': 'application/json' };

const axiosClient = axios.create({ baseURL, headers: jsonHeaders, timeout: 30000 });

// Client riêng, KHÔNG gắn interceptor, dùng để gọi /auth/refresh (tránh vòng lặp 401).
const refreshClient = axios.create({ baseURL, headers: jsonHeaders, timeout: 30000 });

// Dùng chung một Promise cho mọi lần refresh đồng thời. Backend xoay vòng refresh token,
// nếu hai request cùng dùng một token cũ thì token bị coi là bị đánh cắp và thu hồi toàn bộ phiên.
let refreshPromise = null;

export function refreshAccessToken() {
  if (refreshPromise) return refreshPromise;

  const { refreshToken, setTokens, clearSession } = useAuthStore.getState();
  if (!refreshToken) return Promise.reject(new Error('NO_REFRESH_TOKEN'));

  refreshPromise = refreshClient
    .post('/auth/refresh', { refresh_token: refreshToken })
    .then(({ data }) => {
      setTokens({ accessToken: data.access_token, refreshToken: data.refresh_token });
      return data.access_token;
    })
    .catch((error) => {
      // Chỉ xóa phiên khi Backend từ chối token; lỗi mạng thì giữ lại để thử lại sau.
      const status = error.response?.status;
      if (status === 401 || status === 403) clearSession();
      throw error;
    })
    .finally(() => {
      refreshPromise = null;
    });

  return refreshPromise;
}

axiosClient.interceptors.request.use(
  (config) => {
    const { accessToken } = useAuthStore.getState();
    if (accessToken) {
      config.headers.Authorization = `Bearer ${accessToken}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

axiosClient.interceptors.response.use(
  (response) => response.data,
  async (error) => {
    const original = error.config;
    const status = error.response?.status;
    const isAuthEndpoint = original?.url?.startsWith('/auth/');

    // Access Token hết hạn (15 phút) -> tự refresh rồi gửi lại request ban đầu đúng 1 lần.
    if (status === 401 && original && !original._retry && !isAuthEndpoint && useAuthStore.getState().refreshToken) {
      original._retry = true;
      try {
        const token = await refreshAccessToken();
        original.headers.Authorization = `Bearer ${token}`;
        return axiosClient(original);
      } catch {
        return Promise.reject(error);
      }
    }
    return Promise.reject(error);
  }
);

export default axiosClient;
