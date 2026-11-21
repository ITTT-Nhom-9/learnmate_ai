import { Suspense, useState } from 'react';
import { Link, NavLink, Outlet } from 'react-router-dom';
import { ArrowLeft, Coins, FileText, LogOut, Menu, ScrollText, Users } from 'lucide-react';
import clsx from 'clsx';
import Logo from '../../components/common/Logo';
import Spinner from '../../components/common/Spinner';
import Drawer from '../../components/layout/Drawer';
import { useAuth } from '../../hooks/useAuth';
import { getInitials } from '../../utils/formatters';

const ADMIN_NAV = [
  { to: '/admin/users', label: 'Người dùng', icon: Users },
  { to: '/admin/prompts', label: 'Prompt AI', icon: ScrollText },
  { to: '/admin/tokens', label: 'Token & chi phí AI', icon: Coins },
  { to: '/admin/documents', label: 'Tài liệu RAG', icon: FileText },
];

/** Menu quản trị + khối tài khoản. tone="dark": sidebar desktop (nền navy); tone="light": Drawer trên mobile. */
function AdminNav({ tone, onNavigate }) {
  const dark = tone === 'dark';
  const { user, logout } = useAuth();
  const [loggingOut, setLoggingOut] = useState(false);

  const handleLogout = async () => {
    setLoggingOut(true);
    await logout(); // xóa phiên -> ProtectedRoute tự chuyển về /login
  };

  const footerLink = clsx(
    'flex h-10 w-full items-center gap-3 rounded-lg px-3 text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-400',
    dark ? 'text-slate-300 hover:bg-white/5 hover:text-white' : 'text-slate-600 hover:bg-slate-50'
  );

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <p className={clsx('px-6 pt-5 text-[11px] font-semibold uppercase tracking-wider', dark ? 'text-slate-400' : 'text-slate-400')}>
        Quản trị hệ thống
      </p>
      <nav aria-label="Điều hướng quản trị" className="thin-scroll flex-1 space-y-1 overflow-y-auto px-3 py-3">
        {ADMIN_NAV.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            onClick={onNavigate}
            className={({ isActive }) =>
              clsx(
                'flex h-11 items-center gap-3 rounded-lg px-3 text-sm font-medium transition-colors',
                'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-400',
                dark
                  ? isActive ? 'bg-white/10 text-white' : 'text-slate-300 hover:bg-white/5 hover:text-white'
                  : isActive ? 'bg-blue-50 text-blue-700' : 'text-slate-600 hover:bg-slate-50'
              )
            }
          >
            <Icon size={18} aria-hidden="true" />
            {label}
          </NavLink>
        ))}
      </nav>

      <div className={clsx('space-y-1 border-t px-3 py-4', dark ? 'border-white/10' : 'border-slate-100')}>
        <div className="mb-2 flex items-center gap-3 px-3">
          <span className={clsx('flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-xs font-semibold', dark ? 'bg-white/10 text-white' : 'bg-blue-50 text-blue-700')}>
            {getInitials(user?.full_name)}
          </span>
          <div className="min-w-0">
            <p className={clsx('truncate text-sm font-semibold', dark ? 'text-white' : 'text-navy-800')}>{user?.full_name}</p>
            <p className="truncate text-xs text-slate-400">{user?.email}</p>
          </div>
        </div>
        <Link to="/courses" onClick={onNavigate} className={footerLink}>
          <ArrowLeft size={18} aria-hidden="true" />
          Về trang học tập
        </Link>
        <button type="button" onClick={handleLogout} disabled={loggingOut} className={clsx(footerLink, 'disabled:opacity-60')}>
          <LogOut size={18} aria-hidden="true" />
          {loggingOut ? 'Đang đăng xuất...' : 'Đăng xuất'}
        </button>
      </div>
    </div>
  );
}

/**
 * Khung SCR-08 (Quản trị viên).
 *  - Desktop (>= lg): Sidebar cố định bên trái rộng 250px, nội dung bên phải.
 *  - Mobile: Top Bar (nút Hamburger + Logo); menu mở bằng Drawer trượt từ cạnh trái.
 */
export default function AdminLayout() {
  const [menuOpen, setMenuOpen] = useState(false);

  return (
    <div className="min-h-screen bg-slate-50">
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-[250px] flex-col bg-navy-800 lg:flex">
        <div className="flex h-16 shrink-0 items-center border-b border-white/10 px-5">
          <Logo tone="light" />
        </div>
        <AdminNav tone="dark" />
      </aside>

      <header className="sticky top-0 z-20 flex h-14 items-center gap-2 border-b border-slate-200 bg-white px-3 lg:hidden">
        <button
          type="button"
          onClick={() => setMenuOpen(true)}
          aria-label="Mở menu quản trị"
          aria-expanded={menuOpen}
          className="flex h-11 w-11 items-center justify-center rounded-lg text-navy-800 hover:bg-slate-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600"
        >
          <Menu size={22} />
        </button>
        <Logo />
      </header>

      <Drawer open={menuOpen} onClose={() => setMenuOpen(false)} title="Menu quản trị">
        <div className="flex min-h-full flex-col">
          <AdminNav tone="light" onNavigate={() => setMenuOpen(false)} />
        </div>
      </Drawer>

      <div className="lg:pl-[250px]">
        <main className="mx-auto max-w-6xl px-4 py-6 sm:px-6 lg:px-8">
          <Suspense
            fallback={
              <div className="flex justify-center py-24 text-slate-400">
                <Spinner size={28} />
              </div>
            }
          >
            <Outlet />
          </Suspense>
        </main>
      </div>
    </div>
  );
}
