import { Loader2 } from 'lucide-react';
import clsx from 'clsx';

export default function Spinner({ size = 20, className, label = 'Đang tải' }) {
  return <Loader2 size={size} role="status" aria-label={label} className={clsx('animate-spin', className)} />;
}
