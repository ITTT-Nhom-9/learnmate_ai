import { useMemo, useState, useEffect } from 'react';
import {
  Circle,
  CircleDot,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Lightbulb,
  Lock,
} from 'lucide-react';
import clsx from 'clsx';
import ProgressBar from '../../components/common/ProgressBar';
import { formatPercent } from '../../utils/formatters';
import {
  MASTERY_DONE_THRESHOLD,
  computeLockStates,
  getLessonState,
  getTopicState,
  groupLessonsIntoModules,
} from './courseUtils';

const STATE_ICON = {
  done: { Icon: CheckCircle2, className: 'text-emerald-500', label: 'Đã hoàn thành' },
  progress: { Icon: CircleDot, className: 'text-blue-600', label: 'Đang học' },
  todo: { Icon: Circle, className: 'text-slate-300', label: 'Chưa học' },
  locked: { Icon: Lock, className: 'text-slate-400', label: 'Chưa mở khóa' },
};

function StateIcon({ state, size = 18 }) {
  const item = STATE_ICON[state] || STATE_ICON.todo;
  const { Icon, className, label } = item;
  return <Icon size={size} className={clsx('shrink-0', className)} aria-label={label} role="img" />;
}

/**
 * Cây bài học (SCR-04): Môn học > Module (Chương) > Bài học > Chủ đề.
 * Hỗ trợ:
 * - Phân cấp Module (Chương) chuẩn theo bản vẽ SCR-04.
 * - Cơ chế Khóa tuần tự: Chủ đề/bài học tiếp theo chỉ mở khi chủ đề trước đó đạt Mastery >= 60%.
 */
