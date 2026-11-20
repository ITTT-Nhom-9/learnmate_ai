// Đề trắc nghiệm giả lập cho SCR-05/06 (VITE_USE_MOCK=true). Mô phỏng đúng hợp đồng của Backend:
// khi sinh đề KHÔNG trả đáp án đúng; chỉ sau khi nộp mới trả đáp án + lời giải.
const delay = (ms = 400) => new Promise((resolve) => setTimeout(resolve, ms));

const BANK = [
  {
    content: 'Cây B-Tree bậc **m** có đặc điểm nào sau đây?',
    options: ['Mỗi nút có tối đa m con', 'Mọi nút đều có đúng 2 con', 'Chiều cao luôn bằng n', 'Chỉ lưu khóa ở nút gốc'],
    correct: 0,
    explanation: 'B-Tree bậc m cho phép mỗi nút có **tối đa m con** và tối đa m − 1 khóa, nhờ vậy cây thấp và ít lần đọc đĩa.',
  },
  {
    content: 'Độ phức tạp thời gian tìm kiếm trong cây AVL (trường hợp xấu nhất) là bao nhiêu?',
    options: ['$O(1)$', '$O(\\log n)$', '$O(n)$', '$O(n \\log n)$'],
    correct: 1,
    explanation: 'AVL luôn cân bằng nên chiều cao $h = O(\\log n)$, mỗi bước tìm kiếm loại bỏ một nửa cây con.',
  },
  {
    content: 'Khóa ngoại (FOREIGN KEY) dùng để làm gì?',
    options: ['Tăng tốc truy vấn SELECT', 'Mã hóa dữ liệu trong bảng', 'Đảm bảo toàn vẹn tham chiếu giữa hai bảng', 'Sao lưu dữ liệu tự động'],
    correct: 2,
    explanation: 'Khóa ngoại ràng buộc giá trị cột phải tồn tại ở khóa chính của bảng cha, giữ **toàn vẹn tham chiếu**.',
  },
  {
    content: 'Đoạn mã sau thực hiện thao tác gì?\n\n```python\nstack = []\nstack.append(1)\nstack.pop()\n```',
    options: ['Thêm rồi lấy phần tử theo kiểu FIFO', 'Thêm rồi lấy phần tử theo kiểu LIFO', 'Sắp xếp danh sách', 'Xóa toàn bộ danh sách'],
    correct: 1,
    explanation: '`append` đẩy vào cuối và `pop` lấy từ cuối ra: đây là ngăn xếp **LIFO** (vào sau ra trước).',
  },
  {
    content: 'Dạng chuẩn 2NF yêu cầu điều gì ngoài 1NF?',
    options: ['Không có thuộc tính đa trị', 'Không có phụ thuộc bắc cầu', 'Mọi thuộc tính không khóa phụ thuộc đầy đủ vào khóa chính', 'Mọi bảng đều có đúng một khóa'],
    correct: 2,
    explanation: '2NF loại bỏ **phụ thuộc hàm riêng phần**: thuộc tính không khóa phải phụ thuộc vào toàn bộ khóa chính.',
  },
];

// Đáp án đúng chỉ nằm ở "server" giả lập này, không bao giờ nằm trong dữ liệu gửi ra giao diện khi đang làm.
const keyByQuiz = new Map();
let nextQuizId = 9000;
let nextAttemptId = 7000;

export async function generate({ topicId, numQuestions = 5, difficulty = 'MEDIUM' }) {
  await delay(700);
  const quizId = nextQuizId++;
  const picked = Array.from({ length: Math.min(numQuestions, 10) }, (_, i) => BANK[i % BANK.length]);
  const key = {};
  const questions = picked.map((item, qi) => {
    const id = quizId * 100 + qi;
    const options = item.options.map((content, oi) => ({ id: id * 10 + oi, opt_label: 'ABCD'[oi], content }));
    key[id] = { correctOptionId: options[item.correct].id, explanation: item.explanation, options };
    return { id, content: item.content, options };
  });
  keyByQuiz.set(quizId, key);
  return { id: quizId, topic_id: Number(topicId) || 1, title: 'Đánh giá kiến thức: Cấu trúc dữ liệu và CSDL', difficulty, total_questions: questions.length, questions };
}

export async function submit({ quiz_id: quizId, duration_sec: durationSec, answers }) {
  await delay(500);
  const key = keyByQuiz.get(quizId);
  if (!key) throw Object.assign(new Error('not found'), { response: { status: 404, data: { detail: 'Bài trắc nghiệm không tồn tại' } } });
  const chosen = Object.fromEntries(answers.map((a) => [a.question_id, a.selected_option_id]));
  const labelOf = (qid, optId) => key[qid].options.find((o) => o.id === optId)?.opt_label ?? null;
  const results = Object.keys(key).map((qidText) => {
    const qid = Number(qidText);
    const selected = chosen[qid] ?? null;
    return {
      question_id: qid,
      selected_option_id: selected,
      selected_label: selected == null ? null : labelOf(qid, selected),
      correct_option_id: key[qid].correctOptionId,
      correct_label: labelOf(qid, key[qid].correctOptionId),
      is_correct: selected === key[qid].correctOptionId,
      explanation: key[qid].explanation,
    };
  });
  const correct = results.filter((r) => r.is_correct).length;
  const unanswered = results.filter((r) => r.selected_option_id == null).length;
  const total = results.length;
  return {
    attempt_id: nextAttemptId++,
    quiz_id: quizId,
    score: Math.round((correct / total) * 1000) / 100,
    total_questions: total,
    correct_count: correct,
    wrong_count: total - correct,
    unanswered_count: unanswered,
    duration_sec: durationSec,
    status: 'SUBMITTED',
    answers: results,
  };
}

export async function getAttempt(attemptId) {
  await delay(300);
  const quizId = 501;
  const picked = BANK.slice(0, 5);
  const questions = picked.map((item, qi) => {
    const id = quizId * 100 + qi;
    const options = item.options.map((content, oi) => ({ id: id * 10 + oi, opt_label: 'ABCD'[oi], content }));
    return { id, content: item.content, options, correctOptionId: options[item.correct].id, explanation: item.explanation };
  });
  const results = questions.map((q, idx) => ({
    question_id: q.id,
    selected_option_id: idx % 2 === 0 ? q.correctOptionId : q.options[(q.correctOptionId % 4)].id,
    selected_label: idx % 2 === 0 ? 'A' : 'B',
    correct_option_id: q.correctOptionId,
    correct_label: 'A',
    is_correct: idx % 2 === 0,
    explanation: q.explanation,
  }));
  const correct = results.filter((r) => r.is_correct).length;
  return {
    attempt_id: Number(attemptId),
    quiz_id: quizId,
    score: Math.round((correct / questions.length) * 10),
    total_questions: questions.length,
    correct_count: correct,
    wrong_count: questions.length - correct,
    unanswered_count: 0,
    duration_sec: 420,
    status: 'SUBMITTED',
    answers: results,
    quiz: {
      id: quizId,
      topic_id: 1,
      title: 'Trắc nghiệm: DBMS & ACID',
      difficulty: 'MEDIUM',
      total_questions: questions.length,
      questions: questions.map((q) => ({ id: q.id, content: q.content, options: q.options })),
    },
    topic_id: 1,
    lesson_id: 1,
  };
}
