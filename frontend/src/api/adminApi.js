import axiosClient from './axiosClient';

// VITE_USE_MOCK=true: chạy giao diện Admin (SCR-08) bằng dữ liệu giả lập, không cần Backend TK-23.
const USE_MOCK = import.meta.env.VITE_USE_MOCK === 'true';
const loadMock = () => import('../mocks/mockAdminApi.js');

// Bỏ các tham số rỗng để không gửi ?search=&role= lên Backend (FastAPI sẽ coi "" là giá trị lọc).
const clean = (params) => Object.fromEntries(Object.entries(params).filter(([, v]) => v !== '' && v != null));

/** Toàn bộ endpoint đều yêu cầu vai trò ADMIN (Backend trả 403 nếu là sinh viên). */
export const adminApi = {
  /** API-16: GET /admin/users -> { items, total, page, page_size, total_pages } */
  getUsers: ({ page = 1, pageSize = 10, search, role, status } = {}) =>
    USE_MOCK
      ? loadMock().then((m) => m.getUsers({ page, pageSize, search, role, status }))
      : axiosClient.get('/admin/users', { params: clean({ page, page_size: pageSize, search, role, status }) }),

  /** PATCH /admin/users/{id}/status { status: 'ACTIVE'|'LOCKED', reason? } -> UserAdminItem. Khóa sẽ thu hồi refresh token. */
  updateUserStatus: (userId, { status, reason }) =>
    USE_MOCK
      ? loadMock().then((m) => m.updateUserStatus(userId, { status, reason }))
      : axiosClient.patch(`/admin/users/${userId}/status`, clean({ status, reason })),

  /** PATCH /admin/users/{id}/role { role: 'STUDENT'|'ADMIN' } -> UserAdminItem. Backend chặn Admin tự giáng quyền của chính mình. */
  updateUserRole: (userId, role) =>
    USE_MOCK
      ? loadMock().then((m) => m.updateUserRole(userId, role))
      : axiosClient.patch(`/admin/users/${userId}/role`, { role }),

  /** GET /admin/prompts -> [{ id, code, version, content, is_active, created_at }] */
  getPrompts: ({ code } = {}) =>
    USE_MOCK ? loadMock().then((m) => m.getPrompts({ code })) : axiosClient.get('/admin/prompts', { params: clean({ code }) }),

  /** POST /admin/prompts: tạo phiên bản mới (version tự tăng). is_active=true sẽ tắt các phiên bản cũ cùng mã. */
  createPrompt: ({ code, content, isActive }) =>
    USE_MOCK
      ? loadMock().then((m) => m.createPrompt({ code, content, isActive }))
      : axiosClient.post('/admin/prompts', { code, content, is_active: isActive }),

  /** API-17: PUT /admin/prompts/{id} { content?, is_active? } */
  updatePrompt: (promptId, { content, isActive }) =>
    USE_MOCK
      ? loadMock().then((m) => m.updatePrompt(promptId, { content, isActive }))
      : axiosClient.put(`/admin/prompts/${promptId}`, clean({ content, is_active: isActive })),

  /**
   * API-18: GET /admin/logs/tokens?start_date=&end_date=
   * -> { summary, by_feature[], by_provider[], by_date[], pricing_rates, exchange_rate_vnd }
   */
  getTokenStats: ({ startDate, endDate } = {}) =>
    USE_MOCK
      ? loadMock().then((m) => m.getTokenStats({ startDate, endDate }))
      : axiosClient.get('/admin/logs/tokens', { params: clean({ start_date: startDate, end_date: endDate }) }),

  /** GET /admin/logs -> { items, total, page, page_size, total_pages } (mỗi dòng có estimated_cost_usd / _vnd) */
  getLogs: ({ page = 1, pageSize = 10, feature, provider, startDate, endDate } = {}) =>
    USE_MOCK
      ? loadMock().then((m) => m.getLogs({ page, pageSize, feature, provider, startDate, endDate }))
      : axiosClient.get('/admin/logs', {
          params: clean({ page, page_size: pageSize, feature, provider, start_date: startDate, end_date: endDate }),
        }),
};
