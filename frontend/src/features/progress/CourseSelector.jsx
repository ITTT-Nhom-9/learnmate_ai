import { useEffect, useState } from 'react';
import { courseApi } from '../../api/courseApi';

/**
 * Dropdown chọn môn học đã ghi danh, dùng cho trang Dashboard (SCR-07).
 * Mặc định chọn môn đầu tiên (đã ghi danh) nếu chưa có lựa chọn.
 */
export default function CourseSelector({ selectedCourseId, onSelect }) {
  const [courses, setCourses] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    courseApi
      .getCourses()
      .then((data) => {
        if (cancelled) return;
        // Chỉ hiển thị môn đã ghi danh và đang hoạt động (không hiển thị môn bị ẩn/lưu trữ)
        const enrolled = (data.courses || []).filter(
          (c) => c.is_enrolled && c.status !== 'INACTIVE'
        );
        setCourses(enrolled);
        // Tự chọn môn đầu tiên nếu chưa chọn
        if (!selectedCourseId && enrolled.length > 0) {
          onSelect(enrolled[0].id);
        }
      })
      .catch(() => {/* Lỗi tải danh sách môn, bỏ qua */})
      .finally(() => !cancelled && setLoading(false));
    return () => { cancelled = true; };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  if (loading) {
    return (
      <div className="h-10 w-48 animate-pulse rounded-lg bg-slate-200" />
    );
  }

  if (courses.length === 0) {
    return (
      <p className="text-sm text-slate-500">Bạn chưa ghi danh môn học nào.</p>
    );
  }

  return (
    <select
      value={selectedCourseId || ''}
      onChange={(e) => onSelect(Number(e.target.value))}
      aria-label="Chọn môn học"
      className="h-10 rounded-lg border border-slate-300 bg-white px-3 text-sm font-medium text-navy-800 shadow-sm transition-colors hover:border-slate-400 focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/20"
    >
      {courses.map((c) => (
        <option key={c.id} value={c.id}>
          {c.code} – {c.title}
        </option>
      ))}
    </select>
  );
}
