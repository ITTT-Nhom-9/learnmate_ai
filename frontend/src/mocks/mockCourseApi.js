// Dữ liệu mock cho SCR-02 / SCR-03: lấy từ chính bộ seed của TK-03 (2 môn, 8 bài, 16 chủ đề)
// cộng thêm 4 môn minh họa (không có bài học) để thấy đủ các trạng thái trên giao diện.
import seed from './seedCourses.json';

const delay = (ms = 250) => new Promise((resolve) => setTimeout(resolve, ms));

const DEMO_COURSES = [
  { id: 101, code: 'CS102', title: 'Lập trình hướng đối tượng', total_lessons: 10, lessons: [] },
  { id: 102, code: 'MATH201', title: 'Đại số tuyến tính', total_lessons: 16, lessons: [] },
  { id: 103, code: 'CS202', title: 'Mạng máy tính', total_lessons: 12, lessons: [] },
  { id: 104, code: 'MATH202', title: 'Xác suất và Thống kê', total_lessons: 10, lessons: [] },
];

const allCourses = [
  ...seed.courses.map((c) => ({ ...c, total_lessons: c.lessons.length })),
  ...DEMO_COURSES,
];

// Môn đã ghi danh -> % tiến độ
const progressByCourse = { 1: 50, 101: 40, 102: 25, 104: 100 };

function httpError(status, detail) {
  return Object.assign(new Error(detail), { response: { status, data: { detail } } });
}

function findCourse(courseId) {
  const course = allCourses.find((c) => c.id === Number(courseId));
  if (!course) throw httpError(404, 'Môn học không tồn tại');
  return course;
}

function summarize(course) {
  const enrolled = course.id in progressByCourse;
  return {
    id: course.id,
    code: course.code,
    title: course.title,
    description: course.description || null,
    progress_pct: enrolled ? progressByCourse[course.id] : 0,
    is_enrolled: enrolled,
    total_lessons: course.total_lessons,
  };
}

/** Điểm Mastery giả lập: các bài đầu đã vững, bài kế tiếp đang học dở, còn lại chưa học. */
function masteryFor(course, lessonIndex, topicIndex) {
  const pct = progressByCourse[course.id];
  if (!pct) return 0; // chưa ghi danh hoặc mới ghi danh (0%) -> chưa học chủ đề nào
  const done = Math.floor((course.lessons.length * pct) / 100);
  if (lessonIndex < done) return 65 + ((lessonIndex * 7 + topicIndex * 11) % 30);
  if (lessonIndex === done) return topicIndex === 0 ? 45 : 0;
  return 0;
}

function lessonWithMastery(course, lesson, lessonIndex) {
  return {
    ...lesson,
    topics: lesson.topics.map((t, i) => ({ ...t, mastery_score: masteryFor(course, lessonIndex, i) })),
  };
}

export async function getCourses() {
  await delay();
  const courses = allCourses.map(summarize);
  return { courses, total: courses.length };
}

export async function getCourseDetail(courseId) {
  await delay();
  const course = findCourse(courseId);
  return {
    id: course.id,
    code: course.code,
    title: course.title,
    description: course.description || null,
    lessons: course.lessons.map((lesson, i) => {
      const { contents, ...rest } = lessonWithMastery(course, lesson, i); // danh sách bài không kèm nội dung
      return rest;
    }),
  };
}

export async function enroll(courseId) {
  await delay();
  const course = findCourse(courseId);
  if (course.id in progressByCourse) throw httpError(409, 'Bạn đã ghi danh môn học này');
  progressByCourse[course.id] = 0;
  return {
    enrollment_id: Date.now(),
    course_id: course.id,
    user_id: 0,
    status: 'ACTIVE',
    enrolled_at: new Date().toISOString(),
  };
}

export async function getLessonDetail(courseId, lessonId) {
  await delay();
  const course = findCourse(courseId);
  const index = course.lessons.findIndex((l) => l.id === Number(lessonId));
  if (index < 0) throw httpError(404, 'Bài học không tồn tại');
  return { ...lessonWithMastery(course, course.lessons[index], index), course_id: course.id };
}
