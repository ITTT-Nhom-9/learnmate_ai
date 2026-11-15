import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { ArrowLeft, ArrowRight, BookX, Send, ShieldCheck, SlidersHorizontal, TimerOff } from 'lucide-react';
import clsx from 'clsx';
import { quizApi } from '../../api/quizApi';
import AlertBox from '../../components/common/AlertBox';
import Badge from '../../components/common/Badge';
import Button from '../../components/common/Button';
import EmptyState from '../../components/common/EmptyState';
import ProgressBar from '../../components/common/ProgressBar';
import Spinner from '../../components/common/Spinner';
import Breadcrumb from '../../components/layout/Breadcrumb';
import { useQuizTimer } from '../../hooks/useQuizTimer';
import { getErrorMessage } from '../../utils/apiError';
import QuestionCard from './QuestionCard';
import QuestionNavigator from './QuestionNavigator';
import QuizDialog from './QuizDialog';
import QuizTimer from './QuizTimer';
import { clearSession, loadSession, saveResult, saveSession } from './quizSession';
import { DIFFICULTY_LABELS, buildSubmitPayload, countAnswered, formatClock, getTimeLimitSec } from './quizUtils';

const DEFAULT_QUESTIONS = 5;
const DIFFICULTY_TONE = { EASY: 'green', MEDIUM: 'blue', HARD: 'gray' };

// React.StrictMode chạy effect 2 lần ở môi trường dev -> dùng chung 1 lời gọi đang bay để không sinh 2 đề (tốn token AI).
const inflightGenerate = new Map();
function requestQuiz(key, params) {
  if (!inflightGenerate.has(key)) {
    const promise = quizApi.generate(params).finally(() => inflightGenerate.delete(key));
    inflightGenerate.set(key, promise);
  }
  return inflightGenerate.get(key);
}

function LoadingView() {
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-28 text-center text-slate-500" role="status">
      <Spinner size={32} label="Đang tạo đề trắc nghiệm" />
      <p className="text-sm font-medium text-navy-800">Gia sư AI đang soạn đề cho bạn…</p>
      <p className="max-w-xs text-xs">Việc này có thể mất vài giây. Đồng hồ chỉ bắt đầu chạy khi đề hiển thị.</p>
    </div>
  );
}

