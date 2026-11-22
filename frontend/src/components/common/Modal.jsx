import { useCallback, useRef } from 'react';
import { X } from 'lucide-react';
import clsx from 'clsx';
import { useModalBehavior } from '../../hooks/useModalBehavior';

const SIZES = { md: 'sm:max-w-md', lg: 'sm:max-w-2xl' };

/**
 * Hộp thoại giữa màn hình (desktop) / trượt từ đáy (mobile). Esc để đóng, khóa cuộn nền, trả tiêu điểm khi đóng.
 * busy=true: chặn đóng bằng Esc / bấm nền / nút X trong lúc đang gửi dữ liệu.
 */
export default function Modal({ open, onClose, title, children, footer, size = 'md', busy = false }) {
  // Giữ tham chiếu ổn định tới hàm đóng. Nếu truyền hàm mới ở mỗi lần render, useModalBehavior sẽ chạy lại effect
  // sau mỗi phím gõ: tiêu điểm bị kéo ra khỏi ô nhập (input/textarea) và người dùng chỉ gõ được 1 ký tự.
  const closeRef = useRef(onClose);
  closeRef.current = () => !busy && onClose();
  const requestClose = useCallback(() => closeRef.current(), []);
  const panelRef = useModalBehavior(open, requestClose);
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center sm:items-center sm:p-4">
      <div onClick={requestClose} aria-hidden="true" className="absolute inset-0 animate-fade-in bg-slate-900/40" />
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-label={title}
        tabIndex={-1}
        className={clsx(
          'relative flex max-h-[92dvh] w-full animate-slide-in-up flex-col rounded-t-2xl bg-white shadow-xl focus:outline-none sm:rounded-2xl',
          SIZES[size]
        )}
      >
        <div className="flex items-center justify-between border-b border-slate-100 px-5 py-4">
          <h2 className="text-base font-semibold text-navy-800">{title}</h2>
          <button
            type="button"
            onClick={requestClose}
            disabled={busy}
            aria-label="Đóng hộp thoại"
            className="rounded-full p-1.5 text-slate-500 hover:bg-slate-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600 disabled:opacity-50"
          >
            <X size={20} />
          </button>
        </div>
        <div className="thin-scroll min-h-0 flex-1 overflow-y-auto px-5 py-4">{children}</div>
        {footer && (
          <div className="flex flex-col-reverse gap-2 border-t border-slate-100 px-5 py-3 pb-[max(0.75rem,env(safe-area-inset-bottom))] sm:flex-row sm:justify-end">
            {footer}
          </div>
        )}
      </div>
    </div>
  );
}
