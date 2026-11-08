import { Outlet } from 'react-router-dom';
import Header from './Header';
import BottomNav from './BottomNav';

/** Khung chung cho mọi trang sau đăng nhập: Header + nội dung + Bottom Navigation (mobile). */
export default function AppLayout() {
  return (
    <div className="min-h-screen bg-slate-50">
      <Header />
      <main className="pb-24 lg:pb-10">
        <Outlet />
      </main>
      <BottomNav />
    </div>
  );
}
