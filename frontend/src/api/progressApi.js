import axiosClient from './axiosClient';

// VITE_USE_MOCK=true: chạy bằng dữ liệu giả lập khi Backend chưa có API /progress (TK-21).
const USE_MOCK = import.meta.env.VITE_USE_MOCK === 'true';
const loadMock = () => import('../mocks/mockProgressApi.js');

export const progressApi = {
  /**
   * GET /progress/summary?course_id= (TK-21, API tiến độ)
   * -> { course_id, course_code, course_title, overall_progress_pct, stats, weak_topics, recent_attempts }
   */
  getSummary: (courseId) =>
    USE_MOCK
      ? loadMock().then((m) => m.getProgressSummary(courseId))
      : axiosClient.get('/progress/summary', { params: { course_id: courseId } }),

  /**
   * GET /progress/radar?course_id=&max_axes=6 (TK-21, Radar năng lực)
   * -> { course_id, max_axes, total_topics, truncated, axes, labels, scores }
   */
  getRadar: (courseId, maxAxes = 6) =>
    USE_MOCK
      ? loadMock().then((m) => m.getProgressRadar(courseId, maxAxes))
      : axiosClient.get('/progress/radar', { params: { course_id: courseId, max_axes: maxAxes } }),
};
