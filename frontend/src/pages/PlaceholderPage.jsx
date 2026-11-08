import { useNavigate, useParams } from 'react-router-dom';
import { Construction } from 'lucide-react';
import Button from '../components/common/Button';
import EmptyState from '../components/common/EmptyState';

/** Trang giữ chỗ cho các màn hình thuộc task khác (Gia sư AI, Tiến độ) để liên kết điều hướng không bị 404. */
export default function PlaceholderPage({ title }) {
  const navigate = useNavigate();
  const { lessonId } = useParams();
  return (
    <div className="mx-auto max-w-3xl px-4 py-12 sm:px-6">
      <EmptyState
        icon={Construction}
        title={`${title}${lessonId ? ` (bài học #${lessonId})` : ''} đang được phát triển`}
        description="Màn hình này sẽ được hoàn thiện ở task tiếp theo trong kế hoạch."
        action={<Button variant="outline" onClick={() => navigate('/courses')}>Về danh mục môn học</Button>}
      />
    </div>
  );
}
