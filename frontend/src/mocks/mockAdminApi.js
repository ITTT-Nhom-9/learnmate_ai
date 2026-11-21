// Dữ liệu mock cho SCR-08: Quản trị viên (TK-26). Mô phỏng đúng hợp đồng API của Backend (TK-23):
//  /admin/users, /admin/prompts, /admin/logs, /admin/logs/tokens.
// Dữ liệu nằm trong bộ nhớ: thao tác khóa / sửa prompt có hiệu lực đến khi tải lại trang.
import { normalizeText } from '../utils/formatters';

const delay = (ms = 300) => new Promise((resolve) => setTimeout(resolve, ms));

function httpError(status, detail) {
  return Object.assign(new Error(detail), { response: { status, data: { detail } } });
}

// Bộ sinh số giả ngẫu nhiên cố định để mỗi lần mở trang cho cùng một bộ dữ liệu
let seedValue = 20261121;
const rand = () => {
  seedValue = (seedValue * 1664525 + 1013904223) % 4294967296;
  return seedValue / 4294967296;
};
const between = (min, max) => Math.floor(min + rand() * (max - min + 1));
const isoAgo = (days, hours = 0) => new Date(Date.now() - days * 86400000 - hours * 3600000).toISOString();

// ---------------------------------------------------------------- Người dùng
const NAMES = [
  'Nguyễn Minh Anh', 'Trần Quốc Bảo', 'Lê Thu Hà', 'Phạm Gia Huy', 'Võ Ngọc Lan', 'Đặng Hoàng Nam', 'Bùi Khánh Linh',
  'Hoàng Đức Thịnh', 'Phan Thảo Vy', 'Đỗ Anh Tuấn', 'Ngô Phương Thảo', 'Dương Quang Vinh', 'Lý Mai Chi', 'Trương Tấn Phát',
  'Huỳnh Bảo Ngọc', 'Mai Thanh Sơn', 'Châu Diệp Anh', 'Tô Hữu Nghĩa', 'Lâm Kim Ngân', 'Vũ Đình Khôi', 'Cao Thùy Dương',
];

const users = [
  { id: 1, email: 'admin@learnmate.ai', full_name: 'Quản trị viên LearnMate', role: 'ADMIN', status: 'ACTIVE', created_at: isoAgo(60) },
  ...NAMES.map((name, i) => ({
    id: i + 2,
    email: `${normalizeText(name).replace(/\s+/g, '.')}${i + 1}@student.univ.edu.vn`,
    full_name: name,
    role: 'STUDENT',
    status: i % 7 === 4 ? 'LOCKED' : 'ACTIVE',
    created_at: isoAgo(50 - i * 2),
  })),
];

export async function getUsers({ page = 1, pageSize = 10, search, role, status }) {
  await delay();
  const q = normalizeText(search);
  const rows = users.filter(
    (u) =>
      (!q || normalizeText(u.full_name).includes(q) || u.email.includes(q)) &&
      (!role || u.role === role) &&
      (!status || u.status === status)
  );
  return {
    items: rows.slice((page - 1) * pageSize, page * pageSize).map((u) => ({ ...u })),
    total: rows.length,
    page,
    page_size: pageSize,
    total_pages: Math.max(1, Math.ceil(rows.length / pageSize)),
  };
}

export async function updateUserStatus(userId, { status }) {
  await delay();
  const user = users.find((u) => u.id === Number(userId));
  if (!user) throw httpError(404, 'Người dùng không tồn tại');
  if (status === 'LOCKED' && user.role === 'ADMIN' && users.filter((u) => u.role === 'ADMIN' && u.status === 'ACTIVE').length <= 1) {
    throw httpError(403, 'Không thể khóa Quản trị viên đang hoạt động duy nhất của hệ thống');
  }
  user.status = status;
  return { ...user };
}

