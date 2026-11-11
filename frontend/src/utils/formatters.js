/** Bỏ dấu tiếng Việt + chữ thường, dùng cho tìm kiếm không phân biệt dấu. */
export function normalizeText(value) {
  return (value || '')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/đ/g, 'd')
    .replace(/Đ/g, 'D')
    .toLowerCase()
    .trim();
}

/** Lấy 2 chữ cái đầu của tên để làm avatar (VD: "Trần Văn A" -> "TA"). */
export function getInitials(fullName) {
  const parts = (fullName || '').trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return '?';
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

/** Ước tính số phút đọc (~200 từ/phút), tối thiểu 1 phút. */
export function estimateReadMinutes(text) {
  const words = (text || '').trim().split(/\s+/).filter(Boolean).length;
  return Math.max(1, Math.round(words / 200));
}

export function formatPercent(value) {
  const n = Number(value);
  if (!Number.isFinite(n)) return '0%';
  return `${Math.round(Math.min(100, Math.max(0, n)))}%`;
}

// ---- Thời gian (dùng cho khung chat) ----

/**
 * Backend lưu thời gian UTC trong cột DATETIME không múi giờ nên JSON có dạng "2026-11-09T04:00:00" (không có "Z").
 * Nếu để nguyên, JavaScript hiểu là giờ máy và hiển thị lệch 7 tiếng ở Việt Nam -> chủ động thêm "Z".
 */
export function parseServerDate(value) {
  if (!value) return null;
  if (value instanceof Date) return value;
  const text = String(value).trim();
  const isDateOnly = /^\d{4}-\d{2}-\d{2}$/.test(text);
  const hasZone = /(?:Z|[+-]\d{2}:?\d{2})$/i.test(text);
  const date = new Date(isDateOnly || hasZone ? text : `${text}Z`);
  return Number.isNaN(date.getTime()) ? null : date;
}

export function formatTime(date) {
  if (!date) return '';
  return date.toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit', hour12: false });
}

export function isSameDay(a, b) {
  return Boolean(a && b) && a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate() === b.getDate();
}

/** "Hôm nay" / "Hôm qua" / "dd/MM/yyyy". */
export function formatDayLabel(date, now = new Date()) {
  if (!date) return '';
  if (isSameDay(date, now)) return 'Hôm nay';
  const yesterday = new Date(now);
  yesterday.setDate(now.getDate() - 1);
  if (isSameDay(date, yesterday)) return 'Hôm qua';
  return date.toLocaleDateString('vi-VN', { day: '2-digit', month: '2-digit', year: 'numeric' });
}
