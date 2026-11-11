// Giả lập API-08/API-09 để phát triển giao diện khi Backend chưa có API chat (TK-12).
import { TutorStreamError } from '../api/tutorErrors';

const DAILY_QUOTA = 50;
const sessions = new Map(); // lessonId -> { session_id, mode, hint_level, messages }
let usedToday = 0;
let nextMessageId = 1000;
let nextSessionId = 1;

const sleep = (ms, signal) =>
  new Promise((resolve, reject) => {
    const timer = setTimeout(resolve, ms);
    signal?.addEventListener('abort', () => {
      clearTimeout(timer);
      reject(new DOMException('Aborted', 'AbortError'));
    });
  });

function httpError(status, detail) {
  return Object.assign(new Error(detail), { response: { status, data: { detail } } });
}

export async function getHistory(lessonId) {
  await sleep(250);
  const session = sessions.get(Number(lessonId));
  if (!session) throw httpError(404, 'Chưa có phiên chat cho bài học này');
  return { ...session, messages: session.messages.map((m) => ({ ...m })) };
}

const EXPLAIN_ANSWER = (question) => `Bạn hỏi: “${question}”. Mình trả lời theo nội dung bài học nhé.

Mấu chốt nằm ở **chiều cao $h$** của cây. Mỗi lần so sánh, ta chỉ đi tiếp vào một trong hai cây con.

**1. Cây cân bằng:** loại bỏ khoảng một nửa số nút mỗi bước.

$$\\frac{n}{2^h} \\approx 1 \\;\\Rightarrow\\; h \\approx \\log_2 n \\;\\Rightarrow\\; T(n) = O(\\log n)$$

\`\`\`python
def search(node, key):
    if node is None or node.key == key:
        return node
    if key < node.key:
        return search(node.left, key)   # chỉ xét cây con trái
    return search(node.right, key)
\`\`\`

**2. Cây suy biến:** nếu chèn các khóa $1, 2, 3, \\dots, n$ theo thứ tự tăng dần, cây giống một danh sách liên kết. Khi đó $h = n - 1$ và tìm kiếm mất $O(n)$.

| Trường hợp | Chiều cao $h$ | Chi phí tìm kiếm |
|---|---|---|
| Cây cân bằng | $\\log_2 n$ | $O(\\log n)$ |
| Cây suy biến | $n - 1$ | $O(n)$ |

Bạn thử dự đoán: cây có 15 nút cân bằng cần tối đa mấy lần so sánh?`;

// 5 giai đoạn Socratic (TK-14): Khám phá -> Thách thức -> Gợi ý -> Đúc kết -> Đánh giá. Tuyệt đối không nói đáp án ở các bước đầu (BR-02).
const SOCRATIC_STEPS = [
  'Câu hỏi hay đấy! Trước khi đi vào chi tiết, bạn thử nói xem: khi tìm một khóa trong BST, ở mỗi nút ta cần quyết định điều gì?',
  'Chính xác, ta chọn đi sang trái hoặc phải. Vậy nếu cây có $n$ nút nhưng **chỉ có nhánh phải**, bạn nghĩ ta phải so sánh tối đa bao nhiêu lần? Vì sao?',
  'Gợi ý nhỏ: hãy so sánh hai cây cùng có 7 nút, một cây "đầy đặn" ba tầng và một cây chỉ kéo dài thành một đường. Chiều cao $h$ của chúng khác nhau thế nào?',
  'Bạn đã đi đúng hướng. Tóm lại: chi phí tìm kiếm tỉ lệ với chiều cao $h$, nên cây cân bằng cho $O(\\log n)$ còn cây suy biến cho $O(n)$.',
  'Để kiểm tra lại: nếu chèn $1, 2, 3, 4, 5$ theo đúng thứ tự vào BST rỗng, chiều cao cây là bao nhiêu và việc tìm khóa $5$ tốn mấy lần so sánh?',
];

function* chunk(text) {
  const parts = text.match(/\s*\S+\s*/g) || [text];
  for (let i = 0; i < parts.length; i += 2) yield parts.slice(i, i + 2).join('');
}

export async function* streamChat({ lessonId, message, mode }, signal) {
  await sleep(350, signal); // độ trễ trước token đầu tiên
  if (usedToday >= DAILY_QUOTA) {
    throw new TutorStreamError(`Bạn đã dùng hết ${DAILY_QUOTA} lượt hỏi trong hôm nay. Hãy quay lại vào ngày mai.`, { status: 429 });
  }

  const key = Number(lessonId);
  if (!sessions.has(key)) sessions.set(key, { session_id: nextSessionId++, mode, hint_level: 0, messages: [] });
  const session = sessions.get(key);
  session.mode = mode;

  let hintLevel = session.hint_level;
  let isConcluded = false;
  let answer;
  if (mode === 'SOCRATIC') {
    hintLevel = Math.min(5, hintLevel + 1);
    isConcluded = hintLevel >= 5;
    answer = SOCRATIC_STEPS[hintLevel - 1];
  } else {
    answer = EXPLAIN_ANSWER(message.length > 80 ? `${message.slice(0, 80)}…` : message);
  }

  let produced = '';
  for (const piece of chunk(answer)) {
    await sleep(22, signal);
    produced += piece;
    yield { type: 'token', token: piece, hintLevel: mode === 'SOCRATIC' ? hintLevel : null, isConcluded: mode === 'SOCRATIC' ? isConcluded : null };
  }

  usedToday += 1;
  session.hint_level = hintLevel;
  const now = new Date().toISOString().replace('Z', ''); // giống Backend: UTC không có hậu tố Z
  session.messages.push({ id: nextMessageId++, role: 'USER', content: message, created_at: now });
  const messageId = nextMessageId++;
  session.messages.push({ id: messageId, role: 'ASSISTANT', content: produced, created_at: now });
  yield { type: 'done', messageId, tokensUsed: Math.ceil(produced.length / 4), quotaRemaining: DAILY_QUOTA - usedToday };
}
