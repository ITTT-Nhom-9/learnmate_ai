// Chuyển lỗi trả về từ Backend (FastAPI) thành thông báo tiếng Việt cho giao diện.
//  - HTTPException  -> { detail: "chuỗi thông báo" }
//  - Pydantic (422) -> { detail: [{ loc: ["body", "email"], msg: "..." }, ...] }

const FIELD_ALIASES = { full_name: 'fullName' };

export function getErrorMessage(error, fallback = 'Đã có lỗi xảy ra, vui lòng thử lại sau') {
  if (!error) return fallback;
  if (!error.response) {
    return error.code === 'ECONNABORTED'
      ? 'Máy chủ phản hồi quá lâu, vui lòng thử lại'
      : 'Không thể kết nối tới máy chủ, vui lòng kiểm tra mạng';
  }
  const { status, data } = error.response;
  const detail = data?.detail;
  if (typeof detail === 'string' && detail) return detail;
  if (Array.isArray(detail) && detail.length > 0) return detail[0]?.msg || fallback;
  if (status === 429) return 'Bạn thao tác quá nhanh, vui lòng thử lại sau';
  if (status >= 500) return 'Máy chủ đang gặp sự cố, vui lòng thử lại sau';
  return fallback;
}

/** Tách lỗi theo từng trường (chỉ có ở lỗi 422) để hiển thị ngay dưới ô nhập liệu. */
export function getFieldErrors(error) {
  const detail = error?.response?.data?.detail;
  if (!Array.isArray(detail)) return {};
  const result = {};
  detail.forEach((item) => {
    const raw = Array.isArray(item?.loc) ? item.loc[item.loc.length - 1] : null;
    if (typeof raw !== 'string') return;
    const field = FIELD_ALIASES[raw] || raw;
    if (!result[field]) result[field] = item.msg;
  });
  return result;
}
