import { create } from 'zustand';

// Chiến lược lưu trữ phiên đăng nhập (TK-05):
//  - Access Token (15 phút): CHỈ nằm trong bộ nhớ Zustand, không ghi xuống đĩa -> hạn chế rủi ro XSS đánh cắp token.
//  - Refresh Token (7 ngày) + thông tin user: ghi vào localStorage (tick "Ghi nhớ đăng nhập")
//    hoặc sessionStorage (không tick) để tải lại trang vẫn đăng nhập lại được bằng cách xin Access Token mới.
const REFRESH_KEY = 'lm_refresh_token';
const USER_KEY = 'lm_user';

const safe = {
  get(storage, key) {
    try {
      return storage.getItem(key);
    } catch {
      return null;
    }
  },
  set(storage, key, value) {
    try {
      storage.setItem(key, value);
    } catch {
      /* Trình duyệt chặn storage (chế độ riêng tư) -> bỏ qua, phiên chỉ sống trong bộ nhớ */
    }
  },
  remove(storage, key) {
    try {
      storage.removeItem(key);
    } catch {
      /* noop */
    }
  },
};

/** Storage đang giữ phiên: localStorage nếu có, ngược lại sessionStorage. */
function findStorage() {
  if (safe.get(localStorage, REFRESH_KEY)) return localStorage;
  if (safe.get(sessionStorage, REFRESH_KEY)) return sessionStorage;
  return null;
}

function readStoredUser() {
  const storage = findStorage();
  const raw = storage ? safe.get(storage, USER_KEY) : null;
  if (!raw) return null;
  try {
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

function clearStored() {
  [localStorage, sessionStorage].forEach((storage) => {
    safe.remove(storage, REFRESH_KEY);
    safe.remove(storage, USER_KEY);
  });
}

const storedStorage = findStorage();
const storedRefreshToken = storedStorage ? safe.get(storedStorage, REFRESH_KEY) : null;

export const useAuthStore = create((set, get) => ({
  user: readStoredUser(),
  accessToken: null, // chỉ trong bộ nhớ
  refreshToken: storedRefreshToken,
  isAuthenticated: false,
  // true khi có refresh token đang chờ khôi phục phiên lúc mở trang -> ProtectedRoute hiện spinner thay vì đá về /login
  isInitializing: Boolean(storedRefreshToken),

  /** Gọi sau khi đăng nhập thành công. */
  setSession: ({ user, accessToken, refreshToken, remember = true }) => {
    clearStored();
    const storage = remember ? localStorage : sessionStorage;
    safe.set(storage, REFRESH_KEY, refreshToken);
    safe.set(storage, USER_KEY, JSON.stringify(user));
    set({ user, accessToken, refreshToken, isAuthenticated: true, isInitializing: false });
  },

  /** Gọi sau mỗi lần refresh (Backend xoay vòng: cấp refresh token mới, thu hồi token cũ). */
  setTokens: ({ accessToken, refreshToken }) => {
    const nextRefresh = refreshToken || get().refreshToken;
    const storage = findStorage();
    if (storage && nextRefresh) safe.set(storage, REFRESH_KEY, nextRefresh);
    set({ accessToken, refreshToken: nextRefresh, isAuthenticated: Boolean(accessToken), isInitializing: false });
  },

  clearSession: () => {
    clearStored();
    set({ user: null, accessToken: null, refreshToken: null, isAuthenticated: false, isInitializing: false });
  },

  finishInitializing: () => set({ isInitializing: false }),
}));
