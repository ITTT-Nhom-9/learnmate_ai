import { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Calendar, LayoutGrid, List, Search, SearchX, BookX } from 'lucide-react';
import clsx from 'clsx';
import AlertBox from '../../components/common/AlertBox';
import Button from '../../components/common/Button';
import EmptyState from '../../components/common/EmptyState';
import { courseApi } from '../../api/courseApi';
import { getErrorMessage } from '../../utils/apiError';
import CourseCard, { CourseCardSkeleton } from './CourseCard';
import { filterCourses, getCourseStatus } from './courseUtils';

const SEMESTER_LABEL = 'Học kỳ I · 2026 – 2027';
const FILTERS = [
  { key: 'all', label: 'Tất cả' },
  { key: 'learning', label: 'Đang học' },
  { key: 'done', label: 'Đã hoàn thành' },
];

/** SCR-02: Danh mục môn học. */
export default function CourseCatalogPage() {
  const navigate = useNavigate();
  const [courses, setCourses] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState('');
  const [actionError, setActionError] = useState('');
  const [query, setQuery] = useState('');
  const [filter, setFilter] = useState('all');
  const [layout, setLayout] = useState('grid');
  const [enrollingId, setEnrollingId] = useState(null);

  const loadCourses = useCallback(async (signal) => {
    setLoading(true);
    setLoadError('');
    try {
      const data = await courseApi.getCourses();
      if (!signal?.cancelled) setCourses(data.courses || []);
    } catch (error) {
      if (!signal?.cancelled) setLoadError(getErrorMessage(error, 'Không tải được danh sách môn học'));
    } finally {
      if (!signal?.cancelled) setLoading(false);
    }
  }, []);

  useEffect(() => {
    const signal = { cancelled: false };
    loadCourses(signal);
    return () => {
      signal.cancelled = true;
    };
  }, [loadCourses]);

  const stats = useMemo(() => {
    const statuses = courses.map(getCourseStatus);
    return {
      total: courses.length,
      learning: statuses.filter((s) => s === 'IN_PROGRESS').length,
      done: statuses.filter((s) => s === 'COMPLETED').length,
    };
  }, [courses]);

  const visible = useMemo(() => filterCourses(courses, { query, filter }), [courses, query, filter]);

  // Môn chưa ghi danh: "Bắt đầu học" = ghi danh (API-07) rồi vào môn học. Các trạng thái còn lại vào thẳng môn học.
  const handleAction = async (course) => {
    setActionError('');
    if (getCourseStatus(course) !== 'NOT_STARTED') {
      navigate(`/courses/${course.id}`);
      return;
    }
    setEnrollingId(course.id);
    try {
      await courseApi.enroll(course.id);
    } catch (error) {
      // 409: đã ghi danh từ trước -> coi như thành công
      if (error.response?.status !== 409) {
        setActionError(getErrorMessage(error, 'Không thể ghi danh môn học, vui lòng thử lại'));
        setEnrollingId(null);
        return;
      }
    }
    setCourses((prev) => prev.map((c) => (c.id === course.id ? { ...c, is_enrolled: true } : c)));
    setEnrollingId(null);
    navigate(`/courses/${course.id}`);
  };

  const resetFilters = () => {
    setQuery('');
    setFilter('all');
  };

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-3xl font-bold text-navy-800">Danh mục môn học</h1>
          <p className="mt-1.5 text-sm text-slate-500">Chọn môn học và tiếp tục hành trình chinh phục kiến thức.</p>
        </div>
        <p className="hidden items-center gap-2 text-sm text-slate-500 sm:flex">
          <Calendar size={16} aria-hidden="true" />
          {SEMESTER_LABEL}
        </p>
      </div>

      <div className="mt-7 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div className="relative md:w-full md:max-w-md">
          <Search size={18} className="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" aria-hidden="true" />
          <input
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Tìm kiếm tên môn học hoặc mã môn..."
            aria-label="Tìm kiếm môn học"
            className="h-12 w-full rounded-lg border border-slate-300 bg-white pl-10 pr-3 text-base placeholder:text-slate-400 focus:border-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-100 sm:text-sm"
          />
        </div>

        <div role="group" aria-label="Lọc theo trạng thái" className="flex rounded-lg bg-slate-200/60 p-1">
          {FILTERS.map(({ key, label }) => (
            <button
              key={key}
              type="button"
              onClick={() => setFilter(key)}
              aria-pressed={filter === key}
              className={clsx(
                'flex-1 whitespace-nowrap rounded-md px-4 py-2 text-sm transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600 md:flex-none md:px-5',
                filter === key ? 'bg-white font-semibold text-navy-800 shadow-sm' : 'font-medium text-slate-500 hover:text-navy-800'
              )}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      <div className="mt-4 flex items-center justify-between text-xs text-slate-500">
        <p>
          {stats.total} môn học · {stats.learning} đang học · {stats.done} đã hoàn thành
        </p>
        <button
          type="button"
          onClick={() => setLayout((l) => (l === 'grid' ? 'list' : 'grid'))}
          className="hidden items-center gap-1.5 rounded px-1 text-xs font-medium text-slate-600 hover:text-navy-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600 sm:flex"
        >
          {layout === 'grid' ? <LayoutGrid size={16} className="text-blue-600" /> : <List size={16} className="text-blue-600" />}
          {layout === 'grid' ? 'Dạng lưới' : 'Dạng danh sách'}
        </button>
      </div>

      {actionError && <AlertBox tone="error" className="mt-4">{actionError}</AlertBox>}

      <section aria-label="Danh sách môn học" aria-busy={loading} className="mt-4">
        {loading ? (
          <div className="grid gap-5 sm:grid-cols-2 xl:grid-cols-3">
            {Array.from({ length: 6 }, (_, i) => (
              <CourseCardSkeleton key={i} />
            ))}
          </div>
        ) : loadError ? (
          <AlertBox
            tone="error"
            action={
              <Button size="sm" variant="outline" onClick={() => loadCourses()}>
                Thử lại
              </Button>
            }
          >
            {loadError}
          </AlertBox>
        ) : courses.length === 0 ? (
          <EmptyState icon={BookX} title="Chưa có môn học nào" description="Danh sách sẽ xuất hiện khi giảng viên mở môn học." />
        ) : visible.length === 0 ? (
          <EmptyState
            icon={SearchX}
            title="Không tìm thấy môn học phù hợp"
            description="Thử đổi từ khóa tìm kiếm hoặc bộ lọc trạng thái."
            action={
              <Button variant="outline" size="sm" onClick={resetFilters}>
                Xóa bộ lọc
              </Button>
            }
          />
        ) : (
          <div className={clsx('grid gap-5', layout === 'grid' ? 'sm:grid-cols-2 xl:grid-cols-3' : 'grid-cols-1')}>
            {visible.map((course) => (
              <CourseCard
                key={course.id}
                course={course}
                layout={layout}
                busy={enrollingId === course.id}
                onAction={handleAction}
              />
            ))}
          </div>
        )}
      </section>

      {!loading && !loadError && courses.length > 0 && (
        <div className="mt-6 flex flex-wrap items-center justify-between gap-2 text-xs text-slate-500">
          <p>
            Hiển thị {visible.length} trên {courses.length} môn học
          </p>
          <p>Nội dung được cập nhật bởi giảng viên của bạn</p>
        </div>
      )}
    </div>
  );
}
