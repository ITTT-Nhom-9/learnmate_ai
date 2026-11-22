import { useState } from 'react';
import { FileText, UploadCloud, X } from 'lucide-react';
import clsx from 'clsx';
import AlertBox from '../../components/common/AlertBox';
import Button from '../../components/common/Button';
import ProgressBar from '../../components/common/ProgressBar';
import Spinner from '../../components/common/Spinner';
import { ragApi } from '../../api/ragApi';
import { getErrorMessage } from '../../utils/apiError';
import { Panel } from '../admin/AdminCommon';
import { formatBytes, formatNumber } from '../admin/adminUtils';
import { validatePdf } from './ragUtils';

/** Khung kéo-thả / chọn tệp PDF, hiển thị tiến trình tải lên rồi lập chỉ mục (FR-RG-01, BR-09). */
export default function UploadCard({ courseId, onUploaded, className }) {
  const [file, setFile] = useState(null);
  const [error, setError] = useState(null);
  const [dragging, setDragging] = useState(false);
  const [progress, setProgress] = useState(null); // null: không tải; 0..100: đang tải lên
  const [result, setResult] = useState(null);
  const uploading = progress !== null;

  const pick = (picked) => {
    setResult(null);
    const message = validatePdf(picked);
    setError(message);
    setFile(message ? null : picked);
  };

  const submit = async () => {
    setError(null);
    setResult(null);
    setProgress(0);
    try {
      const done = await ragApi.uploadDocument({ courseId, file, onProgress: setProgress });
      setResult(done);
      setFile(null);
      onUploaded();
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setProgress(null);
    }
  };

  return (
    <Panel title="Tải lên giáo trình PDF" icon={UploadCloud} className={className}>
      <label
        htmlFor="rag-file"
        onDragOver={(e) => {
          e.preventDefault();
          if (!uploading) setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragging(false);
          if (!uploading) pick(e.dataTransfer.files?.[0]);
        }}
        className={clsx(
          'flex cursor-pointer flex-col items-center rounded-xl border-2 border-dashed px-4 py-8 text-center transition-colors focus-within:ring-2 focus-within:ring-blue-600',
          dragging ? 'border-blue-500 bg-blue-50' : 'border-slate-300 bg-slate-50 hover:border-slate-400',
          uploading && 'pointer-events-none opacity-60'
        )}
      >
        <UploadCloud size={32} className="text-slate-400" aria-hidden="true" />
        <span className="mt-2 text-sm font-semibold text-navy-800">Kéo thả tệp PDF vào đây hoặc bấm để chọn</span>
        <span className="mt-1 text-xs text-slate-500">Chỉ nhận .pdf, tối đa 20 MB</span>
        <input
          id="rag-file"
          type="file"
          accept="application/pdf,.pdf"
          disabled={uploading}
          className="sr-only"
          onChange={(e) => {
            pick(e.target.files?.[0]);
            e.target.value = ''; // cho phép chọn lại đúng tệp vừa bỏ
          }}
        />
      </label>

      {file && (
        <div className="mt-3 flex items-center gap-3 rounded-lg border border-slate-200 p-3">
          <FileText size={20} className="shrink-0 text-red-500" aria-hidden="true" />
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-medium text-slate-700">{file.name}</p>
            <p className="text-xs text-slate-400">{formatBytes(file.size)}</p>
          </div>
          {!uploading && (
            <button type="button" onClick={() => setFile(null)} aria-label="Bỏ tệp đã chọn" className="rounded-full p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-600">
              <X size={16} />
            </button>
          )}
        </div>
      )}

      {uploading && (
        <div className="mt-3" role="status">
          <ProgressBar value={progress} label="Tiến trình tải lên" />
          <p className="mt-1.5 flex items-center gap-2 text-xs text-slate-500">
            {progress < 100 ? (
              `Đang tải lên… ${progress}%`
            ) : (
              <>
                <Spinner size={14} /> Đang trích xuất văn bản và tạo vector embedding, vui lòng chờ…
              </>
            )}
          </p>
        </div>
      )}

      {error && <AlertBox tone="error" className="mt-3">{error}</AlertBox>}
      {result && (
        <AlertBox tone="success" className="mt-3">
          Đã lập chỉ mục “{result.file_name}”: {formatNumber(result.total_pages)} trang · {formatNumber(result.total_chunks)} đoạn · vector {result.embedding_dim} chiều.
        </AlertBox>
      )}

      <Button icon={UploadCloud} size="lg" className="mt-4 w-full" onClick={submit} loading={uploading} disabled={!file || !courseId}>
        Tải lên & lập chỉ mục
      </Button>
    </Panel>
  );
}
