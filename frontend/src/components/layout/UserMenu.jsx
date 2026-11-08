import { useEffect, useRef, useState } from 'react';
import { ChevronDown, LogOut, User } from 'lucide-react';
import clsx from 'clsx';
import { useAuth } from '../../hooks/useAuth';
import { getInitials } from '../../utils/formatters';

const ROLE_LABEL = { STUDENT: 'Sinh viên', ADMIN: 'Quản trị viên' };

/**
 * Menu tài khoản. variant="header": avatar + tên (desktop). variant="tab": nút "Tài khoản" ở Bottom Navigation (mobile).
 */
export default function UserMenu({ variant = 'header' }) {
  const { user, logout } = useAuth();
  const [open, setOpen] = useState(false);
  const [loggingOut, setLoggingOut] = useState(false);
  const rootRef = useRef(null);

  useEffect(() => {
    if (!open) return undefined;
    const onPointerDown = (event) => {
      if (rootRef.current && !rootRef.current.contains(event.target)) setOpen(false);
    };
    const onKeyDown = (event) => event.key === 'Escape' && setOpen(false);
    document.addEventListener('mousedown', onPointerDown);
    document.addEventListener('keydown', onKeyDown);
    return () => {
      document.removeEventListener('mousedown', onPointerDown);
      document.removeEventListener('keydown', onKeyDown);
    };
  }, [open]);

  const handleLogout = async () => {
    setLoggingOut(true);
    await logout(); // xóa phiên -> ProtectedRoute tự chuyển về /login
  };

  const isTab = variant === 'tab';

  return (
    <div ref={rootRef} className="relative">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-haspopup="menu"
        aria-expanded={open}
        className={clsx(
          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600',
          isTab
            ? 'flex h-14 w-full flex-col items-center justify-center gap-0.5 text-[11px] font-medium text-slate-500'
            : 'flex items-center gap-2.5 rounded-lg py-1.5 pl-3 pr-2 hover:bg-slate-50'
        )}
      >
        {isTab ? (
          <>
            <User size={22} aria-hidden="true" />
            Tài khoản
          </>
        ) : (
          <>
            <span className="flex h-8 w-8 items-center justify-center rounded-full bg-blue-50 text-xs font-semibold text-blue-700">
              {getInitials(user?.full_name)}
            </span>
            <span className="max-w-[150px] truncate text-sm font-medium text-navy-800">{user?.full_name}</span>
            <ChevronDown size={16} className="text-slate-400" aria-hidden="true" />
          </>
        )}
      </button>

      {open && (
        <div
          role="menu"
          className={clsx(
            'absolute z-50 w-64 rounded-xl border border-slate-200 bg-white p-2 shadow-lg',
            isTab ? 'bottom-full right-2 mb-2' : 'right-0 top-full mt-2'
          )}
        >
          <div className="border-b border-slate-100 px-3 pb-3 pt-2">
            <p className="truncate text-sm font-semibold text-navy-800">{user?.full_name}</p>
            <p className="truncate text-xs text-slate-500">{user?.email}</p>
            <p className="mt-1 text-xs font-medium text-blue-600">{ROLE_LABEL[user?.role] || user?.role}</p>
          </div>
          <button
            type="button"
            role="menuitem"
            onClick={handleLogout}
            disabled={loggingOut}
            className="mt-1 flex w-full items-center gap-2 rounded-lg px-3 py-2.5 text-sm font-medium text-red-600 hover:bg-red-50 disabled:opacity-60"
          >
            <LogOut size={16} aria-hidden="true" />
            {loggingOut ? 'Đang đăng xuất...' : 'Đăng xuất'}
          </button>
        </div>
      )}
    </div>
  );
}
