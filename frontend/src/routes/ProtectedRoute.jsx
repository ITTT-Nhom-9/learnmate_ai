import { Navigate, Outlet, useLocation } from 'react-router-dom';
import Spinner from '../components/common/Spinner';
import { useAuth } from '../hooks/useAuth';

function FullScreenSpinner() {
  return (
    <div className="flex min-h-screen items-center justify-center text-slate-400">
      <Spinner size={32} label="Đang khôi phục phiên đăng nhập" />
    </div>
  );
}

/** Chặn truy cập khi chưa đăng nhập; truyền roles={['ADMIN']} để giới hạn theo quyền (RBAC). */
export default function ProtectedRoute({ roles }) {
  const { isAuthenticated, isInitializing, user } = useAuth();
  const location = useLocation();

  if (isInitializing) return <FullScreenSpinner />;
  if (!isAuthenticated) return <Navigate to="/login" replace state={{ from: location }} />;
  if (roles && !roles.includes(user?.role)) return <Navigate to="/courses" replace />;
  return <Outlet />;
}

/** Trang dành cho khách (đăng nhập/đăng ký): đã đăng nhập thì chuyển về danh mục môn học. */
export function GuestRoute() {
  const { isAuthenticated, isInitializing } = useAuth();
  if (isInitializing) return <FullScreenSpinner />;
  if (isAuthenticated) return <Navigate to="/courses" replace />;
  return <Outlet />;
}
