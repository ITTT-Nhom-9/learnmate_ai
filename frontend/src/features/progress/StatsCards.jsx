import clsx from 'clsx';
import { Award, BookCheck, AlertTriangle, Clock, TrendingUp, Target, BarChart3, BookOpen } from 'lucide-react';

const ICONS = [Target, Award, BookCheck, AlertTriangle, BookOpen, TrendingUp, Clock, BarChart3];
const COLORS = [
  'bg-indigo-50 text-indigo-600',   // Tổng chủ đề
  'bg-green-50 text-green-600',     // Giỏi
  'bg-blue-50 text-blue-600',       // Khá
  'bg-red-50 text-red-600',         // Yếu
  'bg-slate-50 text-slate-500',     // Chưa học
  'bg-purple-50 text-purple-600',   // Tổng lượt
  'bg-amber-50 text-amber-600',     // Thời gian
  'bg-cyan-50 text-cyan-600',       // Điểm TB
];

function formatDuration(totalSec) {
  const h = Math.floor(totalSec / 3600);
  const m = Math.floor((totalSec % 3600) / 60);
  if (h > 0) return `${h}h ${m}m`;
  return `${m} phút`;
}

/**
 * 4 thẻ chỉ số nhanh nằm ngang trên Dashboard (SCR-07).
 * Hiển thị: Tổng chủ đề, Đã vững (Giỏi), Cần cải thiện (Yếu), Điểm TB.
 */
export default function StatsCards({ stats }) {
  if (!stats) return null;

  const cards = [
    { label: 'Tổng chủ đề', value: stats.total_topics, iconIdx: 0, colorIdx: 0 },
    { label: 'Đã vững', value: stats.mastered_topics, iconIdx: 1, colorIdx: 1 },
    { label: 'Cần cải thiện', value: stats.weak_topics, iconIdx: 3, colorIdx: 3, highlight: stats.weak_topics > 0 },
    { label: 'Điểm TB', value: stats.average_quiz_score.toFixed(1), iconIdx: 7, colorIdx: 7 },
  ];

  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 sm:gap-4">
      {cards.map(({ label, value, iconIdx, colorIdx, highlight }) => {
        const Icon = ICONS[iconIdx];
        return (
          <div
            key={label}
            className={clsx(
              'flex items-center gap-3 rounded-xl border bg-white p-4 shadow-sm transition-shadow hover:shadow-md',
              highlight ? 'border-red-200' : 'border-slate-200'
            )}
          >
            <span className={clsx('flex h-10 w-10 shrink-0 items-center justify-center rounded-lg', COLORS[colorIdx])}>
              <Icon size={20} aria-hidden="true" />
            </span>
            <div className="min-w-0">
              <p className="truncate text-xs text-slate-500">{label}</p>
              <p className={clsx('text-lg font-bold', highlight ? 'text-red-600' : 'text-navy-800')}>
                {value}
              </p>
            </div>
          </div>
        );
      })}
    </div>
  );
}
