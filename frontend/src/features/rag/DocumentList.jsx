import { FileText, Pencil, Trash2 } from 'lucide-react';
import AlertBox from '../../components/common/AlertBox';
import Button from '../../components/common/Button';
import EmptyState from '../../components/common/EmptyState';
import Spinner from '../../components/common/Spinner';
import { Panel } from '../admin/AdminCommon';
import { formatBytes, formatDate, formatNumber } from '../admin/adminUtils';

/**
 * Danh sách tài liệu của môn: bảng (desktop) / thẻ (mobile).
 * canManage(doc) quyết định có hiện nút Đổi tên / Xóa hay không (chủ tài liệu hoặc Admin).
 */
export default function DocumentList({ documents, loading, error, onReload, onRename, onDelete, canManage, className }) {
  const actions = (d) =>
    canManage(d) ? (
      <div className="flex gap-1 md:justify-end">
        <Button variant="ghost" size="sm" icon={Pencil} onClick={() => onRename(d)} aria-label={`Đổi tên ${d.file_name}`}>
          <span className="md:hidden">Đổi tên</span>
        </Button>
        <Button variant="ghost" size="sm" icon={Trash2} onClick={() => onDelete(d)} aria-label={`Xóa ${d.file_name}`} className="text-red-600 hover:bg-red-50">
          <span className="md:hidden">Xóa</span>
        </Button>
      </div>
    ) : null;

  return (
    <Panel title={`Tài liệu đã lập chỉ mục${documents ? ` (${documents.length})` : ''}`} icon={FileText} className={className}>
      {error && <AlertBox tone="error" action={<Button variant="outline" size="sm" onClick={onReload}>Thử lại</Button>}>{error}</AlertBox>}
      {loading && !documents && <div className="flex justify-center py-12 text-slate-400"><Spinner size={24} label="Đang tải tài liệu" /></div>}
      {documents && documents.length === 0 && (
        <EmptyState icon={FileText} title="Chưa có tài liệu" description="Tải lên giáo trình PDF để hỏi đáp kèm trích dẫn số trang." />
      )}

      {documents?.length > 0 && (
        <div className={loading ? 'opacity-60 transition-opacity' : 'transition-opacity'}>
          <div className="hidden overflow-x-auto md:block">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-slate-200 text-xs font-semibold uppercase tracking-wide text-slate-500">
                  <th className="px-3 py-2.5">Tên tệp</th>
                  <th className="whitespace-nowrap px-3 py-2.5 text-right">Dung lượng</th>
                  <th className="px-3 py-2.5 text-right">Trang</th>
                  <th className="px-3 py-2.5 text-right">Đoạn</th>
                  <th className="whitespace-nowrap px-3 py-2.5">Lập chỉ mục</th>
                  <th className="px-3 py-2.5"><span className="sr-only">Thao tác</span></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {documents.map((d) => (
                  <tr key={d.id} className="hover:bg-slate-50">
                    <td className="max-w-[16rem] px-3 py-3">
                      <span className="flex items-center gap-2">
                        <FileText size={16} className="shrink-0 text-red-500" aria-hidden="true" />
                        <span className="truncate font-medium text-slate-700" title={d.file_name}>{d.file_name}</span>
                      </span>
                    </td>
                    <td className="whitespace-nowrap px-3 py-3 text-right text-slate-600">{formatBytes(d.file_size)}</td>
                    <td className="px-3 py-3 text-right text-slate-600">{d.total_pages != null ? formatNumber(d.total_pages) : '—'}</td>
                    <td className="px-3 py-3 text-right text-slate-600">{formatNumber(d.total_chunks)}</td>
                    <td className="whitespace-nowrap px-3 py-3 text-slate-500">{formatDate(d.created_at)}</td>
                    <td className="px-3 py-3">{actions(d)}</td>
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
                <p className="mt-2 text-xs text-slate-500">
                  {formatBytes(d.file_size)}
                  {d.total_pages != null ? ` · ${formatNumber(d.total_pages)} trang` : ''} · {formatNumber(d.total_chunks)} đoạn · {formatDate(d.created_at)}
                </p>
                {canManage(d) && <div className="mt-3">{actions(d)}</div>}
              </li>
            ))}
          </ul>
        </div>
      )}
    </Panel>
  );
}
