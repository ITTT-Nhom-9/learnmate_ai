import { useState } from 'react';
import AlertBox from '../../components/common/AlertBox';
import Button from '../../components/common/Button';
import Modal from '../../components/common/Modal';
import { adminApi } from '../../api/adminApi';
import { getErrorMessage } from '../../utils/apiError';
import { FilterSelect } from './AdminCommon';
import { PROMPT_CODES } from './adminUtils';

/**
 * Soạn / sửa Prompt Template.
 *  - mode="edit": sửa nội dung và bật/tắt kích hoạt phiên bản hiện tại (PUT /admin/prompts/{id}).
 *  - mode="create": tạo phiên bản mới cho một mã (POST /admin/prompts), version tự tăng, phục vụ A/B Testing.
 * templates: { [code]: nội dung đang kích hoạt } để điền sẵn khi tạo phiên bản mới.
 */
export default function PromptEditorDialog({ mode, prompt, defaultCode = 'TUTOR_EXPLAIN', templates = {}, onClose, onSaved }) {
  const isEdit = mode === 'edit' || (Boolean(prompt) && mode !== 'create');
  const [code, setCode] = useState(prompt?.code || defaultCode);
  const [content, setContent] = useState(prompt?.content || templates[defaultCode] || '');
  const [isActive, setIsActive] = useState(prompt?.is_active ?? true);
  const [dirty, setDirty] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  // Các biến {topic}, {context}... mà Backend sẽ thay thế khi gọi AI
  const variables = [...new Set([...content.matchAll(/\{(\w+)\}/g)].map((m) => m[1]))];

  const changeCode = (next) => {
    setCode(next);
    if (!dirty) setContent(templates[next] || ''); // chưa gõ gì thì điền sẵn nội dung bản đang dùng của mã mới chọn
  };

  const submit = async () => {
    if (!content.trim()) {
      setError('Nội dung prompt không được để trống.');
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const saved = isEdit
        ? await adminApi.updatePrompt(prompt.id, { content: content.trim(), isActive })
        : await adminApi.createPrompt({ code, content: content.trim(), isActive });
      onSaved(saved, isEdit);
    } catch (err) {
      setError(getErrorMessage(err)); // ví dụ 409: phiên bản đã tồn tại
      setBusy(false);
    }
  };

  return (
    <Modal
      open
      size="lg"
      busy={busy}
      onClose={onClose}
      title={isEdit ? `Sửa prompt ${prompt.code} · v${prompt.version}` : 'Tạo phiên bản prompt mới'}
      footer={
        <>
          <Button variant="outline" onClick={onClose} disabled={busy}>Hủy</Button>
          <Button loading={busy} onClick={submit}>{isEdit ? 'Lưu thay đổi' : 'Tạo phiên bản'}</Button>
        </>
      }
    >
      {isEdit ? (
        <AlertBox tone="info" className="mb-4">
          Thay đổi áp dụng ngay cho phiên bản v{prompt.version}. Muốn thử nghiệm song song (A/B), hãy tạo phiên bản mới thay vì sửa trực tiếp.
        </AlertBox>
      ) : (
        <div className="mb-4">
          <label htmlFor="prompt-code" className="mb-1.5 block text-sm font-medium text-slate-700">Mã tính năng</label>
          <FilterSelect id="prompt-code" label="Mã tính năng" value={code} onChange={changeCode} className="w-full">
            {Object.entries(PROMPT_CODES).map(([value, label]) => (
              <option key={value} value={value}>{value} — {label}</option>
            ))}
          </FilterSelect>
        </div>
      )}

      <label htmlFor="prompt-content" className="mb-1.5 block text-sm font-medium text-slate-700">Nội dung System Prompt</label>
      <textarea
        id="prompt-content"
        value={content}
        onChange={(e) => {
          setContent(e.target.value);
          setDirty(true);
        }}
        rows={12}
        spellCheck={false}
        className="w-full resize-y rounded-lg border border-slate-300 px-3.5 py-3 font-mono text-sm leading-relaxed focus:border-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-100"
      />
      <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-slate-500">
        <span>{content.length.toLocaleString('vi-VN')} ký tự</span>
        {variables.length > 0 && (
          <span>
            Biến phát hiện: {variables.map((v) => (
              <code key={v} className="mr-1 rounded bg-slate-100 px-1.5 py-0.5 font-mono text-slate-700">{`{${v}}`}</code>
            ))}
          </span>
        )}
      </div>

      <label className="mt-4 flex cursor-pointer items-start gap-2.5 text-sm text-slate-700">
        <input type="checkbox" checked={isActive} onChange={(e) => setIsActive(e.target.checked)} className="mt-0.5 h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-600" />
        <span>
          Kích hoạt phiên bản này
          <span className="block text-xs text-slate-500">Mỗi mã chỉ có một phiên bản đang dùng; kích hoạt sẽ tự tắt các phiên bản cũ cùng mã.</span>
        </span>
      </label>

      {error && <AlertBox tone="error" className="mt-3">{error}</AlertBox>}
    </Modal>
  );
}
