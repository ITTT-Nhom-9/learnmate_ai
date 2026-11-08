import axiosClient from './axiosClient';

// Đặt VITE_USE_MOCK=true để chạy giao diện bằng dữ liệu seed khi Backend chưa có API /courses (TK-06).
const USE_MOCK = import.meta.env.VITE_USE_MOCK === 'true';
const loadMock = () => import('../mocks/mockCourseApi.js'); // tách chunk riêng, không nằm trong bundle production nếu tắt mock

export const courseApi = {
  /** API-05 -> { courses: [{ id, code, title, progress_pct, is_enrolled, total_lessons }], total } */
  getCourses: ({ page = 1, limit = 50 } = {}) =>
    USE_MOCK ? loadMock().then((m) => m.getCourses()) : axiosClient.get('/courses', { params: { page, limit } }),

  /** API-06 -> { id, code, title, lessons: [{ id, title, order_index, topics: [{ id, name, mastery_score }] }] } */
  getCourseDetail: (courseId) =>
    USE_MOCK ? loadMock().then((m) => m.getCourseDetail(courseId)) : axiosClient.get(`/courses/${courseId}`),

  /** API-07 -> { enrollment_id, course_id, user_id, status, enrolled_at }. 409 nếu đã ghi danh. */
  enroll: (courseId) =>
    USE_MOCK ? loadMock().then((m) => m.enroll(courseId)) : axiosClient.post(`/courses/${courseId}/enroll`),

  /**
   * ĐỀ XUẤT (chưa có trong đặc tả API-01..18): nội dung lý thuyết của một bài học.
   * -> { id, title, order_index, topics: [...], contents: [{ id, content_type: 'MARKDOWN'|'VIDEO'|'PDF', body }] }
   */
  getLessonDetail: (courseId, lessonId) =>
    USE_MOCK
      ? loadMock().then((m) => m.getLessonDetail(courseId, lessonId))
      : axiosClient.get(`/courses/${courseId}/lessons/${lessonId}`),
};
