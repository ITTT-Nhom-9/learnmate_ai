import { useMemo, useState } from 'react';
import { Pencil, Plus, ScrollText, Zap } from 'lucide-react';
import AlertBox from '../../components/common/AlertBox';
import Badge from '../../components/common/Badge';
import Button from '../../components/common/Button';
import EmptyState from '../../components/common/EmptyState';
import Spinner from '../../components/common/Spinner';
import { adminApi } from '../../api/adminApi';
import { getErrorMessage } from '../../utils/apiError';
import { AdminPageHeader, FilterSelect, Panel } from './AdminCommon';
import PromptEditorDialog from './PromptEditorDialog';
import { PROMPT_CODES, formatDate } from './adminUtils';
import { useAdminQuery } from './useAdminQuery';

const CODE_ORDER = Object.keys(PROMPT_CODES);
const preview = (text) => {
  const flat = (text || '').replace(/\s+/g, ' ').trim();
  return flat.length > 110 ? `${flat.slice(0, 110)}…` : flat;
};

/** SCR-08 · Cấu hình Prompt Templates (API-17): xem các phiên bản, sửa nội dung, tạo phiên bản mới, đổi bản đang dùng. */
export default function PromptConfigPage() {
  const [code, setCode] = useState('');
  const [editor, setEditor] = useState(null); // { mode: 'edit', prompt } | { mode: 'create' }
  const [notice, setNotice] = useState(null);
  const [actionError, setActionError] = useState(null);
  const [busyId, setBusyId] = useState(null);

  const { data, loading, error, reload } = useAdminQuery(() => adminApi.getPrompts({ code }), [code]);

  // Sắp xếp theo thứ tự tính năng rồi phiên bản mới nhất lên trước
  const prompts = useMemo(
    () => [...(data || [])].sort((a, b) => CODE_ORDER.indexOf(a.code) - CODE_ORDER.indexOf(b.code) || b.version - a.version),
    [data]
  );
  const templates = useMemo(
    () => Object.fromEntries(prompts.filter((p) => p.is_active).map((p) => [p.code, p.content])),
    [prompts]
  );

  const activate = async (p) => {
    setBusyId(p.id);
    setActionError(null);
    try {
      await adminApi.updatePrompt(p.id, { isActive: true });
      setNotice(`Đã kích hoạt ${p.code} v${p.version}; các phiên bản khác của mã này đã được tắt.`);
      reload();
    } catch (err) {
      setActionError(getErrorMessage(err));
    } finally {
      setBusyId(null);
    }
  };

  const handleSaved = (saved, wasEdit) => {
    setEditor(null);
    setNotice(wasEdit ? `Đã lưu ${saved.code} v${saved.version}.` : `Đã tạo ${saved.code} v${saved.version}.`);
    reload();
  };

  const renderActions = (p) => (
    <div className="flex flex-wrap gap-2 md:justify-end">
      <Button variant="outline" size="sm" icon={Pencil} onClick={() => setEditor({ mode: 'edit', prompt: p })}>Sửa</Button>
      {!p.is_active && (
        <Button variant="ghost" size="sm" icon={Zap} loading={busyId === p.id} onClick={() => activate(p)}>Kích hoạt</Button>
      )}
    </div>
  );

  const statusBadge = (p) => <Badge tone={p.is_active ? 'green' : 'gray'}>{p.is_active ? 'Đang dùng' : 'Không dùng'}</Badge>;

  return (
    <>
      <AdminPageHeader
        title="Cấu hình Prompt AI"
        description="Chỉnh System Prompt của Gia sư AI, Socratic, Sinh Quiz và RAG ngay trên web."
        actions={
          <>
            <FilterSelect label="Lọc theo mã prompt" value={code} onChange={setCode}>
              <option value="">Tất cả mã</option>
              {CODE_ORDER.map((c) => <option key={c} value={c}>{c}</option>)}
            </FilterSelect>
            <Button icon={Plus} onClick={() => setEditor({ mode: 'create' })}>Tạo phiên bản mới</Button>
          </>
        }
      />

      {notice && (
        <AlertBox tone="success" className="mb-4" action={<button type="button" onClick={() => setNotice(null)} className="text-xs font-semibold underline">Đóng</button>}>
          {notice}
        </AlertBox>
      )}
      {actionError && <AlertBox tone="error" className="mb-4">{actionError}</AlertBox>}

      <Panel>
        {error && <AlertBox tone="error" action={<Button variant="outline" size="sm" onClick={reload}>Thử lại</Button>}>{error}</AlertBox>}
        {loading && !data && <div className="flex justify-center py-16 text-slate-400"><Spinner size={28} label="Đang tải prompt" /></div>}
        {data && prompts.length === 0 && (
          <EmptyState icon={ScrollText} title="Chưa có mẫu prompt" description="Tạo phiên bản đầu tiên để Backend dùng khi gọi AI." />
        )}

        {prompts.length > 0 && (
          <div className={loading ? 'opacity-60 transition-opacity' : 'transition-opacity'}>
            {/* Desktop / tablet: bảng nhiều cột */}
            <div className="hidden overflow-x-auto md:block">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-slate-200 text-xs font-semibold uppercase tracking-wide text-slate-500">
                    <th className="px-3 py-2.5">Mã prompt</th>
                    <th className="px-3 py-2.5">Phiên bản</th>
                    <th className="px-3 py-2.5">Trạng thái</th>
                    <th className="px-3 py-2.5">Nội dung</th>
                    <th className="whitespace-nowrap px-3 py-2.5">Ngày tạo</th>
                    <th className="px-3 py-2.5 text-right">Thao tác</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {prompts.map((p) => (
                    <tr key={p.id} className="align-top hover:bg-slate-50">
                      <td className="px-3 py-3">
                        <p className="font-mono text-xs font-semibold text-navy-800">{p.code}</p>
                        <p className="text-xs text-slate-500">{PROMPT_CODES[p.code]}</p>
                      </td>
                      <td className="whitespace-nowrap px-3 py-3 font-medium text-slate-700">v{p.version}</td>
                      <td className="px-3 py-3">{statusBadge(p)}</td>
                      <td className="max-w-xs px-3 py-3 text-slate-600">{preview(p.content)}</td>
                      <td className="whitespace-nowrap px-3 py-3 text-slate-500">{formatDate(p.created_at)}</td>
                      <td className="px-3 py-3">{renderActions(p)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Mobile: Detail Card View */}
            <ul className="space-y-3 md:hidden">
              {prompts.map((p) => (
                <li key={p.id} className="rounded-xl border border-slate-200 p-4">
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0">
                      <p className="truncate font-mono text-xs font-semibold text-navy-800">{p.code} · v{p.version}</p>
                      <p className="text-xs text-slate-500">{PROMPT_CODES[p.code]}</p>
                    </div>
                    {statusBadge(p)}
                  </div>
                  <p className="mt-2 text-sm text-slate-600">{preview(p.content)}</p>
                  <p className="mt-2 text-xs text-slate-400">Tạo {formatDate(p.created_at)}</p>
                  <div className="mt-3">{renderActions(p)}</div>
                </li>
              ))}
            </ul>
          </div>
        )}
      </Panel>

      {editor && (
        <PromptEditorDialog
          mode={editor.mode}
          prompt={editor.prompt}
          defaultCode={code || CODE_ORDER[0]}
          templates={templates}
          onClose={() => setEditor(null)}
          onSaved={handleSaved}
        />
      )}
    </>
  );
}
