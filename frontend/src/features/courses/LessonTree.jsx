import { Circle, CircleDot, CheckCircle2, ChevronDown, ChevronRight, Lightbulb } from 'lucide-react';
import clsx from 'clsx';
import ProgressBar from '../../components/common/ProgressBar';
import { formatPercent } from '../../utils/formatters';
import { MASTERY_DONE_THRESHOLD, getLessonState, getTopicState } from './courseUtils';

const STATE_ICON = {
  done: { Icon: CheckCircle2, className: 'text-emerald-500', label: 'Đã hoàn thành' },
  progress: { Icon: CircleDot, className: 'text-blue-600', label: 'Đang học' },
  todo: { Icon: Circle, className: 'text-slate-300', label: 'Chưa học' },
};

function StateIcon({ state, size = 18 }) {
  const { Icon, className, label } = STATE_ICON[state];
  return <Icon size={size} className={clsx('shrink-0', className)} aria-label={label} role="img" />;
}

/** Cây bài học (Môn học > Bài học > Chủ đề) hiển thị trong Sidebar của SCR-03. */
export default function LessonTree({
  course,
  lessons,
  progress,
  activeLessonId,
  activeTopicId,
  expandedIds,
  onToggleLesson,
  onSelectLesson,
  onSelectTopic,
}) {
  return (
    <div className="p-5">
      <p className="text-xs font-semibold uppercase tracking-wide text-blue-600">{course.code} · Nội dung khóa học</p>
      <h2 className="mt-2 text-lg font-bold leading-snug text-navy-800">{course.title}</h2>

      <div className="mt-3 flex items-center justify-between text-xs text-slate-500">
        <span>
          {progress.done} / {progress.total} bài đã học
        </span>
        <span className="font-semibold text-blue-600">{formatPercent(progress.pct)}</span>
      </div>
      <ProgressBar value={progress.pct} label="Tiến độ môn học" className="mt-2" />

      <ul className="mt-5 space-y-1 border-t border-slate-100 pt-4">
        {lessons.map((lesson) => {
          const topics = lesson.topics || [];
          const isActive = lesson.id === activeLessonId;
          const isOpen = expandedIds.has(lesson.id);
          const panelId = `lesson-topics-${lesson.id}`;

          return (
            <li key={lesson.id}>
              <div className="flex items-start gap-1">
                <button
                  type="button"
                  onClick={() => onSelectLesson(lesson)}
                  aria-current={isActive ? 'true' : undefined}
                  className={clsx(
                    'flex min-w-0 flex-1 items-start gap-2.5 rounded-lg px-2.5 py-2 text-left text-sm',
                    'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600',
                    isActive ? 'font-semibold text-navy-800' : 'font-medium text-slate-600 hover:bg-slate-50'
                  )}
                >
                  <span className="mt-0.5">
                    <StateIcon state={getLessonState(lesson)} />
                  </span>
                  <span className="min-w-0 flex-1 leading-snug">{lesson.title}</span>
                </button>
                {topics.length > 0 && (
                  <button
                    type="button"
                    onClick={() => onToggleLesson(lesson.id)}
                    aria-expanded={isOpen}
                    aria-controls={panelId}
                    aria-label={`${isOpen ? 'Thu gọn' : 'Mở rộng'} các chủ đề của ${lesson.title}`}
                    className="mt-1.5 rounded p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-600 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600"
                  >
                    {isOpen ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
                  </button>
                )}
              </div>

              {isOpen && topics.length > 0 && (
                <ul id={panelId} className="mb-1 ml-5 mt-0.5 space-y-0.5 border-l border-slate-100 pl-2">
                  {topics.map((topic) => {
                    const topicActive = isActive && topic.id === activeTopicId;
                    return (
                      <li key={topic.id}>
                        <button
                          type="button"
                          onClick={() => onSelectTopic(lesson, topic)}
                          aria-current={topicActive ? 'true' : undefined}
                          className={clsx(
                            'flex w-full items-start gap-2.5 rounded-lg px-2.5 py-2 text-left text-[13px] leading-snug',
                            'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600',
                            topicActive ? 'bg-blue-50 font-semibold text-blue-600' : 'text-slate-600 hover:bg-slate-50'
                          )}
                        >
                          <span className="mt-0.5">
                            <StateIcon state={getTopicState(topic)} size={16} />
                          </span>
                          <span className="min-w-0 flex-1">{topic.name}</span>
                        </button>
                      </li>
                    );
                  })}
                </ul>
              )}
            </li>
          );
        })}
      </ul>

      <div className="mt-5 flex items-start gap-2.5 rounded-lg bg-slate-50 px-3.5 py-3 text-xs leading-relaxed text-slate-500">
        <Lightbulb size={16} className="mt-0.5 shrink-0 text-slate-400" aria-hidden="true" />
        Chủ đề đạt điểm thành thạo từ {MASTERY_DONE_THRESHOLD}% trở lên được tính là đã hoàn thành.
      </div>
    </div>
  );
}
