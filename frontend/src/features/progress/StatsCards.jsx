import clsx from 'clsx';
import { Award, FileCheck2, Layers, Clock } from 'lucide-react';

function formatDuration(totalSec) {
  if (totalSec == null || totalSec === 0) return '0 phút';
  const h = Math.floor(totalSec / 3600);
  const m = Math.floor((totalSec % 3600) / 60);
  if (h > 0) return `${h}h ${m > 0 ? m + 'm' : ''}`;
  return `${m} phút`;
}

/**
 * 4 thẻ chỉ số nhanh nằm ngang trên Dashboard (SCR-07).
 *
 * Chuẩn bản vẽ SCR-07_Bang_Tien_Do_Ca_Nhan.png:
 *  Thẻ 1: Điểm thành thạo trung bình  (avgScore% · phụ đề: Dựa trên điểm EMA các chủ đề)
 *  Thẻ 2: Số bài quiz đã làm           (totalAttempts · phụ đề: Tổng lượt làm bài kiểm tra)
 *  Thẻ 3: Chủ đề đã vững               (mastered/total · phụ đề: Đã đạt mức Khá trở lên)
 *  Thẻ 4: Thời gian học                 (formatted · phụ đề: Tổng thời gian luyện tập)
 */
export default function StatsCards({ stats }) {
  if (!stats) return null;

  const cards = [
    {
      label: 'Điểm thành thạo TB',
      value: `${stats.average_quiz_score != null ? stats.average_quiz_score.toFixed(1) : '—'}%`,
      sub: 'Dựa trên điểm EMA các chủ đề',
      Icon: Award,
      iconBg: 'bg-indigo-50 text-indigo-600',
    },
    {
      label: 'Số bài quiz đã làm',
      value: stats.total_attempts ?? 0,
      sub: 'Tổng lượt làm bài kiểm tra',
      Icon: FileCheck2,
      iconBg: 'bg-green-50 text-green-600',
    },
    {
      label: 'Chủ đề đã vững',
      value: `${stats.mastered_topics ?? 0}/${stats.total_topics ?? 0}`,
      sub: 'Đã đạt mức Khá trở lên',
      Icon: Layers,
      iconBg: 'bg-blue-50 text-blue-600',
    },
    {
      label: 'Thời gian học',
      value: formatDuration(stats.total_study_time_sec),
      sub: 'Tổng thời gian luyện tập',
      Icon: Clock,
      iconBg: 'bg-amber-50 text-amber-600',
    },
  ];

  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 sm:gap-4">
      {cards.map(({ label, value, sub, Icon, iconBg }) => (
        <div
          key={label}
          className="flex items-start gap-3 rounded-xl border border-slate-200 bg-white p-4 shadow-sm transition-shadow hover:shadow-md"
        >
          <span
            className={clsx(
              'flex h-10 w-10 shrink-0 items-center justify-center rounded-lg',
              iconBg
            )}
          >
            <Icon size={20} aria-hidden="true" />
          </span>
          <div className="min-w-0">
            <p className="truncate text-xs text-slate-500">{label}</p>
            <p className="text-lg font-bold text-navy-800">{value}</p>
            <p className="mt-0.5 truncate text-[11px] leading-tight text-slate-400">{sub}</p>
          </div>
        </div>
      ))}
    </div>
  );
}
