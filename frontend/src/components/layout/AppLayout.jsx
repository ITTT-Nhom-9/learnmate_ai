import { Outlet, useLocation } from 'react-router-dom';
import Header from './Header';
import BottomNav from './BottomNav';

/** Khung chung cho mọi trang sau đăng nhập: Header + nội dung + Bottom Navigation (mobile). */
export default function AppLayout() {
  const { pathname } = useLocation();
  // Màn chat Gia sư AI tự chiếm trọn phần còn lại và ghim ô nhập ở đáy -> không hiện Bottom Navigation
  const isChat = pathname === '/tutor' || pathname.startsWith('/tutor/');

  // Màn làm bài trắc nghiệm (/quiz/:topicId) dùng thanh thao tác riêng ở đáy (Câu trước / Câu tiếp / Nộp bài)
  const isQuizTake = /^\/quiz\/[^/]+\/?$/.test(pathname);
  const hideBottomNav = isChat || isQuizTake;

  return (
    <div className="min-h-screen bg-slate-50">
      <Header />
      <main className={isChat ? '' : isQuizTake ? 'lg:pb-10' : 'pb-24 lg:pb-10'}>
        <Outlet />
      </main>
      {!hideBottomNav && <BottomNav />}
    </div>
  );
}
