import { Suspense, lazy } from 'react';
import { Navigate, Route, Routes } from 'react-router-dom';
import AppLayout from '../components/layout/AppLayout';
import LoginPage from '../features/auth/LoginPage';
import RegisterPage from '../features/auth/RegisterPage';
import CourseCatalogPage from '../features/courses/CourseCatalogPage';
import Spinner from '../components/common/Spinner';
import NotFoundPage from '../pages/NotFoundPage';
import PlaceholderPage from '../pages/PlaceholderPage';
import ProtectedRoute, { GuestRoute } from './ProtectedRoute';

// Trang chi tiết môn kéo theo thư viện Markdown/KaTeX/Prism (nặng) -> chỉ tải khi người dùng mở môn học
const CourseDetailPage = lazy(() => import('../features/courses/CourseDetailPage'));

const pageFallback = (
  <div className="flex justify-center py-24 text-slate-400">
    <Spinner size={28} />
  </div>
);

export default function AppRoutes() {
  return (
    <Routes>
      <Route element={<GuestRoute />}>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
      </Route>

      <Route element={<ProtectedRoute />}>
        <Route element={<AppLayout />}>
          <Route path="/" element={<Navigate to="/courses" replace />} />
          <Route path="/courses" element={<CourseCatalogPage />} />
          {/* "/*" bắt cả /courses/:id và /courses/:id/lessons/:lessonId bằng một trang, đổi bài không remount */}
          <Route
            path="/courses/:courseId/*"
            element={
              <Suspense fallback={pageFallback}>
                <CourseDetailPage />
              </Suspense>
            }
          />
          <Route path="/tutor" element={<PlaceholderPage title="Gia sư AI" />} />
          <Route path="/tutor/:lessonId" element={<PlaceholderPage title="Gia sư AI" />} />
          <Route path="/progress" element={<PlaceholderPage title="Bảng tiến độ" />} />
        </Route>
      </Route>

      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  );
}
