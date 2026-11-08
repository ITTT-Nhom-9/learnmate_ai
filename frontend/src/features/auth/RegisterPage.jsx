import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import AuthLayout from './AuthLayout';
import TextField from '../../components/common/TextField';
import Button from '../../components/common/Button';
import AlertBox from '../../components/common/AlertBox';
import { useAuth } from '../../hooks/useAuth';
import {
  PASSWORD_MIN_LENGTH,
  validateConfirmPassword,
  validateEmail,
  validateFullName,
  validatePassword,
  validateRegisterForm,
} from '../../utils/validators';
import { getErrorMessage, getFieldErrors } from '../../utils/apiError';

const FIELD_VALIDATORS = {
  fullName: (f) => validateFullName(f.fullName),
  email: (f) => validateEmail(f.email),
  password: (f) => validatePassword(f.password),
  confirmPassword: (f) => validateConfirmPassword(f.password, f.confirmPassword),
};

export default function RegisterPage() {
  const { register, login } = useAuth();
  const navigate = useNavigate();

  const [form, setForm] = useState({ fullName: '', email: '', password: '', confirmPassword: '' });
  const [errors, setErrors] = useState({});
  const [formError, setFormError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const setField = (name) => (event) => {
    const value = event.target.value;
    setForm((prev) => ({ ...prev, [name]: value }));
    if (errors[name]) setErrors((prev) => ({ ...prev, [name]: '' }));
    if (formError) setFormError('');
  };

  // Kiểm tra từng trường khi rời ô nhập (chỉ khi đã nhập gì đó, tránh báo lỗi khi vừa chạm vào)
  const handleBlur = (name) => () => {
    if (!form[name]) return;
    setErrors((prev) => ({ ...prev, [name]: FIELD_VALIDATORS[name](form) }));
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    const found = validateRegisterForm(form);
    setErrors(found);
    if (Object.keys(found).length > 0) return;

    const credentials = { email: form.email.trim(), password: form.password };
    setSubmitting(true);
    setFormError('');
    try {
      await register({ ...credentials, fullName: form.fullName.trim() });
    } catch (error) {
      const fieldErrors = getFieldErrors(error);
      if (Object.keys(fieldErrors).length > 0) setErrors(fieldErrors);
      else if (error.response?.status === 400) setErrors({ email: getErrorMessage(error, 'Email đã được đăng ký') });
      else setFormError(getErrorMessage(error, 'Đăng ký không thành công, vui lòng thử lại'));
      setSubmitting(false);
      return;
    }

    // Backend không cấp token khi đăng ký -> tự đăng nhập để người dùng vào thẳng danh mục môn học
    try {
      await login({ ...credentials, remember: true });
      navigate('/courses', { replace: true });
    } catch {
      navigate('/login', { replace: true, state: { notice: 'Đăng ký thành công. Vui lòng đăng nhập để bắt đầu học.' } });
    }
  };

  return (
    <AuthLayout>
      <p className="text-xs font-semibold uppercase tracking-wide text-blue-600">Bắt đầu hành trình của bạn</p>
      <h1 className="mt-2 text-3xl font-bold text-navy-800">Đăng ký tài khoản sinh viên</h1>
      <p className="mt-2 text-sm text-slate-500">Một tài khoản, cả hành trình chinh phục kiến thức.</p>

      {formError && <AlertBox tone="error" className="mt-6">{formError}</AlertBox>}

      <form onSubmit={handleSubmit} noValidate className="mt-8 space-y-4">
        <TextField
          id="register-name"
          label="Họ và tên"
          autoComplete="name"
          placeholder="Nguyễn Văn A"
          value={form.fullName}
          onChange={setField('fullName')}
          onBlur={handleBlur('fullName')}
          error={errors.fullName}
        />
        <TextField
          id="register-email"
          label="Email sinh viên"
          type="email"
          inputMode="email"
          autoComplete="email"
          placeholder="sv@univ.edu.vn"
          value={form.email}
          onChange={setField('email')}
          onBlur={handleBlur('email')}
          error={errors.email}
        />
        <TextField
          id="register-password"
          label="Mật khẩu"
          type="password"
          autoComplete="new-password"
          placeholder="Nhập mật khẩu"
          hint={`Tối thiểu ${PASSWORD_MIN_LENGTH} ký tự`}
          value={form.password}
          onChange={setField('password')}
          onBlur={handleBlur('password')}
          error={errors.password}
        />
        <TextField
          id="register-confirm"
          label="Nhập lại mật khẩu"
          type="password"
          autoComplete="new-password"
          placeholder="Nhập lại mật khẩu"
          value={form.confirmPassword}
          onChange={setField('confirmPassword')}
          onBlur={handleBlur('confirmPassword')}
          error={errors.confirmPassword}
        />

        <Button type="submit" size="lg" loading={submitting} className="mt-2 w-full">
          {submitting ? 'Đang tạo tài khoản...' : 'Đăng ký ngay'}
        </Button>
      </form>

      <p className="mt-4 text-center text-xs leading-relaxed text-slate-500">
        Bằng việc đăng ký, bạn đồng ý với Điều khoản sử dụng và Chính sách bảo mật của LearnMate AI.
      </p>

      <p className="mt-6 text-center text-sm text-slate-500">
        Đã có tài khoản?{' '}
        <Link to="/login" className="font-semibold text-blue-600 hover:underline">
          Đăng nhập
        </Link>
      </p>
    </AuthLayout>
  );
}
