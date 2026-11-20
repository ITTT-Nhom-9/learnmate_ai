import { useEffect, useRef } from 'react';
import { Chart, registerables } from 'chart.js';
import clsx from 'clsx';

// Đăng ký tất cả controller / scale / plugin của Chart.js (gồm RadarController, RadialLinearScale, …).
Chart.register(...registerables);

/**
 * Biểu đồ Radar năng lực chủ đề (SCR-07).
 *
 * Chuẩn bản vẽ SCR-07_Bang_Tien_Do_Ca_Nhan.png:
 *  - Bố cục 2 cột bên trong Card: Trái = Canvas Radar (~55%), Phải = Danh sách điểm % (~45%).
 *  - Tiêu đề card & nhãn phụ được render ở component cha (ProgressDashboardPage).
 *
 * Props:
 * - labels: string[]  — tên các chủ đề (tối đa 6-12 trục)
 * - scores: number[]  — điểm Mastery (0-100) tương ứng
 * - axes:   object[]  — chi tiết từng trục (status, label_vi) để tô màu điểm
 */
export default function RadarChart({ labels = [], scores = [], axes = [], className = '' }) {
  const canvasRef = useRef(null);
  const chartRef = useRef(null);

  useEffect(() => {
    if (!canvasRef.current || labels.length === 0) return;

    // Rút gọn nhãn dài: "Hệ quản trị CSDL (DBMS) và Hệ thống Tập tin truyền thống" → "Hệ quản trị CSDL…"
    const shortLabels = labels.map((label) => {
      if (label.length <= 20) return label;
      const cut = label.lastIndexOf(' ', 18);
      return label.slice(0, cut > 8 ? cut : 18) + '…';
    });

    // Tô màu điểm theo hạng Mastery
    const pointColors = (axes || []).map((a) => {
      if (a?.status === 'MASTER') return '#16a34a';  // green-600
      if (a?.status === 'FAIR') return '#2563eb';     // blue-600
      if (a?.status === 'WEAK') return '#dc2626';     // red-600
      return '#94a3b8';                                // slate-400 (chưa học)
    });

    if (chartRef.current) chartRef.current.destroy();

    chartRef.current = new Chart(canvasRef.current, {
      type: 'radar',
      data: {
        labels: shortLabels,
        datasets: [
          {
            label: 'Mastery (%)',
            data: scores,
            fill: true,
            backgroundColor: 'rgba(99, 102, 241, 0.15)',
            borderColor: '#6366f1',
            borderWidth: 2,
            pointBackgroundColor: pointColors.length === scores.length ? pointColors : '#6366f1',
            pointBorderColor: '#fff',
            pointBorderWidth: 2,
            pointRadius: 5,
            pointHoverRadius: 7,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: true,
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              title: (items) => labels[items[0]?.dataIndex] || '',
              label: (item) => {
                const axis = axes[item.dataIndex];
                const tag = axis?.label_vi || '';
                return `Mastery: ${item.raw}% ${tag ? `(${tag})` : ''}`;
              },
            },
          },
        },
        scales: {
          r: {
            beginAtZero: true,
            min: 0,
            max: 100,
            ticks: {
              stepSize: 20,
              backdropColor: 'transparent',
              font: { size: 10 },
              color: '#94a3b8',
            },
            grid: { color: '#e2e8f0' },
            angleLines: { color: '#e2e8f0' },
            pointLabels: {
              font: { size: 11, weight: '500' },
              color: '#475569',
            },
          },
        },
      },
    });

    return () => {
      chartRef.current?.destroy();
      chartRef.current = null;
    };
  }, [labels, scores, axes]);

  if (labels.length === 0) {
    return (
      <div className="flex h-64 items-center justify-center text-sm text-slate-400">
        Chưa có dữ liệu năng lực để hiển thị
      </div>
    );
  }

  return (
    <div className={clsx('grid grid-cols-1 gap-4 md:grid-cols-[55%_45%] md:items-center', className)}>
      {/* Cột trái: Canvas Radar */}
      <div className="mx-auto w-full max-w-sm">
        <canvas ref={canvasRef} aria-label="Biểu đồ Radar năng lực chủ đề" role="img" />
      </div>

      {/* Cột phải: Danh sách điểm % chi tiết từng chủ đề */}
      <div className="flex flex-col justify-center space-y-3.5 pl-0 md:pl-4">
        {axes.map((axis, idx) => (
          <div
            key={axis.topic_id || idx}
            className="grid grid-cols-[1fr_auto] items-center gap-4 py-1.5 text-sm"
          >
            <span className="truncate text-slate-700" title={axis.topic_name || labels[idx]}>
              {axis.topic_name || labels[idx]}
            </span>
            <span
              className={clsx(
                'min-w-[48px] text-right font-semibold',
                scores[idx] >= 80
                  ? 'text-emerald-600'
                  : scores[idx] >= 60
                    ? 'text-blue-600'
                    : scores[idx] > 0
                      ? 'text-amber-600'
                      : 'text-red-500'
              )}
            >
              {Math.round(scores[idx])}%
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
