import { useEffect, useState } from 'react';
import { FileText } from 'lucide-react';
import AlertBox from '../../components/common/AlertBox';
import Button from '../../components/common/Button';
import EmptyState from '../../components/common/EmptyState';
import Spinner from '../../components/common/Spinner';
import { courseApi } from '../../api/courseApi';
import RagWorkspace from '../rag/RagWorkspace';
import { AdminPageHeader, FilterSelect } from './AdminCommon';
import { useAdminQuery } from './useAdminQuery';

/**
 * SCR-08 · Tab RAG của Quản trị viên: chọn môn học rồi quản lý giáo trình chuẩn cho toàn trường.
 * Sinh viên dùng cùng RagWorkspace tại /courses/:id/documents (FR-RG-01, FR-RG-03).
 */
export default function RagDocumentsPage() {
  const [courseId, setCourseId] = useState(null);
  const courses = useAdminQuery(() => courseApi.getCourses({ limit: 100 }), []);
  const courseList = courses.data?.courses ?? [];

  // Mặc định chọn môn đầu tiên khi danh sách môn tải xong
  useEffect(() => {
    if (!courseId && courseList.length > 0) setCourseId(courseList[0].id);
  }, [courseId, courseList]);

  return (
    <>
      <AdminPageHeader
        title="Tài liệu RAG"
        description="Quản lý giáo trình PDF theo môn học. Sinh viên đã ghi danh cũng có thể tải lên và hỏi đáp ở trang môn học."
        actions={
          courseList.length > 0 && (
            <FilterSelect label="Chọn môn học" value={courseId ?? ''} onChange={(v) => setCourseId(Number(v))} className="max-w-full sm:max-w-xs">
              {courseList.map((c) => (
                <option key={c.id} value={c.id}>{c.code} – {c.title}</option>
              ))}
            </FilterSelect>
          )
        }
      />

      {courses.error && <AlertBox tone="error" className="mb-4" action={<Button variant="outline" size="sm" onClick={courses.reload}>Thử lại</Button>}>{courses.error}</AlertBox>}
      {courses.loading && !courses.data && <div className="flex justify-center py-16 text-slate-400"><Spinner size={28} label="Đang tải danh sách môn" /></div>}
      {courses.data && courseList.length === 0 && (
        <EmptyState icon={FileText} title="Chưa có môn học" description="Cần có ít nhất một môn học để gắn tài liệu giáo trình." />
      )}

      {courseId && <RagWorkspace courseId={courseId} />}
    </>
  );
}
