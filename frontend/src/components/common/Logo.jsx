import { BookOpen } from 'lucide-react';
import clsx from 'clsx';

/** Logo LearnMate AI. tone="dark": dùng trên nền sáng; tone="light": dùng trên nền navy. */
export default function Logo({ tone = 'dark', className }) {
  const isLight = tone === 'light';
  return (
    <div className={clsx('flex items-center gap-2.5', className)}>
      <span
        className={clsx(
          'flex h-9 w-9 items-center justify-center rounded-lg',
          isLight ? 'bg-white/10 text-white' : 'bg-navy-800 text-white'
        )}
      >
        <BookOpen size={20} strokeWidth={2} aria-hidden="true" />
      </span>
      <span className={clsx('text-xl tracking-tight', isLight ? 'text-white' : 'text-navy-800')}>
        <span className="font-bold">LearnMate</span> <span className="font-normal">AI</span>
      </span>
    </div>
  );
}
