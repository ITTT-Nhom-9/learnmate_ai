import { useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { GraduationCap } from 'lucide-react';
import AuthLayout from './AuthLayout';
import TextField from '../../components/common/TextField';
import Button from '../../components/common/Button';
import AlertBox from '../../components/common/AlertBox';
import { useAuth } from '../../hooks/useAuth';
import { validateEmail, validateLoginForm } from '../../utils/validators';
import { getErrorMessage, getFieldErrors } from '../../utils/apiError';

export default function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const redirectTo = location.state?.from?.pathname || '/courses';

  const [form, setForm] = useState({ email: '', password: '', remember: false });
  const [errors, setErrors] = useState({});
  const [formError, setFormError] = useState('');
  const [showForgot, setShowForgot] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const setField = (name) => (event) => {
    const value = event.target.type === 'checkbox' ? event.target.checked : event.target.value;
    setForm((prev) => ({ ...prev, [name]: value }));
    if (errors[name]) setErrors((prev) => ({ ...prev, [name]: '' })); // xóa lỗi khi người dùng sửa lại
    if (formError) setFormError('');
  };

  const handleEmailBlur = () => {
    const message = form.email ? validateEmail(form.email) : '';
    setErrors((prev) => ({ ...prev, email: message }));
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    const found = validateLoginForm(form);
    setErrors(found);
    if (Object.keys(found).length > 0) return;

    setSubmitting(true);
    setFormError('');
    try {
      await login({ email: form.email.trim(), password: form.password, remember: form.remember });
      navigate(redirectTo, { replace: true });
    } catch (error) {
      const fieldErrors = getFieldErrors(error);
      if (Object.keys(fieldErrors).length > 0) setErrors(fieldErrors);
      else setFormError(getErrorMessage(error, 'Đăng nhập không thành công, vui lòng thử lại'));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <AuthLayout>
      <p className="text-xs font-semibold uppercase tracking-wide text-blue-600">Chào mừng bạn trở lại</p>
      <h1 className="mt-2 text-3xl font-bold text-navy-800">Đăng nhập hệ thống</h1>
      <p className="mt-2 text-sm text-slate-500">Tiếp tục học tập, tiến gần hơn đến mục tiêu của bạn.</p>

      {location.state?.notice && <AlertBox tone="success" className="mt-6">{location.state.notice}</AlertBox>}
      {formError && <AlertBox tone="error" className="mt-6">{formError}</AlertBox>}

      <form onSubmit={handleSubmit} noValidate className="mt-8 space-y-5">
        <TextField
          id="login-email"
          label="Email sinh viên"
          type="email"
          inputMode="email"
          autoComplete="username"
          placeholder="sv@univ.edu.vn"
          value={form.email}
          onChange={setField('email')}
          onBlur={handleEmailBlur}
          error={errors.email}
        />
        <TextField
          id="login-password"
          label="Mật khẩu"
          type="password"
          autoComplete="current-password"
          placeholder="Nhập mật khẩu của bạn"
          value={form.password}
          onChange={setField('password')}
          error={errors.password}
        />

        <div className="flex items-center justify-between">
          <label className="flex cursor-pointer items-center gap-2 text-sm text-slate-600">
            <input
              type="checkbox"
              checked={form.remember}
              onChange={setField('remember')}
              className="h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-600"
            />
            Ghi nhớ đăng nhập
          </label>
          <button
            type="button"
            onClick={() => setShowForgot((v) => !v)}
            className="text-sm font-medium text-blue-600 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600"
          >
            Quên mật khẩu?
          </button>
        </div>

        {showForgot && (
          <AlertBox tone="info">
            Tính năng khôi phục mật khẩu chưa được hỗ trợ. Vui lòng liên hệ quản trị viên để được cấp lại mật khẩu.
          </AlertBox>
        )}

        <Button type="submit" size="lg" loading={submitting} className="w-full">
          {submitting ? 'Đang đăng nhập...' : 'Đăng nhập'}
        </Button>
      </form>

      <p className="mt-6 text-center text-sm text-slate-500">
        Chưa có tài khoản?{' '}
        <Link to="/register" className="font-semibold text-blue-600 hover:underline">
          Đăng ký ngay
        </Link>
      </p>

      <div className="mt-6 flex items-start gap-3 rounded-lg bg-slate-50 px-4 py-3.5 text-sm text-slate-500">
        <GraduationCap size={20} className="mt-0.5 shrink-0 text-slate-400" aria-hidden="true" />
        Kiến thức của bạn được lưu tự động. Bắt đầu lại đúng nơi bạn đã dừng.
      </div>
    </AuthLayout>
  );
}
