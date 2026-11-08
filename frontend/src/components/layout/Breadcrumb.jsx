import { Link } from 'react-router-dom';
import { ChevronRight } from 'lucide-react';

/** items: [{ label, to? }] - phần tử cuối là trang hiện tại (không có liên kết). */
export default function Breadcrumb({ items }) {
  return (
    <nav aria-label="Đường dẫn" className="min-w-0">
      <ol className="flex flex-wrap items-center gap-1.5 text-sm text-slate-500">
        {items.map((item, index) => {
          const isLast = index === items.length - 1;
          return (
            <li key={`${item.label}-${index}`} className="flex min-w-0 items-center gap-1.5">
              {item.to && !isLast ? (
                <Link to={item.to} className="hover:text-navy-800 hover:underline">
                  {item.label}
                </Link>
              ) : (
                <span aria-current={isLast ? 'page' : undefined} className={isLast ? 'truncate font-semibold text-navy-800' : ''}>
                  {item.label}
                </span>
              )}
              {!isLast && <ChevronRight size={14} className="shrink-0 text-slate-400" aria-hidden="true" />}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
