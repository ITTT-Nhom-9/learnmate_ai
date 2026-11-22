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
    // Ẩn các môn có trạng thái INACTIVE khỏi danh mục học sinh
    if (course.status && course.status === 'INACTIVE') return false;

    const status = getCourseStatus(course);
    if (filter === 'learning' && status !== 'IN_PROGRESS') return false;
    if (filter === 'done' && status !== 'COMPLETED') return false;
    if (!q) return true;
    return normalizeText(course.title).includes(q) || normalizeText(course.code).includes(q);
  });
}

// ---- Trạng thái học tập của chủ đề / bài học (suy ra từ mastery_score của API-06) ----

export function getTopicState(topic, isLocked = false) {
  if (isLocked) return 'locked';
  const score = Number(topic.mastery_score) || 0;
  if (score >= MASTERY_DONE_THRESHOLD) return 'done';
  return score > 0 ? 'progress' : 'todo';
}

export function getLessonState(lesson, isLocked = false) {
  if (isLocked) return 'locked';
  const topics = lesson.topics || [];
  if (topics.length === 0) return 'todo';
  const states = topics.map((t) => getTopicState(t));
  if (states.every((s) => s === 'done')) return 'done';
  return states.some((s) => s !== 'todo') ? 'progress' : 'todo';
}

export function getCourseProgress(lessons, course = null) {
  const total = lessons.length;
  // Số bài học đã học: Có ít nhất một chủ đề sinh viên đã làm bài hoặc hoàn thành
  const learned = lessons.filter((l) => {
    const state = getLessonState(l);
    return state === 'done' || state === 'progress';
  }).length;
  const done = lessons.filter((l) => getLessonState(l) === 'done').length;

  const allTopics = lessons.flatMap((l) => l.topics || []);
  const doneTopics = allTopics.filter(
    (t) => (Number(t.mastery_score) || 0) >= MASTERY_DONE_THRESHOLD
  ).length;

  // Tỷ lệ hoàn thành %: Ưu tiên lấy từ course.progress_pct của backend để đồng nhất toàn hệ thống
  let pct = 0;
  if (course && course.progress_pct != null) {
    pct = Math.round(Number(course.progress_pct));
  } else if (allTopics.length > 0) {
    pct = Math.round((doneTopics / allTopics.length) * 100);
  }

  return { done, learned, total, doneTopics, totalTopics: allTopics.length, pct };
}

/**
 * Tính toán trạng thái Khóa tuần tự (Sequential Prerequisite Lock theo SCR-04).
 * Quy tắc nghiệp vụ LMS:
 * - Chủ đề/bài học đầu tiên luôn mở khóa.
 * - Bất kỳ chủ đề/bài học nào sinh viên đã từng làm bài (mastery_score > 0) thì luôn mở.
 * - Chủ đề tiếp theo được MỞ KHÓA ngay khi sinh viên hoàn thành bài trắc nghiệm của chủ đề liền trước (mastery_score > 0).
 * - Các bài học/chủ đề phía sau chưa học sẽ ở trạng thái BỊ KHÓA (locked) cho đến khi sinh viên làm bài chủ đề trước.
 */
export function computeLockStates(lessons) {
  const lockedTopicIds = new Set();
  const lockedLessonIds = new Set();

  let previousTopicCompleted = true; // Chủ đề đầu tiên của môn luôn mở

  lessons.forEach((lesson, lIdx) => {
    const topics = lesson.topics || [];
    let hasUnlockedTopicInLesson = false;

    if (topics.length === 0) {
      if (lIdx > 0 && !previousTopicCompleted) {
        lockedLessonIds.add(lesson.id);
      }
      return;
    }

    topics.forEach((topic) => {
      const score = Number(topic.mastery_score) || 0;
      const isAttempted = score > 0;

      // Một chủ đề được mở nếu:
      // 1. Chủ đề trước đó đã được làm bài (previousTopicCompleted = true)
      // 2. HOẶC chính chủ đề này đã từng được làm bài (isAttempted = true)
      if (!previousTopicCompleted && !isAttempted) {
        lockedTopicIds.add(topic.id);
      } else {
        hasUnlockedTopicInLesson = true;
      }

      // Điều kiện để mở chủ đề kế tiếp là chủ đề này đã được làm bài (score > 0)
      previousTopicCompleted = isAttempted;
    });

    if (lIdx > 0 && !hasUnlockedTopicInLesson) {
      lockedLessonIds.add(lesson.id);
    }
  });

  return { lockedTopicIds, lockedLessonIds };
}

/** Tên danh mục Module theo môn học (SCR-04). */
const KNOWN_MODULE_TITLES = {
  IT201: [
    'Tổng quan & Thiết kế CSDL',
    'Mô hình Quan hệ & Truy vấn SQL',
    'Tối ưu hóa & Quản trị CSDL',
  ],
  CS101: [
    'Cấu trúc tuyến tính',
    'Cây và ứng dụng',
    'Đồ thị',
  ],
  IT202: [
    'Cấu trúc tuyến tính',
    'Cây và ứng dụng',
    'Đồ thị & Giải thuật',
  ],
};

/**
 * Phân nhóm danh sách bài học thành các Module (Chương) tương ứng với bản vẽ SCR-04.
 * Mặc định mỗi 2 bài học được gom thành 1 Module.
 */
export function groupLessonsIntoModules(lessons, course) {
  if (!lessons || lessons.length === 0) return [];
  const code = (course?.code || '').toUpperCase().trim();
  const titles = KNOWN_MODULE_TITLES[code] || [];

  const modules = [];
  const lessonsPerModule = 2;

  for (let i = 0; i < lessons.length; i += lessonsPerModule) {
    const slice = lessons.slice(i, i + lessonsPerModule);
    const modIdx = Math.floor(i / lessonsPerModule) + 1;
    const title = titles[modIdx - 1] || `Chương ${modIdx}`;
    modules.push({
      id: `module-${modIdx}`,
      orderIndex: modIdx,
      title: `Module ${modIdx} · ${title}`,
      shortTitle: `Module ${modIdx}`,
      lessons: slice,
    });
  }

  return modules;
}

/** Ghép khối nội dung với chủ đề: ưu tiên so khớp tiêu đề "# Tên chủ đề" ở đầu nội dung, không có thì theo thứ tự. */
export function matchTopicId(content, topics, index) {
  const heading = /^#\s+(.+)$/m.exec(content.body || '')?.[1]?.trim();
  const byHeading = heading && topics.find((t) => t.name === heading);
  return (byHeading || topics[index])?.id ?? null;
}
