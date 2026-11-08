import { useEffect } from 'react';
import { ExternalLink, FileWarning } from 'lucide-react';
import MarkdownViewer from '../../components/viewer/MarkdownViewer';
import { matchTopicId } from './courseUtils';

/** Chỉ cho phép liên kết http(s) để tránh javascript:/data: URL trong nội dung do giảng viên nhập. */
function toSafeUrl(value) {
  try {
    const url = new URL((value || '').trim());
    return url.protocol === 'https:' || url.protocol === 'http:' ? url : null;
  } catch {
    return null;
  }
}

function youtubeEmbedUrl(url) {
  let id = null;
  if (url.hostname === 'youtu.be') id = url.pathname.slice(1);
  else if (/(^|\.)youtube\.com$/.test(url.hostname)) {
    id = url.searchParams.get('v') || /^\/(?:embed|shorts)\/([\w-]+)/.exec(url.pathname)?.[1];
  }
  return id && /^[\w-]{6,}$/.test(id) ? `https://www.youtube-nocookie.com/embed/${id}` : null;
}

function UnavailableBlock({ message }) {
  return (
    <div className="my-4 flex items-center gap-2.5 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
      <FileWarning size={18} className="shrink-0" aria-hidden="true" />
      {message}
    </div>
  );
}

function VideoBlock({ body }) {
  const url = toSafeUrl(body);
  if (!url) return <UnavailableBlock message="Liên kết video không hợp lệ." />;
  const embed = youtubeEmbedUrl(url);
  return (
    <div className="my-5 aspect-video overflow-hidden rounded-xl bg-navy-950">
      {embed ? (
        <iframe
          src={embed}
          title="Video bài giảng"
          allow="accelerometer; encrypted-media; gyroscope; picture-in-picture"
          allowFullScreen
          loading="lazy"
          className="h-full w-full"
        />
      ) : (
        <video src={url.href} controls preload="metadata" className="h-full w-full" />
      )}
    </div>
  );
}

function PdfBlock({ body }) {
  const url = toSafeUrl(body);
  if (!url) return <UnavailableBlock message="Liên kết tài liệu PDF không hợp lệ." />;
  return (
    <div className="my-5">
      <iframe src={url.href} title="Tài liệu PDF bài giảng" loading="lazy" className="hidden h-[70vh] w-full rounded-xl border border-slate-200 md:block" />
      <a
        href={url.href}
        target="_blank"
        rel="noopener noreferrer"
        className="inline-flex items-center gap-2 rounded-lg border border-slate-300 px-4 py-2.5 text-sm font-semibold text-navy-800 hover:bg-slate-50 md:mt-3"
      >
        <ExternalLink size={16} aria-hidden="true" /> Mở tài liệu PDF trong tab mới
      </a>
    </div>
  );
}

function ContentBlock({ content }) {
  switch ((content.content_type || '').toUpperCase()) {
    case 'MARKDOWN':
      return <MarkdownViewer source={content.body} />;
    case 'VIDEO':
      return <VideoBlock body={content.body} />;
    case 'PDF':
      return <PdfBlock body={content.body} />;
    default:
      return <UnavailableBlock message="Định dạng nội dung này chưa được hỗ trợ." />;
  }
}

/**
 * Nội dung lý thuyết của bài học (đa định dạng: Markdown, Video, PDF).
 * Mỗi khối gắn với một chủ đề để Sidebar cuộn tới / đánh dấu chủ đề đang đọc.
 */
export default function LessonContentView({ lesson, onTopicVisible }) {
  const contents = lesson.contents || [];
  const topics = lesson.topics || [];
  const blocks = contents.map((content, index) => ({ content, topicId: matchTopicId(content, topics, index) }));

  // Scroll-spy: chủ đề nào đang nằm ở phần trên màn hình thì báo về trang cha
  useEffect(() => {
    if (!onTopicVisible || typeof IntersectionObserver === 'undefined') return undefined;
    const observer = new IntersectionObserver(
      (entries) => {
        const hit = entries.find((entry) => entry.isIntersecting);
        if (hit) onTopicVisible(Number(hit.target.dataset.topicId));
      },
      { rootMargin: '-15% 0px -70% 0px' }
    );
    document.querySelectorAll('[data-topic-id]').forEach((el) => observer.observe(el));
    return () => observer.disconnect();
  }, [lesson.id, onTopicVisible]);

  if (blocks.length === 0) {
    return <p className="rounded-lg bg-slate-50 px-4 py-6 text-center text-sm text-slate-500">Bài học này chưa có nội dung.</p>;
  }

  return (
    <div className="divide-y divide-slate-100">
      {blocks.map(({ content, topicId }) => (
        <section
          key={content.id}
          id={topicId != null ? `topic-${topicId}` : undefined}
          data-topic-id={topicId ?? undefined}
          className="scroll-mt-24 py-6 first:pt-2 last:pb-2"
        >
          <ContentBlock content={content} />
        </section>
      ))}
    </div>
  );
}
