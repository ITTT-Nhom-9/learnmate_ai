import { courseApi } from '../../api/courseApi';

// Phiên chat gắn với BÀI HỌC (API-09: /tutor/history/{lessonId}), còn danh sách bài học thuộc MÔN HỌC (API-06).
// Các hàm dưới đây xác định môn học + bài học cần mở khi URL chưa đủ thông tin.

const LAST_KEY = 'lm_last_tutor';

export function rememberTutorTarget(courseId, lessonId) {
  try {
    localStorage.setItem(LAST_KEY, JSON.stringify({ courseId: Number(courseId), lessonId: Number(lessonId) }));
  } catch {
    /* storage bị chặn -> bỏ qua */
  }
}

export function readTutorTarget() {
  try {
    const value = JSON.parse(localStorage.getItem(LAST_KEY) || 'null');
    return value?.courseId && value?.lessonId ? value : null;
  } catch {
    return null;
  }
}

export const sortLessons = (course) => [...(course?.lessons || [])].sort((a, b) => a.order_index - b.order_index);

async function listCourses() {
  const { courses } = await courseApi.getCourses({ limit: 100 });
  return [...(courses || [])].sort((a, b) => Number(b.is_enrolled) - Number(a.is_enrolled)); // môn đã ghi danh lên trước
}

/** URL /tutor/:lessonId không kèm ?course= -> dò xem bài học thuộc môn nào. */
export async function findCourseOfLesson(lessonId) {
  for (const summary of await listCourses()) {
    const detail = await courseApi.getCourseDetail(summary.id);
    if ((detail.lessons || []).some((l) => String(l.id) === String(lessonId))) return detail;
  }
  return null;
}

/** URL /tutor (từ menu "Học cùng AI"): ưu tiên môn học gần nhất, không có thì môn đã ghi danh đầu tiên. */
export async function pickDefaultCourse() {
  const last = readTutorTarget();
  if (last) {
    try {
      const detail = await courseApi.getCourseDetail(last.courseId);
      if (sortLessons(detail).length > 0) return detail;
    } catch {
      /* môn học cũ không còn -> chọn môn khác */
    }
  }
  for (const summary of await listCourses()) {
    const detail = await courseApi.getCourseDetail(summary.id);
    if (sortLessons(detail).length > 0) return detail;
  }
  return null;
}
