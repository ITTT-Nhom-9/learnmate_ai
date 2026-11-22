import { useState } from 'react';
import { FileUp, Lock, MessageSquareText } from 'lucide-react';
import clsx from 'clsx';
import AlertBox from '../../components/common/AlertBox';
import EmptyState from '../../components/common/EmptyState';
import { ragApi } from '../../api/ragApi';
import { useAuth } from '../../hooks/useAuth';
import { useAdminQuery } from '../admin/useAdminQuery';
import { DeleteDocumentDialog, RenameDocumentDialog } from './DocumentDialogs';
import DocumentList from './DocumentList';
import RagQueryPanel from './RagQueryPanel';
import UploadCard from './UploadCard';

const TABS = [
  { id: 'upload', label: 'Tài liệu giáo trình', icon: FileUp },
  { id: 'ask', label: 'Hỏi đáp tài liệu', icon: MessageSquareText },
];

/**
 * Không gian RAG của MỘT môn học: tải lên, danh sách (đổi tên / xóa) và hỏi đáp có trích dẫn số trang.
 * Dùng chung cho Sinh viên (/courses/:id/documents) và Quản trị viên (/admin/documents).
 * Quyền do Backend quyết định: sinh viên phải ghi danh; chỉ chủ tài liệu hoặc Admin được đổi tên / xóa.
 */
export default function RagWorkspace({ courseId, defaultTab = 'upload' }) {
  const { user } = useAuth();
  const [tab, setTab] = useState(defaultTab);
  const [renaming, setRenaming] = useState(null);
  const [deleting, setDeleting] = useState(null);
  const [notice, setNotice] = useState(null);

  const docs = useAdminQuery(() => (courseId ? ragApi.getDocuments(courseId) : null), [courseId]);
  const documents = docs.data?.items ?? null;

  // Chủ tài liệu hoặc Admin. Backend cũ chưa trả uploaded_by thì vẫn hiện nút và để Backend trả 403 nếu không đủ quyền.
  const canManage = (d) => user?.role === 'ADMIN' || d.uploaded_by == null || d.uploaded_by === user?.id;

  if (docs.errorStatus === 403) {
    return (
      <EmptyState
        icon={Lock}
        title="Bạn chưa ghi danh môn học này"
        description={`${docs.error} Hãy ghi danh môn học trong danh mục để dùng tài liệu và hỏi đáp PDF.`}
      />
    );
  }

  return (
    <>
      {notice && (
        <AlertBox tone="success" className="mb-4" action={<button type="button" onClick={() => setNotice(null)} className="text-xs font-semibold underline">Đóng</button>}>
          {notice}
        </AlertBox>
      )}

      <div role="tablist" aria-label="Chức năng tài liệu PDF" className="mb-4 flex gap-1 border-b border-slate-200">
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
          <UploadCard courseId={courseId} onUploaded={docs.reload} className="lg:col-span-2" />
          <DocumentList
            className="lg:col-span-3"
            documents={documents}
            loading={docs.loading}
            error={docs.error}
            onReload={docs.reload}
            canManage={canManage}
            onRename={setRenaming}
            onDelete={setDeleting}
          />
        </div>
      ) : (
        <div role="tabpanel" id="rag-panel-ask" aria-labelledby="rag-tab-ask" className="mx-auto max-w-3xl">
          <RagQueryPanel courseId={courseId} documents={documents ?? []} />
        </div>
      )}

      {renaming && (
        <RenameDocumentDialog
          key={renaming.id}
          document={renaming}
          onClose={() => setRenaming(null)}
          onDone={(updated) => {
            setRenaming(null);
            setNotice(`Đã đổi tên thành “${updated.file_name}”.`);
            docs.reload();
          }}
        />
      )}
      {deleting && (
        <DeleteDocumentDialog
          key={deleting.id}
          document={deleting}
          onClose={() => setDeleting(null)}
          onDone={(removed) => {
            setDeleting(null);
            setNotice(`Đã xóa “${removed.file_name}”.`);
            docs.reload();
          }}
        />
      )}
    </>
  );
}
