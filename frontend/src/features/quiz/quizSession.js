// Lưu phiên làm bài vào sessionStorage để F5 / lỡ đóng tab không mất đề, đáp án đã chọn và đồng hồ.
// Hạn chót (deadline) là mốc thời gian tuyệt đối nên đồng hồ vẫn chạy khi rời trang; quay lại sau khi hết giờ
// thì trang tự nộp bài ngay.
//
// Backend hiện chưa có API đọc lại kết quả theo attempt_id (chỉ POST /quiz/submit trả kết quả một lần),
// nên màn hình kết quả (SCR-06) lấy dữ liệu từ đây. Nếu sau này có GET /quiz/attempts/{id} thì thay hàm loadResult.

const SESSION_PREFIX = 'lm_quiz_session:';
const RESULT_PREFIX = 'lm_quiz_result:';

function read(key) {
  try {
    return JSON.parse(sessionStorage.getItem(key) || 'null');
  } catch {
    return null;
  }
}

function write(key, value) {
  try {
    sessionStorage.setItem(key, JSON.stringify(value));
  } catch {
    /* storage đầy hoặc bị chặn -> vẫn làm bài được, chỉ không khôi phục được khi tải lại trang */
  }
}

function remove(key) {
  try {
    sessionStorage.removeItem(key);
  } catch {
    /* bỏ qua */
  }
}

/** Phiên hợp lệ phải có đề với ít nhất 1 câu và mốc hạn chót là số. */
const isValidSession = (s) => Boolean(s?.quiz?.id && Array.isArray(s.quiz.questions) && s.quiz.questions.length > 0 && Number.isFinite(s.deadline));

export function loadSession(topicId) {
  const session = read(SESSION_PREFIX + topicId);
  return isValidSession(session) ? session : null;
}

export const saveSession = (topicId, session) => write(SESSION_PREFIX + topicId, session);
export const clearSession = (topicId) => remove(SESSION_PREFIX + topicId);

/** Lưu kết quả đã chấm kèm đề (nội dung câu hỏi/phương án) để SCR-06 hiển thị lại. */
export const saveResult = (attemptId, data) => write(RESULT_PREFIX + attemptId, data);

export function loadResult(attemptId) {
  const data = read(RESULT_PREFIX + attemptId);
  return data?.quiz?.questions && data?.result?.answers ? data : null;
}
