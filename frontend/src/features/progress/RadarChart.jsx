import { useEffect, useRef } from 'react';
import { Chart, registerables } from 'chart.js';

// Đăng ký tất cả controller / scale / plugin của Chart.js (gồm RadarController, RadialLinearScale, …).
Chart.register(...registerables);

/**
 * Biểu đồ Radar năng lực chủ đề (SCR-07).
 *
 * Props:
 * - labels: string[]  — tên các chủ đề (tối đa 6-12 trục)
 * - scores: number[]  — điểm Mastery (0-100) tương ứng
 * - axes:   object[]  — chi tiết từng trục (status, label_vi) để tô màu điểm
 *
 * Thư viện: Chart.js v4 (đã có trong package.json sau cài đặt TK-22).
 */
export default function RadarChart({ labels = [], scores = [], axes = [], className = '' }) {
  const canvasRef = useRef(null);
  const chartRef = useRef(null);

  useEffect(() => {
    if (!canvasRef.current || labels.length === 0) return;

    // Rút gọn nhãn dài: "Hệ quản trị CSDL (DBMS) và Hệ thống Tập tin truyền thống" → "Hệ quản trị CSDL…"
    const shortLabels = labels.map((label) => {
      if (label.length <= 20) return label;
      // Cắt tại khoảng trắng gần vị trí 18 ký tự
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
            backgroundColor: 'rgba(99, 102, 241, 0.15)',   // brand-500 / 15%
            borderColor: '#6366f1',                          // brand-500
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
    <div className={className}>
      <canvas ref={canvasRef} aria-label="Biểu đồ Radar năng lực chủ đề" role="img" />
    </div>
  );
}
