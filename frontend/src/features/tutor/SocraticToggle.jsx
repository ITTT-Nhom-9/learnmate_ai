import { Lightbulb, Sparkles } from 'lucide-react';
import clsx from 'clsx';

const OPTIONS = [
  { value: 'EXPLAIN', label: 'Giải thích cận kề', short: 'Giải thích', icon: Sparkles },
  { value: 'SOCRATIC', label: 'Gợi mở Socratic (Từng bước)', short: 'Gợi mở Socratic', icon: Lightbulb },
];

/** Chuyển chế độ trả lời: EXPLAIN (giải thích) / SOCRATIC (đặt câu hỏi gợi mở, không đưa đáp án ngay). */
export function ModeToggle({ mode, onChange, disabled }) {
  return (
    <div role="radiogroup" aria-label="Chế độ trả lời" className="grid grid-cols-2 gap-1 rounded-xl bg-slate-100/80 p-1">
      {OPTIONS.map(({ value, label, short, icon: Icon }) => {
        const active = mode === value;
        return (
          <button
            key={value}
            type="button"
            role="radio"
            aria-checked={active}
            disabled={disabled}
            onClick={() => onChange(value)}
            className={clsx(
              'flex items-center justify-center gap-2 rounded-lg px-3 py-2 text-sm transition-colors',
              'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600 disabled:cursor-not-allowed',
              active ? 'bg-navy-800 font-semibold text-white shadow-sm' : 'font-medium text-slate-600 hover:text-navy-800 disabled:hover:text-slate-600',
              disabled && !active && 'opacity-60'
            )}
          >
            <Icon size={16} aria-hidden="true" />
            <span className="hidden sm:inline">{label}</span>
            <span className="sm:hidden">{short}</span>
          </button>
        );
      })}
    </div>
  );
}

// 5 giai đoạn của máy trạng thái Socratic (TK-14): hint_level 1..5
export const SOCRATIC_STAGES = ['Khám phá', 'Thách thức', 'Gợi ý', 'Đúc kết', 'Đánh giá'];

export function SocraticProgress({ hintLevel, isConcluded }) {
  const current = isConcluded ? SOCRATIC_STAGES.length : Math.min(SOCRATIC_STAGES.length, Math.max(0, hintLevel || 0));
  const title =
    current === 0
      ? 'Bắt đầu hành trình gợi mở'
      : isConcluded
        ? 'Đã hoàn thành 5 bước gợi mở'
        : `Bước ${current}/${SOCRATIC_STAGES.length} · ${SOCRATIC_STAGES[current - 1]}`;

  return (
    <div className="rounded-lg bg-blue-50/70 px-3 py-2.5" data-testid="socratic-progress">
      <div className="flex items-center justify-between gap-3 text-xs">
        <span className="font-semibold text-navy-800">{title}</span>
        <span className="hidden text-slate-500 md:inline">AI sẽ gợi ý từng bước, không đưa đáp án ngay</span>
      </div>
      <ol className="mt-2 grid grid-cols-5 gap-1.5" aria-label="Tiến trình gợi mở">
        {SOCRATIC_STAGES.map((name, index) => (
          <li key={name} aria-current={index + 1 === current ? 'step' : undefined}>
            <div className={clsx('h-1.5 rounded-full transition-colors', index < current ? 'bg-blue-600' : 'bg-blue-100')} />
            <span className={clsx('mt-1 hidden text-[10px] sm:block', index + 1 === current ? 'font-semibold text-blue-700' : 'text-slate-400')}>{name}</span>
          </li>
        ))}
      </ol>
    </div>
  );
}
