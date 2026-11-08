import { AlertCircle, CheckCircle2, Info } from 'lucide-react';
import clsx from 'clsx';

const TONES = {
  error: { box: 'border-red-200 bg-red-50 text-red-700', Icon: AlertCircle },
  success: { box: 'border-emerald-200 bg-emerald-50 text-emerald-700', Icon: CheckCircle2 },
  info: { box: 'border-blue-200 bg-blue-50 text-blue-700', Icon: Info },
};

export default function AlertBox({ tone = 'info', className, children, action }) {
  const { box, Icon } = TONES[tone];
  return (
    <div role={tone === 'error' ? 'alert' : 'status'} className={clsx('flex items-start gap-2.5 rounded-lg border px-3.5 py-3 text-sm', box, className)}>
      <Icon size={18} className="mt-0.5 shrink-0" aria-hidden="true" />
      <div className="min-w-0 flex-1">{children}</div>
      {action}
    </div>
  );
}
