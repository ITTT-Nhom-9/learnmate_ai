import { Check } from 'lucide-react';
import clsx from 'clsx';

/** Dãy ô số câu hỏi: xanh navy + dấu ✓ = đã trả lời, xanh dương = đang xem, trắng = chưa trả lời. Bấm để nhảy tới câu. */
export default function QuestionNavigator({ questions, answers, currentIndex, onGo, disabled }) {
  return (
    <nav aria-label="Danh sách câu hỏi" className="thin-scroll -mx-1 overflow-x-auto px-1 py-1">
      <ol className="flex gap-2">
        {questions.map((q, index) => {
          const isCurrent = index === currentIndex;
          const answered = answers[q.id] != null;
          return (
            <li key={q.id}>
              <button
                type="button"
                disabled={disabled}
                onClick={() => onGo(index)}
                aria-current={isCurrent ? 'step' : undefined}
                aria-label={`Câu ${index + 1}, ${answered ? 'đã trả lời' : 'chưa trả lời'}`}
                className={clsx(
                  'flex h-9 w-9 items-center justify-center rounded-md border text-xs font-semibold transition-colors',
                  'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600 focus-visible:ring-offset-1 disabled:cursor-not-allowed',
                  isCurrent && 'border-blue-600 bg-blue-600 text-white',
                  !isCurrent && answered && 'border-navy-800 bg-navy-800 text-white',
                  !isCurrent && !answered && 'border-slate-300 bg-white text-slate-600 hover:border-blue-400'
                )}
              >
                {answered && !isCurrent ? <Check size={15} aria-hidden="true" /> : index + 1}
              </button>
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
