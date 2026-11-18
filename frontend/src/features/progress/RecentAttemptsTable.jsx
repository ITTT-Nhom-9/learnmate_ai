import clsx from 'clsx';
import { Clock } from 'lucide-react';

function formatDuration(sec) {
  const m = Math.floor(sec / 60);
  const s = sec % 60;
  return m > 0 ? `${m}:${String(s).padStart(2, '0')}` : `${s}s`;
}

const DIFF_COLORS = {
  EASY: 'bg-green-100 text-green-700',
  MEDIUM: 'bg-amber-100 text-amber-700',
  HARD: 'bg-red-100 text-red-700',
};

const DIFF_LABELS = { EASY: 'Dễ', MEDIUM: 'TB', HARD: 'Khó' };

/**
 * Bảng lịch sử làm bài gần đây (10 lượt) trên Dashboard (SCR-07).
 */
export default function RecentAttemptsTable({ attempts = [] }) {
  if (attempts.length === 0) {
    return (
      <p className="py-6 text-center text-sm text-slate-400">
        Chưa có lượt làm bài nào.
      </p>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left text-sm">
        <thead>
          <tr className="border-b border-slate-200 text-xs font-semibold uppercase tracking-wide text-slate-500">
            <th className="whitespace-nowrap px-3 py-2.5">Bài trắc nghiệm</th>
            <th className="whitespace-nowrap px-3 py-2.5 text-center">Độ khó</th>
            <th className="whitespace-nowrap px-3 py-2.5 text-center">Điểm</th>
            <th className="hidden whitespace-nowrap px-3 py-2.5 text-center sm:table-cell">
              <Clock size={14} className="mx-auto" aria-label="Thời gian" />
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {attempts.map((a) => {
            const scoreColor = a.score >= 8 ? 'text-green-600' : a.score >= 5 ? 'text-amber-600' : 'text-red-600';
            return (
              <tr key={a.attempt_id} className="transition-colors hover:bg-slate-50">
                <td className="max-w-[200px] truncate px-3 py-2.5 font-medium text-slate-700 sm:max-w-xs">
                  {a.quiz_title}
                </td>
                <td className="px-3 py-2.5 text-center">
                  <span className={clsx('inline-block rounded-full px-2 py-0.5 text-[11px] font-semibold', DIFF_COLORS[a.difficulty] || DIFF_COLORS.MEDIUM)}>
                    {DIFF_LABELS[a.difficulty] || a.difficulty}
                  </span>
                </td>
                <td className={clsx('px-3 py-2.5 text-center font-bold', scoreColor)}>
                  {a.score}
                </td>
                <td className="hidden px-3 py-2.5 text-center text-slate-500 sm:table-cell">
                  {formatDuration(a.duration_sec)}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