export default function LessonTree({
  course,
  lessons = [],
  progress,
  activeLessonId,
  activeTopicId,
  expandedIds,
  onToggleLesson,
  onSelectLesson,
  onSelectTopic,
}) {
  const modules = useMemo(() => groupLessonsIntoModules(lessons, course), [lessons, course]);
  const { lockedTopicIds, lockedLessonIds } = useMemo(() => computeLockStates(lessons), [lessons]);

  // Quản lý mở rộng các Module (mặc định mở Module chứa bài học đang chọn)
  const [expandedModuleIds, setExpandedModuleIds] = useState(() => new Set());

  useEffect(() => {
    if (!activeLessonId || modules.length === 0) return;
    const currentMod = modules.find((m) => m.lessons.some((l) => l.id === activeLessonId));
    if (currentMod) {
      setExpandedModuleIds((prev) => new Set(prev).add(currentMod.id));
    } else if (modules[0]) {
      setExpandedModuleIds((prev) => new Set(prev).add(modules[0].id));
    }
  }, [activeLessonId, modules]);

  const toggleModule = (modId) => {
    setExpandedModuleIds((prev) => {
      const next = new Set(prev);
      if (next.has(modId)) {
        next.delete(modId);
      } else {
        next.add(modId);
      }
      return next;
    });
  };

  return (
    <div className="p-4 sm:p-5">
      <p className="text-xs font-semibold uppercase tracking-wide text-blue-600">
        {course.code} · Nội dung khóa học
      </p>
      <h2 className="mt-1.5 text-lg font-bold leading-snug text-navy-800">{course.title}</h2>

      <div className="mt-3 flex items-center justify-between text-xs text-slate-500">
        <span>
          Đã học {progress.learned || 0}/{progress.total} bài
          {progress.totalTopics > 0 ? ` (${progress.doneTopics}/${progress.totalTopics} chủ đề vững)` : ''}
        </span>
        <span className="font-semibold text-blue-600" title="Điểm thành thạo tích lũy toàn môn">
          {formatPercent(progress.pct)}
        </span>
      </div>
      <ProgressBar value={progress.pct} label="Độ thành thạo môn học" className="mt-2" />

      {/* Danh sách phân cấp Module (Chương) theo SCR-04 */}
      <div className="mt-5 space-y-3 border-t border-slate-100 pt-4">
        {modules.map((mod) => {
          const isModOpen = expandedModuleIds.has(mod.id);
          const isModLocked = mod.lessons.every((l) => lockedLessonIds.has(l.id));

          return (
            <div key={mod.id} className="rounded-lg border border-slate-100 bg-slate-50/50 p-1.5">
              {/* Tiêu đề Module (Chương) */}
              <button
                type="button"
                onClick={() => toggleModule(mod.id)}
                className="flex w-full items-center justify-between rounded-md px-2 py-1.5 text-left text-xs font-bold uppercase tracking-wider text-slate-600 transition hover:bg-slate-100 hover:text-navy-800"
              >
                <span className="flex items-center gap-1.5 truncate">
                  {isModOpen ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                  <span className="truncate">{mod.title}</span>
                </span>
                {isModLocked && (
                  <Lock size={13} className="shrink-0 text-slate-400" aria-label="Chương bị khóa" />
                )}
              </button>

              {/* Danh sách bài học trong Module */}
              {isModOpen && (
                <ul className="mt-1 space-y-1 pl-1">
                  {mod.lessons.map((lesson) => {
                    const topics = lesson.topics || [];
                    const isLessonLocked = lockedLessonIds.has(lesson.id);
                    const isActive = lesson.id === activeLessonId;
                    const isOpen = expandedIds.has(lesson.id);
                    const panelId = `lesson-topics-${lesson.id}`;
                    const lessonState = getLessonState(lesson, isLessonLocked);

                    return (
                      <li key={lesson.id}>
                        <div className="flex items-start gap-1">
                          <button
                            type="button"
                            onClick={() => !isLessonLocked && onSelectLesson(lesson)}
                            disabled={isLessonLocked}
                            aria-current={isActive ? 'true' : undefined}
                            title={isLessonLocked ? 'Vui lòng hoàn thành bài học trước để mở khóa' : lesson.title}
                            className={clsx(
                              'flex min-w-0 flex-1 items-start gap-2.5 rounded-lg px-2.5 py-2 text-left text-sm transition',
                              'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600',
                              isLessonLocked
                                ? 'cursor-not-allowed text-slate-400'
                                : isActive
                                  ? 'bg-blue-50/60 font-semibold text-navy-800'
                                  : 'font-medium text-slate-600 hover:bg-slate-100/70'
                            )}
                          >
                            <span className="mt-0.5">
                              <StateIcon state={lessonState} />
                            </span>
                            <span className="min-w-0 flex-1 leading-snug">{lesson.title}</span>
                          </button>

                          {topics.length > 0 && !isLessonLocked && (
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

                        {/* Danh sách chủ đề của bài học (SCR-04) */}
                        {isOpen && topics.length > 0 && !isLessonLocked && (
                          <ul
                            id={panelId}
                            className="mb-1 ml-5 mt-0.5 space-y-0.5 border-l border-slate-200 pl-2"
                          >
                            {topics.map((topic) => {
                              const isTopicLocked = lockedTopicIds.has(topic.id);
                              const topicActive = isActive && topic.id === activeTopicId;
                              const topicState = getTopicState(topic, isTopicLocked);

                              return (
                                <li key={topic.id}>
                                  <button
                                    type="button"
                                    onClick={() => !isTopicLocked && onSelectTopic(lesson, topic)}
                                    disabled={isTopicLocked}
                                    aria-current={topicActive ? 'true' : undefined}
                                    title={
                                      isTopicLocked
                                        ? 'Vui lòng hoàn thành chủ đề trước để mở khóa'
                                        : topic.name
                                    }
                                    className={clsx(
                                      'flex w-full items-start gap-2.5 rounded-lg px-2.5 py-1.5 text-left text-[13px] leading-snug transition',
                                      'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600',
                                      isTopicLocked
                                        ? 'cursor-not-allowed text-slate-400'
                                        : topicActive
                                          ? 'bg-blue-100/70 font-semibold text-blue-700'
                                          : 'text-slate-600 hover:bg-slate-100'
                                    )}
                                  >
                                    <span className="mt-0.5">
                                      <StateIcon state={topicState} size={15} />
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
              )}
            </div>
          );
        })}
      </div>

      {/* Ghi chú chân trang đúng chuẩn SCR-04 */}
      <div className="mt-5 flex items-start gap-2.5 rounded-lg border border-slate-200 bg-white px-3.5 py-3 text-xs leading-relaxed text-slate-600 shadow-sm">
        <Lightbulb size={16} className="mt-0.5 shrink-0 text-amber-500" aria-hidden="true" />
        <span>Làm bài Quiz để mở khóa chủ đề tiếp theo. Đạt từ 60% điểm để hoàn thành.</span>
      </div>
    </div>
  );
}
