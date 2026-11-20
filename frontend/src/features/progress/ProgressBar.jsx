import clsx from 'clsx';

/**
 * Thanh phần trăm hoàn thành môn học (SCR-07).
 * Hiển thị con số % và thanh progress ngang có gradient.
 */
export default function ProgressBar({ percent = 0, label, className }) {
  const clamped = Math.min(100, Math.max(0, Math.round(percent)));

  // Màu thanh theo tiến độ: đỏ < 30%, vàng 30-60%, xanh 60-80%, tím > 80%
  let barColor = 'from-red-400 to-red-500';
  if (clamped >= 80) barColor = 'from-indigo-500 to-purple-500';
  else if (clamped >= 60) barColor = 'from-green-400 to-emerald-500';
  else if (clamped >= 30) barColor = 'from-amber-400 to-yellow-500';

  return (
    <div className={className}>
      <div className="mb-1.5 flex items-baseline justify-between gap-2">
        <span className="text-sm font-medium text-slate-700">{label || 'Tiến độ hoàn thành'}</span>
        <span className="text-lg font-bold text-navy-800">{clamped}%</span>
      </div>
      <div className="h-3 w-full overflow-hidden rounded-full bg-slate-200" role="progressbar" aria-valuenow={clamped} aria-valuemin={0} aria-valuemax={100} aria-label={`${label || 'Tiến độ'}: ${clamped}%`}>
        <div
          className={clsx('h-full rounded-full bg-gradient-to-r transition-all duration-500 ease-out', barColor)}
          style={{ width: `${clamped}%` }}
        />
      </div>
    </div>
  );
}
