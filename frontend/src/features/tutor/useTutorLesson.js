import { useEffect, useRef, useState } from 'react';
import { getErrorMessage } from '../../utils/apiError';
import { courseApi } from '../../api/courseApi';
import { findCourseOfLesson, pickDefaultCourse, readTutorTarget, sortLessons } from './tutorContext';

/**
 * Xác định môn học + bài học cho màn Gia sư AI từ URL (/tutor/:lessonId?course=:courseId).
 * Đổi bài trong cùng môn thì dùng lại dữ liệu môn học, không gọi API lại.
 * status: 'loading' | 'ready' | 'empty' | 'notfound' | 'error'
 */
export function useTutorLesson({ lessonId, courseId }) {
  const [state, setState] = useState({ status: 'loading', course: null, lessons: [], lesson: null, error: '' });
  const [reload, setReload] = useState(0);
  const cachedCourse = useRef(null);

  useEffect(() => {
    let cancelled = false;

    const cacheHit = () => {
      const c = cachedCourse.current;
      if (!c) return null;
      if (courseId && String(c.id) !== String(courseId)) return null;
      if (lessonId && !c.lessons.some((l) => String(l.id) === String(lessonId))) return null;
      return c;
    };

    async function run() {
      try {
        let course = cacheHit();
        if (!course) {
          setState({ status: 'loading', course: null, lessons: [], lesson: null, error: '' });
          if (courseId) course = await courseApi.getCourseDetail(courseId);
          else if (lessonId) course = await findCourseOfLesson(lessonId);
          else course = await pickDefaultCourse();
        }
        if (cancelled) return;
        const lessons = sortLessons(course);
        if (!course || lessons.length === 0) {
          setState({ status: lessonId ? 'notfound' : 'empty', course, lessons: [], lesson: null, error: '' });
          return;
        }
        const last = readTutorTarget();
        const wantedId = lessonId ?? (last && String(last.courseId) === String(course.id) ? last.lessonId : null);
        const lesson = lessons.find((l) => String(l.id) === String(wantedId)) || (lessonId ? null : lessons[0]);
        if (!lesson) {
          setState({ status: 'notfound', course, lessons, lesson: null, error: '' });
          return;
        }
        cachedCourse.current = course;
        setState({ status: 'ready', course, lessons, lesson, error: '' });
      } catch (error) {
        if (cancelled) return;
        setState({
          status: error.response?.status === 404 ? 'notfound' : 'error',
          course: null,
          lessons: [],
          lesson: null,
          error: getErrorMessage(error, 'Không tải được thông tin bài học'),
        });
      }
    }
    run();
    return () => {
      cancelled = true;
    };
  }, [lessonId, courseId, reload]);

  // Bài học lấy đồng bộ theo URL (nếu đã có trong môn) để đổi bài không bị trễ một nhịp render
  const fromUrl = state.status === 'ready' && lessonId ? state.lessons.find((l) => String(l.id) === String(lessonId)) : null;
  return { ...state, lesson: fromUrl || state.lesson, retry: () => setReload((n) => n + 1) };
}