// ---------------------------------------------------------------- Prompt Templates
const prompts = [
  {
    id: 1, code: 'TUTOR_EXPLAIN', version: 1, is_active: false, created_at: isoAgo(30),
    content: 'Bạn là gia sư CNTT. Hãy giải thích chủ đề "{topic}" cho sinh viên.\n\nNgữ cảnh bài học:\n{context}',
  },
  {
    id: 2, code: 'TUTOR_EXPLAIN', version: 2, is_active: true, created_at: isoAgo(12),
    content: 'Bạn là gia sư CNTT kiên nhẫn. Giải thích chủ đề "{topic}" rõ ràng, từng bước, có ví dụ minh họa.\n\nNgữ cảnh bài học:\n{context}\n\nChỉ dùng kiến thức trong ngữ cảnh; nếu thiếu thông tin, hãy nói rõ thay vì đoán.',
  },
  {
    id: 3, code: 'TUTOR_SOCRATIC', version: 1, is_active: true, created_at: isoAgo(25),
    content: 'Bạn là gia sư theo phương pháp Socratic. TUYỆT ĐỐI không đưa đáp án trực tiếp về "{topic}". Mỗi lượt chỉ đặt MỘT câu hỏi gợi mở.\n\nNgữ cảnh:\n{context}',
  },
  {
    id: 4, code: 'QUIZ_GEN', version: 1, is_active: true, created_at: isoAgo(25),
    content: 'Sinh {total_questions} câu trắc nghiệm về "{topic}", mỗi câu đúng 4 phương án A-D, 1 đáp án đúng, kèm giải thích ngắn. Chỉ trả về JSON hợp lệ.\n\nNội dung bài học:\n{context}',
  },
  {
    id: 5, code: 'RAG', version: 1, is_active: true, created_at: isoAgo(18),
    content: 'Chỉ trả lời dựa trên các đoạn tài liệu sau và luôn ghi rõ số trang trích dẫn. Nếu câu hỏi nằm ngoài tài liệu, hãy từ chối lịch sự.\n\n{context}',
  },
];
let nextPromptId = 6;

export async function getPrompts({ code } = {}) {
  await delay();
  return prompts.filter((p) => !code || p.code === code).map((p) => ({ ...p }));
}

const activateOnly = (target) => prompts.forEach((p) => p.code === target.code && p !== target && (p.is_active = false));

export async function createPrompt({ code, content, isActive }) {
  await delay();
  if (!content?.trim()) throw httpError(400, 'Nội dung prompt không được để trống');
  const version = Math.max(0, ...prompts.filter((p) => p.code === code).map((p) => p.version)) + 1;
  const created = { id: nextPromptId++, code, version, content: content.trim(), is_active: Boolean(isActive), created_at: new Date().toISOString() };
  prompts.push(created);
  if (created.is_active) activateOnly(created);
  return { ...created };
}

export async function updatePrompt(promptId, { content, isActive }) {
  await delay();
  const prompt = prompts.find((p) => p.id === Number(promptId));
  if (!prompt) throw httpError(404, `Không tìm thấy mẫu prompt có ID ${promptId}`);
  if (content !== undefined) {
    if (!content.trim()) throw httpError(400, 'Nội dung prompt không được để trống');
    prompt.content = content.trim();
  }
  if (isActive !== undefined) {
    prompt.is_active = isActive;
    if (isActive) activateOnly(prompt);
  }
  return { ...prompt };
}

// ---------------------------------------------------------------- Nhật ký gọi AI & thống kê Token
const PRICING = {
  gemini: { prompt_per_1m: 0.1, completion_per_1m: 0.4 },
  openai: { prompt_per_1m: 2.5, completion_per_1m: 10 },
};
const EXCHANGE_RATE_VND = 25400;
const FEATURES = ['TUTOR', 'TUTOR', 'TUTOR', 'SOCRATIC', 'SOCRATIC', 'QUIZ_GEN', 'QUIZ_GEN', 'RAG'];

