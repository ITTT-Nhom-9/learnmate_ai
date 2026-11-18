import { AlertTriangle, BookOpen, RotateCcw } from 'lucide-react';
import clsx from 'clsx';

const ACTION_LABELS = {
  REVIEW_THEORY: 'Ôn lý thuyết',
  RETAKE_QUIZ: 'Làm lại bài',
  ASK_TUTOR: 'Hỏi gia sư AI',
};

/**
 * Danh sách cảnh báo đỏ: chủ đề yếu (Mastery < 60%) cần cải thiện gấp (SCR-07, BR-08).
 * Mỗi thẻ hiển thị: tên chủ đề, bài học, điểm Mastery, lần luyện cuối, hành động gợi ý.
 */
export default function WeakTopicAlerts({ weakTopics = [] }) {
  if (weakTopics.length === 0) {
    return (
      <div className="flex flex-col items-center rounded-xl border border-dashed border-green-300 bg-green-50/50 py-8 text-center">
        <span className="flex h-10 w-10 items-center justify-center rounded-full bg-green-100 text-green-500">
          <BookOpen size={20} />
        </span>
        <p className="mt-3 text-sm font-medium text-green-700">Không có chủ đề yếu!</p>
        <p className="mt-1 text-xs text-green-600">Tất cả chủ đề đã luyện tập đều đạt mức Khá hoặc Giỏi.</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {weakTopics.map((topic) => (
        <div
          key={topic.topic_id}
          className="rounded-xl border border-red-200 bg-red-50/60 p-4 transition-shadow hover:shadow-md"
        >
          <div className="flex items-start gap-3">
            <span className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-red-100 text-red-500">
              <AlertTriangle size={16} />
            </span>
            <div className="min-w-0 flex-1">
              <h4 className="text-sm font-semibold text-red-800 line-clamp-2">{topic.topic_name}</h4>
              <p className="mt-0.5 truncate text-xs text-red-600/80">{topic.lesson_title}</p>

              <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-red-700/70">
                <span className="font-semibold text-red-700">
                  Mastery: {Math.round(topic.mastery_score)}%
                </span>
                {topic.last_quiz_score != null && (
                  <span>Điểm gần nhất: {topic.last_quiz_score}/10</span>
                )}
                <span>Đã luyện {topic.attempt_count} lần</span>
              </div>

              <div className="mt-2.5">
                <span
                  className={clsx(
                    'inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-medium',
                    'bg-red-100 text-red-700'
                  )}
                >
                  <RotateCcw size={12} />
                  {ACTION_LABELS[topic.recommended_action] || 'Ôn tập'}
                </span>
              </div>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
