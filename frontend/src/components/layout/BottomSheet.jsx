import { X } from 'lucide-react';
import { useModalBehavior } from '../../hooks/useModalBehavior';

/** Bảng trượt từ đáy màn hình (mobile / màn hình nhỏ). Chỉ gắn vào DOM khi đang mở. */
export default function BottomSheet({ open, onClose, title, children, hideFrom = 'xl' }) {
  const panelRef = useModalBehavior(open, onClose);
  if (!open) return null;
  const hide = { lg: 'lg:hidden', xl: 'xl:hidden' }[hideFrom] || '';
  return (
    <div className={`fixed inset-0 z-50 ${hide}`}>
      <div onClick={onClose} aria-hidden="true" className="absolute inset-0 animate-fade-in bg-slate-900/40" />
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-label={title}
        tabIndex={-1}
        className="absolute inset-x-0 bottom-0 flex max-h-[80dvh] animate-slide-in-up flex-col rounded-t-2xl bg-white pb-[env(safe-area-inset-bottom)] shadow-xl focus:outline-none"
      >
        <div className="mx-auto mt-2 h-1 w-10 rounded-full bg-slate-300" aria-hidden="true" />
        <div className="flex items-center justify-between px-4 pb-2 pt-2">
          <span className="text-base font-semibold text-navy-800">{title}</span>
          <button
            type="button"
            onClick={onClose}
            aria-label={`Đóng ${title.toLowerCase()}`}
            className="rounded-full p-1.5 text-slate-500 hover:bg-slate-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600"
          >
            <X size={20} />
          </button>
        </div>
        <div className="thin-scroll min-h-0 flex-1 overflow-y-auto px-4 pb-4">{children}</div>
      </div>
    </div>
  );
}
