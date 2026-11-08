import { BookOpen, LineChart, Sparkles } from 'lucide-react';

// Điều hướng chính. Header (desktop) và Bottom Navigation (mobile) dùng chung danh sách này.
export const NAV_ITEMS = [
  { to: '/courses', label: 'Khóa học', mobileLabel: 'Môn học', icon: BookOpen },
  { to: '/tutor', label: 'Học cùng AI', mobileLabel: 'Gia sư AI', icon: Sparkles },
  { to: '/progress', label: 'Tiến độ', mobileLabel: 'Tiến độ', icon: LineChart },
];
