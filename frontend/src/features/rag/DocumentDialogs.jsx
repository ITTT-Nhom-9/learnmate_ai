import { useState } from 'react';
import { Trash2 } from 'lucide-react';
import AlertBox from '../../components/common/AlertBox';
import Button from '../../components/common/Button';
import Modal from '../../components/common/Modal';
import { ragApi } from '../../api/ragApi';
import { getErrorMessage } from '../../utils/apiError';
import { formatNumber } from '../admin/adminUtils';
import { validateDocumentName } from './ragUtils';

/** Đổi tên hiển thị tài liệu (FR-RG-04). Tên mới cũng xuất hiện trong phần trích dẫn nguồn khi hỏi đáp. */
export function RenameDocumentDialog({ document, onClose, onDone }) {
  const [name, setName] = useState(document.file_name);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  const submit = async (event) => {
    event?.preventDefault();
    const invalid = validateDocumentName(name);
    if (invalid) {
      setError(invalid);
      return;
    }
    if (name.trim() === document.file_name) {
      onClose();
      return;
    }
    setBusy(true);
    setError(null);
    try {
      onDone(await ragApi.renameDocument(document.id, name.trim()));
    } catch (err) {
      setError(getErrorMessage(err));
      setBusy(false);
    }
  };

  return (
    <Modal
      open
      busy={busy}
      onClose={onClose}
      title="Đổi tên tài liệu"
      footer={
        <>
          <Button variant="outline" onClick={onClose} disabled={busy}>Hủy</Button>
          <Button loading={busy} onClick={submit}>Lưu tên mới</Button>
        </>
      }
    >
      <form onSubmit={submit}>
        <label htmlFor="doc-name" className="mb-1.5 block text-sm font-medium text-slate-700">Tên hiển thị</label>
        <input
          id="doc-name"
          autoFocus
          value={name}
          onChange={(e) => setName(e.target.value)}
          maxLength={255}
          className="h-11 w-full rounded-lg border border-slate-300 px-3.5 text-base focus:border-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-100 sm:text-sm"
        />
        <p className="mt-1.5 text-xs text-slate-500">Chỉ đổi tên hiển thị, nội dung đã lập chỉ mục được giữ nguyên.</p>
        {error && <AlertBox tone="error" className="mt-3">{error}</AlertBox>}
      </form>
    </Modal>
  );
}

/** Xác nhận xóa tài liệu và toàn bộ vector embedding liên quan. */
export function DeleteDocumentDialog({ document, onClose, onDone }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  const submit = async () => {
    setBusy(true);
    setError(null);
    try {
      await ragApi.deleteDocument(document.id);
      onDone(document);
    } catch (err) {
      setError(getErrorMessage(err));
      setBusy(false);
    }
  };

  return (
    <Modal
      open
      busy={busy}
      onClose={onClose}
      title="Xóa tài liệu"
      footer={
        <>
          <Button variant="outline" onClick={onClose} disabled={busy}>Hủy</Button>
          <Button variant="danger" icon={Trash2} loading={busy} onClick={submit}>Xóa tài liệu</Button>
        </>
      }
    >
      <p className="text-sm text-slate-600">
        Xóa <strong className="break-words text-navy-800">{document.file_name}</strong> cùng toàn bộ {formatNumber(document.total_chunks)} đoạn vector embedding? Không thể hoàn tác và không còn hỏi đáp được theo tài liệu này.
      </p>
      {error && <AlertBox tone="error" className="mt-3">{error}</AlertBox>}
    </Modal>
  );
}
