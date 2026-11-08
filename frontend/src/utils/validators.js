// Quy tắc kiểm tra form Đăng nhập / Đăng ký (SCR-01).
// Khớp với ràng buộc của Backend (schemas/auth.py): email <= 255, mật khẩu >= 8 ký tự
// và <= 72 byte (giới hạn BCrypt), họ tên <= 150 ký tự.

export const PASSWORD_MIN_LENGTH = 8;
export const PASSWORD_MAX_BYTES = 72;
export const EMAIL_MAX_LENGTH = 255;
export const FULL_NAME_MAX_LENGTH = 150;

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;

export function validateEmail(value) {
  const email = (value || '').trim();
  if (!email) return 'Vui lòng nhập email';
  if (email.length > EMAIL_MAX_LENGTH) return `Email không được vượt quá ${EMAIL_MAX_LENGTH} ký tự`;
  if (!EMAIL_PATTERN.test(email)) return 'Email không đúng định dạng (ví dụ: sv@univ.edu.vn)';
  return '';
}

export function validatePassword(value) {
  const password = value || '';
  if (!password) return 'Vui lòng nhập mật khẩu';
  if (password.length < PASSWORD_MIN_LENGTH) return `Mật khẩu phải có ít nhất ${PASSWORD_MIN_LENGTH} ký tự`;
  if (new TextEncoder().encode(password).length > PASSWORD_MAX_BYTES) {
    return `Mật khẩu không được vượt quá ${PASSWORD_MAX_BYTES} byte`;
  }
  return '';
}

export function validateFullName(value) {
  const name = (value || '').trim();
  if (!name) return 'Vui lòng nhập họ và tên';
  if (name.length > FULL_NAME_MAX_LENGTH) return `Họ và tên không được vượt quá ${FULL_NAME_MAX_LENGTH} ký tự`;
  return '';
}

export function validateConfirmPassword(password, confirm) {
  if (!confirm) return 'Vui lòng nhập lại mật khẩu';
  if (password !== confirm) return 'Mật khẩu nhập lại không khớp';
  return '';
}

function compact(errors) {
  return Object.fromEntries(Object.entries(errors).filter(([, message]) => message));
}

/** Đăng nhập: chỉ cần email đúng định dạng và mật khẩu không rỗng (không lộ quy tắc mật khẩu). */
export function validateLoginForm({ email, password }) {
  return compact({
    email: validateEmail(email),
    password: password ? '' : 'Vui lòng nhập mật khẩu',
  });
}

export function validateRegisterForm({ fullName, email, password, confirmPassword }) {
  return compact({
    fullName: validateFullName(fullName),
    email: validateEmail(email),
    password: validatePassword(password),
    confirmPassword: validateConfirmPassword(password, confirmPassword),
  });
}
