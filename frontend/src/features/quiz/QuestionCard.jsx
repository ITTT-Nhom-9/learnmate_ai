import clsx from 'clsx';
import MarkdownViewer from '../../components/viewer/MarkdownViewer';

/**
 * Khung câu hỏi SCR-05. Dùng radio gốc của trình duyệt (ẩn bằng sr-only) nên bàn phím/trình đọc màn hình hoạt động đúng:
 * Tab vào nhóm, phím mũi tên đổi phương án. Mỗi phương án cao tối thiểu 56px để chống bấm nhầm trên điện thoại.
 * Nội dung do AI sinh ra nên hiển thị bằng MarkdownViewer biến thể "chat" (hỗ trợ KaTeX/code, chặn ảnh ngoài).
 */
export default function QuestionCard({ question, index, total, selectedOptionId, onSelect, disabled }) {
  const groupName = `question-${question.id}`;
  return (
    <fieldset disabled={disabled} className="min-w-0 rounded-xl border border-slate-200 bg-white p-4 sm:p-7">
      <legend className="sr-only">
        Câu {index + 1} trên {total}
      </legend>
      <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">Chọn một đáp án đúng</p>
      <div className="mt-2 text-lg font-semibold leading-snug text-navy-800 [&_p]:my-0 [&_p]:text-lg [&_p]:font-semibold [&_p]:text-navy-800">
        <MarkdownViewer source={question.content} variant="chat" />
      </div>

      <div className="mt-5 space-y-3">
        {question.options.map((option) => {
          const checked = selectedOptionId === option.id;
          return (
            <label
              key={option.id}
              className={clsx(
                'flex min-h-14 cursor-pointer items-center gap-3 rounded-lg border px-3 py-2.5 transition-colors sm:px-4 lg:min-h-[60px]',
                'focus-within:ring-2 focus-within:ring-blue-600 focus-within:ring-offset-1',
                checked ? 'border-2 border-blue-600 bg-blue-50' : 'border-slate-200 bg-white hover:border-blue-300 hover:bg-slate-50',
                disabled && 'cursor-not-allowed opacity-70'
              )}
            >
              <input
                type="radio"
                name={groupName}
                value={option.id}
                checked={checked}
                onChange={() => onSelect(question.id, option.id)}
                className="sr-only"
              />
              <span
                aria-hidden="true"
                className={clsx(
                  'flex h-8 w-8 shrink-0 items-center justify-center rounded-md text-sm font-bold',
                  checked ? 'bg-blue-600 text-white' : 'bg-slate-100 text-slate-700'
                )}
              >
                {option.opt_label}
              </span>
              <span className={clsx('min-w-0 flex-1 [&_p]:my-0', checked ? 'font-medium text-blue-700 [&_p]:text-blue-700' : 'text-slate-700')}>
                <MarkdownViewer source={option.content} variant="chat" />
              </span>
              <span
                aria-hidden="true"
                className={clsx(
                  'flex h-5 w-5 shrink-0 items-center justify-center rounded-full border',
                  checked ? 'border-blue-600' : 'border-slate-300'
                )}
              >
                {checked && <span className="h-2.5 w-2.5 rounded-full bg-blue-600" />}
              </span>
            </label>
          );
        })}
      </div>
    </fieldset>
  );
}
