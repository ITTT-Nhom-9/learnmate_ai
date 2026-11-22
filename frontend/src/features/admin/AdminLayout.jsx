import { Suspense, useState } from 'react';
import { Link, NavLink, Outlet, useLocation } from 'react-router-dom';
import {
  ArrowLeft,
  Bell,
  BookOpen,
  HelpCircle,
  LogOut,
  Menu,
  ScrollText,
  SlidersHorizontal,
  Users,
} from 'lucide-react';
import clsx from 'clsx';
import Logo from '../../components/common/Logo';
import Spinner from '../../components/common/Spinner';
import Drawer from '../../components/layout/Drawer';
import { useAuth } from '../../hooks/useAuth';

const ADMIN_NAV = [
  { to: '/admin/users', label: 'Quản lý người dùng', icon: Users },
  { to: '/admin/courses', label: 'Quản lý khóa học', icon: BookOpen },
  { to: '/admin/prompts', label: 'Quản lý Prompt AI', icon: SlidersHorizontal },
  { to: '/admin/tokens', label: 'Nhật ký Token', icon: ScrollText },
];

const BREADCRUMB_MAP = {
  '/admin/prompts': 'Tổng quan AI & Prompt',
  '/admin/users': 'Quản lý người dùng',
  '/admin/courses': 'Quản lý khóa học & RAG',
  '/admin/tokens': 'Nhật ký Token & Chi phí',
};

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
      <p className="px-5 pt-6 pb-2 text-[11px] font-semibold uppercase tracking-wider text-slate-400">
        Không gian quản trị
      </p>
      <nav aria-label="Điều hướng quản trị" className="thin-scroll flex-1 space-y-1 overflow-y-auto px-3 py-2">
        {ADMIN_NAV.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            onClick={onNavigate}
            className={({ isActive }) =>
              clsx(
                'flex h-11 items-center gap-3 rounded-xl px-3.5 text-sm font-medium transition-all',
                'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-400',
                dark
                  ? isActive
                    ? 'bg-[#2563EB] font-semibold text-white shadow-sm'
                    : 'text-slate-300 hover:bg-white/5 hover:text-white'
                  : isActive
                  ? 'bg-blue-50 font-semibold text-blue-700'
                  : 'text-slate-600 hover:bg-slate-50'
              )
            }
          >
            <Icon size={18} aria-hidden="true" />
            {label}
          </NavLink>
        ))}
      </nav>

      {/* Card trạng thái hệ thống chuẩn Figma */}
      <div className="px-4 py-2">
        <div className={clsx(
          'rounded-xl border p-3.5',
          dark ? 'border-white/10 bg-white/5' : 'border-slate-200 bg-slate-50'
        )}>
          <div className="flex items-center gap-2">
            <span className="relative flex h-2 w-2">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-500"></span>
            </span>
            <p className={clsx('text-xs font-semibold', dark ? 'text-emerald-400' : 'text-emerald-600')}>
              Hệ thống hoạt động ổn định
            </p>
          </div>
          <p className={clsx('mt-1 text-[11px]', dark ? 'text-slate-400' : 'text-slate-500')}>
            Môi trường Production
          </p>
        </div>
      </div>

      {/* Thông tin tài khoản quản trị */}
      <div className={clsx('border-t px-4 py-4', dark ? 'border-white/10' : 'border-slate-100')}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3 min-w-0">
            <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-slate-700 text-xs font-bold text-white shadow-inner">
              QT
            </span>
            <div className="min-w-0">
              <p className={clsx('truncate text-sm font-semibold', dark ? 'text-white' : 'text-navy-800')}>
                {user?.full_name || 'Quản trị viên'}
              </p>
              <p className="truncate text-xs text-slate-400">
                {user?.email || 'admin@learnmate.ai'}
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={handleLogout}
            disabled={loggingOut}
            title="Đăng xuất"
            aria-label="Đăng xuất"
            className={clsx(
              'rounded-lg p-1.5 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-400',
              dark ? 'text-slate-400 hover:bg-white/10 hover:text-white' : 'text-slate-500 hover:bg-slate-100'
            )}
          >
            <LogOut size={18} aria-hidden="true" />
          </button>
        </div>
      </div>
    </div>
  );
}

/**
 * Khung SCR-08 (Quản trị viên) chuẩn Figma.
 *  - Desktop (>= lg): Sidebar cố định bên trái rộng 250px, Top header có Breadcrumb + Status Production.
 *  - Mobile: Top Bar (nút Hamburger + Logo); menu mở bằng Drawer trượt từ cạnh trái.
 */
export default function AdminLayout() {
  const [menuOpen, setMenuOpen] = useState(false);
  const location = useLocation();
  const currentSub = BREADCRUMB_MAP[location.pathname] || 'Tổng quan AI & Prompt';

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Sidebar Desktop 250px chuẩn Figma */}
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-[250px] flex-col bg-[#0B132B] lg:flex">
        <div className="flex h-16 shrink-0 items-center border-b border-white/10 px-5">
          <Logo tone="light" />
        </div>
        <AdminNav tone="dark" />
      </aside>

      {/* Top Header Mobile */}
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

      {/* Drawer Mobile */}
      <Drawer open={menuOpen} onClose={() => setMenuOpen(false)} title="Menu quản trị">
        <div className="flex min-h-full flex-col">
          <AdminNav tone="light" onNavigate={() => setMenuOpen(false)} />
        </div>
      </Drawer>

      <div className="lg:pl-[250px]">
        {/* Top Header Desktop chuẩn Figma: Breadcrumb + Production badge + Notification */}
        <div className="hidden h-14 items-center justify-between border-b border-slate-200 bg-white px-8 lg:flex">
          <div className="flex items-center gap-2 text-xs font-medium text-slate-500">
            <span>Quản trị</span>
            <span>›</span>
            <span className="font-semibold text-slate-800">{currentSub}</span>
          </div>

          <div className="flex items-center gap-3">
            <Link
              to="/courses"
              className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-600 shadow-sm transition-colors hover:bg-slate-50 hover:text-slate-900"
            >
              <ArrowLeft size={14} />
              <span>Về LMS</span>
            </Link>
          </div>
        </div>

        {/* Nội dung trang */}
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
