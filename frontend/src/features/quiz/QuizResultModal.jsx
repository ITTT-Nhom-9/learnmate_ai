import React from 'react';
import { Award, CheckCircle2, RotateCcw, X, XCircle } from 'lucide-react';
import Button from '../../components/common/Button';

/**
 * Modal hiển thị kết quả nhanh ngay sau khi nộp bài (SCR-06 Pop-up).
 */
export default function QuizResultModal({
  isOpen,
  onClose,
  resultData,
  onViewDetails,
  onRetakeQuiz,
}) {
  if (!isOpen || !resultData) return null;

  const {
    score = 0,
    total_questions = 0,
    correct_count = 0,
    wrong_count = 0,
    mastery_new,
  } = resultData;

  const scoreNum = Number(score);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-navy-950/60 p-4 backdrop-blur-xs animate-fade-in">
      <div
        className="w-full max-w-lg overflow-hidden rounded-3xl border border-slate-200 bg-white p-6 shadow-2xl animate-slide-in-up sm:p-8"
        role="dialog"
        aria-modal="true"
      >
        <div className="flex items-center justify-between border-b border-slate-100 pb-4">
          <div className="flex items-center gap-2 text-navy-900 font-bold text-lg">
            <Award className="text-amber-500" size={22} />
            <span>Kết quả bài làm trắc nghiệm</span>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-600"
          >
            <X size={18} />
          </button>
        </div>

        <div className="py-6 text-center">
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
            Điểm số đạt được
          </span>
          <div className="mt-2 flex items-baseline justify-center gap-1">
            <span className="text-5xl font-extrabold text-navy-900">{scoreNum.toFixed(1)}</span>
            <span className="text-xl font-bold text-slate-400">/ 10</span>
          </div>

          <p className="mt-2 text-sm text-slate-600">
            {scoreNum >= 8.0
              ? 'Tuyệt vời! Bạn đã hoàn thành xuất sắc bài kiểm tra thích ứng.'
              : scoreNum >= 5.0
              ? 'Làm tốt lắm! Bạn đã nắm được đa số kiến thức trọng tâm.'
              : 'Hãy xem lại lời giải chi tiết để củng cố các câu chưa chính xác.'}
          </p>

          <div className="mt-6 grid grid-cols-2 gap-3">
            <div className="flex items-center justify-center gap-2 rounded-xl bg-emerald-50 p-3 text-emerald-800">
              <CheckCircle2 size={18} />
              <span className="font-bold text-lg">{correct_count}</span>
              <span className="text-xs">câu đúng</span>
            </div>
            <div className="flex items-center justify-center gap-2 rounded-xl bg-rose-50 p-3 text-rose-800">
              <XCircle size={18} />
              <span className="font-bold text-lg">{wrong_count}</span>
              <span className="text-xs">câu sai</span>
            </div>
          </div>

          {mastery_new != null && (
            <div className="mt-4 rounded-xl border border-blue-100 bg-blue-50/60 p-3 text-xs text-blue-900">
              Độ thông thạo chủ đề cập nhật: <strong className="font-bold text-blue-950">{mastery_new}%</strong>
            </div>
          )}
        </div>

        <div className="flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
          <Button variant="outline" icon={RotateCcw} onClick={onRetakeQuiz}>
            Làm lại đề mới
          </Button>
          <Button variant="primary" onClick={onViewDetails}>
            Xem giải thích chi tiết
          </Button>
        </div>
      </div>
    </div>
  );
}
