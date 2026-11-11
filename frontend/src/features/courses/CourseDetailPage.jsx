import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { ArrowLeft, ArrowRight, BookX, ListTree, Sparkles } from 'lucide-react';
import AlertBox from '../../components/common/AlertBox';
import Badge from '../../components/common/Badge';
import Button from '../../components/common/Button';
import EmptyState from '../../components/common/EmptyState';
import Spinner from '../../components/common/Spinner';
import Breadcrumb from '../../components/layout/Breadcrumb';
import Sidebar from '../../components/layout/Sidebar';
import { courseApi } from '../../api/courseApi';
import { estimateReadMinutes } from '../../utils/formatters';
import { getErrorMessage } from '../../utils/apiError';
import LessonContentView from './LessonContentView';
import LessonTree from './LessonTree';
import { getCourseProgress } from './courseUtils';

const prefersReducedMotion = () => window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;

/**
 * SCR-03: Chi tiết môn học = Cây bài học (Sidebar) + nội dung lý thuyết bài giảng.
 * Route: /courses/:courseId và /courses/:courseId/lessons/:lessonId (cùng một trang, đổi bài không tải lại cả môn).
 */
export default function CourseDetailPage() {
  const params = useParams();
  const navigate = useNavigate();
  const courseId = params.courseId;
  const lessonIdFromUrl = Number(/^lessons\/(\d+)/.exec(params['*'] || '')?.[1]) || null;

  const [course, setCourse] = useState(null);
  const [courseState, setCourseState] = useState({ loading: true, error: '', notFound: false });
  const [courseReload, setCourseReload] = useState(0);

  const [lesson, setLesson] = useState(null);
  const [lessonState, setLessonState] = useState({ loading: false, error: '' });
  const [lessonReload, setLessonReload] = useState(0);

  const [expandedIds, setExpandedIds] = useState(() => new Set());
  const [activeTopicId, setActiveTopicId] = useState(null);
  const [drawerOpen, setDrawerOpen] = useState(false);

  const spyLockUntil = useRef(0); // tạm tắt scroll-spy ngay sau khi người dùng bấm chọn chủ đề
  const pendingTopicId = useRef(null); // chủ đề cần cuộn tới sau khi tải xong bài học mới

  // ---- Tải môn học (API-06) ----
  useEffect(() => {
    let cancelled = false;
    setCourseState({ loading: true, error: '', notFound: false });
    courseApi
      .getCourseDetail(courseId)
      .then((data) => {
        if (cancelled) return;
        setCourse(data);
        setCourseState({ loading: false, error: '', notFound: false });
      })
      .catch((error) => {
        if (cancelled) return;
        setCourseState({
          loading: false,
          error: getErrorMessage(error, 'Không tải được nội dung môn học'),
          notFound: error.response?.status === 404,
        });
      });
    return () => {
      cancelled = true;
    };
  }, [courseId, courseReload]);

  const lessons = useMemo(
    () => [...(course?.lessons || [])].sort((a, b) => a.order_index - b.order_index),
    [course]
  );
  const activeLessonId = lessons.find((l) => l.id === lessonIdFromUrl)?.id ?? lessons[0]?.id ?? null;
  const activeIndex = lessons.findIndex((l) => l.id === activeLessonId);
  const activeLesson = lessons[activeIndex] || null;
  const prevLesson = activeIndex > 0 ? lessons[activeIndex - 1] : null;
  const nextLesson = activeIndex >= 0 && activeIndex < lessons.length - 1 ? lessons[activeIndex + 1] : null;
  const progress = useMemo(() => getCourseProgress(lessons), [lessons]);

  // ---- Tải nội dung bài học đang chọn ----
  useEffect(() => {
    if (activeLessonId == null) return undefined;
    let cancelled = false;
    setLesson(null);
    setLessonState({ loading: true, error: '' });
    courseApi
      .getLessonDetail(courseId, activeLessonId)
      .then((data) => {
        if (cancelled) return;
        setLesson(data);
        setLessonState({ loading: false, error: '' });
        const target = pendingTopicId.current ?? data.topics?.[0]?.id ?? null;
        setActiveTopicId(target);
        if (pendingTopicId.current != null) {
          requestAnimationFrame(() => scrollToTopic(pendingTopicId.current));
          pendingTopicId.current = null;
        } else {
          window.scrollTo({ top: 0 });
        }
      })
      .catch((error) => {
        if (cancelled) return;
        setLessonState({ loading: false, error: getErrorMessage(error, 'Không tải được nội dung bài học') });
      });
    return () => {
      cancelled = true;
    };
  }, [courseId, activeLessonId, lessonReload]);

  // Luôn mở sẵn bài đang học trong cây
  useEffect(() => {
    if (activeLessonId != null) setExpandedIds((prev) => new Set(prev).add(activeLessonId));
  }, [activeLessonId]);

  function scrollToTopic(topicId) {
    spyLockUntil.current = Date.now() + 900;
    setActiveTopicId(topicId);
    document.getElementById(`topic-${topicId}`)?.scrollIntoView({
      behavior: prefersReducedMotion() ? 'auto' : 'smooth',
      block: 'start',
    });
  }

  const goToLesson = (lessonId) => navigate(`/courses/${courseId}/lessons/${lessonId}`);

  const handleSelectLesson = (target) => {
    setDrawerOpen(false);
    if (target.id === activeLessonId) window.scrollTo({ top: 0, behavior: prefersReducedMotion() ? 'auto' : 'smooth' });
    else goToLesson(target.id);
  };

  const handleSelectTopic = (targetLesson, topic) => {
    setDrawerOpen(false);
    if (targetLesson.id === activeLessonId) {
      scrollToTopic(topic.id);
    } else {
      pendingTopicId.current = topic.id;
      goToLesson(targetLesson.id);
    }
  };

  const handleToggleLesson = (lessonId) =>
    setExpandedIds((prev) => {
      const next = new Set(prev);
      if (next.has(lessonId)) next.delete(lessonId);
      else next.add(lessonId);
      return next;
    });

  const handleTopicVisible = useCallback((topicId) => {
    if (Date.now() >= spyLockUntil.current) setActiveTopicId(topicId);
  }, []);

  // ---- Các trạng thái toàn trang ----
  if (courseState.loading) {
    return (
      <div className="flex justify-center py-24 text-slate-400">
        <Spinner size={28} label="Đang tải môn học" />
      </div>
    );
  }

  if (courseState.error || !course) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-12 sm:px-6">
        {courseState.notFound ? (
          <EmptyState
            icon={BookX}
            title="Môn học không tồn tại"
            description="Môn học có thể đã bị gỡ hoặc đường dẫn không đúng."
            action={<Button variant="outline" onClick={() => navigate('/courses')}>Về danh mục môn học</Button>}
          />
        ) : (
          <AlertBox
            tone="error"
            action={<Button size="sm" variant="outline" onClick={() => setCourseReload((n) => n + 1)}>Thử lại</Button>}
          >
            {courseState.error}
          </AlertBox>
        )}
      </div>
    );
  }

  const breadcrumb = [{ label: 'Khóa học', to: '/courses' }, { label: course.code }, { label: course.title }];

  if (lessons.length === 0) {
    return (
      <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
        <Breadcrumb items={breadcrumb} />
        <div className="mt-6">
          <EmptyState
            icon={BookX}
            title="Môn học chưa có bài giảng"
            description="Nội dung sẽ hiển thị khi giảng viên đăng bài học cho môn này."
            action={<Button variant="outline" onClick={() => navigate('/courses')}>Về danh mục môn học</Button>}
          />
        </div>
      </div>
    );
  }

  const topicCount = activeLesson.topics?.length || 0;
  const readMinutes = lesson ? estimateReadMinutes((lesson.contents || []).map((c) => c.body).join(' ')) : null;

  return (
    <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
      <Breadcrumb items={breadcrumb} />

      <div className="mt-4 grid gap-6 lg:grid-cols-[340px_minmax(0,1fr)] lg:items-start">
        <Sidebar open={drawerOpen} onClose={() => setDrawerOpen(false)} title="Mục lục khóa học">
          <LessonTree
            course={course}
            lessons={lessons}
            progress={progress}
            activeLessonId={activeLessonId}
            activeTopicId={activeTopicId}
            expandedIds={expandedIds}
            onToggleLesson={handleToggleLesson}
            onSelectLesson={handleSelectLesson}
            onSelectTopic={handleSelectTopic}
          />
        </Sidebar>

        <article className="mb-20 min-w-0 rounded-xl border border-slate-200 bg-white p-5 sm:p-8 lg:mb-0">
          <div className="flex items-center gap-3">
            <Badge>BÀI {activeLesson.order_index}</Badge>
            <span className="min-w-0 truncate text-sm text-slate-500">
              {topicCount} chủ đề{readMinutes ? ` · ${readMinutes} phút đọc` : ''}
            </span>
            <button
              type="button"
              onClick={() => setDrawerOpen(true)}
              className="ml-auto flex shrink-0 items-center gap-1.5 whitespace-nowrap rounded-lg border border-slate-300 px-3 py-1.5 text-sm font-medium text-navy-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600 lg:hidden"
            >
              <ListTree size={16} aria-hidden="true" /> Mục lục
            </button>
          </div>

          <h1 className="mt-3 border-b border-slate-200 pb-5 text-2xl font-bold leading-snug text-navy-800 sm:text-[28px]">
            {activeLesson.title}
          </h1>

          <div className="mt-4 min-h-[240px]" aria-busy={lessonState.loading}>
            {lessonState.loading && (
              <div className="flex justify-center py-16 text-slate-400">
                <Spinner size={26} label="Đang tải bài học" />
              </div>
            )}
            {lessonState.error && (
              <AlertBox
                tone="error"
                action={<Button size="sm" variant="outline" onClick={() => setLessonReload((n) => n + 1)}>Thử lại</Button>}
              >
                {lessonState.error}
              </AlertBox>
            )}
            {lesson && <LessonContentView lesson={lesson} onTopicVisible={handleTopicVisible} />}
          </div>

          {/* Thanh điều hướng bài: cố định phía trên Bottom Nav trên mobile, nằm cuối nội dung trên desktop */}
          <div className="fixed inset-x-0 bottom-[calc(3.5rem+env(safe-area-inset-bottom))] z-30 flex items-center gap-2 border-t border-slate-200 bg-white px-4 py-3 lg:static lg:z-auto lg:mt-8 lg:border-0 lg:bg-transparent lg:p-0">
            <Button
              variant="outline"
              icon={ArrowLeft}
              disabled={!prevLesson}
              onClick={() => prevLesson && goToLesson(prevLesson.id)}
              aria-label="Bài trước"
            >
              <span className="hidden sm:inline">Bài trước</span>
            </Button>
            {nextLesson && (
              <Button variant="outline" onClick={() => goToLesson(nextLesson.id)} aria-label="Bài tiếp theo">
                <span className="hidden sm:inline">Bài tiếp theo</span>
                <ArrowRight size={18} aria-hidden="true" />
              </Button>
            )}
            <Button icon={Sparkles} className="flex-1 whitespace-nowrap lg:ml-auto lg:flex-none" onClick={() => navigate(`/tutor/${activeLesson.id}?course=${courseId}`)}>
              <span className="sm:hidden">Học cùng Gia sư AI</span>
              <span className="hidden sm:inline">Học cùng Gia sư AI bài này</span>
            </Button>
          </div>
        </article>
      </div>
    </div>
  );
}
