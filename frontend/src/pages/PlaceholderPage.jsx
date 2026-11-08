import { Construction } from 'lucide-react';
import Button from '../components/common/Button';
import EmptyState from '../components/common/EmptyState';
import { useAuth } from '../hooks/useAuth';

/** Trang giữ chỗ cho màn hình thuộc task khác. Có nút đăng xuất để kiểm tra luồng xác thực. */
export default function PlaceholderPage({ title }) {
  const { user, logout } = useAuth();
  return (
    <div className="mx-auto max-w-3xl px-4 py-12 sm:px-6">
      <EmptyState
        icon={Construction}
        title={`${title} đang được phát triển`}
        description={`Bạn đã đăng nhập với tên ${user?.full_name || ''}. Màn hình này sẽ được hoàn thiện ở task tiếp theo.`}
        action={
          <Button variant="outline" onClick={logout}>
            Đăng xuất
          </Button>
        }
      />
    </div>
  );
}
