import { formatTime, parseServerDate } from '../../utils/formatters';

export const FEATURE_LABELS = {
  TUTOR: 'Gia sư AI',
  SOCRATIC: 'Socratic',
  QUIZ_GEN: 'Sinh Quiz',
  RAG: 'Hỏi đáp PDF',
};

export const PROMPT_CODES = {
  TUTOR_EXPLAIN: 'Gia sư AI · Giải thích',
  TUTOR_SOCRATIC: 'Gia sư AI · Socratic',
  QUIZ_GEN: 'Sinh Quiz',
  RAG: 'Hỏi đáp PDF (RAG)',
};

export function formatDate(value) {
  const date = parseServerDate(value);
  return date ? date.toLocaleDateString('vi-VN', { day: '2-digit', month: '2-digit', year: 'numeric' }) : '—';
}

export function formatDateTime(value) {
  const date = parseServerDate(value);
  return date ? `${formatTime(date)} ${formatDate(date)}` : '—';
}

export const formatNumber = (n) => Number(n || 0).toLocaleString('vi-VN');

/** Chi phí AI thường rất nhỏ (< 1 cent/lượt) nên hiển thị 4 chữ số thập phân khi dưới 1 USD. */
export function formatUsd(n) {
  const value = Number(n) || 0;
  return `$${value.toLocaleString('en-US', { minimumFractionDigits: value >= 1 ? 2 : 4, maximumFractionDigits: value >= 1 ? 2 : 4 })}`;
}

export const formatVnd = (n) => `${Math.round(Number(n) || 0).toLocaleString('vi-VN')} ₫`;

export function formatBytes(bytes) {
  const n = Number(bytes) || 0;
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / (1024 * 1024)).toFixed(1)} MB`;
}

/** Date -> "YYYY-MM-DD" theo giờ máy (dùng cho <input type="date">). */
export function toInputDate(date) {
  const pad = (v) => String(v).padStart(2, '0');
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
}

export function daysAgo(days) {
  const d = new Date();
  d.setDate(d.getDate() - days);
  return toInputDate(d);
}
