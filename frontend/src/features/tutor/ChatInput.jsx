import { useLayoutEffect } from 'react';
import { ArrowUp, Square } from 'lucide-react';
import clsx from 'clsx';

const MAX_HEIGHT_PX = 168;
export const MAX_MESSAGE_LENGTH = 2000;

/** Ô nhập câu hỏi: tự giãn chiều cao, Enter gửi, Shift+Enter xuống dòng, có nút Dừng khi AI đang trả lời. */
export default function ChatInput({ value, onChange, onSend, onStop, isStreaming, disabled, disabledReason, inputRef, footerRight }) {
  useLayoutEffect(() => {
    const el = inputRef?.current;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = `${Math.min(el.scrollHeight, MAX_HEIGHT_PX)}px`;
  }, [value, inputRef]);

  const handleKeyDown = (event) => {
    // isComposing/229: đang gõ dấu tiếng Việt (Telex/VNI) bằng bộ gõ -> Enter chỉ xác nhận chữ, không gửi
    if (event.key !== 'Enter' || event.shiftKey || event.nativeEvent.isComposing || event.keyCode === 229) return;
    event.preventDefault();
    if (!isStreaming && !disabled) onSend();
  };

  const canSend = value.trim().length > 0 && !disabled;
  const nearLimit = value.length > MAX_MESSAGE_LENGTH * 0.85;

  return (
    <div className="border-t border-slate-100 bg-white px-3 pb-[max(0.75rem,env(safe-area-inset-bottom))] pt-3 sm:px-6 sm:pb-4">
      <div className="mx-auto max-w-3xl">
        <div
          className={clsx(
            'flex items-end gap-2 rounded-xl border px-3 py-2.5 transition-colors focus-within:border-blue-600 focus-within:ring-2 focus-within:ring-blue-100',
            disabled ? 'border-slate-200 bg-slate-50' : 'border-slate-300 bg-white'
          )}
        >
          <label htmlFor="tutor-message" className="sr-only">
            Câu hỏi cho Gia sư AI
          </label>
          <textarea
            id="tutor-message"
            ref={inputRef}
            rows={1}
            value={value}
            maxLength={MAX_MESSAGE_LENGTH}
            disabled={disabled}
            onChange={(e) => onChange(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={disabled ? disabledReason : 'Nhập câu hỏi của bạn về bài học...'}
            enterKeyHint="send"
            className="thin-scroll max-h-[168px] min-h-[28px] flex-1 resize-none bg-transparent py-1 text-base leading-6 text-slate-900 placeholder:text-slate-400 focus:outline-none disabled:cursor-not-allowed sm:text-sm"
          />
          {isStreaming ? (
            <button
              type="button"
              onClick={onStop}
              aria-label="Dừng tạo câu trả lời"
              className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-navy-800 text-white hover:bg-navy-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-navy-800 focus-visible:ring-offset-2"
            >
              <Square size={14} fill="currentColor" aria-hidden="true" />
            </button>
          ) : (
            <button
              type="button"
              onClick={onSend}
              disabled={!canSend}
              aria-label="Gửi câu hỏi"
              className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-blue-600 text-white transition-colors hover:bg-blue-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600 focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:bg-slate-200 disabled:text-slate-400"
            >
              <ArrowUp size={18} aria-hidden="true" />
            </button>
          )}
        </div>

        <div className="mt-1.5 flex items-center justify-between gap-3 px-1 text-[11px] text-slate-400">
          <span className="hidden sm:inline">Enter để gửi · Shift+Enter xuống dòng</span>
          <span className={clsx('ml-auto text-right', nearLimit && 'font-semibold text-amber-600')}>
            {nearLimit ? `${value.length}/${MAX_MESSAGE_LENGTH} ký tự` : footerRight}
          </span>
        </div>
      </div>
    </div>
  );
}
