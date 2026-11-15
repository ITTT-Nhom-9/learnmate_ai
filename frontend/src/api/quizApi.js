import axiosClient from './axiosClient';

// VITE_USE_MOCK=true: chạy bằng đề giả lập khi Backend/AI Service chưa sẵn sàng.
const USE_MOCK = import.meta.env.VITE_USE_MOCK === 'true';
const loadMock = () => import('../mocks/mockQuizApi.js');

// Sinh đề gọi AI nên lâu hơn các API thường (axiosClient mặc định 30s).
const GENERATE_TIMEOUT_MS = 90000;

export const quizApi = {
  /**
   * POST /quizzes/generate (TK-15, API-10) -> { id, topic_id, title, difficulty, total_questions,
   *   questions: [{ id, content, options: [{ id, opt_label, content }] }] }
   * Backend KHÔNG trả is_correct / explanation khi đang làm bài (BR-04).
   */
  generate: ({ topicId, lessonId, numQuestions = 5, difficulty = 'MEDIUM' }) => {
    if (USE_MOCK) return loadMock().then((m) => m.generate({ topicId, numQuestions, difficulty }));
    const body = { num_questions: numQuestions, difficulty };
    if (topicId != null) body.topic_id = Number(topicId);
    if (lessonId != null) body.lesson_id = Number(lessonId);
    return axiosClient.post('/quizzes/generate', body, { timeout: GENERATE_TIMEOUT_MS });
  },

  /**
   * POST /quiz/submit (TK-16) body { quiz_id, duration_sec, answers: [{ question_id, selected_option_id|null }] }
   * -> { attempt_id, quiz_id, score (0-10), total_questions, correct_count, wrong_count, unanswered_count,
   *      duration_sec, status, answers: [{ question_id, selected_option_id, selected_label, correct_option_id,
   *      correct_label, is_correct, explanation }] }
   */
  submit: (payload) => (USE_MOCK ? loadMock().then((m) => m.submit(payload)) : axiosClient.post('/quiz/submit', payload)),
};
