import { useState } from 'react';
import { RefreshCw, AlertTriangle, LineChart, History } from 'lucide-react';
import Spinner from '../../components/common/Spinner';
import Button from '../../components/common/Button';
import CourseSelector from './CourseSelector';
import StatsCards from './StatsCards';
import RadarChart from './RadarChart';
import WeakTopicAlerts from './WeakTopicAlerts';
import RecentAttemptsTable from './RecentAttemptsTable';
import { useProgress } from '../../hooks/useProgress';

/**
 * Màn hình SCR-07: Bảng tiến độ cá nhân (Dashboard sinh viên).
 *
 * Bố cục chuẩn bản vẽ SCR-07_Bang_Tien_Do_Ca_Nhan.png:
 *  ┌────────────────────────────────────────────┐
 *  │  Tiêu đề + Chọn môn + Nút làm mới         │
 *  ├────────────────────────────────────────────┤
 *  │  Thanh % hoàn thành                         │
 *  ├────────────────────────────────────────────┤
 *  │  4 thẻ chỉ số nhanh (StatsCards)            │
 *  ├────────────────────────────────────────────┤
 *  │  Mức độ thành thạo (Radar + Điểm chi tiết) │
 *  ├────────────────────────────────────────────┤
 *  │  Chủ đề cần củng cố (Cảnh báo đỏ)          │
 *  ├────────────────────────────────────────────┤
 *  │  Lịch sử làm bài gần đây                   │
 *  └────────────────────────────────────────────┘
 */
export default function ProgressDashboardPage() {
  const [courseId, setCourseId] = useState(null);
  const [showAllAttempts, setShowAllAttempts] = useState(false);
  const { summary, radar, loading, error, reload } = useProgress(courseId);

  return (
    <div className="mx-auto max-w-6xl px-4 py-6 sm:px-6 lg:px-8">
      {/* ===== HEADER (chuẩn SCR-07) ===== */}
      <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Bảng tiến độ cá nhân</h1>
          <p className="mt-1 text-sm text-slate-500">
            Hiểu rõ năng lực, học tập đúng trọng tâm.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <CourseSelector selectedCourseId={courseId} onSelect={setCourseId} />
          <Button
            variant="ghost"
            size="sm"
            icon={RefreshCw}
            onClick={reload}
            disabled={loading}
            aria-label="Làm mới dữ liệu"
            className="shrink-0"
          />
        </div>
      </div>

      {/* Loading */}
      {loading && (
        <div className="flex justify-center py-24">
          <Spinner size={28} label="Đang tải tiến độ" />
        </div>
      )}

      {/* Error */}
      {!loading && error && (
        <div className="rounded-xl border border-red-200 bg-red-50 p-6 text-center">
          <p className="text-sm text-red-700">{error}</p>
          <Button variant="outline" size="sm" onClick={reload} className="mt-3">
            Thử lại
          </Button>
        </div>
      )}

      {/* Chưa chọn môn */}
      {!loading && !error && !summary && (
        <div className="rounded-xl border border-dashed border-slate-300 bg-white p-10 text-center">
          <LineChart size={40} className="mx-auto text-slate-300" />
          <p className="mt-3 text-sm text-slate-500">Chọn một môn học để xem tiến độ.</p>
        </div>
      )}

      {/* ===== DASHBOARD CONTENT ===== */}
      {!loading && !error && summary && (
        <div className="space-y-6">
          {/* 1. 4 thẻ chỉ số nhanh */}
          <StatsCards stats={summary.stats} />

          {/* 3 & 4. Mức độ thành thạo + Cảnh báo củng cố (Desktop: Grid 12 cột, tỷ lệ ~60:40) */}
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-12 lg:items-start">
            {/* 3. Mức độ thành thạo theo chủ đề (Radar + Danh sách điểm) - chiếm 7/8 cột */}
            <div className="flex flex-col rounded-xl border border-slate-200 bg-white p-5 shadow-sm lg:col-span-7 xl:col-span-8">
              <div className="mb-4 flex items-center justify-between">
                <h2 className="flex items-center gap-2 text-base font-semibold text-navy-800">
                  <LineChart size={18} className="text-brand-500" />
                  Mức độ thành thạo theo chủ đề
                </h2>
                <span className="text-xs text-slate-400">Điểm EMA · Thang 100</span>
              </div>
              {radar && (
                <>
                  <RadarChart
                    labels={radar.labels}
                    scores={radar.scores}
                    axes={radar.axes}
                  />
                  {radar.truncated && (
                    <p className="mt-2 text-center text-xs text-slate-400">
                      Hiển thị {radar.axes.length}/{radar.total_topics} chủ đề
                    </p>
                  )}
                </>
              )}
            </div>

            {/* 4. Chủ đề cần củng cố (Cảnh báo đỏ) - chiếm 5/4 cột */}
            <div className="flex flex-col rounded-xl border border-slate-200 bg-white p-5 shadow-sm lg:col-span-5 xl:col-span-4">
              <h2 className="mb-4 flex items-center gap-2 text-base font-semibold text-navy-800">
                <AlertTriangle size={18} className="text-red-500" />
                Chủ đề cần củng cố
                {summary.weak_topics.length > 0 && (
                  <span className="ml-auto inline-flex h-5 w-5 items-center justify-center rounded-full bg-red-100 text-xs font-bold text-red-600">
                    {summary.weak_topics.length}
                  </span>
                )}
              </h2>
              <WeakTopicAlerts weakTopics={summary.weak_topics} />
            </div>
          </div>

          {/* 5. Lịch sử làm bài gần đây */}
          <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="flex items-center gap-2 text-base font-semibold text-navy-800">
                <History size={18} className="text-slate-500" />
                Lịch sử làm bài gần đây
              </h2>
              {summary.recent_attempts?.length > 5 && (
                <button
                  type="button"
                  onClick={() => setShowAllAttempts((prev) => !prev)}
                  className="text-xs font-semibold text-brand-600 hover:text-brand-700 cursor-pointer"
                >
                  {showAllAttempts ? 'Thu gọn \u2191' : 'Xem tất cả \u2192'}
                </button>
              )}
            </div>
            <RecentAttemptsTable
              attempts={showAllAttempts ? summary.recent_attempts : summary.recent_attempts?.slice(0, 5)}
            />
          </div>
        </div>
      )}
    </div>
  );
}
