import axiosClient from './axiosClient';

// Đặt VITE_USE_MOCK=true để chạy giao diện bằng dữ liệu seed khi Backend chưa có API /courses (TK-06).
const USE_MOCK = import.meta.env.VITE_USE_MOCK === 'true';
const loadMock = () => import('../mocks/mockCourseApi.js'); // tách chunk riêng, không nằm trong bundle production nếu tắt mock

export const courseApi = {
  /** API-05 -> { courses: [{ id, code, title, progress_pct, is_enrolled, total_lessons }], total } */
  getCourses: ({ page = 1, limit = 50, include_inactive = false } = {}) =>
    USE_MOCK
      ? loadMock().then((m) => m.getCourses())
      : axiosClient.get('/courses', { params: { page, limit, include_inactive } }),

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

  // ===========================================================================
  // QUẢN TRỊ VIÊN: CRUD KHÓA HỌC, BÀI HỌC, CHỦ ĐỀ VÀ NỘI DUNG (TK-26 / TK-35)
  // ===========================================================================

  /** POST /courses: Thêm môn học mới */
  createCourse: ({ code, title, description, status = 'ACTIVE' }) =>
    axiosClient.post('/courses', { code, title, description, status }),

  /** PUT /courses/{id}: Cập nhật thông tin môn học */
  updateCourse: (courseId, { code, title, description, status }) =>
    axiosClient.put(`/courses/${courseId}`, { code, title, description, status }),

  /** DELETE /courses/{id}: Xóa môn học hoặc chuyển sang INACTIVE nếu đã có ghi danh */
  deleteCourse: (courseId) =>
    axiosClient.delete(`/courses/${courseId}`),

  /** POST /courses/{id}/lessons: Thêm bài học mới */
  createLesson: (courseId, { title, orderIndex = 1 }) =>
    axiosClient.post(`/courses/${courseId}/lessons`, { title, order_index: orderIndex }),

  /** PUT /courses/{id}/lessons/{lesson_id}: Sửa bài học */
  updateLesson: (courseId, lessonId, { title, orderIndex }) =>
    axiosClient.put(`/courses/${courseId}/lessons/${lessonId}`, { title, order_index: orderIndex }),

  /** DELETE /courses/{id}/lessons/{lesson_id}: Xóa bài học */
  deleteLesson: (courseId, lessonId) =>
    axiosClient.delete(`/courses/${courseId}/lessons/${lessonId}`),

  /** POST /courses/{id}/lessons/{lesson_id}/topics: Thêm chủ đề mới */
  createTopic: (courseId, lessonId, { name, description }) =>
    axiosClient.post(`/courses/${courseId}/lessons/${lessonId}/topics`, { name, description }),

  /** PUT /courses/{id}/topics/{topic_id}: Sửa chủ đề */
  updateTopic: (courseId, topicId, { name, description }) =>
    axiosClient.put(`/courses/${courseId}/topics/${topicId}`, { name, description }),

  /** DELETE /courses/{id}/topics/{topic_id}: Xóa chủ đề */
  deleteTopic: (courseId, topicId) =>
    axiosClient.delete(`/courses/${courseId}/topics/${topicId}`),

  /** POST /courses/{id}/lessons/{lesson_id}/contents: Soạn / cập nhật nội dung lý thuyết Markdown */
  saveLessonContent: (courseId, lessonId, { body, contentType = 'MARKDOWN', contentId }) =>
    axiosClient.post(
      `/courses/${courseId}/lessons/${lessonId}/contents`,
      { body, content_type: contentType },
      { params: contentId ? { content_id: contentId } : {} }
    ),
};
