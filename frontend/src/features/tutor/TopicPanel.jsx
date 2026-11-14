import { Link } from 'react-router-dom';
import { BookOpen, FileText } from 'lucide-react';

/**
 * Cột phải: ngữ cảnh của bài học (các chủ đề kiến thức). Bấm vào chủ đề để điền sẵn câu hỏi vào ô chat.
 * Panel "Nguồn tham khảo" trích dẫn PDF theo trang (RAG) sẽ do TK-24/25/26 bổ sung vào cột này.
 */
export default function TopicPanel({ course, lesson, onAsk }) {
  const topics = lesson.topics || [];
  return (
    <div className="p-4">
      <h2 className="flex items-center gap-2 text-lg font-bold text-navy-800">
        <BookOpen size={20} className="text-slate-500" aria-hidden="true" />
        Chủ đề trong bài
      </h2>

      <div className="mt-4 rounded-xl bg-blue-50 p-4">
        <div className="flex items-start gap-2.5">
          <FileText size={18} className="mt-0.5 shrink-0 text-blue-600" aria-hidden="true" />
          <div className="min-w-0">
            <p className="text-sm font-semibold leading-snug text-navy-800">{lesson.title}</p>
            <p className="mt-1 text-xs text-slate-500">
              Bài {lesson.order_index} · {topics.length} chủ đề · Môn {course.code}
            </p>
          </div>
        </div>
        <Link
          to={`/courses/${course.id}/lessons/${lesson.id}`}
          className="mt-3 inline-block rounded text-xs font-semibold text-blue-600 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600"
        >
          Mở nội dung bài học →
        </Link>
      </div>

      <p className="mb-2 mt-5 text-[11px] font-semibold uppercase tracking-wide text-slate-500">Hỏi nhanh theo chủ đề</p>
      {topics.length === 0 ? (
        <p className="rounded-lg bg-slate-50 px-3 py-4 text-center text-sm text-slate-500">Bài học này chưa có chủ đề.</p>
      ) : (
        <ul className="space-y-3">
          {topics.map((topic, index) => (
            <li key={topic.id}>
              <button
                type="button"
                onClick={() => onAsk(`Giải thích giúp em chủ đề “${topic.name}” trong bài học này.`)}
                className="w-full rounded-xl border border-slate-200 bg-slate-50/50 p-4 text-left transition-colors hover:border-blue-200 hover:bg-blue-50/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600"
              >
                <span className="text-xs font-semibold text-slate-500">Chủ đề {index + 1}</span>
                <span className="mt-1 block text-sm font-semibold leading-snug text-navy-800">{topic.name}</span>
                {topic.description && <span className="mt-1.5 line-clamp-3 block text-xs leading-relaxed text-slate-500">{topic.description}</span>}
                <span className="mt-2 block text-xs font-medium text-blue-600">Hỏi gia sư về chủ đề này →</span>
              </button>
            </li>
          ))}
        </ul>
      )}

      <p className="mt-5 text-xs leading-relaxed text-slate-400">AI có thể mắc lỗi. Hãy đối chiếu câu trả lời với nội dung bài học khi cần.</p>
    </div>
  );
}
