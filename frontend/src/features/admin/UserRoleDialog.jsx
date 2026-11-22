import { useState } from 'react';
import { ShieldCheck, ShieldOff } from 'lucide-react';
import AlertBox from '../../components/common/AlertBox';
import Button from '../../components/common/Button';
import Modal from '../../components/common/Modal';
import { adminApi } from '../../api/adminApi';
import { getErrorMessage } from '../../utils/apiError';

/** Hộp thoại xác nhận phân quyền STUDENT <-> ADMIN (FR-AD-01). Nút chỉ hiện với người dùng khác chính mình. */
export default function UserRoleDialog({ user, onClose, onDone }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const promoting = user.role !== 'ADMIN';
  const nextRole = promoting ? 'ADMIN' : 'STUDENT';

  const submit = async () => {
    setBusy(true);
    setError(null);
    try {
      const updated = await adminApi.updateUserRole(user.id, nextRole);
      onDone(updated, promoting);
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
      title={promoting ? 'Cấp quyền Quản trị viên' : 'Thu hồi quyền Quản trị viên'}
      footer={
        <>
          <Button variant="outline" onClick={onClose} disabled={busy}>Hủy</Button>
          <Button variant={promoting ? 'primary' : 'danger'} icon={promoting ? ShieldCheck : ShieldOff} loading={busy} onClick={submit}>
            {promoting ? 'Cấp quyền Admin' : 'Chuyển về Sinh viên'}
          </Button>
        </>
      }
    >
      {promoting ? (
        <>
          <p className="text-sm text-slate-600">
            <strong className="text-navy-800">{user.full_name}</strong> sẽ trở thành Quản trị viên.
          </p>
          <AlertBox tone="info" className="mt-3">
            Quản trị viên có toàn quyền: khóa/mở khóa người dùng, đổi vai trò, sửa Prompt AI, xem chi phí token và quản lý mọi tài liệu RAG.
          </AlertBox>
        </>
      ) : (
        <p className="text-sm text-slate-600">
          <strong className="text-navy-800">{user.full_name}</strong> sẽ trở lại vai trò Sinh viên và mất toàn bộ quyền quản trị ngay ở lần tải trang tiếp theo.
        </p>
      )}
      {error && <AlertBox tone="error" className="mt-3">{error}</AlertBox>}
    </Modal>
  );
}
