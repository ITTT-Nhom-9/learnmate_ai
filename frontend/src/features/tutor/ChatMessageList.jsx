import { Fragment, useLayoutEffect, useRef, useState, useEffect } from 'react';
import { ArrowDown } from 'lucide-react';
import ChatMessage from './ChatMessage';
import { formatDayLabel, formatTime, isSameDay } from '../../utils/formatters';

const NEAR_BOTTOM_PX = 80;

/**
 * Vùng cuộn của hội thoại. Tự cuộn theo tin nhắn mới khi người dùng đang ở đáy;
 * nếu họ cuộn lên đọc lại thì giữ nguyên vị trí và hiện nút "Tin nhắn mới".
 */
export default function ChatMessageList({ messages, initials, onRetry, isStreaming, empty }) {
  const scrollRef = useRef(null);
  const stickRef = useRef(true);
  const previousLength = useRef(0);
  const [showJump, setShowJump] = useState(false);

  const scrollToBottom = (behavior = 'auto') => {
    const el = scrollRef.current;
    if (el) el.scrollTo({ top: el.scrollHeight, behavior });
  };

  const handleScroll = () => {
    const el = scrollRef.current;
    if (!el) return;
    const near = el.scrollHeight - el.scrollTop - el.clientHeight < NEAR_BOTTOM_PX;
    stickRef.current = near;
    setShowJump(!near);
  };

  useLayoutEffect(() => {
    const grew = messages.length > previousLength.current;
    const last = messages[messages.length - 1];
    const justSent = grew && last?.status === 'streaming' && messages[messages.length - 2]?.role === 'user';
    previousLength.current = messages.length;
    if (justSent) stickRef.current = true; // người dùng vừa gửi -> luôn kéo xuống đáy
    if (stickRef.current) scrollToBottom();
  }, [messages]);

  // Bàn phím ảo mở/đóng làm khung đổi chiều cao -> giữ nguyên đáy hội thoại
  useEffect(() => {
    const el = scrollRef.current;
    if (!el || typeof ResizeObserver === 'undefined') return undefined;
    const observer = new ResizeObserver(() => stickRef.current && scrollToBottom());
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  return (
    <div className="relative min-h-0 flex-1">
      <div
        ref={scrollRef}
        onScroll={handleScroll}
        role="log"
        aria-label="Cuộc trò chuyện với Gia sư AI"
        aria-live={isStreaming ? 'off' : 'polite'}
        className="thin-scroll h-full overflow-y-auto overscroll-contain px-4 py-5 sm:px-6"
      >
        {messages.length === 0 ? (
          empty
        ) : (
          <div className="mx-auto flex max-w-3xl flex-col gap-5">
            {messages.map((message, index) => {
              const newDay = index === 0 || !isSameDay(messages[index - 1].createdAt, message.createdAt);
              return (
                <Fragment key={message.id}>
                  {newDay && message.createdAt && (
                    <p className="text-center text-xs text-slate-400">
                      {formatDayLabel(message.createdAt)}, {formatTime(message.createdAt)}
                    </p>
                  )}
                  <ChatMessage message={message} initials={initials} onRetry={onRetry} />
                </Fragment>
              );
            })}
          </div>
        )}
      </div>

      {showJump && (
        <button
          type="button"
          onClick={() => scrollToBottom('smooth')}
          className="absolute bottom-3 left-1/2 flex -translate-x-1/2 items-center gap-1.5 rounded-full border border-slate-200 bg-white px-3.5 py-1.5 text-xs font-semibold text-navy-800 shadow-md hover:bg-slate-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600"
        >
          <ArrowDown size={14} aria-hidden="true" />
          {isStreaming ? 'Đang trả lời' : 'Tin nhắn mới'}
        </button>
      )}
    </div>
  );
}
