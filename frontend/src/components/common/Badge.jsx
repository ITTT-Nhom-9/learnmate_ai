import clsx from 'clsx';

const TONES = {
  blue: 'bg-blue-50 text-blue-600',
  green: 'bg-emerald-50 text-emerald-600',
  gray: 'bg-slate-100 text-slate-500',
};

export default function Badge({ tone = 'blue', className, children }) {
  return (
    <span className={clsx('inline-flex items-center whitespace-nowrap rounded-md px-2.5 py-1 text-xs font-semibold', TONES[tone], className)}>
      {children}
    </span>
  );
}
