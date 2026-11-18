// Dữ liệu mock cho SCR-07: Bảng tiến độ Dashboard & Radar Chart (TK-22).
// Mô phỏng đúng hợp đồng API của Backend (TK-21): GET /progress/summary & GET /progress/radar.
import seed from './seedCourses.json';

const delay = (ms = 300) => new Promise((resolve) => setTimeout(resolve, ms));

// --- Dữ liệu seed Mastery giả lập cho môn IT201 (Cơ sở dữ liệu, courseId = 1) ---
// 4 bài × 2 chủ đề = 8 chủ đề. 50% tiến độ → 4 chủ đề đã vững, 1 đang yếu, 3 chưa học.
const course1 = seed.courses[0];
const course1Topics = course1.lessons.flatMap((lesson, li) =>
  lesson.topics.map((topic, ti) => ({ ...topic, lessonId: lesson.id, lessonTitle: lesson.title, li, ti }))
);

function masteryScore(li, ti) {
  // Bài 1 & 2 (index 0,1): đã vững (65-95%), Bài 3 topic đầu: yếu (42%), còn lại: chưa học (0%)
  if (li < 2) return 65 + ((li * 7 + ti * 11) % 30);
  if (li === 2 && ti === 0) return 42;
  return 0;
}

function statusOf(score, practiced) {
  if (!practiced) return 'NOT_STARTED';
  if (score >= 80) return 'MASTER';
  if (score >= 60) return 'FAIR';
  return 'WEAK';
}

function labelViOf(status) {
  return { MASTER: 'Giỏi', FAIR: 'Khá', WEAK: 'Yếu', NOT_STARTED: 'Chưa học' }[status];
}

// --- Lịch sử làm bài gần đây ---
const RECENT_ATTEMPTS = [
  { attempt_id: 101, quiz_id: 501, quiz_title: 'Trắc nghiệm: DBMS & ACID', topic_id: 1, topic_name: 'Hệ quản trị CSDL (DBMS) và Hệ thống Tập tin truyền thống', difficulty: 'MEDIUM', score: 7.5, duration_sec: 420 },
  { attempt_id: 102, quiz_id: 502, quiz_title: 'Trắc nghiệm: Kiến trúc 3 lược đồ', topic_id: 2, topic_name: 'Kiến trúc 3 lược đồ ANSI-SPARC và Tính độc lập dữ liệu', difficulty: 'MEDIUM', score: 8.0, duration_sec: 350 },
  { attempt_id: 103, quiz_id: 503, quiz_title: 'Trắc nghiệm: Thực thể & Khóa', topic_id: 3, topic_name: 'Thực thể, Thuộc tính và Các loại Khóa định danh', difficulty: 'HARD', score: 6.5, duration_sec: 510 },
  { attempt_id: 104, quiz_id: 504, quiz_title: 'Trắc nghiệm: ERD & Cardinality', topic_id: 4, topic_name: 'Mối kết hợp (Relationship) và Bản số (Cardinality)', difficulty: 'MEDIUM', score: 9.0, duration_sec: 280 },
  { attempt_id: 105, quiz_id: 505, quiz_title: 'Trắc nghiệm: Ràng buộc Toàn vẹn', topic_id: 5, topic_name: 'Lược đồ Quan hệ và Ràng buộc Toàn vẹn (Integrity Constraints)', difficulty: 'MEDIUM', score: 4.0, duration_sec: 600 },
  { attempt_id: 106, quiz_id: 501, quiz_title: 'Trắc nghiệm: DBMS & ACID (lần 2)', topic_id: 1, topic_name: 'Hệ quản trị CSDL (DBMS) và Hệ thống Tập tin truyền thống', difficulty: 'HARD', score: 8.5, duration_sec: 390 },
];

// --- Chủ đề yếu (cảnh báo đỏ) ---
const WEAK_TOPICS = [
  {
    topic_id: 5,
    topic_name: 'Lược đồ Quan hệ và Ràng buộc Toàn vẹn (Integrity Constraints)',
    lesson_id: 3,
    lesson_title: 'Bài 3: Mô hình Dữ liệu Quan hệ & Đại số Quan hệ',
    mastery_score: 42,
    status: 'WEAK',
    alert_level: 'RED',
    attempt_count: 2,
    last_quiz_score: 4.0,
    last_practiced_at: '2026-11-16T14:30:00Z',
    recommended_action: 'REVIEW_THEORY',
  },
];

function httpError(status, detail) {
  return Object.assign(new Error(detail), { response: { status, data: { detail } } });
}

// --- API: GET /progress/summary ---
export async function getProgressSummary(courseId) {
  await delay();
  if (Number(courseId) !== 1) throw httpError(404, 'Môn học không tồn tại');

  const topics = course1Topics;
  let mastered = 0, fair = 0, weak = 0, notStarted = 0;
  topics.forEach(({ li, ti }) => {
    const score = masteryScore(li, ti);
    const practiced = li < 2 || (li === 2 && ti === 0);
    if (!practiced) { notStarted++; return; }
    if (score >= 80) mastered++;
    else if (score >= 60) fair++;
    else weak++;
  });

  const totalAttempts = RECENT_ATTEMPTS.length;
  const scoreSum = RECENT_ATTEMPTS.reduce((s, a) => s + a.score, 0);

  return {
    course_id: 1,
    course_code: course1.code,
    course_title: course1.title,
    overall_progress_pct: 43.38,
    stats: {
      total_topics: topics.length,
      mastered_topics: mastered,
      fair_topics: fair,
      weak_topics: weak,
      not_started_topics: notStarted,
      total_attempts: totalAttempts,
      average_quiz_score: Math.round((scoreSum / totalAttempts) * 100) / 100,
      total_study_time_sec: RECENT_ATTEMPTS.reduce((s, a) => s + a.duration_sec, 0),
      last_practiced_at: '2026-11-16T14:30:00Z',
    },
    weak_topics: WEAK_TOPICS,
    recent_attempts: RECENT_ATTEMPTS,
  };
}

// --- API: GET /progress/radar ---
export async function getProgressRadar(courseId, maxAxes = 6) {
  await delay();
  if (Number(courseId) !== 1) throw httpError(404, 'Môn học không tồn tại');

  const topics = course1Topics;
  const selected = topics.slice(0, Math.min(maxAxes, topics.length));
  const axes = selected.map(({ id, name, lessonId, li, ti }) => {
    const score = masteryScore(li, ti);
    const practiced = li < 2 || (li === 2 && ti === 0);
    const status = statusOf(score, practiced);
    return {
      topic_id: id,
      topic_name: name,
      lesson_id: lessonId,
      mastery_score: score,
      status,
      label_vi: labelViOf(status),
      is_practiced: practiced,
    };
  });

  return {
    course_id: 1,
    max_axes: maxAxes,
    total_topics: topics.length,
    truncated: topics.length > axes.length,
    axes,
    labels: axes.map((a) => a.topic_name),
    scores: axes.map((a) => a.mastery_score),
  };
}