const logs = Array.from({ length: 150 }, (_, i) => {
  const feature = FEATURES[between(0, FEATURES.length - 1)];
  const provider = feature === 'RAG' && rand() < 0.5 ? 'openai' : 'gemini';
  const student = users[between(1, users.length - 1)];
  const tokens_prompt = between(300, feature === 'QUIZ_GEN' ? 3000 : 1800);
  const tokens_completion = between(80, feature === 'QUIZ_GEN' ? 1400 : 700);
  const rate = PRICING[provider];
  const usd = (tokens_prompt * rate.prompt_per_1m + tokens_completion * rate.completion_per_1m) / 1e6;
  return {
    id: i + 1,
    user_id: student.id,
    user_email: student.email,
    user_full_name: student.full_name,
    feature,
    provider,
    tokens_prompt,
    tokens_completion,
    total_tokens: tokens_prompt + tokens_completion,
    latency_ms: between(600, 3800),
    estimated_cost_usd: usd,
    estimated_cost_vnd: usd * EXCHANGE_RATE_VND,
    created_at: isoAgo(between(0, 35), between(0, 23)), // trải đều 35 ngày gần nhất
  };
}).sort((a, b) => b.created_at.localeCompare(a.created_at));

function filterLogs({ feature, provider, startDate, endDate }) {
  const from = startDate ? new Date(startDate).getTime() : -Infinity;
  const to = endDate ? new Date(endDate).getTime() : Infinity;
  return logs.filter((l) => {
    const t = new Date(l.created_at).getTime();
    return (!feature || l.feature === feature) && (!provider || l.provider === provider) && t >= from && t <= to;
  });
}

export async function getLogs({ page = 1, pageSize = 10, feature, provider, startDate, endDate }) {
  await delay();
  const rows = filterLogs({ feature, provider, startDate, endDate });
  return {
    items: rows.slice((page - 1) * pageSize, page * pageSize),
    total: rows.length,
    page,
    page_size: pageSize,
    total_pages: Math.max(1, Math.ceil(rows.length / pageSize)),
  };
}

function groupBy(rows, keyOf) {
  const map = new Map();
  rows.forEach((l) => {
    const key = keyOf(l);
    const g = map.get(key) || { key, request_count: 0, tokens_prompt: 0, tokens_completion: 0, total_tokens: 0, estimated_cost_usd: 0, estimated_cost_vnd: 0, latency: 0 };
    g.request_count += 1;
    g.tokens_prompt += l.tokens_prompt;
    g.tokens_completion += l.tokens_completion;
    g.total_tokens += l.total_tokens;
    g.estimated_cost_usd += l.estimated_cost_usd;
    g.estimated_cost_vnd += l.estimated_cost_vnd;
    g.latency += l.latency_ms;
    map.set(key, g);
  });
  return [...map.values()].map(({ latency, ...g }) => ({ ...g, avg_latency_ms: latency / g.request_count }));
}

export async function getTokenStats({ startDate, endDate } = {}) {
  await delay();
  const rows = filterLogs({ startDate, endDate });
  const sum = (field) => rows.reduce((s, l) => s + l[field], 0);
  return {
    summary: {
      total_requests: rows.length,
      total_tokens_prompt: sum('tokens_prompt'),
      total_tokens_completion: sum('tokens_completion'),
      total_tokens: sum('total_tokens'),
      estimated_cost_usd: sum('estimated_cost_usd'),
      estimated_cost_vnd: sum('estimated_cost_vnd'),
      avg_latency_ms: rows.length ? sum('latency_ms') / rows.length : 0,
    },
    by_feature: groupBy(rows, (l) => l.feature).sort((a, b) => b.total_tokens - a.total_tokens),
    by_provider: groupBy(rows, (l) => l.provider).sort((a, b) => b.total_tokens - a.total_tokens),
    by_date: groupBy(rows, (l) => l.created_at.slice(0, 10)).sort((a, b) => a.key.localeCompare(b.key)),
    pricing_rates: PRICING,
    exchange_rate_vnd: EXCHANGE_RATE_VND,
  };
}
