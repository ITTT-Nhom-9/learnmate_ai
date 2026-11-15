import { useModalBehavior } from '../../hooks/useModalBehavior';

const noop = () => {};

/**
 * Hộp thoại giữa màn hình dùng cho xác nhận nộp bài / thông báo hết giờ.
 * dismissible=false: không đóng được bằng Esc hay bấm nền (hộp thoại "Hết giờ" đang tự nộp bài).
 */
export default function QuizDialog({ open, title, onClose, dismissible = true, role = 'dialog', children }) {
  const panelRef = useModalBehavior(open, dismissible ? onClose : noop);
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center p-4 sm:items-center">
      <div onClick={dismissible ? onClose : undefined} aria-hidden="true" className="absolute inset-0 animate-fade-in bg-slate-900/50" />
      <div
        ref={panelRef}
        role={role}
        aria-modal="true"
        aria-label={title}
        tabIndex={-1}
        className="relative w-full max-w-md animate-slide-in-up rounded-2xl bg-white p-6 shadow-xl focus:outline-none"
      >
        {children}
      </div>
    </div>
  );
}
