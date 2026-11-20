import { Link } from 'react-router-dom';
import clsx from 'clsx';
import { Clock, ExternalLink } from 'lucide-react';

function formatDate(isoOrTs) {
  if (!isoOrTs) return '—';
  const d = new Date(isoOrTs);
  if (isNaN(d.getTime())) return '—';
  const dd = String(d.getDate()).padStart(2, '0');
  const mm = String(d.getMonth() + 1).padStart(2, '0');
  const yyyy = d.getFullYear();
  return `${dd}/${mm}/${yyyy}`;
}

function formatDuration(sec) {
  if (sec == null) return '—';
  const m = Math.floor(sec / 60);
  const s = sec % 60;
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
}

function scoreColor100(score) {
  if (score >= 80) return 'text-emerald-600';
  if (score >= 50) return 'text-amber-600';
  return 'text-red-600';
}

/**
 * Bảng lịch sử làm bài gần đây (SCR-07).
 *
 * Chuẩn bản vẽ SCR-07_Bang_Tien_Do_Ca_Nhan.png:
 *  Cột: Ngày làm bài | Bài kiểm tra | Điểm số (X/100) | Thời gian (MM:SS) | Thao tác (Xem chi tiết)
 *  Tiêu đề góc phải: Liên kết "Xem tất cả →"
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
            <th className="whitespace-nowrap px-3 py-2.5">Ngày làm bài</th>
            <th className="whitespace-nowrap px-3 py-2.5">Bài kiểm tra</th>
            <th className="whitespace-nowrap px-3 py-2.5 text-center">Điểm số</th>
            <th className="hidden whitespace-nowrap px-3 py-2.5 text-center sm:table-cell">
              <Clock size={14} className="mx-auto" aria-label="Thời gian" />
            </th>
            <th className="whitespace-nowrap px-3 py-2.5 text-center">Thao tác</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {attempts.map((a) => {
            // Chuyển đổi điểm từ thang 10 → thang 100
            const score100 = Math.round((a.score ?? 0) * 10);
            return (
              <tr key={a.attempt_id} className="transition-colors hover:bg-slate-50">
                {/* Ngày làm bài */}
                <td className="whitespace-nowrap px-3 py-2.5 text-slate-500">
                  {formatDate(a.completed_at || a.created_at || a.last_practiced_at)}
                </td>

                {/* Bài kiểm tra + chủ đề */}
                <td className="max-w-[200px] px-3 py-2.5 sm:max-w-xs">
                  <span className="block truncate font-medium text-slate-700">
                    {a.quiz_title}
                  </span>
                  {a.topic_name && (
                    <span className="block truncate text-xs text-slate-400">
                      {a.topic_name}
                    </span>
                  )}
                </td>

                {/* Điểm số X/100 */}
                <td className={clsx('px-3 py-2.5 text-center font-bold', scoreColor100(score100))}>
                  {score100}/100
                </td>

                {/* Thời gian */}
                <td className="hidden px-3 py-2.5 text-center text-slate-500 sm:table-cell">
                  {formatDuration(a.duration_sec)}
                </td>

                {/* Thao tác */}
                <td className="px-3 py-2.5 text-center">
                  <Link
                    to={`/quiz/${a.attempt_id}/result`}
                    className="inline-flex items-center gap-1 text-xs font-semibold text-brand-600 hover:text-brand-700 hover:underline"
                  >
                    Xem chi tiết
                    <ExternalLink size={12} />
                  </Link>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
