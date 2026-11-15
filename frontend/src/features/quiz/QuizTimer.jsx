import { Timer } from 'lucide-react';
import clsx from 'clsx';
import { formatClock, getTimerTone } from './quizUtils';

const TONES = {
  normal: { box: 'border-slate-200 bg-white', text: 'text-navy-800', icon: 'text-slate-500' },
  warning: { box: 'border-amber-300 bg-amber-50', text: 'text-amber-700', icon: 'text-amber-600' },
  critical: { box: 'border-red-300 bg-red-50', text: 'text-red-600', icon: 'text-red-600' },
};

/**
 * Đồng hồ đếm ngược. Còn <= 60s chuyển cam, <= 30s chuyển đỏ và nhấp nháy.
 * Màu không phải tín hiệu duy nhất: sr-only đọc "sắp hết giờ", biểu tượng đổi nhịp.
 * variant="card": khối "Thời gian còn lại" ở góc phải tiêu đề (desktop). variant="inline": gọn trong thanh dính (mobile).
 */
export default function QuizTimer({ remainingSec, variant = 'card' }) {
  const tone = TONES[getTimerTone(remainingSec ?? 0)];
  const critical = getTimerTone(remainingSec ?? 0) === 'critical' && remainingSec > 0;
  const clock = formatClock(remainingSec ?? 0);

  if (variant === 'inline') {
    return (
      <div role="timer" aria-label={`Thời gian còn lại ${clock}`} className={clsx('flex items-center gap-1.5 font-bold tabular-nums', tone.text)}>
        <Timer size={18} aria-hidden="true" className={clsx(tone.icon, critical && 'animate-pulse')} />
        <span className="text-lg leading-none">{clock}</span>
      </div>
    );
  }

  return (
    <div role="timer" aria-label={`Thời gian còn lại ${clock}`} className={clsx('flex items-center gap-3 rounded-lg border px-4 py-2.5 transition-colors', tone.box)}>
      <Timer size={22} aria-hidden="true" className={clsx(tone.icon, critical && 'animate-pulse')} />
      <div>
        <p className="text-[11px] leading-tight text-slate-500">Thời gian còn lại</p>
        <p className={clsx('text-2xl font-bold leading-tight tabular-nums', tone.text)}>{clock}</p>
      </div>
    </div>
  );
}
