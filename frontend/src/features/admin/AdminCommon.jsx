import { ChevronLeft, ChevronRight } from 'lucide-react';
import clsx from 'clsx';
import Button from '../../components/common/Button';
import { formatNumber } from './adminUtils';

/** Tiêu đề trang Admin: tên + mô tả bên trái, nút thao tác bên phải. */
export function AdminPageHeader({ title, description, actions }) {
  return (
    <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">{title}</h1>
        {description && <p className="mt-1 text-sm text-slate-500">{description}</p>}
      </div>
      {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
    </div>
  );
}

/** Khung trắng bo góc dùng chung cho mọi khối nội dung Admin. */
export function Panel({ title, icon: Icon, aside, className, children }) {
  return (
    <section className={clsx('rounded-xl border border-slate-200 bg-white p-4 shadow-sm sm:p-5', className)}>
      {title && (
        <div className="mb-4 flex items-center justify-between gap-3">
          <h2 className="flex items-center gap-2 text-base font-semibold text-navy-800">
            {Icon && <Icon size={18} className="text-brand-500" aria-hidden="true" />}
            {title}
          </h2>
          {aside}
        </div>
      )}
      {children}
    </section>
  );
}

/** Ô <select> thống nhất kiểu dáng với CourseSelector của SCR-07. */
export function FilterSelect({ id, label, value, onChange, children, className }) {
  return (
    <select
      id={id}
      value={value}
      onChange={(e) => onChange(e.target.value)}
      aria-label={label}
      className={clsx(
        'h-10 rounded-lg border border-slate-300 bg-white px-3 text-sm font-medium text-navy-800 shadow-sm transition-colors',
        'hover:border-slate-400 focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/20',
        className
      )}
    >
      {children}
    </select>
  );
}

/** Phân trang theo hợp đồng Backend: page, page_size, total, total_pages. */
export function Pagination({ page, totalPages, total, pageSize, onChange, disabled }) {
  if (!total) return null;
  const from = (page - 1) * pageSize + 1;
  const to = Math.min(total, page * pageSize);
  return (
    <div className="mt-4 flex flex-col items-center gap-3 border-t border-slate-100 pt-4 text-sm text-slate-500 sm:flex-row sm:justify-between">
      <span>
        Hiển thị {formatNumber(from)}–{formatNumber(to)} / {formatNumber(total)}
      </span>
      <div className="flex items-center gap-2">
        <Button variant="outline" size="sm" icon={ChevronLeft} disabled={disabled || page <= 1} onClick={() => onChange(page - 1)}>
          Trước
        </Button>
        <span className="min-w-[4.5rem] text-center font-medium text-slate-700">
          {page} / {Math.max(1, totalPages)}
        </span>
        <Button variant="outline" size="sm" disabled={disabled || page >= totalPages} onClick={() => onChange(page + 1)}>
          Sau <ChevronRight size={16} aria-hidden="true" />
        </Button>
      </div>
    </div>
  );
}
