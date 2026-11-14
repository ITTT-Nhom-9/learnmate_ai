import { X } from 'lucide-react';
import { useModalBehavior } from '../../hooks/useModalBehavior';

/** Ngăn kéo trượt từ cạnh trái (chỉ dùng trên mobile). Chỉ gắn vào DOM khi đang mở. */
export default function Drawer({ open, onClose, title, children }) {
  const panelRef = useModalBehavior(open, onClose);
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 lg:hidden">
      <div onClick={onClose} aria-hidden="true" className="absolute inset-0 animate-fade-in bg-slate-900/40" />
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-label={title}
        tabIndex={-1}
        className="absolute inset-y-0 left-0 flex w-[88%] max-w-sm animate-slide-in-left flex-col bg-white shadow-xl focus:outline-none"
      >
        <div className="flex items-center justify-between border-b border-slate-100 px-4 py-3">
          <span className="text-sm font-semibold text-navy-800">{title}</span>
          <button
            type="button"
            onClick={onClose}
            aria-label={`Đóng ${title.toLowerCase()}`}
            className="rounded-full p-1.5 text-slate-500 hover:bg-slate-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600"
          >
            <X size={20} />
          </button>
        </div>
        <div className="thin-scroll min-h-0 flex-1 overflow-y-auto">{children}</div>
      </div>
    </div>
  );
}
