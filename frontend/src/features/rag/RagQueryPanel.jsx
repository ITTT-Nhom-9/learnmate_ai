import { useEffect, useRef, useState } from 'react';
import { Info, Quote, Send } from 'lucide-react';
import AlertBox from '../../components/common/AlertBox';
import Badge from '../../components/common/Badge';
import Button from '../../components/common/Button';
import { ragApi } from '../../api/ragApi';
import { getErrorMessage } from '../../utils/apiError';
import { FilterSelect } from '../admin/AdminCommon';

function CitationList({ citations }) {
  return (
    <div className="mt-4 border-t border-slate-100 pt-3">
      <p className="mb-2 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-slate-500">
        <Quote size={14} aria-hidden="true" /> Nguồn trích dẫn ({citations.length})
      </p>
      <ul className="space-y-2">
        {citations.map((c) => (
          <li key={c.chunk_id} className="rounded-lg bg-slate-50 p-3">
            <div className="flex flex-wrap items-center gap-2">
              <Badge tone="blue">Trang {c.page_number}</Badge>
              <span className="min-w-0 flex-1 truncate text-xs font-medium text-slate-600">{c.file_name}</span>
              <span className="text-xs text-slate-400">Tương đồng {Math.round(c.similarity_score * 100)}%</span>
            </div>
            <p className="mt-1.5 text-xs italic leading-relaxed text-slate-500">{c.snippet}</p>
          </li>
        ))}
      </ul>
    </div>
  );
}

/**
 * Hỏi đáp theo tài liệu PDF kèm trích dẫn số trang (API-15, FR-RG-03, FR-RG-05).
 * Dùng độc lập được: chỉ cần courseId và danh sách tài liệu của môn đó -> có thể gắn lại vào khung chat SCR-04 (tab RAG).
 */
export default function RagQueryPanel({ courseId, documents = [] }) {
  const [question, setQuestion] = useState('');
  const [docFilter, setDocFilter] = useState('');
  const [thread, setThread] = useState([]);
  const [asking, setAsking] = useState(false);
  const [error, setError] = useState(null);
  const endRef = useRef(null);
  const noDocs = documents.length === 0;

  // Đổi môn học -> làm mới hội thoại
  useEffect(() => {
    setThread([]);
    setDocFilter('');
    setError(null);
  }, [courseId]);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }, [thread.length, asking]);

  const ask = async () => {
    const text = question.trim();
    if (text.length < 2 || asking || noDocs) return;
    setAsking(true);
    setError(null);
    try {
      const result = await ragApi.query({ courseId, query: text, documentIds: docFilter ? [Number(docFilter)] : undefined });
      setThread((t) => [...t, { id: Date.now(), query: text, result }]);
      setQuestion('');
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setAsking(false);
    }
  };

  const onKeyDown = (event) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault(); // Enter gửi, Shift+Enter xuống dòng
      ask();
    }
  };

  return (
    <div className="flex flex-col gap-4">
      {noDocs && (
        <AlertBox tone="info">Môn học này chưa có tài liệu nào được lập chỉ mục. Hãy tải PDF ở tab “Tài liệu giáo trình” trước.</AlertBox>
      )}

      <div aria-live="polite" className="space-y-4">
        {thread.length === 0 && !noDocs && (
          <p className="rounded-xl border border-dashed border-slate-300 bg-slate-50 px-4 py-8 text-center text-sm text-slate-500">
            Đặt câu hỏi về nội dung giáo trình, AI sẽ trả lời kèm số trang tham chiếu.
          </p>
        )}
        {thread.map(({ id, query, result }) => (
          <div key={id} className="space-y-3">
            <div className="flex justify-end">
              <p className="max-w-[85%] whitespace-pre-wrap rounded-2xl rounded-br-sm bg-navy-800 px-4 py-2.5 text-sm text-white">{query}</p>
            </div>
            <div className="rounded-2xl rounded-bl-sm border border-slate-200 bg-white p-4 shadow-sm">
              {result.is_out_of_scope && (
                <p className="mb-2 flex items-center gap-1.5 text-xs font-semibold text-amber-600">
                  <Info size={14} aria-hidden="true" /> Câu hỏi nằm ngoài phạm vi tài liệu
                </p>
              )}
              <p className="whitespace-pre-wrap text-sm leading-relaxed text-slate-700">{result.answer}</p>
              {result.citations?.length > 0 && <CitationList citations={result.citations} />}
            </div>
          </div>
        ))}
        {asking && <p className="text-sm text-slate-400">AI đang tra cứu tài liệu…</p>}
        <div ref={endRef} />
      </div>

      {error && <AlertBox tone="error">{error}</AlertBox>}

      <div className="rounded-xl border border-slate-200 bg-white p-3 shadow-sm">
        <textarea
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={onKeyDown}
          disabled={noDocs}
          rows={2}
          maxLength={1000}
          aria-label="Câu hỏi về tài liệu"
          placeholder="Ví dụ: Các dạng chuẩn 1NF, 2NF, 3NF khác nhau thế nào?"
          className="w-full resize-none rounded-lg border-0 bg-transparent px-2 py-1.5 text-base focus:outline-none focus:ring-0 disabled:cursor-not-allowed sm:text-sm"
        />
        <div className="mt-2 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
          <FilterSelect label="Phạm vi tài liệu" value={docFilter} onChange={setDocFilter} className="w-full sm:w-64">
            <option value="">Tất cả tài liệu của môn</option>
            {documents.map((d) => (
              <option key={d.id} value={d.id}>{d.file_name}</option>
            ))}
          </FilterSelect>
          <Button icon={Send} onClick={ask} loading={asking} disabled={noDocs || question.trim().length < 2} className="w-full sm:w-auto">
            Gửi câu hỏi
          </Button>
        </div>
      </div>
    </div>
  );
}
