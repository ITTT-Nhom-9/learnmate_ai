import { BookX, FileText } from 'lucide-react';
import { useNavigate, useParams } from 'react-router-dom';
import AlertBox from '../../components/common/AlertBox';
import Button from '../../components/common/Button';
import EmptyState from '../../components/common/EmptyState';
import Spinner from '../../components/common/Spinner';
import Breadcrumb from '../../components/layout/Breadcrumb';
import { courseApi } from '../../api/courseApi';
import { useAdminQuery } from '../admin/useAdminQuery';
import RagWorkspace from '../rag/RagWorkspace';

/**
 * Tài liệu & Hỏi đáp PDF của một môn học dành cho Sinh viên (FR-RG-01, FR-RG-03, FR-RG-04, FR-RG-05).
 * Route: /courses/:courseId/documents. Vào từ nút "Tài liệu PDF" ở SCR-03.
 * Sinh viên phải ghi danh môn học; AI trả lời kèm số trang tham chiếu hoặc từ chối khi câu hỏi nằm ngoài tài liệu.
 */
export default function CourseDocumentsPage() {
  const { courseId } = useParams();
  const navigate = useNavigate();
  const course = useAdminQuery(() => courseApi.getCourseDetail(courseId), [courseId]);

  if (course.loading && !course.data) {
    return (
      <div className="flex justify-center py-24 text-slate-400">
        <Spinner size={28} label="Đang tải môn học" />
      </div>
    );
  }

  if (!course.data) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-12 sm:px-6">
        {course.errorStatus === 404 ? (
          <EmptyState
            icon={BookX}
            title="Môn học không tồn tại"
            description="Môn học có thể đã bị gỡ hoặc đường dẫn không đúng."
            action={<Button variant="outline" onClick={() => navigate('/courses')}>Về danh mục môn học</Button>}
          />
        ) : (
          <AlertBox tone="error" action={<Button size="sm" variant="outline" onClick={course.reload}>Thử lại</Button>}>
            {course.error}
          </AlertBox>
        )}
      </div>
    );
  }

  const { code, title } = course.data;
  return (
    <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
      <Breadcrumb items={[{ label: 'Khóa học', to: '/courses' }, { label: code, to: `/courses/${courseId}` }, { label: 'Tài liệu PDF' }]} />
      <div className="mb-6 mt-4">
        <h1 className="flex items-center gap-2 text-2xl font-bold text-navy-800">
          <FileText size={24} className="text-brand-500" aria-hidden="true" />
          Tài liệu & Hỏi đáp PDF
        </h1>
        <p className="mt-1 text-sm text-slate-500">{code} – {title}. Tải giáo trình PDF rồi hỏi đáp kiến thức nâng cao, AI trích dẫn số trang tham chiếu.</p>
      </div>
      <RagWorkspace courseId={Number(courseId)} defaultTab="ask" />
    </div>
  );
}
