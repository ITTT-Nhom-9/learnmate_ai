import { useEffect, useState } from 'react';
import { FileText, FileUp, MessageSquareText, Trash2, UploadCloud, X } from 'lucide-react';
import clsx from 'clsx';
import AlertBox from '../../components/common/AlertBox';
import Button from '../../components/common/Button';
import EmptyState from '../../components/common/EmptyState';
import Modal from '../../components/common/Modal';
import ProgressBar from '../../components/common/ProgressBar';
import Spinner from '../../components/common/Spinner';
import { courseApi } from '../../api/courseApi';
import { MAX_PDF_BYTES, ragApi } from '../../api/ragApi';
import { getErrorMessage } from '../../utils/apiError';
import { AdminPageHeader, FilterSelect, Panel } from './AdminCommon';
import RagQueryPanel from './RagQueryPanel';
import { formatBytes, formatDate, formatNumber } from './adminUtils';
import { useAdminQuery } from './useAdminQuery';

const TABS = [
  { id: 'upload', label: 'Tài liệu giáo trình', icon: FileUp },
  { id: 'ask', label: 'Hỏi đáp thử', icon: MessageSquareText },
];

/** BR-09: chỉ nhận PDF, tối đa 20MB. Trả về thông báo lỗi hoặc null nếu hợp lệ. */
function validatePdf(file) {
  if (!file) return 'Vui lòng chọn một tệp PDF.';
  const isPdf = file.type === 'application/pdf' || file.name.toLowerCase().endsWith('.pdf');
  if (!isPdf) return 'Chỉ chấp nhận tệp định dạng .pdf (BR-09).';
  if (file.size === 0) return 'Tệp rỗng, vui lòng chọn tệp khác.';
  if (file.size > MAX_PDF_BYTES) return `Tệp ${formatBytes(file.size)} vượt quá giới hạn 20 MB (BR-09).`;
  return null;
}

