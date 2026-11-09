import { Link, NavLink } from 'react-router-dom';
import { Bell } from 'lucide-react';
import clsx from 'clsx';
import Logo from '../common/Logo';
import UserMenu from './UserMenu';
import { NAV_ITEMS } from './navItems';

/**
 * Header chung. Desktop: logo + menu giữa + thông báo + tài khoản.
 * Mobile: thu gọn thành Top Bar (logo + chuông thông báo), menu chính chuyển xuống BottomNav.
 */
export default function Header() {
  return (
    <header className="sticky top-0 z-40 border-b border-slate-200 bg-white">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:grid lg:grid-cols-[1fr_auto_1fr] lg:px-8">
        <Link to="/courses" aria-label="LearnMate AI - Trang chủ" className="justify-self-start rounded-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600">
          <Logo />
        </Link>

        <nav aria-label="Điều hướng chính" className="hidden h-full items-stretch gap-10 lg:flex">
          {NAV_ITEMS.map(({ to, label }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                clsx(
                  'relative flex items-center text-sm transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600',
                  isActive ? 'font-semibold text-navy-800' : 'font-medium text-slate-500 hover:text-navy-800'
                )
              }
            >
              {({ isActive }) => (
                <>
                  {label}
                  {isActive && <span className="absolute inset-x-0 bottom-0 h-0.5 bg-blue-600" aria-hidden="true" />}
                </>
              )}
            </NavLink>
          ))}
        </nav>

        <div className="flex items-center gap-3 justify-self-end">
          <button
            type="button"
            aria-label="Thông báo"
            className="rounded-full p-2 text-slate-500 hover:bg-slate-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600"
          >
            <Bell size={20} />
          </button>
          <div className="hidden items-center gap-1 border-l border-slate-200 pl-3 lg:flex">
            <UserMenu variant="header" />
          </div>
        </div>
      </div>
    </header>
  );
}
