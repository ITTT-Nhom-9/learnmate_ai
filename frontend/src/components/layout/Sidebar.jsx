import { useEffect } from 'react';
import { X } from 'lucide-react';
import clsx from 'clsx';

/**
 * Sidebar thích ứng: desktop (lg+) là cột cố định bên trái, mobile là Drawer trượt từ cạnh trái.
 * Dùng một phần tử duy nhất, CSS quyết định hiển thị theo breakpoint nên không nhân đôi nội dung.
 */
export default function Sidebar({ open, onClose, title = 'Mục lục', children, className }) {
  useEffect(() => {
    if (!open) return undefined;
    const onKeyDown = (event) => event.key === 'Escape' && onClose();
    document.addEventListener('keydown', onKeyDown);
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden'; // khóa cuộn nền khi Drawer đang mở
    return () => {
      document.removeEventListener('keydown', onKeyDown);
      document.body.style.overflow = previousOverflow;
    };
  }, [open, onClose]);

  return (
    <>
      <div
        onClick={onClose}
        aria-hidden="true"
        className={clsx(
          'fixed inset-0 z-50 bg-slate-900/40 transition-opacity lg:hidden',
          open ? 'opacity-100' : 'pointer-events-none opacity-0'
        )}
      />
      <aside
        aria-label={title}
        className={clsx(
          // mobile: Drawer
          'fixed inset-y-0 left-0 z-50 flex w-[88%] max-w-sm flex-col bg-white shadow-xl',
          'transition-[transform,visibility] duration-200',
          open ? 'translate-x-0' : '-translate-x-full invisible',
          // desktop: cột cố định
          'lg:visible lg:sticky lg:top-24 lg:z-auto lg:max-h-[calc(100vh-7rem)] lg:w-auto lg:max-w-none lg:translate-x-0 lg:rounded-xl lg:border lg:border-slate-200 lg:shadow-none',
          className
        )}
      >
        <div className="flex items-center justify-between border-b border-slate-100 px-4 py-3 lg:hidden">
          <span className="text-sm font-semibold text-navy-800">{title}</span>
          <button
            type="button"
            onClick={onClose}
            aria-label="Đóng mục lục"
            className="rounded-full p-1.5 text-slate-500 hover:bg-slate-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600"
          >
            <X size={20} />
          </button>
        </div>
        <div className="thin-scroll flex-1 overflow-y-auto">{children}</div>
      </aside>
    </>
  );
}
