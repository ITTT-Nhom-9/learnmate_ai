import clsx from 'clsx';

const TONES = { blue: 'bg-blue-600', green: 'bg-emerald-500', gray: 'bg-slate-300' };

export default function ProgressBar({ value = 0, tone = 'blue', label, className }) {
  const pct = Math.min(100, Math.max(0, Number(value) || 0));
  return (
    <div
      role="progressbar"
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={Math.round(pct)}
      aria-label={label}
      className={clsx('h-1.5 w-full overflow-hidden rounded-full bg-slate-200', className)}
    >
      <div className={clsx('h-full rounded-full transition-[width] duration-500', TONES[tone])} style={{ width: `${pct}%` }} />
    </div>
  );
}