export default function QuizTakePage() {
  const { topicId } = useParams();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const lessonId = searchParams.get('lesson');
  const requestedDifficulty = (searchParams.get('difficulty') || '').toUpperCase();
  const difficulty = DIFFICULTY_LABELS[requestedDifficulty] ? requestedDifficulty : 'MEDIUM';

  // session: { topicId, lessonId, quiz, answers: {questionId: optionId}, currentIndex, startedAt, deadline, timeLimitSec }
  const [session, setSession] = useState(null);
  const [loadError, setLoadError] = useState('');
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [submitState, setSubmitState] = useState({ status: 'idle', auto: false, message: '', code: null });
  const [reloadKey, setReloadKey] = useState(0);
  const sessionRef = useRef(null);
  const submittingRef = useRef(false);

  // ---------- Nạp phiên làm bài: khôi phục phiên đang dở hoặc sinh đề mới ----------
  useEffect(() => {
    let cancelled = false;
    submittingRef.current = false;
    setSubmitState({ status: 'idle', auto: false, message: '', code: null });
    setConfirmOpen(false);
    setLoadError('');

    const existing = loadSession(topicId);
    if (existing) {
      sessionRef.current = existing;
      setSession(existing);
      return undefined;
    }

    sessionRef.current = null;
    setSession(null);
    requestQuiz(`${topicId}:${lessonId}:${difficulty}`, { topicId, lessonId, numQuestions: DEFAULT_QUESTIONS, difficulty })
      .then((quiz) => {
        if (cancelled) return;
        const now = Date.now();
        const timeLimitSec = getTimeLimitSec(quiz.questions?.length);
        const fresh = { topicId, lessonId, quiz, answers: {}, currentIndex: 0, startedAt: now, timeLimitSec, deadline: now + timeLimitSec * 1000 };
        saveSession(topicId, fresh);
        sessionRef.current = fresh;
        setSession(fresh);
      })
      .catch((error) => {
        if (!cancelled) setLoadError(getErrorMessage(error, 'Không tạo được đề trắc nghiệm, vui lòng thử lại'));
      });
    return () => {
      cancelled = true;
    };
  }, [topicId, lessonId, difficulty, reloadKey]);

  const updateSession = useCallback(
    (patch) => {
      const next = { ...sessionRef.current, ...patch };
      sessionRef.current = next;
      setSession(next);
      saveSession(topicId, next);
    },
    [topicId]
  );

  // ---------- Nộp bài (thủ công hoặc tự động khi hết giờ) ----------
  const submit = useCallback(
    async ({ auto = false } = {}) => {
      const current = sessionRef.current;
      if (!current || submittingRef.current) return; // chống bấm đúp / hết giờ trùng lúc đang nộp
      submittingRef.current = true;
      setConfirmOpen(false);
      setSubmitState({ status: 'submitting', auto, message: '', code: null });

      const elapsed = Math.round((Date.now() - current.startedAt) / 1000);
      const durationSec = Math.min(current.timeLimitSec, Math.max(0, elapsed)); // không báo quá thời gian cho phép
      try {
        const result = await quizApi.submit(buildSubmitPayload({ quiz: current.quiz, answers: current.answers, durationSec }));
        saveResult(result.attempt_id, { quiz: current.quiz, result, topicId: current.topicId, lessonId: current.lessonId, difficulty: current.quiz.difficulty });
        clearSession(topicId);
        navigate(`/quiz/${result.attempt_id}/result`, { replace: true });
      } catch (error) {
        submittingRef.current = false;
        setSubmitState({ status: 'error', auto, message: getErrorMessage(error, 'Không nộp được bài, vui lòng thử lại'), code: error.response?.status ?? null });
      }
    },
    [navigate, topicId]
  );

  const handleExpire = useCallback(() => submit({ auto: true }), [submit]);
  const { remainingSec, isExpired } = useQuizTimer({
    deadline: session?.deadline ?? null,
    onExpire: handleExpire,
    paused: submitState.status === 'submitting',
  });

  // Cảnh báo khi đóng/tải lại tab giữa chừng (phiên vẫn được khôi phục, nhưng đồng hồ vẫn chạy trong lúc vắng mặt)
  const inProgress = Boolean(session) && submitState.status !== 'submitting';
  useEffect(() => {
    if (!inProgress) return undefined;
    const warn = (event) => {
      event.preventDefault();
      event.returnValue = '';
    };
    window.addEventListener('beforeunload', warn);
    return () => window.removeEventListener('beforeunload', warn);
  }, [inProgress]);

  // ---------- Dữ liệu dẫn xuất ----------
  const quiz = session?.quiz;
  const questions = useMemo(() => quiz?.questions ?? [], [quiz]);
  const answers = session?.answers ?? {};
  const answeredCount = countAnswered(questions, answers);
  const unansweredCount = questions.length - answeredCount;
  const currentIndex = Math.min(session?.currentIndex ?? 0, Math.max(0, questions.length - 1));
  const current = questions[currentIndex];
  const locked = submitState.status !== 'idle' || isExpired; // hết giờ hoặc đang nộp -> khóa không cho đổi đáp án

  const selectOption = (questionId, optionId) => updateSession({ answers: { ...sessionRef.current.answers, [questionId]: optionId } });
  const goTo = (index) => updateSession({ currentIndex: Math.min(Math.max(0, index), questions.length - 1) });

  // Thông báo cho trình đọc màn hình ở các mốc quan trọng (không đọc từng giây)
  const announcement = { 300: 'Còn 5 phút', 60: 'Còn 1 phút', 30: 'Còn 30 giây', 10: 'Còn 10 giây' }[remainingSec] ?? '';

  // ---------- Hiển thị theo trạng thái ----------
  if (loadError) {
    return (
      <div className="mx-auto max-w-xl px-4 py-16">
        <EmptyState
          icon={BookX}
          title="Không tạo được đề trắc nghiệm"
          description={loadError}
          action={
            <div className="flex flex-wrap justify-center gap-2">
              <Button onClick={() => setReloadKey((k) => k + 1)}>Thử lại</Button>
              <Link to="/courses" className="inline-flex h-11 items-center rounded-lg border border-slate-300 bg-white px-4 text-sm font-semibold text-navy-800 hover:bg-slate-50">
                Về danh mục môn học
              </Link>
            </div>
          }
        />
      </div>
    );
  }
  if (!session || !current) return <LoadingView />;

  const isLast = currentIndex === questions.length - 1;
  const difficultyKey = (quiz.difficulty || 'MEDIUM').toUpperCase();
  const progressPct = (answeredCount / questions.length) * 100;

  return (
    <div className="pb-28 lg:pb-0">
      {/* Mobile: thanh dính dưới Header gồm đồng hồ + tiến độ câu hỏi */}
      <div className="sticky top-16 z-30 border-b border-slate-200 bg-white/95 px-4 py-2.5 backdrop-blur lg:hidden">
        <div className="flex items-center justify-between">
          <QuizTimer remainingSec={remainingSec} variant="inline" />
          <p className="text-sm font-semibold text-navy-800">
            Câu {currentIndex + 1}/{questions.length}
          </p>
        </div>
        <ProgressBar value={progressPct} tone="green" label={`Đã trả lời ${answeredCount} trên ${questions.length} câu`} className="mt-2" />
      </div>

      <div className="mx-auto max-w-5xl px-4 pt-5 sm:px-6 lg:px-8 lg:pt-6">
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0">
            <Breadcrumb items={[{ label: 'Môn học', to: '/courses' }, { label: 'Bài kiểm tra thích ứng' }]} />
            <h1 className="mt-1.5 text-xl font-bold leading-tight text-navy-800 sm:text-2xl lg:text-[28px]">{quiz.title}</h1>
          </div>
          <div className="hidden shrink-0 lg:block">
            <QuizTimer remainingSec={remainingSec} />
          </div>
        </div>

        <div className="mx-auto mt-6 max-w-3xl">
          <div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-2">
            <div className="hidden lg:block">
              <p className="text-sm font-semibold text-navy-800">
                Câu {currentIndex + 1} / {questions.length}
              </p>
            </div>
            <p className="flex items-center gap-2 text-xs text-slate-500 lg:ml-auto">
              <SlidersHorizontal size={14} aria-hidden="true" />
              Độ khó thích ứng
              <Badge tone={DIFFICULTY_TONE[difficultyKey] || 'blue'}>{difficultyKey}</Badge>
            </p>
          </div>
          <div className="mt-2">
            <QuestionNavigator questions={questions} answers={answers} currentIndex={currentIndex} onGo={goTo} disabled={locked} />
          </div>

          <div className="mt-4">
            <QuestionCard
              key={current.id}
              question={current}
              index={currentIndex}
              total={questions.length}
              selectedOptionId={answers[current.id] ?? null}
              onSelect={selectOption}
              disabled={locked}
            />
          </div>

          {/* Thanh thao tác: cố định ở đáy trên mobile (nút Nộp bài đỏ nổi bật), nằm dưới khung câu hỏi trên desktop */}
          <div
            className={clsx(
              'fixed inset-x-0 bottom-0 z-40 border-t border-slate-200 bg-white px-4 pb-[calc(0.75rem+env(safe-area-inset-bottom))] pt-3',
              'lg:static lg:z-auto lg:mt-5 lg:border-0 lg:bg-transparent lg:p-0'
            )}
          >
            <div className="mx-auto flex max-w-3xl items-center gap-2 lg:justify-between">
              <Button variant="outline" size="lg" icon={ArrowLeft} disabled={currentIndex === 0 || locked} onClick={() => goTo(currentIndex - 1)}>
                <span className="sr-only sm:not-sr-only">Câu trước</span>
              </Button>
              <div className="flex flex-1 gap-2 lg:flex-none">
                {!isLast && (
                  <Button size="lg" icon={ArrowRight} disabled={locked} onClick={() => goTo(currentIndex + 1)} className="flex-1 lg:flex-none">
                    Câu tiếp theo
                  </Button>
                )}
                <Button variant="danger" size="lg" icon={Send} disabled={locked} onClick={() => setConfirmOpen(true)} className="flex-1 lg:flex-none">
                  Nộp bài
                </Button>
              </div>
            </div>
          </div>

          <p className="mt-4 flex items-center gap-2 text-xs text-slate-500">
            <ShieldCheck size={14} className="shrink-0" aria-hidden="true" />
            Câu trả lời được lưu tự động. Độ khó sẽ điều chỉnh theo kết quả của bạn.
          </p>
        </div>
      </div>

      <p className="sr-only" aria-live="polite">
        {announcement}
      </p>

      {/* Xác nhận nộp bài thủ công */}
      <QuizDialog open={confirmOpen} title="Xác nhận nộp bài" onClose={() => setConfirmOpen(false)}>
        <h2 className="text-lg font-bold text-navy-800">Nộp bài ngay?</h2>
        <p className="mt-2 text-sm text-slate-600">
          Bạn đã trả lời <strong>{answeredCount}/{questions.length}</strong> câu.
          {unansweredCount > 0 && (
            <>
              {' '}
              Còn <strong className="text-red-600">{unansweredCount} câu chưa trả lời</strong> sẽ bị tính là sai.
            </>
          )}{' '}
          Thời gian còn lại {formatClock(remainingSec)}. Sau khi nộp bạn không thể sửa bài.
        </p>
        <div className="mt-5 flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
          <Button variant="outline" onClick={() => setConfirmOpen(false)}>
            Tiếp tục làm bài
          </Button>
          <Button variant="danger" icon={Send} onClick={() => submit()}>
            Nộp bài
          </Button>
        </div>
      </QuizDialog>

      {/* Đang nộp / hết giờ tự nộp / lỗi nộp bài: không đóng được để tránh thao tác dở dang */}
      <QuizDialog open={submitState.status !== 'idle'} title={submitState.auto ? 'Hết giờ làm bài' : submitState.status === 'error' ? 'Chưa nộp được bài' : 'Đang nộp bài'} dismissible={false} role="alertdialog">
        {submitState.status === 'submitting' ? (
          <div className="flex flex-col items-center gap-3 py-2 text-center" role="status">
            <Spinner size={30} label="Đang nộp bài" />
            <h2 className="text-lg font-bold text-navy-800">{submitState.auto ? 'Đã hết giờ! Đang tự động nộp bài…' : 'Đang nộp bài và chấm điểm…'}</h2>
            <p className="text-sm text-slate-500">Vui lòng không đóng trang.</p>
          </div>
        ) : (
          <div>
            <div className="flex items-center gap-2 text-red-600">
              <TimerOff size={22} aria-hidden="true" />
              <h2 className="text-lg font-bold">{submitState.auto ? 'Hết giờ nhưng chưa nộp được bài' : 'Chưa nộp được bài'}</h2>
            </div>
            <AlertBox tone="error" className="mt-3">
              {submitState.message}
            </AlertBox>
            <p className="mt-3 text-xs text-slate-500">Các đáp án của bạn vẫn được giữ lại.</p>
            <div className="mt-5 flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
              {submitState.code === 404 && (
                <Button
                  variant="outline"
                  onClick={() => {
                    clearSession(topicId);
                    setReloadKey((k) => k + 1);
                  }}
                >
                  Tạo đề mới
                </Button>
              )}
              <Button onClick={() => submit({ auto: submitState.auto })}>Thử nộp lại</Button>
            </div>
          </div>
        )}
      </QuizDialog>
    </div>
  );
}
