import { useEffect, useRef, useState } from 'react';
import { useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { BookOpen, BookX, PanelLeft, Sparkles } from 'lucide-react';
import clsx from 'clsx';
import AlertBox from '../../components/common/AlertBox';
import Button from '../../components/common/Button';
import EmptyState from '../../components/common/EmptyState';
import Spinner from '../../components/common/Spinner';
import BottomSheet from '../../components/layout/BottomSheet';
import Drawer from '../../components/layout/Drawer';
import { useAuth } from '../../hooks/useAuth';
import { useTutorChat } from '../../hooks/useTutorChat';
import { useVisualViewportHeight } from '../../hooks/useVisualViewportHeight';
import { getInitials } from '../../utils/formatters';
import ChatInput from './ChatInput';
import ChatMessageList from './ChatMessageList';
import LessonListPanel from './LessonListPanel';
import { ModeToggle, SocraticProgress } from './SocraticToggle';
import TopicPanel from './TopicPanel';
import { rememberTutorTarget } from './tutorContext';
import { useTutorLesson } from './useTutorLesson';

const HEADER_HEIGHT_PX = 64; // khớp h-16 của Header

const SUGGESTIONS = ['Tóm tắt các ý chính của bài học này', 'Cho em một ví dụ minh họa dễ hiểu', 'Em muốn kiểm tra xem mình đã hiểu bài chưa'];

function EmptyChat({ firstName, lesson, onPick }) {
  const topicPrompts = (lesson.topics || []).slice(0, 2).map((t) => `Giải thích giúp em: ${t.name}`);
  return (
    <div className="mx-auto flex h-full max-w-xl flex-col items-center justify-center py-6 text-center">
      <span className="flex h-12 w-12 items-center justify-center rounded-2xl bg-blue-50 text-blue-600">
        <Sparkles size={24} aria-hidden="true" />
      </span>
      <h2 className="mt-4 text-lg font-bold text-navy-800">Xin chào {firstName}! Mình là gia sư AI của bài học này</h2>
      <p className="mt-1.5 text-sm text-slate-500">Hãy hỏi bất cứ điều gì về “{lesson.title}”, hoặc chọn một gợi ý bên dưới.</p>
      <div className="mt-5 flex flex-wrap justify-center gap-2">
        {[...SUGGESTIONS, ...topicPrompts].map((text) => (
          <button
            key={text}
            type="button"
            onClick={() => onPick(text)}
            className="rounded-full border border-slate-200 bg-white px-3.5 py-2 text-left text-sm text-slate-700 transition-colors hover:border-blue-300 hover:bg-blue-50 hover:text-blue-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600"
          >
            {text}
          </button>
        ))}
      </div>
    </div>
  );
}

function StatusBadge({ streaming }) {
  return (
    <span
      className={clsx(
        'inline-flex items-center gap-1.5 whitespace-nowrap rounded-md px-2 py-1 text-xs font-semibold sm:px-2.5',
        streaming ? 'bg-blue-50 text-blue-600' : 'bg-emerald-50 text-emerald-600'
      )}
    >
      <span aria-hidden="true" className={clsx('h-1.5 w-1.5 rounded-full', streaming ? 'animate-pulse bg-blue-500' : 'bg-emerald-500')} />
      <span className="sr-only sm:not-sr-only">{streaming ? 'Đang trả lời' : 'Đang trực tuyến'}</span>
    </span>
  );
}

/** Không gian chat của một bài học (chỉ gắn vào khi đã xác định được môn học + bài học). */
function ChatWorkspace({ course, lessons, lesson, height }) {
  const navigate = useNavigate();
  const { user } = useAuth();
  const chat = useTutorChat(lesson.id);
  const [draft, setDraft] = useState('');
  const [listOpen, setListOpen] = useState(false);
  const [topicsOpen, setTopicsOpen] = useState(false);
  const inputRef = useRef(null);

  useEffect(() => setDraft(''), [lesson.id]);

  const quotaExceeded = chat.quotaRemaining === 0;
  const quotaLow = chat.quotaRemaining != null && chat.quotaRemaining <= 5;
  const firstName = (user?.full_name || '').trim().split(/\s+/).pop() || 'bạn';

  const handleSend = () => {
    if (chat.send(draft)) setDraft('');
  };
  const handlePrefill = (text) => {
    setDraft(text);
    setTopicsOpen(false);
    requestAnimationFrame(() => inputRef.current?.focus());
  };
  const goToLesson = (target) => {
    setListOpen(false);
    if (target.id !== lesson.id) navigate(`/tutor/${target.id}?course=${course.id}`);
  };
  const trySocratic = () => {
    chat.setMode('SOCRATIC');
    setListOpen(false);
  };

  const listPanel = (
    <LessonListPanel course={course} lessons={lessons} activeLessonId={lesson.id} onSelect={goToLesson} mode={chat.mode} onTrySocratic={trySocratic} />
  );
  const topicPanel = <TopicPanel course={course} lesson={lesson} onAsk={handlePrefill} />;

  let emptyView;
  if (chat.history.loading) {
    emptyView = (
      <div className="flex h-full items-center justify-center text-slate-400">
        <Spinner size={26} label="Đang tải lịch sử trò chuyện" />
      </div>
    );
  } else if (chat.history.error) {
    emptyView = (
      <AlertBox tone="error" action={<Button size="sm" variant="outline" onClick={chat.reloadHistory}>Thử lại</Button>}>
        {chat.history.error}
      </AlertBox>
    );
  } else {
    emptyView = <EmptyChat firstName={firstName} lesson={lesson} onPick={chat.send} />;
  }

  return (
    <>
      <div
        style={{ height }}
        className="mx-auto grid max-w-[1600px] grid-cols-[minmax(0,1fr)] gap-4 sm:p-4 lg:grid-cols-[260px_minmax(0,1fr)] xl:grid-cols-[260px_minmax(0,1fr)_300px]"
      >
        <aside aria-label="Danh sách bài học" className="hidden min-h-0 overflow-hidden rounded-xl border border-slate-200 bg-white lg:block">
          {listPanel}
        </aside>

        <section aria-label="Khung chat Gia sư AI" className="flex min-h-0 flex-col bg-white sm:overflow-hidden sm:rounded-xl sm:border sm:border-slate-200">
          <header className="border-b border-slate-100 px-4 pb-3 pt-3 sm:px-6 sm:pt-4">
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <p className="truncate text-xs text-slate-500">
                  {course.code} / Bài {lesson.order_index}
                </p>
                <h1 className="mt-0.5 truncate text-lg font-bold text-navy-800 sm:text-xl">{lesson.title}</h1>
              </div>
              <div className="flex shrink-0 items-center gap-1.5">
                <StatusBadge streaming={chat.isStreaming} />
                <button
                  type="button"
                  onClick={() => setListOpen(true)}
                  aria-label="Danh sách bài học"
                  className="rounded-lg border border-slate-200 p-2 text-slate-600 hover:bg-slate-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600 lg:hidden"
                >
                  <PanelLeft size={18} />
                </button>
                <button
                  type="button"
                  onClick={() => setTopicsOpen(true)}
                  aria-label="Chủ đề trong bài"
                  className="rounded-lg border border-slate-200 p-2 text-slate-600 hover:bg-slate-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600 xl:hidden"
                >
                  <BookOpen size={18} />
                </button>
              </div>
            </div>

            <div className="mt-3">
              <ModeToggle mode={chat.mode} onChange={chat.setMode} disabled={chat.isStreaming} />
            </div>
            {chat.mode === 'SOCRATIC' && (
              <div className="mt-2.5">
                <SocraticProgress hintLevel={chat.hintLevel} isConcluded={chat.isConcluded} />
              </div>
            )}
          </header>

          <ChatMessageList
            key={lesson.id}
            messages={chat.messages}
            initials={getInitials(user?.full_name)}
            onRetry={chat.retry}
            isStreaming={chat.isStreaming}
            empty={emptyView}
          />

          {quotaExceeded && (
            <div className="px-4 sm:px-6">
              <AlertBox tone="error" className="mx-auto mb-2 max-w-3xl">
                Bạn đã dùng hết lượt hỏi trong hôm nay (tối đa {chat.quotaTotal} câu/ngày). Hãy quay lại vào ngày mai nhé.
              </AlertBox>
            </div>
          )}

          <ChatInput
            value={draft}
            onChange={setDraft}
            onSend={handleSend}
            onStop={chat.stop}
            isStreaming={chat.isStreaming}
            disabled={quotaExceeded || (chat.history.loading && chat.messages.length === 0)}
            disabledReason={quotaExceeded ? 'Bạn đã hết lượt hỏi hôm nay' : 'Đang tải cuộc trò chuyện...'}
            inputRef={inputRef}
            footerRight={
              chat.quotaRemaining != null ? (
                <span className={quotaLow ? 'font-semibold text-amber-600' : undefined}>
                  Còn {chat.quotaRemaining}/{chat.quotaTotal} lượt hỏi hôm nay
                </span>
              ) : (
                <span>AI có thể mắc lỗi, hãy đối chiếu với bài học</span>
              )
            }
          />
          <div role="status" className="sr-only">
            {chat.isStreaming ? 'Gia sư AI đang trả lời' : ''}
          </div>
        </section>

        <aside aria-label="Chủ đề trong bài" className="thin-scroll hidden min-h-0 overflow-y-auto rounded-xl border border-slate-200 bg-white xl:block">
          {topicPanel}
        </aside>
      </div>

      <Drawer open={listOpen} onClose={() => setListOpen(false)} title="Danh sách bài học">
        {listPanel}
      </Drawer>
      <BottomSheet open={topicsOpen} onClose={() => setTopicsOpen(false)} title="Chủ đề trong bài">
        {topicPanel}
      </BottomSheet>
    </>
  );
}

/** SCR-04: Khung chat Gia sư AI. Route: /tutor và /tutor/:lessonId?course=:courseId */
export default function TutorChatPage() {
  const { lessonId } = useParams();
  const [search] = useSearchParams();
  const courseParam = search.get('course');
  const navigate = useNavigate();
  const ctx = useTutorLesson({ lessonId, courseId: courseParam });

  // Khung chat tự quản lý cuộn bên trong -> khóa cuộn trang để iOS không kéo cả trang khi mở bàn phím ảo
  useEffect(() => {
    const root = document.documentElement;
    const previous = root.style.overflow;
    root.style.overflow = 'hidden';
    return () => {
      root.style.overflow = previous;
    };
  }, []);

  // Đưa URL về dạng chuẩn /tutor/:lessonId?course=:courseId và nhớ bài học gần nhất cho menu "Học cùng AI"
  const readyCourseId = ctx.status === 'ready' ? ctx.course.id : null;
  const readyLessonId = ctx.status === 'ready' ? ctx.lesson.id : null;
  useEffect(() => {
    if (readyCourseId == null) return;
    rememberTutorTarget(readyCourseId, readyLessonId);
    // Chỉ bổ sung phần URL còn thiếu. Nếu URL đã có :lessonId thì URL là nguồn đúng, không kéo ngược về bài cũ.
    if (!lessonId || !courseParam) {
      navigate(`/tutor/${readyLessonId}?course=${readyCourseId}`, { replace: true });
    }
  }, [readyCourseId, readyLessonId, lessonId, courseParam, navigate]);

  const viewportHeight = useVisualViewportHeight();
  const height = `${Math.max(320, viewportHeight - HEADER_HEIGHT_PX)}px`;

  if (ctx.status === 'ready') return <ChatWorkspace course={ctx.course} lessons={ctx.lessons} lesson={ctx.lesson} height={height} />;

  return (
    <div style={{ height }} className="mx-auto flex max-w-3xl items-center justify-center px-4">
      {ctx.status === 'loading' && (
        <div className="text-slate-400">
          <Spinner size={30} label="Đang tải bài học" />
        </div>
      )}
      {ctx.status === 'error' && (
        <AlertBox tone="error" className="w-full" action={<Button size="sm" variant="outline" onClick={ctx.retry}>Thử lại</Button>}>
          {ctx.error}
        </AlertBox>
      )}
      {(ctx.status === 'notfound' || ctx.status === 'empty') && (
        <EmptyState
          icon={BookX}
          title={ctx.status === 'notfound' ? 'Không tìm thấy bài học' : 'Chưa có bài học để trò chuyện'}
          description={
            ctx.status === 'notfound'
              ? 'Bài học có thể đã bị gỡ hoặc đường dẫn không đúng.'
              : 'Hãy chọn một môn học có bài giảng, rồi bấm “Học cùng Gia sư AI bài này”.'
          }
          action={<Button variant="outline" onClick={() => navigate('/courses')}>Về danh mục môn học</Button>}
        />
      )}
    </div>
  );
}
