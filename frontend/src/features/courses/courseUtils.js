import { BookOpen, Code2, Database, Globe, LineChart, Network, Sigma } from 'lucide-react';
import { normalizeText } from '../../utils/formatters';

/** Điểm Mastery (thang 100) từ mức này trở lên được xem là đã nắm vững chủ đề. Khớp ngưỡng FAIR của Backend. */
export const MASTERY_DONE_THRESHOLD = 60;

export const COURSE_STATUS = {
  IN_PROGRESS: { label: 'Đang học', tone: 'blue', action: 'Tiếp tục học' },
  COMPLETED: { label: 'Đã hoàn thành', tone: 'green', action: 'Xem lại khóa học' },
  NOT_STARTED: { label: 'Chưa bắt đầu', tone: 'gray', action: 'Bắt đầu học' },
};

/** Suy ra trạng thái hiển thị từ dữ liệu API-05 (is_enrolled, progress_pct). */
export function getCourseStatus(course) {
  if (!course.is_enrolled) return 'NOT_STARTED';
  return Number(course.progress_pct) >= 100 ? 'COMPLETED' : 'IN_PROGRESS';
}

/** Số bài đã học = làm tròn(tổng bài x % tiến độ). */
export function getLearnedLessons(course) {
  return Math.round((course.total_lessons * (Number(course.progress_pct) || 0)) / 100);
}

const ICON_RULES = [
  [/co so du lieu|csdl|database/, Database],
  [/cau truc|giai thuat|thuat toan/, Network],
  [/lap trinh|code/, Code2],
  [/dai so|toan|giai tich/, Sigma],
  [/mang/, Globe],
  [/xac suat|thong ke/, LineChart],
];

export function getCourseIcon(course) {
  const text = normalizeText(`${course.title} ${course.code}`);
  return ICON_RULES.find(([pattern]) => pattern.test(text))?.[1] || BookOpen;
}

export function filterCourses(courses, { query, filter }) {
  const q = normalizeText(query);
  return courses.filter((course) => {
    const status = getCourseStatus(course);
    if (filter === 'learning' && status !== 'IN_PROGRESS') return false;
    if (filter === 'done' && status !== 'COMPLETED') return false;
    if (!q) return true;
    return normalizeText(course.title).includes(q) || normalizeText(course.code).includes(q);
  });
}

// ---- Trạng thái học tập của chủ đề / bài học (suy ra từ mastery_score của API-06) ----

export function getTopicState(topic) {
  const score = Number(topic.mastery_score) || 0;
  if (score >= MASTERY_DONE_THRESHOLD) return 'done';
  return score > 0 ? 'progress' : 'todo';
}

export function getLessonState(lesson) {
  const topics = lesson.topics || [];
  if (topics.length === 0) return 'todo';
  const states = topics.map(getTopicState);
  if (states.every((s) => s === 'done')) return 'done';
  return states.some((s) => s !== 'todo') ? 'progress' : 'todo';
}

export function getCourseProgress(lessons) {
  const total = lessons.length;
  const done = lessons.filter((l) => getLessonState(l) === 'done').length;
  return { done, total, pct: total ? Math.round((done / total) * 100) : 0 };
}

/** Ghép khối nội dung với chủ đề: ưu tiên so khớp tiêu đề "# Tên chủ đề" ở đầu nội dung, không có thì theo thứ tự. */
export function matchTopicId(content, topics, index) {
  const heading = /^#\s+(.+)$/m.exec(content.body || '')?.[1]?.trim();
  const byHeading = heading && topics.find((t) => t.name === heading);
  return (byHeading || topics[index])?.id ?? null;
}
