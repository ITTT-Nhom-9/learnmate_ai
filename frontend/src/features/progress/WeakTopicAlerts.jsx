import { useNavigate } from 'react-router-dom';
import { AlertTriangle, RotateCcw, Target } from 'lucide-react';

/**
 * Khối "Chủ đề cần củng cố" – Cảnh báo chủ đề yếu (Mastery < 60%) + Mục tiêu tiếp theo.
 *
 * Chuẩn bản vẽ SCR-07_Bang_Tien_Do_Ca_Nhan.png:
 *  - Hộp cảnh báo (Alert Box) nền hồng nhạt: Tên chủ đề in đậm (trái), điểm EMA đỏ (phải).
 *  - Lời giải thích + Nút "Ôn tập ngay" nổi bật.
 *  - Mục tiêu tiếp theo: Đoạn gợi ý hành động.
 */
export default function WeakTopicAlerts({ weakTopics = [] }) {
  const navigate = useNavigate();

  if (weakTopics.length === 0) {
    return (
      <div className="flex flex-col items-center rounded-xl border border-dashed border-green-300 bg-green-50/50 py-8 text-center">
        <span className="flex h-10 w-10 items-center justify-center rounded-full bg-green-100 text-green-500">
          <Target size={20} />
        </span>
        <p className="mt-3 text-sm font-medium text-green-700">Không có chủ đề yếu!</p>
        <p className="mt-1 text-xs text-green-600">
          Tất cả chủ đề đã luyện tập đều đạt mức Khá hoặc Giỏi.
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full justify-between">
      {/* Vùng danh sách cảnh báo có thanh cuộn dọc mượt khi vượt quá chiều cao */}
      <div className="max-h-[350px] overflow-y-auto pr-1.5 space-y-3.5">
        {weakTopics.map((topic) => (
          <div
            key={topic.topic_id}
            className="rounded-xl border border-red-200 bg-red-50/60 p-4 transition-shadow hover:shadow-sm"
          >
            {/* Hàng trên: Tên chủ đề + Điểm EMA */}
            <div className="flex items-start justify-between gap-3">
              <div className="flex items-start gap-2 min-w-0">
                <AlertTriangle size={18} className="mt-0.5 shrink-0 text-red-500" />
                <h3 className="font-bold text-red-700 line-clamp-2">{topic.topic_name}</h3>
              </div>
              <span className="shrink-0 text-sm font-bold text-red-600">
                EMA {Math.round(topic.mastery_score)}%
              </span>
            </div>

            {/* Mô tả cảnh báo */}
            <p className="mt-2 text-xs leading-relaxed text-red-700/80">
              Dưới ngưỡng 60%. Bạn nên ôn lại lý thuyết và làm bài tập củng cố trước khi sang bài
              tiếp theo.
            </p>

            {/* Nút hành động */}
            <button
              type="button"
              onClick={() => navigate(`/quiz/${topic.topic_id}`)}
              className="mt-3 flex items-center gap-2 rounded-lg bg-navy-800 px-3.5 py-1.5 text-xs font-semibold text-white transition-colors hover:bg-navy-900 cursor-pointer"
            >
              <RotateCcw size={14} />
              Ôn tập ngay
            </button>
          </div>
        ))}
      </div>

      {/* MỤC TIÊU TIẾP THEO */}
      <div className="mt-4 border-t border-slate-100 pt-3">
        <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500">
          Mục tiêu tiếp theo
        </h4>
        <p className="mt-1 text-xs leading-relaxed text-slate-600">
          Nâng điểm thành thạo các chủ đề chưa đạt chuẩn lên mức Khá (≥&nbsp;60%). Hoàn thành các
          bài luyện tập thích ứng được hệ thống đề xuất.
        </p>
      </div>
    </div>
  );
}
