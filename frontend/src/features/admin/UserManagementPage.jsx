import { useEffect, useState } from 'react';
import { Lock, Search, Unlock, Users } from 'lucide-react';
import AlertBox from '../../components/common/AlertBox';
import Badge from '../../components/common/Badge';
import Button from '../../components/common/Button';
import EmptyState from '../../components/common/EmptyState';
import Modal from '../../components/common/Modal';
import Spinner from '../../components/common/Spinner';
import { adminApi } from '../../api/adminApi';
import { useAuth } from '../../hooks/useAuth';
import { getErrorMessage } from '../../utils/apiError';
import { getInitials } from '../../utils/formatters';
import { AdminPageHeader, FilterSelect, Pagination, Panel } from './AdminCommon';
import { formatDate } from './adminUtils';
import { useAdminQuery } from './useAdminQuery';

const PAGE_SIZE = 10;
const ROLE_LABEL = { STUDENT: 'Sinh viên', ADMIN: 'Quản trị viên' };

const RoleBadge = ({ role }) => <Badge tone={role === 'ADMIN' ? 'blue' : 'gray'}>{ROLE_LABEL[role] || role}</Badge>;
const StatusBadge = ({ status }) => (
  <Badge tone={status === 'ACTIVE' ? 'green' : 'red'}>{status === 'ACTIVE' ? 'Hoạt động' : 'Đã khóa'}</Badge>
);

function Avatar({ name }) {
  return (
    <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-blue-50 text-xs font-semibold text-blue-700">
      {getInitials(name)}
    </span>
  );
}

/** Hộp thoại xác nhận khóa / mở khóa. Khóa tài khoản sẽ thu hồi toàn bộ refresh token của người đó. */
function UserStatusDialog({ user, onClose, onDone }) {
  const [reason, setReason] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const locking = user.status === 'ACTIVE';

  const submit = async () => {
    setBusy(true);
    setError(null);
    try {
      const updated = await adminApi.updateUserStatus(user.id, { status: locking ? 'LOCKED' : 'ACTIVE', reason: reason.trim() });
      onDone(updated, locking);
    } catch (err) {
      setError(getErrorMessage(err)); // ví dụ: không thể tự khóa mình / khóa Admin duy nhất
      setBusy(false);
    }
  };

  return (
    <Modal
      open
      busy={busy}
      onClose={onClose}
      title={locking ? 'Khóa tài khoản' : 'Mở khóa tài khoản'}
      footer={
        <>
          <Button variant="outline" onClick={onClose} disabled={busy}>Hủy</Button>
          <Button variant={locking ? 'danger' : 'primary'} icon={locking ? Lock : Unlock} loading={busy} onClick={submit}>
            {locking ? 'Khóa tài khoản' : 'Mở khóa'}
          </Button>
        </>
      }
    >
      <p className="text-sm text-slate-600">
        {locking
          ? <>Người dùng <strong className="text-navy-800">{user.full_name}</strong> sẽ bị đăng xuất khỏi mọi thiết bị và không thể đăng nhập lại cho đến khi được mở khóa.</>
          : <>Người dùng <strong className="text-navy-800">{user.full_name}</strong> sẽ có thể đăng nhập và sử dụng hệ thống trở lại.</>}
      </p>
      <label htmlFor="status-reason" className="mb-1.5 mt-4 block text-sm font-medium text-slate-700">Lý do (không bắt buộc)</label>
      <textarea
        id="status-reason"
        value={reason}
        onChange={(e) => setReason(e.target.value)}
        maxLength={255}
        rows={3}
        className="w-full rounded-lg border border-slate-300 px-3.5 py-2.5 text-base focus:border-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-100 sm:text-sm"
      />
      {error && <AlertBox tone="error" className="mt-3">{error}</AlertBox>}
    </Modal>
  );
}

