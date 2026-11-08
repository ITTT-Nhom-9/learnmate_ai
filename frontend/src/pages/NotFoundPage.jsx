import { Link } from 'react-router-dom';

export default function NotFoundPage() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center px-6 text-center">
      <p className="text-sm font-semibold text-blue-600">Lỗi 404</p>
      <h1 className="mt-2 text-3xl font-bold text-navy-800">Không tìm thấy trang</h1>
      <p className="mt-2 text-sm text-slate-500">Đường dẫn không tồn tại hoặc đã được di chuyển.</p>
      <Link to="/courses" className="mt-6 rounded-lg bg-navy-800 px-5 py-2.5 text-sm font-semibold text-white hover:bg-navy-900">
        Về danh mục môn học
      </Link>
    </div>
  );
}
