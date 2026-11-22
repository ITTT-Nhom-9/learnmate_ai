import { Suspense, lazy } from 'react';
import { Navigate, Route, Routes } from 'react-router-dom';
import AppLayout from '../components/layout/AppLayout';
import LoginPage from '../features/auth/LoginPage';
import RegisterPage from '../features/auth/RegisterPage';
import CourseCatalogPage from '../features/courses/CourseCatalogPage';
import Spinner from '../components/common/Spinner';
import NotFoundPage from '../pages/NotFoundPage';
import ProtectedRoute, { GuestRoute } from './ProtectedRoute';

// Trang chi tiết môn kéo theo thư viện Markdown/KaTeX/Prism (nặng) -> chỉ tải khi người dùng mở môn học
const CourseDetailPage = lazy(() => import('../features/courses/CourseDetailPage'));
const CourseDocumentsPage = lazy(() => import('../features/courses/CourseDocumentsPage')); // RAG cho sinh viên
const TutorChatPage = lazy(() => import('../features/tutor/TutorChatPage'));
const QuizTakePage = lazy(() => import('../features/quiz/QuizTakePage')); // SCR-05
const QuizResultPage = lazy(() => import('../features/quiz/QuizResultPage')); // SCR-06
const ProgressDashboardPage = lazy(() => import('../features/progress/ProgressDashboardPage')); // SCR-07

// SCR-08: khu vực quản trị, tách chunk riêng vì sinh viên không bao giờ tải tới
const AdminLayout = lazy(() => import('../features/admin/AdminLayout'));
const UserManagementPage = lazy(() => import('../features/admin/UserManagementPage'));
const PromptConfigPage = lazy(() => import('../features/admin/PromptConfigPage'));
const TokenLogPage = lazy(() => import('../features/admin/TokenLogPage'));
const RagDocumentsPage = lazy(() => import('../features/admin/RagDocumentsPage'));

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
          {/* Tài liệu PDF & hỏi đáp có trích dẫn trang (FR-RG-*): sinh viên đã ghi danh dùng, không cần quyền Admin */}
          <Route
            path="/courses/:courseId/documents"
            element={
              <Suspense fallback={pageFallback}>
                <CourseDocumentsPage />
              </Suspense>
            }
          />
          {/* "/*" bắt cả /courses/:id và /courses/:id/lessons/:lessonId bằng một trang, đổi bài không remount */}
          <Route
            path="/courses/:courseId/*"
            element={
              <Suspense fallback={pageFallback}>
                <CourseDetailPage />
              </Suspense>
            }
          />
          {/* SCR-04: /tutor (mở bài học gần nhất) và /tutor/:lessonId?course=:courseId */}
          <Route
            path="/tutor"
            element={
              <Suspense fallback={pageFallback}>
                <TutorChatPage />
              </Suspense>
            }
          />
          <Route
            path="/tutor/:lessonId"
            element={
              <Suspense fallback={pageFallback}>
                <TutorChatPage />
              </Suspense>
            }
          />
          {/* SCR-05: làm bài có đồng hồ đếm ngược (topicId); SCR-06: xem kết quả (attemptId) */}
          <Route
            path="/quiz/:topicId"
            element={
              <Suspense fallback={pageFallback}>
                <QuizTakePage />
              </Suspense>
            }
          />
          <Route
            path="/quiz/:attemptId/result"
            element={
              <Suspense fallback={pageFallback}>
                <QuizResultPage />
              </Suspense>
            }
          />
          <Route path="/progress" element={
            <Suspense fallback={pageFallback}>
              <ProgressDashboardPage />
            </Suspense>
          } />
        </Route>
      </Route>

      {/* SCR-08: Quản trị viên (RBAC: sinh viên bị chuyển về /courses) */}
      <Route element={<ProtectedRoute roles={['ADMIN']} />}>
        <Route
          path="/admin"
          element={
            <Suspense fallback={pageFallback}>
              <AdminLayout />
            </Suspense>
          }
        >
          <Route index element={<Navigate to="users" replace />} />
          <Route path="users" element={<UserManagementPage />} />
          <Route path="prompts" element={<PromptConfigPage />} />
          <Route path="tokens" element={<TokenLogPage />} />
          <Route path="documents" element={<RagDocumentsPage />} />
        </Route>
      </Route>

      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  );
}