/** SCR-08 · Quản lý người dùng (API-16): tìm kiếm, lọc vai trò/trạng thái, phân trang, khóa / mở khóa. */
export default function UserManagementPage() {
  const { user: me } = useAuth();
  const [search, setSearch] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [role, setRole] = useState('');
  const [status, setStatus] = useState('');
  const [page, setPage] = useState(1);
  const [target, setTarget] = useState(null);
  const [notice, setNotice] = useState(null);

  // Chờ 400ms sau lần gõ cuối mới gọi API để tránh bắn request theo từng phím
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearch(search.trim());
      setPage(1);
    }, 400);
    return () => clearTimeout(timer);
  }, [search]);

  const { data, loading, error, reload } = useAdminQuery(
    () => adminApi.getUsers({ page, pageSize: PAGE_SIZE, search: debouncedSearch, role, status }),
    [page, debouncedSearch, role, status]
  );
  const users = data?.items ?? [];

  const changeFilter = (setter) => (value) => {
    setter(value);
    setPage(1);
  };

  const handleDone = (updated, locked) => {
    setTarget(null);
    setNotice(`Đã ${locked ? 'khóa' : 'mở khóa'} tài khoản ${updated.full_name}.`);
    reload();
  };

  const renderAction = (u) =>
    u.id === me?.id ? (
      <span className="text-xs text-slate-400">Tài khoản của bạn</span>
    ) : (
      <Button
        variant="outline"
        size="sm"
        icon={u.status === 'ACTIVE' ? Lock : Unlock}
        onClick={() => setTarget(u)}
        className="w-full md:w-auto"
      >
        {u.status === 'ACTIVE' ? 'Khóa' : 'Mở khóa'}
      </Button>
    );

  return (
    <>
      <AdminPageHeader title="Quản lý người dùng" description="Tìm kiếm tài khoản, khóa hoặc mở khóa khi cần." />

      {notice && (
        <AlertBox tone="success" className="mb-4" action={<button type="button" onClick={() => setNotice(null)} className="text-xs font-semibold underline">Đóng</button>}>
          {notice}
        </AlertBox>
      )}

      <Panel>
        <div className="mb-4 flex flex-col gap-3 sm:flex-row">
          <div className="relative flex-1">
            <Search size={16} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" aria-hidden="true" />
            <input
              type="search"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Tìm theo họ tên hoặc email"
              aria-label="Tìm người dùng"
              className="h-10 w-full rounded-lg border border-slate-300 bg-white pl-9 pr-3 text-base shadow-sm focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/20 sm:text-sm"
            />
          </div>
          <div className="flex gap-3">
            <FilterSelect label="Lọc theo vai trò" value={role} onChange={changeFilter(setRole)} className="flex-1 sm:flex-none">
              <option value="">Mọi vai trò</option>
              <option value="STUDENT">Sinh viên</option>
              <option value="ADMIN">Quản trị viên</option>
            </FilterSelect>
            <FilterSelect label="Lọc theo trạng thái" value={status} onChange={changeFilter(setStatus)} className="flex-1 sm:flex-none">
              <option value="">Mọi trạng thái</option>
              <option value="ACTIVE">Hoạt động</option>
              <option value="LOCKED">Đã khóa</option>
            </FilterSelect>
          </div>
        </div>

        {error && (
          <AlertBox tone="error" action={<Button variant="outline" size="sm" onClick={reload}>Thử lại</Button>}>{error}</AlertBox>
        )}

        {loading && !data && <div className="flex justify-center py-16 text-slate-400"><Spinner size={28} label="Đang tải người dùng" /></div>}

        {data && users.length === 0 && (
          <EmptyState icon={Users} title="Không tìm thấy người dùng" description="Thử đổi từ khóa hoặc bộ lọc." />
        )}

        {users.length > 0 && (
          <div className={loading ? 'opacity-60 transition-opacity' : 'transition-opacity'}>
            {/* Desktop / tablet: bảng nhiều cột */}
            <div className="hidden overflow-x-auto md:block">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-slate-200 text-xs font-semibold uppercase tracking-wide text-slate-500">
                    <th className="px-3 py-2.5">Người dùng</th>
                    <th className="px-3 py-2.5">Vai trò</th>
                    <th className="px-3 py-2.5">Trạng thái</th>
                    <th className="whitespace-nowrap px-3 py-2.5">Ngày tạo</th>
                    <th className="px-3 py-2.5 text-right">Thao tác</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {users.map((u) => (
                    <tr key={u.id} className="hover:bg-slate-50">
                      <td className="px-3 py-3">
                        <div className="flex items-center gap-3">
                          <Avatar name={u.full_name} />
                          <div className="min-w-0">
                            <p className="truncate font-medium text-navy-800">{u.full_name}</p>
                            <p className="truncate text-xs text-slate-500">{u.email}</p>
                          </div>
                        </div>
                      </td>
                      <td className="px-3 py-3"><RoleBadge role={u.role} /></td>
                      <td className="px-3 py-3"><StatusBadge status={u.status} /></td>
                      <td className="whitespace-nowrap px-3 py-3 text-slate-500">{formatDate(u.created_at)}</td>
                      <td className="px-3 py-3 text-right">{renderAction(u)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Mobile: danh sách thẻ */}
            <ul className="space-y-3 md:hidden">
              {users.map((u) => (
                <li key={u.id} className="rounded-xl border border-slate-200 p-4">
                  <div className="flex items-center gap-3">
                    <Avatar name={u.full_name} />
                    <div className="min-w-0 flex-1">
                      <p className="truncate font-semibold text-navy-800">{u.full_name}</p>
                      <p className="truncate text-xs text-slate-500">{u.email}</p>
                    </div>
                  </div>
                  <div className="mt-3 flex flex-wrap items-center gap-2">
                    <RoleBadge role={u.role} />
                    <StatusBadge status={u.status} />
                    <span className="text-xs text-slate-400">Tạo {formatDate(u.created_at)}</span>
                  </div>
                  <div className="mt-3">{renderAction(u)}</div>
                </li>
              ))}
            </ul>

            <Pagination page={data.page} totalPages={data.total_pages} total={data.total} pageSize={data.page_size} onChange={setPage} disabled={loading} />
          </div>
        )}
      </Panel>

      {target && <UserStatusDialog key={target.id} user={target} onClose={() => setTarget(null)} onDone={handleDone} />}
    </>
  );
}
