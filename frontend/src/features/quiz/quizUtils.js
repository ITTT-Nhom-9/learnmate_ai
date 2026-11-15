// Hàm thuần dùng chung cho SCR-05 (làm bài) và SCR-06 (xem kết quả). Không phụ thuộc React để dễ kiểm thử.

/** BR-?: mỗi câu được 3 phút -> bài 5 câu có đồng hồ 15:00 như thiết kế Figma. */
export const SECONDS_PER_QUESTION = 180;
export const WARNING_SECONDS = 60; // còn <= 60 giây: đồng hồ chuyển màu cam
export const CRITICAL_SECONDS = 30; // còn <= 30 giây: đồng hồ chuyển màu đỏ + nhấp nháy

export const DIFFICULTY_LABELS = { EASY: 'Dễ', MEDIUM: 'Trung bình', HARD: 'Khó' };

export const getTimeLimitSec = (totalQuestions) => Math.max(1, Number(totalQuestions) || 1) * SECONDS_PER_QUESTION;

/** Số giây còn lại (làm tròn lên, không âm). deadline và now là mili-giây (Date.now()). */
export function getRemainingSec(deadline, now = Date.now()) {
  return Math.max(0, Math.ceil((deadline - now) / 1000));
}

/** 905 -> "15:05". Từ 1 giờ trở lên -> "1:02:03". */
export function formatClock(totalSeconds) {
  const s = Math.max(0, Math.floor(Number(totalSeconds) || 0));
  const hours = Math.floor(s / 3600);
  const minutes = Math.floor((s % 3600) / 60);
  const seconds = s % 60;
  const mm = String(minutes).padStart(2, '0');
  const ss = String(seconds).padStart(2, '0');
  return hours ? `${hours}:${mm}:${ss}` : `${mm}:${ss}`;
}

/** 125 -> "2 phút 5 giây" (đọc cho người dùng / trình đọc màn hình). */
export function formatDurationText(totalSeconds) {
  const s = Math.max(0, Math.floor(Number(totalSeconds) || 0));
  const minutes = Math.floor(s / 60);
  const seconds = s % 60;
  if (minutes === 0) return `${seconds} giây`;
  return seconds === 0 ? `${minutes} phút` : `${minutes} phút ${seconds} giây`;
}

export function getTimerTone(remainingSec) {
  if (remainingSec <= CRITICAL_SECONDS) return 'critical';
  if (remainingSec <= WARNING_SECONDS) return 'warning';
  return 'normal';
}

export const optionLabelOf = (index) => String.fromCharCode(65 + index); // 0 -> A

/** Số câu đã trả lời (có chọn một phương án hợp lệ của chính câu đó). */
export function countAnswered(questions, answers) {
  return questions.filter((q) => answers[q.id] != null).length;
}

/** Body gửi lên POST /quiz/submit. Câu bỏ trống gửi selected_option_id = null (Backend tính là sai). */
export function buildSubmitPayload({ quiz, answers, durationSec }) {
  return {
    quiz_id: quiz.id,
    duration_sec: Math.max(0, Math.round(durationSec)),
    answers: quiz.questions.map((q) => ({ question_id: q.id, selected_option_id: answers[q.id] ?? null })),
  };
}

/**
 * Điểm của Backend theo thang 10 (BR-08). Phân hạng theo SDD: < 60% Yếu, 60-79% Khá, >= 80% Giỏi.
 * Chấp nhận cả điểm thang 100 phòng khi Backend đổi (giá trị > 10 được hiểu là thang 100).
 */
export function normalizeScore10(score) {
  const n = Number(score);
  if (!Number.isFinite(n)) return 0;
  return Math.min(10, Math.max(0, n > 10 ? n / 10 : n));
}

export function formatScore(score) {
  const n = normalizeScore10(score);
  return Number.isInteger(n) ? String(n) : n.toFixed(2).replace(/0$/, '');
}

export const RESULT_LEVELS = {
  MASTER: { label: 'Giỏi', tone: 'green', message: 'Bạn đã nắm vững chủ đề này. Hãy thử thách bản thân với bài khó hơn.' },
  FAIR: { label: 'Khá', tone: 'blue', message: 'Bạn nắm khá tốt kiến thức. Ôn lại các câu sai để đạt mức Giỏi.' },
  WEAK: { label: 'Yếu', tone: 'red', message: 'Bạn nên ôn lại lý thuyết và hỏi Gia sư AI trước khi làm lại bài.' },
};

export function getResultLevel(score) {
  const pct = normalizeScore10(score) * 10;
  if (pct >= 80) return RESULT_LEVELS.MASTER;
  if (pct >= 60) return RESULT_LEVELS.FAIR;
  return RESULT_LEVELS.WEAK;
}

/** Trạng thái của một phương án trong màn hình kết quả. */
export function getOptionReviewState(option, answer) {
  const isCorrect = option.id === answer.correct_option_id;
  const isSelected = option.id === answer.selected_option_id;
  if (isCorrect && isSelected) return 'correct-selected';
  if (isCorrect) return 'correct';
  if (isSelected) return 'wrong-selected';
  return 'neutral';
}
