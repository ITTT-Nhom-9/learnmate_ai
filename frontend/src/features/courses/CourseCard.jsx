import { Link } from 'react-router-dom';
import clsx from 'clsx';
import Badge from '../../components/common/Badge';
import Button from '../../components/common/Button';
import ProgressBar from '../../components/common/ProgressBar';
import { formatPercent } from '../../utils/formatters';
import { COURSE_STATUS, getCourseIcon, getCourseStatus, getLearnedLessons } from './courseUtils';

const BAR_TONE = { IN_PROGRESS: 'blue', COMPLETED: 'green', NOT_STARTED: 'gray' };
const PCT_COLOR = { IN_PROGRESS: 'text-blue-600', COMPLETED: 'text-emerald-600', NOT_STARTED: 'text-blue-600' };

export default function CourseCard({ course, layout = 'grid', busy = false, onAction }) {
  const status = getCourseStatus(course);
  const meta = COURSE_STATUS[status];
  const Icon = getCourseIcon(course);
  const isList = layout === 'list';

  return (
    <article
      className={clsx(
        'rounded-xl border border-slate-200 bg-white p-5 transition-shadow hover:shadow-md',
        isList ? 'flex flex-col gap-4 md:flex-row md:items-center md:gap-6' : 'flex flex-col'
      )}
    >
      <div className={clsx(isList && 'md:w-64 md:shrink-0')}>
        <div className="flex items-center justify-between gap-2">
          <span className="flex items-center gap-2 text-sm font-semibold text-slate-600">
            <Icon size={18} className="text-slate-500" aria-hidden="true" />
            {course.code}
          </span>
          <Badge tone={meta.tone}>{meta.label}</Badge>
        </div>
        <h3 className={clsx('mt-5 text-lg font-bold leading-snug text-navy-800', !isList && 'min-h-[3.5rem]')}>
          <Link to={`/courses/${course.id}`} className="rounded hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600">
            {course.title}
          </Link>
        </h3>
      </div>

      <div className={clsx(isList ? 'md:flex-1' : 'mt-4')}>
        <div className="flex items-center justify-between text-xs text-slate-500">
          <span>
            {course.total_lessons} bài · {getLearnedLessons(course)} bài đã học
          </span>
          <span className={clsx('font-semibold', PCT_COLOR[status])}>{formatPercent(course.progress_pct)}</span>
        </div>
        <ProgressBar value={course.progress_pct} tone={BAR_TONE[status]} label={`Tiến độ ${course.title}`} className="mt-2" />
      </div>

      <Button
        variant="outline"
        loading={busy}
        onClick={() => onAction(course)}
        className={clsx('w-full', isList ? 'md:w-44 md:shrink-0' : 'mt-5')}
      >
        {meta.action}
      </Button>
    </article>
  );
}

export function CourseCardSkeleton({ layout = 'grid' }) {
  return (
    <div
      aria-hidden="true"
      className={clsx('animate-pulse rounded-xl border border-slate-200 bg-white p-5', layout === 'list' && 'md:flex md:items-center md:gap-6')}
    >
      <div className="md:w-64">
        <div className="h-4 w-24 rounded bg-slate-200" />
        <div className="mt-5 h-6 w-3/4 rounded bg-slate-200" />
      </div>
      <div className="mt-6 md:mt-0 md:flex-1">
        <div className="h-3 w-full rounded bg-slate-200" />
        <div className="mt-3 h-1.5 w-full rounded bg-slate-200" />
      </div>
      <div className="mt-5 h-11 rounded-lg bg-slate-200 md:mt-0 md:w-44" />
    </div>
  );
}
