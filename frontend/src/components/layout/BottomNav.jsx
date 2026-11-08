import { NavLink } from 'react-router-dom';
import clsx from 'clsx';
import UserMenu from './UserMenu';
import { NAV_ITEMS } from './navItems';

/** Thanh điều hướng đáy trên điện thoại (ẩn từ breakpoint lg trở lên). */
export default function BottomNav() {
  return (
    <nav
      aria-label="Điều hướng chính"
      className="fixed inset-x-0 bottom-0 z-40 grid grid-cols-4 border-t border-slate-200 bg-white pb-[env(safe-area-inset-bottom)] lg:hidden"
    >
      {NAV_ITEMS.map(({ to, mobileLabel, icon: Icon }) => (
        <NavLink
          key={to}
          to={to}
          className={({ isActive }) =>
            clsx(
              'flex h-14 flex-col items-center justify-center gap-0.5 text-[11px] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-blue-600',
              isActive ? 'font-semibold text-blue-600' : 'font-medium text-slate-500'
            )
          }
        >
          <Icon size={22} aria-hidden="true" />
          {mobileLabel}
        </NavLink>
      ))}
      <UserMenu variant="tab" />
    </nav>
  );
}
