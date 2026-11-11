import axiosClient, { refreshAccessToken } from './axiosClient';
import { TutorStreamError } from './tutorErrors';
import { useAuthStore } from '../store/useAuthStore';
import { readSseStream } from '../utils/sse';

// VITE_USE_MOCK=true: chạy bằng dữ liệu giả lập khi Backend chưa có API chat (TK-12).
const USE_MOCK = import.meta.env.VITE_USE_MOCK === 'true';
const loadMock = () => import('../mocks/mockTutorApi.js');

export const DAILY_QUOTA = 50; // BR-05: tối đa 50 câu hỏi/ngày

function parseJson(text) {
  try {
    return JSON.parse(text);
  } catch {
    return text; // Backend gửi chuỗi thô thay vì JSON -> coi cả chuỗi là token
  }
}

async function toStreamError(response) {
  let detail = '';
  try {
    const body = await response.json();
    detail = typeof body?.detail === 'string' ? body.detail : body?.detail?.[0]?.msg || '';
  } catch {
    /* body không phải JSON */
  }
  const { status } = response;
  if (status === 429) return new TutorStreamError(detail || `Bạn đã dùng hết ${DAILY_QUOTA} lượt hỏi trong hôm nay. Hãy quay lại vào ngày mai.`, { status });
  if (status === 401) return new TutorStreamError('Phiên đăng nhập đã hết hạn, vui lòng đăng nhập lại.', { status });
  if (status === 400 || status === 404 || status === 422) return new TutorStreamError(detail || 'Yêu cầu không hợp lệ.', { status });
  return new TutorStreamError(detail || 'Gia sư AI đang bận, vui lòng thử lại sau ít phút.', { status });
}

/**
 * API-08: POST /tutor/chat -> luồng SSE.
 *   event: message  data: { token, hint_level, is_concluded }
 *   event: done     data: { message_id, tokens_used, quota_remaining }
 *   event: error    data: { detail }   (nếu Backend gửi lỗi giữa luồng)
 * Trả về async generator các sự kiện { type: 'token' | 'done', ... }.
 */
async function* streamFromServer({ lessonId, message, mode }, signal) {
  const url = `${axiosClient.defaults.baseURL}/tutor/chat`;
  const send = () =>
    fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'text/event-stream',
        Authorization: `Bearer ${useAuthStore.getState().accessToken}`,
      },
      body: JSON.stringify({ lesson_id: lessonId, message, mode }),
      signal,
    });

  let response = await send();
  if (response.status === 401 && useAuthStore.getState().refreshToken) {
    try {
      await refreshAccessToken(); // Access Token hết hạn (15 phút) -> làm mới rồi gửi lại đúng 1 lần
    } catch {
      throw new TutorStreamError('Phiên đăng nhập đã hết hạn, vui lòng đăng nhập lại.', { status: 401 });
    }
    response = await send();
  }
  if (!response.ok) throw await toStreamError(response);
  if (!response.body) throw new TutorStreamError('Trình duyệt không hỗ trợ nhận câu trả lời dạng luồng.');

  for await (const frame of readSseStream(response.body)) {
    const data = parseJson(frame.data);
    if (frame.event === 'done') {
      yield {
        type: 'done',
        messageId: data?.message_id ?? null,
        tokensUsed: data?.tokens_used ?? 0,
        quotaRemaining: data?.quota_remaining ?? null,
      };
      return;
    }
    if (frame.event === 'error') {
      throw new TutorStreamError(data?.detail || data?.message || 'Gia sư AI gặp sự cố khi trả lời.', { status: data?.status ?? null });
    }
    const token = typeof data === 'string' ? data : data?.token ?? data?.content ?? '';
    yield {
      type: 'token',
      token,
      hintLevel: typeof data === 'object' ? data?.hint_level ?? null : null,
      isConcluded: typeof data === 'object' ? data?.is_concluded ?? null : null,
    };
  }
  // Luồng đóng mà không có sự kiện "done" -> mạng đứt hoặc server dừng đột ngột
  throw new TutorStreamError('Kết nối bị gián đoạn, câu trả lời có thể chưa đầy đủ.', { interrupted: true });
}

export const tutorApi = {
  /** API-09 -> { session_id, mode, hint_level, messages: [{ id, role: 'USER'|'ASSISTANT', content, created_at }] }. 404 nếu chưa có phiên. */
  getHistory: (lessonId, { limit = 50 } = {}) =>
    USE_MOCK ? loadMock().then((m) => m.getHistory(lessonId)) : axiosClient.get(`/tutor/history/${lessonId}`, { params: { limit } }),

  streamChat: async function* streamChat(payload, signal) {
    if (USE_MOCK) {
      const mock = await loadMock();
      yield* mock.streamChat(payload, signal);
    } else {
      yield* streamFromServer(payload, signal);
    }
  },
};
