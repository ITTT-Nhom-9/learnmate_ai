import { useState } from 'react';
import { RefreshCw, AlertTriangle, BarChart3, LineChart, History } from 'lucide-react';
import Spinner from '../../components/common/Spinner';
import Button from '../../components/common/Button';
import CourseSelector from './CourseSelector';
import ProgressBar from './ProgressBar';
import StatsCards from './StatsCards';
import RadarChart from './RadarChart';
import WeakTopicAlerts from './WeakTopicAlerts';
import RecentAttemptsTable from './RecentAttemptsTable';
import { useProgress } from '../../hooks/useProgress';

/**
 * Màn hình SCR-07: Bảng tiến độ cá nhân (Dashboard sinh viên).
 *
 * Bố cục:
 *  ┌────────────────────────────────────────────┐
 *  │  Tiêu đề + Chọn môn + Nút làm mới         │
 *  ├────────────────────────────────────────────┤
 *  │  Thanh % hoàn thành                         │
 *  ├────────────────────────────────────────────┤
 *  │  4 thẻ chỉ số nhanh (StatsCards)            │
 *  ├─────────────────────┬──────────────────────┤
 *  │  Radar Chart        │  Cảnh báo đỏ         │  (desktop: 2 cột)
 *  ├─────────────────────┴──────────────────────┤
 *  │  Lịch sử làm bài gần đây                   │
 *  └────────────────────────────────────────────┘
 */
export default function ProgressDashboardPage() {
  const [courseId, setCourseId] = useState(null);
  const { summary, radar, loading, error, reload } = useProgress(courseId);

  return (
    <div className="mx-auto max-w-6xl px-4 py-6 sm:px-6 lg:px-8">
      {/* Header */}
      <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="flex items-center gap-2 text-xl font-bold text-navy-800 sm:text-2xl">
            <BarChart3 size={24} className="shrink-0 text-brand-500" aria-hidden="true" />
            Bảng tiến độ học tập
          </h1>
          <p className="mt-0.5 text-sm text-slate-500">Theo dõi tiến độ và năng lực từng chủ đề</p>
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

      {/* Dashboard content */}
      {!loading && !error && summary && (
        <div className="space-y-6">
          {/* Thanh % hoàn thành */}
          <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
            <div className="mb-1 text-xs font-medium text-slate-500">
              {summary.course_code} – {summary.course_title}
            </div>
            <ProgressBar percent={summary.overall_progress_pct} label="Tiến độ hoàn thành môn học" />
          </div>

          {/* 4 thẻ chỉ số */}
          <StatsCards stats={summary.stats} />

          {/* Radar + Cảnh báo: 2 cột trên desktop, xếp dọc trên mobile */}
          <div className="grid gap-6 lg:grid-cols-2">
            {/* Radar Chart */}
            <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
              <h2 className="mb-4 flex items-center gap-2 text-base font-semibold text-navy-800">
                <LineChart size={18} className="text-brand-500" />
                Radar năng lực chủ đề
              </h2>
              {radar && (
                <>
                  <RadarChart
                    labels={radar.labels}
                    scores={radar.scores}
                    axes={radar.axes}
                    className="mx-auto max-w-sm"
                  />
                  {radar.truncated && (
                    <p className="mt-2 text-center text-xs text-slate-400">
                      Hiển thị {radar.axes.length}/{radar.total_topics} chủ đề
                    </p>
                  )}
                  {/* Chú giải màu */}
                  <div className="mt-3 flex flex-wrap justify-center gap-x-4 gap-y-1 text-xs text-slate-500">
                    <span className="flex items-center gap-1"><span className="h-2.5 w-2.5 rounded-full bg-green-500" /> Giỏi (≥80%)</span>
                    <span className="flex items-center gap-1"><span className="h-2.5 w-2.5 rounded-full bg-blue-500" /> Khá (60-79%)</span>
                    <span className="flex items-center gap-1"><span className="h-2.5 w-2.5 rounded-full bg-red-500" /> Yếu (&lt;60%)</span>
                    <span className="flex items-center gap-1"><span className="h-2.5 w-2.5 rounded-full bg-slate-400" /> Chưa học</span>
                  </div>
                </>
              )}
            </div>

            {/* Cảnh báo đỏ */}
            <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
              <h2 className="mb-4 flex items-center gap-2 text-base font-semibold text-navy-800">
                <AlertTriangle size={18} className="text-red-500" />
                Cảnh báo chủ đề yếu
                {summary.weak_topics.length > 0 && (
                  <span className="ml-auto inline-flex h-5 w-5 items-center justify-center rounded-full bg-red-100 text-xs font-bold text-red-600">
                    {summary.weak_topics.length}
                  </span>
                )}
              </h2>
              <WeakTopicAlerts weakTopics={summary.weak_topics} />
            </div>
          </div>

          {/* Lịch sử làm bài */}
          <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
            <h2 className="mb-4 flex items-center gap-2 text-base font-semibold text-navy-800">
              <History size={18} className="text-slate-500" />
              Lịch sử làm bài gần đây
            </h2>
            <RecentAttemptsTable attempts={summary.recent_attempts} />
          </div>
        </div>
      )}
    </div>
  );
}
