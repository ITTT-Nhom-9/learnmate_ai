import { Link } from 'react-router-dom';
import { BookOpen, Lightbulb, MessageSquare, MessagesSquare } from 'lucide-react';
import clsx from 'clsx';

/**
 * Cột trái: các bài học của môn. Mỗi bài học có một cuộc trò chuyện riêng (API-09 lưu lịch sử theo lessonId),
 * nên chọn bài học = chuyển sang cuộc trò chuyện của bài đó.
 */
export default function LessonListPanel({ course, lessons, activeLessonId, onSelect, mode, onTrySocratic }) {
  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="px-4 pt-4">
        <h2 className="flex items-center gap-2 text-lg font-bold text-navy-800">
          <MessagesSquare size={20} className="text-slate-500" aria-hidden="true" />
          Gia sư AI
        </h2>
        <Link
          to={`/courses/${course.id}/lessons/${activeLessonId}`}
          className="mt-4 flex h-11 w-full items-center justify-center gap-2 rounded-lg bg-navy-800 text-sm font-semibold text-white hover:bg-navy-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600 focus-visible:ring-offset-2"
        >
          <BookOpen size={16} aria-hidden="true" /> Xem nội dung bài học
        </Link>
        <p className="mt-5 text-[11px] font-semibold uppercase tracking-wide text-slate-500">Bài học trong môn {course.code}</p>
      </div>

      <ul className="thin-scroll mt-2 min-h-0 flex-1 space-y-1.5 overflow-y-auto px-4 pb-3">
        {lessons.map((lesson) => {
          const active = lesson.id === activeLessonId;
          return (
            <li key={lesson.id}>
              <button
                type="button"
                onClick={() => onSelect(lesson)}
                aria-current={active ? 'true' : undefined}
                className={clsx(
                  'flex w-full items-start gap-2.5 rounded-lg border px-3 py-2.5 text-left transition-colors',
                  'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600',
                  active ? 'border-blue-200 bg-blue-50 text-blue-600' : 'border-transparent text-slate-700 hover:bg-slate-50'
                )}
              >
                <MessageSquare size={16} className={clsx('mt-0.5 shrink-0', active ? 'text-blue-600' : 'text-slate-400')} aria-hidden="true" />
                <span className="min-w-0 flex-1">
                  <span className="line-clamp-2 text-sm font-medium leading-snug">{lesson.title}</span>
                  <span className={clsx('mt-0.5 block text-xs', active ? 'text-blue-500' : 'text-slate-400')}>Bài {lesson.order_index}</span>
                </span>
              </button>
            </li>
          );
        })}
      </ul>

      <div className="m-4 rounded-xl bg-slate-50 p-4">
        <Lightbulb size={18} className="text-slate-400" aria-hidden="true" />
        <p className="mt-2 text-sm font-semibold text-navy-800">Học sâu, không chỉ tìm đáp án</p>
        <p className="mt-1 text-xs leading-relaxed text-slate-500">Thử chế độ Socratic để tự khám phá lời giải qua từng gợi ý.</p>
        {mode !== 'SOCRATIC' && (
          <button
            type="button"
            onClick={onTrySocratic}
            className="mt-2.5 rounded text-xs font-semibold text-blue-600 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600"
          >
            Bật chế độ Socratic →
          </button>
        )}
      </div>
    </div>
  );
}