/** Khung kéo-thả / chọn tệp PDF, hiển thị tiến trình tải lên rồi lập chỉ mục. */
function UploadCard({ courseId, onUploaded }) {
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
    <Panel title="Tải lên giáo trình PDF" icon={UploadCloud} className="lg:col-span-2">
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

/** Danh sách tài liệu của môn: bảng (desktop) / thẻ (mobile), có nút xóa kèm xác nhận. */
function DocumentList({ documents, loading, error, onReload, onDelete }) {
  return (
    <Panel title={`Tài liệu đã lập chỉ mục${documents ? ` (${documents.length})` : ''}`} icon={FileText} className="lg:col-span-3">
      {error && <AlertBox tone="error" action={<Button variant="outline" size="sm" onClick={onReload}>Thử lại</Button>}>{error}</AlertBox>}
      {loading && !documents && <div className="flex justify-center py-12 text-slate-400"><Spinner size={24} label="Đang tải tài liệu" /></div>}
      {documents && documents.length === 0 && (
        <EmptyState icon={FileText} title="Chưa có tài liệu" description="Tải lên giáo trình PDF để sinh viên có thể hỏi đáp kèm trích dẫn số trang." />
      )}

      {documents?.length > 0 && (
        <div className={loading ? 'opacity-60 transition-opacity' : 'transition-opacity'}>
          <div className="hidden overflow-x-auto md:block">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-slate-200 text-xs font-semibold uppercase tracking-wide text-slate-500">
                  <th className="px-3 py-2.5">Tên tệp</th>
                  <th className="whitespace-nowrap px-3 py-2.5 text-right">Dung lượng</th>
                  <th className="px-3 py-2.5 text-right">Đoạn</th>
                  <th className="whitespace-nowrap px-3 py-2.5">Ngày tải</th>
                  <th className="px-3 py-2.5 text-right"><span className="sr-only">Thao tác</span></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {documents.map((d) => (
                  <tr key={d.id} className="hover:bg-slate-50">
                    <td className="max-w-[18rem] px-3 py-3">
                      <span className="flex items-center gap-2">
                        <FileText size={16} className="shrink-0 text-red-500" aria-hidden="true" />
                        <span className="truncate font-medium text-slate-700" title={d.file_name}>{d.file_name}</span>
                      </span>
                    </td>
                    <td className="whitespace-nowrap px-3 py-3 text-right text-slate-600">{formatBytes(d.file_size)}</td>
                    <td className="px-3 py-3 text-right text-slate-600">{formatNumber(d.total_chunks)}</td>
                    <td className="whitespace-nowrap px-3 py-3 text-slate-500">{formatDate(d.created_at)}</td>
                    <td className="px-3 py-3 text-right">
                      <Button variant="ghost" size="sm" icon={Trash2} onClick={() => onDelete(d)} aria-label={`Xóa ${d.file_name}`} className="text-red-600 hover:bg-red-50" />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <ul className="space-y-3 md:hidden">
            {documents.map((d) => (
              <li key={d.id} className="rounded-xl border border-slate-200 p-4">
                <p className="flex items-start gap-2 text-sm font-semibold text-navy-800">
                  <FileText size={16} className="mt-0.5 shrink-0 text-red-500" aria-hidden="true" />
                  <span className="min-w-0 break-words">{d.file_name}</span>
                </p>
                <p className="mt-2 text-xs text-slate-500">{formatBytes(d.file_size)} · {formatNumber(d.total_chunks)} đoạn · {formatDate(d.created_at)}</p>
                <Button variant="outline" size="sm" icon={Trash2} onClick={() => onDelete(d)} className="mt-3 w-full text-red-600">Xóa tài liệu</Button>
              </li>
            ))}
          </ul>
        </div>
      )}
    </Panel>
  );
}

/** SCR-08 · Tab RAG: quản lý giáo trình PDF (API-14) và hỏi đáp thử có trích dẫn số trang (API-15). */
export default function RagDocumentsPage() {
  const [tab, setTab] = useState('upload');
  const [courseId, setCourseId] = useState(null);
  const [toDelete, setToDelete] = useState(null);
  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState(null);

  const courses = useAdminQuery(() => courseApi.getCourses({ limit: 100 }), []);
  const courseList = courses.data?.courses ?? [];
  const docs = useAdminQuery(() => (courseId ? ragApi.getDocuments(courseId) : null), [courseId]);
  const documents = docs.data?.items ?? null;

  // Mặc định chọn môn đầu tiên khi danh sách môn tải xong
  useEffect(() => {
    if (!courseId && courseList.length > 0) setCourseId(courseList[0].id);
  }, [courseId, courseList]);

  const confirmDelete = async () => {
    setDeleting(true);
    setDeleteError(null);
    try {
      await ragApi.deleteDocument(toDelete.id);
      setToDelete(null);
      docs.reload();
    } catch (err) {
      setDeleteError(getErrorMessage(err));
    } finally {
      setDeleting(false);
    }
  };

  return (
    <>
      <AdminPageHeader
        title="Tài liệu RAG"
        description="Tải giáo trình PDF để sinh viên hỏi đáp kiến thức nâng cao kèm trích dẫn số trang."
        actions={
          courseList.length > 0 && (
            <FilterSelect label="Chọn môn học" value={courseId ?? ''} onChange={(v) => setCourseId(Number(v))} className="max-w-full sm:max-w-xs">
              {courseList.map((c) => (
                <option key={c.id} value={c.id}>{c.code} – {c.title}</option>
              ))}
            </FilterSelect>
          )
        }
      />

      {courses.error && <AlertBox tone="error" className="mb-4" action={<Button variant="outline" size="sm" onClick={courses.reload}>Thử lại</Button>}>{courses.error}</AlertBox>}
      {courses.loading && !courses.data && <div className="flex justify-center py-16 text-slate-400"><Spinner size={28} label="Đang tải danh sách môn" /></div>}
      {courses.data && courseList.length === 0 && (
        <EmptyState icon={FileText} title="Chưa có môn học" description="Cần có ít nhất một môn học để gắn tài liệu giáo trình." />
      )}

      {courseId && (
        <>
          <div role="tablist" aria-label="Chức năng RAG" className="mb-4 flex gap-1 border-b border-slate-200">
            {TABS.map(({ id, label, icon: Icon }) => (
              <button
                key={id}
                type="button"
                role="tab"
                id={`rag-tab-${id}`}
                aria-selected={tab === id}
                aria-controls={`rag-panel-${id}`}
                onClick={() => setTab(id)}
                className={clsx(
                  '-mb-px flex h-11 items-center gap-2 border-b-2 px-4 text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-blue-600',
                  tab === id ? 'border-blue-600 text-navy-800' : 'border-transparent text-slate-500 hover:text-navy-800'
                )}
              >
                <Icon size={16} aria-hidden="true" />
                {label}
              </button>
            ))}
          </div>

          {tab === 'upload' ? (
            <div role="tabpanel" id="rag-panel-upload" aria-labelledby="rag-tab-upload" className="grid grid-cols-1 gap-6 lg:grid-cols-5 lg:items-start">
              <UploadCard courseId={courseId} onUploaded={docs.reload} />
              <DocumentList documents={documents} loading={docs.loading} error={docs.error} onReload={docs.reload} onDelete={(d) => { setDeleteError(null); setToDelete(d); }} />
            </div>
          ) : (
            <div role="tabpanel" id="rag-panel-ask" aria-labelledby="rag-tab-ask" className="mx-auto max-w-3xl">
              <RagQueryPanel courseId={courseId} documents={documents ?? []} />
            </div>
          )}
        </>
      )}

      {toDelete && (
        <Modal
          open
          busy={deleting}
          onClose={() => setToDelete(null)}
          title="Xóa tài liệu"
          footer={
            <>
              <Button variant="outline" onClick={() => setToDelete(null)} disabled={deleting}>Hủy</Button>
              <Button variant="danger" icon={Trash2} loading={deleting} onClick={confirmDelete}>Xóa tài liệu</Button>
            </>
          }
        >
          <p className="text-sm text-slate-600">
            Xóa <strong className="break-words text-navy-800">{toDelete.file_name}</strong> cùng toàn bộ {formatNumber(toDelete.total_chunks)} đoạn vector embedding? Sinh viên sẽ không còn hỏi đáp được theo tài liệu này.
          </p>
          {deleteError && <AlertBox tone="error" className="mt-3">{deleteError}</AlertBox>}
        </Modal>
      )}
    </>
  );
}
