import { useCallback, useEffect, useRef, useState } from 'react';
import { DAILY_QUOTA, tutorApi } from '../api/tutorApi';
import { getErrorMessage } from '../utils/apiError';
import { parseServerDate } from '../utils/formatters';

const FLUSH_INTERVAL_MS = 50; // gộp token để chỉ render lại ~20 lần/giây, tránh giật khi Markdown/KaTeX dài ra

/**
 * Điều phối hội thoại với Gia sư AI cho một bài học: tải lịch sử (API-09), gửi câu hỏi và nhận câu trả lời
 * dạng luồng (API-08), dừng/gửi lại, theo dõi hạn mức 50 câu/ngày và cấp độ gợi mở Socratic.
 *
 * Mỗi tin nhắn: { id, role: 'user'|'assistant', content, createdAt, status, errorMessage?, canRetry? }
 *   status: 'sent' | 'streaming' | 'stopped' | 'interrupted' | 'error'
 */
export function useTutorChat(lessonId) {
  const [messages, setMessages] = useState([]);
  const [mode, setModeState] = useState('EXPLAIN');
  const [hintLevel, setHintLevel] = useState(0);
  const [isConcluded, setIsConcluded] = useState(false);
  const [quotaRemaining, setQuotaRemaining] = useState(null);
  const [history, setHistory] = useState({ loading: true, error: '' });
  const [isStreaming, setIsStreaming] = useState(false);
  const [historyReload, setHistoryReload] = useState(0);

  const abortRef = useRef(null);
  const streamingRef = useRef(false);
  const modeRef = useRef(mode);
  const messagesRef = useRef(messages);
  const quotaRef = useRef(quotaRemaining);
  modeRef.current = mode;
  messagesRef.current = messages;
  quotaRef.current = quotaRemaining;

  // ---- Tải lịch sử khi đổi bài học ----
  useEffect(() => {
    let cancelled = false;
    abortRef.current?.abort(); // bài học khác -> hủy câu trả lời đang chạy của bài cũ
    streamingRef.current = false;
    setIsStreaming(false);
    setMessages([]);
    setHintLevel(0);
    setIsConcluded(false);
    setModeState('EXPLAIN');
    setHistory({ loading: true, error: '' });

    tutorApi
      .getHistory(lessonId)
      .then((data) => {
        if (cancelled) return;
        const list = (data.messages || [])
          .map((m) => ({
            id: `s-${m.id}`,
            role: m.role === 'USER' ? 'user' : 'assistant',
            content: m.content,
            createdAt: parseServerDate(m.created_at),
            status: 'sent',
          }))
          .sort((a, b) => (a.createdAt?.getTime() ?? 0) - (b.createdAt?.getTime() ?? 0));
        setMessages(list);
        if (data.mode) setModeState(data.mode);
        setHintLevel(data.hint_level ?? 0);
        setHistory({ loading: false, error: '' });
      })
      .catch((error) => {
        if (cancelled) return;
        // 404 = chưa có phiên chat nào cho bài học này -> bắt đầu hội thoại trống
        if (error.response?.status === 404) setHistory({ loading: false, error: '' });
        else setHistory({ loading: false, error: getErrorMessage(error, 'Không tải được lịch sử trò chuyện') });
      });

    return () => {
      cancelled = true;
    };
  }, [lessonId, historyReload]);

  useEffect(() => () => abortRef.current?.abort(), []);

  // ---- Chạy một lượt hỏi-đáp: nhận luồng token và ghép dần vào tin nhắn trợ lý ----
  const runStream = useCallback(
    async (text, assistantId) => {
      const controller = new AbortController();
      abortRef.current = controller;
      streamingRef.current = true;
      setIsStreaming(true);

      let accumulated = '';
      let timer = null;
      const patch = (changes) =>
        setMessages((prev) => prev.map((m) => (m.id === assistantId ? { ...m, ...changes } : m)));
      const flush = () => {
        timer = null;
        patch({ content: accumulated });
      };

      try {
        for await (const event of tutorApi.streamChat({ lessonId, message: text, mode: modeRef.current }, controller.signal)) {
          if (event.type === 'token') {
            accumulated += event.token;
            if (event.hintLevel != null) setHintLevel(event.hintLevel);
            if (event.isConcluded != null) setIsConcluded(event.isConcluded);
            if (!timer) timer = setTimeout(flush, FLUSH_INTERVAL_MS);
          } else if (event.type === 'done') {
            if (event.quotaRemaining != null) setQuotaRemaining(event.quotaRemaining);
          }
        }
        clearTimeout(timer);
        patch({ content: accumulated, status: 'sent', errorMessage: '' });
      } catch (error) {
        clearTimeout(timer);
        if (error.name === 'AbortError') {
          patch({ content: accumulated, status: 'stopped' });
        } else if (error.status === 429) {
          setQuotaRemaining(0);
          patch({ content: accumulated, status: 'error', errorMessage: error.message, canRetry: false });
        } else if (error.interrupted) {
          patch({ content: accumulated, status: 'interrupted', errorMessage: error.message, canRetry: true });
        } else {
          const message = error.name === 'TutorStreamError' ? error.message : getErrorMessage(error, 'Không thể kết nối tới Gia sư AI');
          patch({ content: accumulated, status: 'error', errorMessage: message, canRetry: true });
        }
      } finally {
        streamingRef.current = false;
        abortRef.current = null;
        setIsStreaming(false);
      }
    },
    [lessonId]
  );

  const send = useCallback(
    (raw) => {
      const text = (raw || '').trim();
      if (!text || streamingRef.current || quotaRef.current === 0) return false;
      const now = new Date();
      const stamp = now.getTime();
      const assistantId = `a-${stamp}`;
      setMessages((prev) => [
        ...prev,
        { id: `u-${stamp}`, role: 'user', content: text, createdAt: now, status: 'sent' },
        { id: assistantId, role: 'assistant', content: '', createdAt: now, status: 'streaming' },
      ]);
      runStream(text, assistantId);
      return true;
    },
    [runStream]
  );

  /** Gửi lại câu hỏi ngay trước tin nhắn trợ lý bị lỗi, ghi đè lên chính tin nhắn đó. */
  const retry = useCallback(
    (assistantId) => {
      if (streamingRef.current) return;
      const list = messagesRef.current;
      const index = list.findIndex((m) => m.id === assistantId);
      const question = index > 0 ? list[index - 1] : null;
      if (!question || question.role !== 'user') return;
      setMessages((prev) =>
        prev.map((m) => (m.id === assistantId ? { ...m, content: '', status: 'streaming', errorMessage: '', createdAt: new Date() } : m))
      );
      runStream(question.content, assistantId);
    },
    [runStream]
  );

  const stop = useCallback(() => abortRef.current?.abort(), []);

  const setMode = useCallback((next) => {
    if (!streamingRef.current) setModeState(next);
  }, []);

  return {
    messages,
    mode,
    setMode,
    hintLevel,
    isConcluded,
    quotaRemaining,
    quotaTotal: DAILY_QUOTA,
    history,
    reloadHistory: () => setHistoryReload((n) => n + 1),
    isStreaming,
    send,
    stop,
    retry,
  };
}
