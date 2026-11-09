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
