import React, { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  ArrowLeft,
  Award,
  CheckCircle2,
  Clock,
  HelpCircle,
  RotateCcw,
  Sparkles,
  TrendingUp,
  XCircle,
} from 'lucide-react';
import clsx from 'clsx';
import Badge from '../../components/common/Badge';
import Button from '../../components/common/Button';
import QuestionCard from './QuestionCard';

/**
 * Component hiển thị chi tiết kết quả làm bài trắc nghiệm và lời giải thích (SCR-06).
 * 
 * Đáp ứng đầy đủ tiêu chí:
 * - Điểm số thang 10 & 100
 * - Thống kê Đúng / Sai / Chưa làm
 * - Cập nhật điểm Mastery EMA
 * - TÔ XANH CÂU ĐÚNG, ĐỎ CÂU SAI KÈM LỜI GIẢI THÍCH CHI TIẾT
 */
export default function QuizResultReview({
  resultData,
  quizMeta = {},
  onRetakeQuiz,
}) {
  const navigate = useNavigate();
  const [filter, setFilter] = useState('ALL'); // 'ALL' | 'CORRECT' | 'WRONG'

  const {
    score = 0,
    total_questions = 0,
    correct_count = 0,
    wrong_count = 0,
    unanswered_count = 0,
    duration_sec = 0,
    mastery_old,
    mastery_new,
    mastery_status,
    answers = [],
    questions = [],
  } = resultData || {};

  // Quy đổi điểm và đánh giá
  const scoreNumber = Number(score);
  const accuracyPct = total_questions > 0 ? Math.round((correct_count / total_questions) * 100) : 0;
  const minutes = Math.floor(duration_sec / 60);
  const seconds = duration_sec % 60;
  const formattedDuration = `${minutes > 0 ? `${minutes}p ` : ''}${seconds}s`;
  const questionsById = new Map(questions.map((question) => [String(question.id), question]));

  // Phân loại xếp loại
  const performance = useMemo(() => {
    if (scoreNumber >= 8.5) {
      return {
        label: 'Xuất sắc!',
        color: 'text-emerald-700 bg-emerald-50 border-emerald-200',
        tone: 'green',
        desc: 'Bạn đã nắm rất vững kiến thức trọng tâm của chủ đề này.',
      };
    }
    if (scoreNumber >= 7.0) {
      return {
        label: 'Khá tốt!',
        color: 'text-blue-700 bg-blue-50 border-blue-200',
        tone: 'blue',
        desc: 'Kết quả tốt! Hãy xem lại các câu giải thích để hoàn thiện hơn.',
      };
    }
    if (scoreNumber >= 5.0) {
      return {
        label: 'Đạt yêu cầu',
        color: 'text-amber-700 bg-amber-50 border-amber-200',
        tone: 'amber',
        desc: 'Bạn đã nắm được kiến thức cơ bản, cần ôn luyện thêm phần nâng cao.',
      };
    }
    return {
      label: 'Cần cải thiện',
      color: 'text-rose-700 bg-rose-50 border-rose-200',
      tone: 'red',
      desc: 'Hãy ôn lại lý thuyết bài giảng và nhờ Gia sư AI giải đáp các thắc mắc.',
    };
  }, [scoreNumber]);

  // Lọc câu hỏi theo bộ lọc
  const filteredAnswers = useMemo(() => {
    if (filter === 'CORRECT') return answers.filter((a) => a.is_correct);
    if (filter === 'WRONG') return answers.filter((a) => !a.is_correct);
    return answers;
  }, [answers, filter]);

  const courseId = quizMeta?.courseId || 1;
  const lessonId = quizMeta?.lessonId;

  return (
    <div className="space-y-6">
      {/* =========================================================================
          SCORE BANNER: Bảng tổng kết điểm số & năng lực
         ========================================================================= */}
      <div className="relative overflow-hidden rounded-3xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8">
        <div className="grid gap-6 md:grid-cols-12 md:items-center">
          {/* Cột điểm số to nổi bật */}
          <div className="flex flex-col items-center justify-center text-center md:col-span-4 md:border-r md:border-slate-100 md:pr-6">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
              Điểm số bài thi
            </span>
            <div className="mt-2 flex items-baseline gap-1">
              <span className="text-5xl font-extrabold tracking-tight text-navy-900 sm:text-6xl">
                {scoreNumber.toFixed(1)}
              </span>
              <span className="text-xl font-bold text-slate-400">/ 10</span>
            </div>

            <div className="mt-3">
              <span className={clsx('inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-bold', performance.color)}>
                <Award size={15} />
                {performance.label}
              </span>
            </div>
            <p className="mt-2 text-xs text-slate-500 max-w-xs">{performance.desc}</p>
          </div>

          {/* Cột 4 thẻ thống kê chỉ số nhanh */}
          <div className="space-y-4 md:col-span-8">
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              {/* Đúng */}
              <div className="rounded-2xl border border-emerald-100 bg-emerald-50/50 p-3.5 text-center">
                <div className="flex items-center justify-center gap-1 text-xs font-semibold text-emerald-800">
                  <CheckCircle2 size={16} /> Đúng
                </div>
                <div className="mt-1.5 text-2xl font-extrabold text-emerald-700">
                  {correct_count} <span className="text-xs font-medium text-emerald-600">/ {total_questions}</span>
                </div>
              </div>

              {/* Sai */}
              <div className="rounded-2xl border border-rose-100 bg-rose-50/50 p-3.5 text-center">
                <div className="flex items-center justify-center gap-1 text-xs font-semibold text-rose-800">
                  <XCircle size={16} /> Sai
                </div>
                <div className="mt-1.5 text-2xl font-extrabold text-rose-700">
                  {wrong_count}
                </div>
              </div>

              {/* Chưa làm */}
              <div className="rounded-2xl border border-slate-100 bg-slate-50 p-3.5 text-center">
                <div className="flex items-center justify-center gap-1 text-xs font-semibold text-slate-600">
                  <HelpCircle size={16} /> Bỏ trống
                </div>
                <div className="mt-1.5 text-2xl font-extrabold text-slate-700">
                  {unanswered_count}
                </div>
              </div>

              {/* Thời gian */}
              <div className="rounded-2xl border border-blue-100 bg-blue-50/50 p-3.5 text-center">
                <div className="flex items-center justify-center gap-1 text-xs font-semibold text-blue-800">
                  <Clock size={16} /> Thời gian
                </div>
                <div className="mt-1.5 text-2xl font-extrabold text-blue-700">
                  {formattedDuration}
                </div>
              </div>
            </div>

            {/* Cập nhật điểm Mastery EMA nếu có */}
            {mastery_new != null && (
              <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-blue-100 bg-gradient-to-r from-blue-50/80 to-indigo-50/80 p-4">
                <div className="flex items-center gap-2.5">
                  <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-blue-600 text-white shadow-xs">
                    <TrendingUp size={18} />
                  </div>
                  <div>
                    <h4 className="text-xs font-bold uppercase tracking-wider text-blue-900">
                      Độ thông thạo chủ đề (Mastery EMA)
                    </h4>
                    <p className="text-xs text-blue-700">
                      Cập nhật sau bài quiz: <strong className="font-semibold">{mastery_old}%</strong> →{' '}
                      <strong className="text-blue-950 font-bold">{mastery_new}%</strong>
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <Badge tone={mastery_status === 'MASTER' ? 'green' : mastery_status === 'FAIR' ? 'blue' : 'amber'}>
                    Hạng: {mastery_status === 'MASTER' ? 'Giỏi' : mastery_status === 'FAIR' ? 'Khá' : 'Cần củng cố'}
                  </Badge>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Thanh nút hành động nhanh */}
        <div className="mt-6 flex flex-wrap items-center justify-between gap-3 border-t border-slate-100 pt-5">
          <Button
            variant="outline"
            icon={ArrowLeft}
            onClick={() => navigate(`/courses/${courseId}`)}
          >
            Quay lại khóa học
          </Button>

          <div className="flex flex-wrap items-center gap-2.5">
            {lessonId && (
              <Button
                variant="outline"
                icon={Sparkles}
                onClick={() => navigate(`/tutor/${lessonId}?course=${courseId}`)}
              >
                Hỏi Gia sư AI
              </Button>
            )}

            <Button
              variant="primary"
              icon={RotateCcw}
              onClick={onRetakeQuiz}
            >
              Làm lại bài Quiz
            </Button>
          </div>
        </div>
      </div>

      {/* =========================================================================
          REVIEW FILTER & LIST: Danh sách từng câu hỏi kèm đáp án đúng/sai & giải thích
         ========================================================================= */}
      <div className="space-y-4">
        {/* Bộ lọc xem lại */}
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h3 className="text-lg font-bold text-navy-900">Chi tiết bài làm & Lời giải</h3>

          <div className="flex rounded-xl border border-slate-200 bg-white p-1 text-xs font-semibold shadow-2xs">
            <button
              type="button"
              onClick={() => setFilter('ALL')}
              className={clsx(
                'rounded-lg px-3 py-1.5 transition-all',
                filter === 'ALL' ? 'bg-navy-800 text-white shadow-xs' : 'text-slate-600 hover:text-navy-900'
              )}
            >
              Tất cả ({answers.length})
            </button>
            <button
              type="button"
              onClick={() => setFilter('CORRECT')}
              className={clsx(
                'rounded-lg px-3 py-1.5 transition-all',
                filter === 'CORRECT' ? 'bg-emerald-600 text-white shadow-xs' : 'text-slate-600 hover:text-emerald-700'
              )}
            >
              Câu đúng ({correct_count})
            </button>
            <button
              type="button"
              onClick={() => setFilter('WRONG')}
              className={clsx(
                'rounded-lg px-3 py-1.5 transition-all',
                filter === 'WRONG' ? 'bg-rose-600 text-white shadow-xs' : 'text-slate-600 hover:text-rose-700'
              )}
            >
              Câu sai ({wrong_count})
            </button>
          </div>
        </div>

        {/* Danh sách các câu hỏi theo filter */}
        <div className="space-y-5">
          {filteredAnswers.map((ans, idx) => {
            const quizQuestion = questionsById.get(String(ans.question_id));
            const questionData = {
              id: ans.question_id,
              content: ans.question_content || quizQuestion?.content || `Câu hỏi số ${idx + 1}`,
              options: ans.options || quizQuestion?.options || [
                { id: 1, opt_label: 'A', content: 'Phương án A' },
                { id: 2, opt_label: 'B', content: 'Phương án B' },
                { id: 3, opt_label: 'C', content: 'Phương án C' },
                { id: 4, opt_label: 'D', content: 'Phương án D' },
              ],
            };

            return (
              <QuestionCard
                key={ans.question_id}
                question={questionData}
                questionIndex={idx}
                totalQuestions={answers.length}
                selectedOptionId={ans.selected_option_id}
                isReviewMode={true}
                reviewResult={ans}
              />
            );
          })}
        </div>
      </div>
    </div>
  );
}
