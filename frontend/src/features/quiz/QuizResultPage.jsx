import { useEffect, useMemo, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { CheckCircle2, CircleDashed, ClipboardX, Clock, Lightbulb, RotateCcw, Sparkles, XCircle } from 'lucide-react';
import clsx from 'clsx';
import Badge from '../../components/common/Badge';
import EmptyState from '../../components/common/EmptyState';
import Spinner from '../../components/common/Spinner';
import Breadcrumb from '../../components/layout/Breadcrumb';
import MarkdownViewer from '../../components/viewer/MarkdownViewer';
import { quizApi } from '../../api/quizApi';
import { loadResult } from './quizSession';
import { formatDurationText, formatScore, getOptionReviewState, getResultLevel, normalizeScore10 } from './quizUtils';

const LEVEL_STYLES = {
  green: { ring: 'border-emerald-500 text-emerald-600', badge: 'green' },
  blue: { ring: 'border-blue-500 text-blue-600', badge: 'blue' },
  red: { ring: 'border-red-500 text-red-600', badge: 'red' },
};

// Màu của phương án khi xem lại: xanh = đáp án đúng, đỏ = bạn chọn sai. Luôn kèm biểu tượng + nhãn chữ (không chỉ dựa vào màu).
const OPTION_STYLES = {
  'correct-selected': { box: 'border-2 border-emerald-500 bg-emerald-50', chip: 'bg-emerald-600 text-white', text: 'text-emerald-900', tag: 'Bạn chọn đúng', tagCls: 'text-emerald-700', Icon: CheckCircle2, iconCls: 'text-emerald-600' },
  correct: { box: 'border-2 border-emerald-500 bg-emerald-50', chip: 'bg-emerald-600 text-white', text: 'text-emerald-900', tag: 'Đáp án đúng', tagCls: 'text-emerald-700', Icon: CheckCircle2, iconCls: 'text-emerald-600' },
  'wrong-selected': { box: 'border-2 border-red-500 bg-red-50', chip: 'bg-red-600 text-white', text: 'text-red-900', tag: 'Bạn đã chọn', tagCls: 'text-red-700', Icon: XCircle, iconCls: 'text-red-600' },
  neutral: { box: 'border border-slate-200 bg-white', chip: 'bg-slate-100 text-slate-700', text: 'text-slate-700', tag: '', tagCls: '', Icon: null, iconCls: '' },
};

function StatTile({ icon: Icon, label, value, tone }) {
  const tones = { green: 'text-emerald-600 bg-emerald-50', red: 'text-red-600 bg-red-50', gray: 'text-slate-500 bg-slate-100', blue: 'text-blue-600 bg-blue-50' };
  return (
    <div className="flex items-center gap-3 rounded-xl border border-slate-200 bg-white p-3.5">
      <span className={clsx('flex h-10 w-10 shrink-0 items-center justify-center rounded-lg', tones[tone])}>
        <Icon size={20} aria-hidden="true" />
      </span>
      <div className="min-w-0">
        <p className="text-xl font-bold leading-tight text-navy-800">{value}</p>
        <p className="text-xs text-slate-500">{label}</p>
      </div>
    </div>
  );
}

function StatusBadge({ answer }) {
  if (answer.selected_option_id == null) return <Badge tone="gray">Bỏ trống</Badge>;
  return answer.is_correct ? <Badge tone="green">Đúng</Badge> : <Badge tone="red">Sai</Badge>;
}

function ReviewCard({ question, index, answer }) {
  const unanswered = answer.selected_option_id == null;
  return (
    <article
      aria-label={`Câu ${index + 1}`}
      className={clsx('rounded-xl border bg-white p-4 sm:p-6', answer.is_correct ? 'border-emerald-200' : unanswered ? 'border-slate-200' : 'border-red-200')}
    >
      <header className="flex items-center justify-between gap-3">
        <h3 className="text-sm font-semibold text-slate-500">Câu {index + 1}</h3>
        <StatusBadge answer={answer} />
      </header>

      <div className="mt-2 text-base font-semibold text-navy-800 [&_p]:my-0 [&_p]:text-base [&_p]:font-semibold [&_p]:text-navy-800">
        <MarkdownViewer source={question.content} variant="chat" />
      </div>

      <ul className="mt-4 space-y-2.5">
        {question.options.map((option) => {
          const state = getOptionReviewState(option, answer);
          const style = OPTION_STYLES[state];
          return (
            <li key={option.id} className={clsx('flex min-h-14 items-center gap-3 rounded-lg px-3 py-2.5 sm:px-4', style.box)}>
              <span aria-hidden="true" className={clsx('flex h-8 w-8 shrink-0 items-center justify-center rounded-md text-sm font-bold', style.chip)}>
                {option.opt_label}
              </span>
              <div className={clsx('min-w-0 flex-1 [&_p]:my-0', style.text, state !== 'neutral' && 'font-medium [&_p]:text-inherit')}>
                <MarkdownViewer source={option.content} variant="chat" />
              </div>
              {style.Icon && (
                <span className={clsx('flex shrink-0 items-center gap-1 text-xs font-semibold', style.tagCls)}>
                  <style.Icon size={20} aria-hidden="true" className={style.iconCls} />
                  <span className="hidden sm:inline">{style.tag}</span>
                  <span className="sr-only sm:hidden">{style.tag}</span>
                </span>
              )}
              {state === 'neutral' && <span className="sr-only">Phương án không được chọn</span>}
            </li>
          );
        })}
      </ul>

      {unanswered && (
        <p className="mt-3 flex items-center gap-2 text-sm text-slate-500">
          <CircleDashed size={16} aria-hidden="true" /> Bạn chưa trả lời câu này (tính là sai).
          {answer.correct_label && <> Đáp án đúng: <strong className="text-emerald-700">{answer.correct_label}</strong>.</>}
        </p>
      )}

      <div className="mt-4 rounded-lg border border-blue-100 bg-blue-50/70 p-3.5 sm:p-4">
        <p className="flex items-center gap-2 text-sm font-semibold text-blue-700">
          <Lightbulb size={16} aria-hidden="true" /> Giải thích
        </p>
        <div className="mt-1.5 text-slate-700">
          {answer.explanation ? <MarkdownViewer source={answer.explanation} variant="chat" /> : <p className="text-sm text-slate-500">Câu hỏi này chưa có lời giải thích.</p>}
        </div>
      </div>
    </article>
  );
}

const FILTERS = [
  { key: 'all', label: 'Tất cả' },
  { key: 'wrong', label: 'Câu sai' },
  { key: 'correct', label: 'Câu đúng' },
];

export default function QuizResultPage() {
  const { attemptId } = useParams();
  const localData = useMemo(() => loadResult(attemptId), [attemptId]);
  const [data, setData] = useState(localData);
  const [loading, setLoading] = useState(!localData);
  const [filter, setFilter] = useState('all');

  useEffect(() => {
    if (localData) {
      setData(localData);
      setLoading(false);
      return;
    }
    let isMounted = true;
    setLoading(true);
    quizApi
      .getAttempt(attemptId)
      .then((res) => {
        if (!isMounted) return;
        if (res?.quiz) {
          setData({
            quiz: res.quiz,
            result: res,
            topicId: res.topic_id,
            lessonId: res.lesson_id,
          });
        }
      })
      .catch(() => {
        // Lỗi hoặc không tìm thấy kết quả bài làm
      })
      .finally(() => {
        if (isMounted) setLoading(false);
      });
    return () => {
      isMounted = false;
    };
  }, [attemptId, localData]);

  if (loading) {
    return (
      <div className="flex justify-center py-28">
        <Spinner size={32} label="Đang tải kết quả bài làm" />
      </div>
    );
  }

  if (!data) {
    return (
      <div className="mx-auto max-w-xl px-4 py-16">
        <EmptyState
          icon={ClipboardX}
          title="Không tìm thấy kết quả bài làm"
          description="Lượt làm bài này không tồn tại hoặc bạn chưa hoàn thành. Hãy làm một bài trắc nghiệm mới để xem kết quả."
          action={
            <Link to="/courses" className="inline-flex h-11 items-center rounded-lg bg-navy-800 px-4 text-sm font-semibold text-white hover:bg-navy-900">
              Về danh mục môn học
            </Link>
          }
        />
      </div>
    );
  }

  const { quiz, result, topicId, lessonId } = data;
  const answerById = Object.fromEntries(result.answers.map((a) => [a.question_id, a]));
  const level = getResultLevel(result.score);
  const levelStyle = LEVEL_STYLES[level.tone];
  const items = quiz.questions
    .map((question, index) => ({ question, index, answer: answerById[question.id] }))
    .filter((item) => item.answer);
  const counts = { all: items.length, wrong: items.filter((i) => !i.answer.is_correct).length, correct: items.filter((i) => i.answer.is_correct).length };
  const visible = items.filter((i) => filter === 'all' || (filter === 'wrong' ? !i.answer.is_correct : i.answer.is_correct));
  const retakeTo = `/quiz/${topicId}${lessonId ? `?lesson=${lessonId}` : ''}`;

  return (
    <div className="mx-auto max-w-3xl px-4 pb-6 pt-5 sm:px-6 lg:pt-8">
      <Breadcrumb items={[{ label: 'Môn học', to: '/courses' }, { label: 'Kết quả bài kiểm tra' }]} />
      <h1 className="mt-1.5 text-xl font-bold leading-tight text-navy-800 sm:text-2xl">{quiz.title}</h1>

      {/* Tổng kết điểm */}
      <section aria-label="Tổng kết kết quả" className="mt-5 rounded-2xl border border-slate-200 bg-white p-4 sm:p-6">
        <div className="flex flex-col items-center gap-4 text-center sm:flex-row sm:text-left">
          <div
            role="img"
            aria-label={`Điểm ${formatScore(result.score)} trên 10`}
            className={clsx('flex h-28 w-28 shrink-0 flex-col items-center justify-center rounded-full border-[6px]', levelStyle.ring)}
          >
            <span className="text-3xl font-extrabold leading-none">{formatScore(result.score)}</span>
            <span className="mt-1 text-xs font-medium text-slate-500">/ 10 điểm</span>
          </div>
          <div className="min-w-0">
            <Badge tone={levelStyle.badge}>Mức {level.label}</Badge>
            <p className="mt-2 text-sm text-slate-600">{level.message}</p>
            <p className="mt-1 text-xs text-slate-500">
              Đúng {result.correct_count}/{result.total_questions} câu · Quy đổi {Math.round(normalizeScore10(result.score) * 10)}%
            </p>
          </div>
        </div>
        <div className="mt-5 grid grid-cols-2 gap-3 sm:grid-cols-4">
          <StatTile icon={CheckCircle2} tone="green" label="Câu đúng" value={result.correct_count} />
          <StatTile icon={XCircle} tone="red" label="Câu sai" value={result.wrong_count - result.unanswered_count} />
          <StatTile icon={CircleDashed} tone="gray" label="Bỏ trống" value={result.unanswered_count} />
          <StatTile icon={Clock} tone="blue" label="Thời gian" value={formatDurationText(result.duration_sec)} />
        </div>
        <div className="mt-5 flex flex-col gap-2 sm:flex-row">
          <Link to={retakeTo} className="inline-flex h-11 items-center justify-center gap-2 rounded-lg bg-navy-800 px-4 text-sm font-semibold text-white hover:bg-navy-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600 focus-visible:ring-offset-2">
            <RotateCcw size={18} aria-hidden="true" /> Làm bài mới
          </Link>
          {lessonId && (
            <Link to={`/tutor/${lessonId}`} className="inline-flex h-11 items-center justify-center gap-2 rounded-lg border border-slate-300 bg-white px-4 text-sm font-semibold text-navy-800 hover:bg-slate-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600 focus-visible:ring-offset-2">
              <Sparkles size={18} aria-hidden="true" /> Hỏi Gia sư AI về câu sai
            </Link>
          )}
          <Link to="/courses" className="inline-flex h-11 items-center justify-center rounded-lg px-4 text-sm font-semibold text-slate-600 hover:bg-slate-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600">
            Về danh mục môn học
          </Link>
        </div>
      </section>

      {/* Xem lại từng câu */}
      <section aria-label="Xem lại bài làm" className="mt-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 className="text-lg font-bold text-navy-800">Xem lại từng câu</h2>
          <div role="group" aria-label="Lọc câu hỏi" className="inline-flex rounded-lg bg-slate-100 p-1">
            {FILTERS.map(({ key, label }) => (
              <button
                key={key}
                type="button"
                aria-pressed={filter === key}
                onClick={() => setFilter(key)}
                className={clsx(
                  'rounded-md px-3 py-1.5 text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600',
                  filter === key ? 'bg-white text-navy-800 shadow-sm' : 'text-slate-500 hover:text-navy-800'
                )}
              >
                {label} ({counts[key]})
              </button>
            ))}
          </div>
        </div>

        <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-xs text-slate-500" aria-hidden="true">
          <span className="flex items-center gap-1.5"><span className="h-3 w-3 rounded-sm border-2 border-emerald-500 bg-emerald-50" /> Đáp án đúng</span>
          <span className="flex items-center gap-1.5"><span className="h-3 w-3 rounded-sm border-2 border-red-500 bg-red-50" /> Bạn chọn sai</span>
        </div>

        {visible.length === 0 ? (
          <p className="mt-4 rounded-xl border border-dashed border-slate-300 bg-white px-4 py-10 text-center text-sm text-slate-500">
            {filter === 'wrong' ? 'Tuyệt vời! Bạn không sai câu nào.' : 'Chưa có câu nào ở mục này.'}
          </p>
        ) : (
          <div className="mt-4 space-y-4">
            {visible.map(({ question, index, answer }) => (
              <ReviewCard key={question.id} question={question} index={index} answer={answer} />
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
