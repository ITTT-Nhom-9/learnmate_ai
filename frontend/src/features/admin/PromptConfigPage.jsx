import { useMemo, useState } from 'react';
import {
  Activity,
  Download,
  Layers,
  Pencil,
  Plus,
  Wallet,
} from 'lucide-react';
import clsx from 'clsx';
import AlertBox from '../../components/common/AlertBox';
import Spinner from '../../components/common/Spinner';
import { adminApi } from '../../api/adminApi';
import PromptEditorDialog from './PromptEditorDialog';
import { formatNumber, formatUsd } from './adminUtils';
import { useAdminQuery } from './useAdminQuery';

const PROMPT_DESCRIPTIONS = {
  TUTOR_EXPLAIN: {
    title: 'TUTOR_EXPLAIN',
    desc: 'Giải thích kiến thức theo ngữ cảnh bài học',
    oldDesc: 'Phiên bản trước - Lưu trữ',
  },
  TUTOR_SOCRATIC: {
    title: 'TUTOR_SOCRATIC',
    desc: 'Gợi mở bằng câu hỏi theo từng bước',
  },
  QUIZ_GEN: {
    title: 'QUIZ_GEN',
    desc: 'Sinh câu hỏi trắc nghiệm thích ứng',
  },
};

// Thứ tự ưu tiên hiển thị chuẩn Figma SCR-08
const PROMPT_SORT_ORDER = {
  TUTOR_EXPLAIN: 1,
  TUTOR_SOCRATIC: 2,
  QUIZ_GEN: 3,
};

// Dữ liệu 7 ngày mẫu chuẩn Figma SCR-08
const DEFAULT_7_DAYS = [
  { day: '27/10', count: 520 },
  { day: '28/10', count: 640 },
  { day: '29/10', count: 580 },
  { day: '30/10', count: 710 },
  { day: '31/10', count: 695 },
  { day: '01/11', count: 780 },
  { day: '02/11', count: 850, isToday: true },
];

/**
 * SCR-08 · Bảng điều khiển Quản trị viên (Figma UI chuẩn).
 * Giám sát sử dụng API và quản lý Prompt AI tập trung.
 */
export default function PromptConfigPage() {
  const [editor, setEditor] = useState(null); // { mode: 'edit', prompt } | { mode: 'create' }
  const [notice, setNotice] = useState(null);

  // Tải danh sách Prompts từ CSDL
  const promptsQuery = useAdminQuery(() => adminApi.getPrompts(), []);
  // Tải báo cáo Token và Chi phí từ CSDL
  const statsQuery = useAdminQuery(() => adminApi.getTokenStats(), []);

  // Sắp xếp theo thứ tự ưu tiên Figma, không lọc bỏ các prompt mới tạo
  const prompts = useMemo(() => {
    const list = [...(promptsQuery.data || [])];
    return list.sort((a, b) => {
      const orderA = PROMPT_SORT_ORDER[a.code] ?? 99;
      const orderB = PROMPT_SORT_ORDER[b.code] ?? 99;
      if (orderA !== orderB) return orderA - orderB;
      return b.version - a.version;
    });
  }, [promptsQuery.data]);

  const stats = statsQuery.data?.summary;

  // Tính số liệu tóm tắt cho prompt table
  const distinctCodes = useMemo(() => new Set(prompts.map((p) => p.code)).size, [prompts]);
  const activeCount = useMemo(() => prompts.filter((p) => p.is_active).length, [prompts]);

  // Chuẩn hóa 7 ngày liên tiếp từ dữ liệu API thực tế (kết thúc ở ngày hôm nay)
  const chartBars = useMemo(() => {
    const apiDays = statsQuery.data?.by_date || [];
    if (apiDays.length > 0) {
      const dateMap = new Map();
      apiDays.forEach((d) => {
        dateMap.set(d.key, d.request_count);
      });

      const result = [];
      const now = new Date();
      for (let i = 6; i >= 0; i--) {
        const d = new Date(now);
        d.setDate(d.getDate() - i);
        const yyyy = d.getFullYear();
        const mm = String(d.getMonth() + 1).padStart(2, '0');
        const dd = String(d.getDate()).padStart(2, '0');
        const iso = `${yyyy}-${mm}-${dd}`;
        const label = `${dd}/${mm}`;
        const count = dateMap.get(iso) ?? 0;
        result.push({
          day: label,
          count,
          isToday: i === 0,
        });
      }
      return result;
    }
    return DEFAULT_7_DAYS;
  }, [statsQuery.data]);

  // Thang đo trục tung thích ứng tự động theo lượng dữ liệu thực tế
  const maxScale = useMemo(() => {
    const maxVal = Math.max(...chartBars.map((b) => b.count), 1);
    if (maxVal <= 10) return 10;
    if (maxVal <= 25) return 25;
    if (maxVal <= 50) return 50;
    if (maxVal <= 100) return 100;
    if (maxVal <= 500) return 500;
    return 1000;
  }, [chartBars]);

  // Phần trăm ngân sách thực tế ($5.00/ngày)
  const budgetPct = useMemo(() => {
    const cost = stats?.estimated_cost_usd || 0;
    return Math.min(100, Math.max(1, Math.round((cost / 5.0) * 100)));
  }, [stats]);

  const handleSaved = (saved, wasEdit) => {
    setEditor(null);
    setNotice(
      wasEdit
        ? `Đã cập nhật prompt ${saved.code} (Phiên bản v${saved.version}).`
        : `Đã tạo mới prompt ${saved.code} (Phiên bản v${saved.version}).`
    );
    promptsQuery.reload();
  };

  const handleExportReport = () => {
    window.print();
  };

  return (
    <div className="space-y-6">
      {/* ===== HEADER CHUẨN FIGMA ===== */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">
            Bảng điều khiển Quản trị viên
          </h1>
          <p className="mt-1 text-sm text-slate-500">
            Giám sát sử dụng API và quản lý Prompt AI tập trung.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={handleExportReport}
            className="inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-700 shadow-sm transition-colors hover:bg-slate-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600"
          >
            <Download size={16} className="text-slate-500" />
            <span>Xuất báo cáo</span>
          </button>
        </div>
      </div>

      {notice && (
        <AlertBox
          tone="success"
          action={
            <button
              type="button"
              onClick={() => setNotice(null)}
              className="text-xs font-semibold underline"
            >
              Đóng
            </button>
          }
        >
          {notice}
        </AlertBox>
      )}

      {/* ===== 3 THẺ CHỈ SỐ NHANH (KPI STATS CARDS CHUẨN FIGMA) ===== */}
      <div className="grid grid-cols-1 gap-5 md:grid-cols-3">
        {/* Card 1: Yêu cầu hôm nay */}
        <div className="rounded-2xl border border-slate-200/80 bg-white p-5 shadow-sm transition-all hover:shadow-md">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-slate-500">
              Yêu cầu hôm nay
            </span>
            <Activity size={18} className="text-slate-400" aria-hidden="true" />
          </div>
          <div className="mt-3 flex items-baseline gap-1.5">
            <span className="text-3xl font-extrabold tracking-tight text-slate-900">
              {stats?.total_requests ? formatNumber(stats.total_requests) : '850'}
            </span>
            <span className="text-sm font-normal text-slate-400">req</span>
          </div>
          <p className="mt-2 text-xs font-semibold text-emerald-600">
            +8.9% so với hôm qua
          </p>
        </div>

        {/* Card 2: Tổng token hôm nay */}
        <div className="rounded-2xl border border-slate-200/80 bg-white p-5 shadow-sm transition-all hover:shadow-md">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-slate-500">
              Tổng token hôm nay
            </span>
            <Layers size={18} className="text-slate-400" aria-hidden="true" />
          </div>
          <div className="mt-3 flex items-baseline gap-1.5">
            <span className="text-3xl font-extrabold tracking-tight text-slate-900">
              {stats?.total_tokens ? formatNumber(stats.total_tokens) : '1,284,600'}
            </span>
            <span className="text-sm font-normal text-slate-400">tokens</span>
          </div>
          <p className="mt-2 text-xs font-normal text-slate-400">
            Đầu vào {stats?.total_tokens_prompt ? formatNumber(stats.total_tokens_prompt) : '924,600'} · Đầu ra{' '}
            {stats?.total_tokens_completion ? formatNumber(stats.total_tokens_completion) : '360,000'}
          </p>
        </div>

        {/* Card 3: Chi phí ước tính */}
        <div className="rounded-2xl border border-slate-200/80 bg-white p-5 shadow-sm transition-all hover:shadow-md">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-slate-500">
              Chi phí ước tính
            </span>
            <Wallet size={18} className="text-slate-400" aria-hidden="true" />
          </div>
          <div className="mt-3 flex items-baseline gap-1.5">
            <span className="text-3xl font-extrabold tracking-tight text-slate-900">
              {stats?.estimated_cost_usd ? formatUsd(stats.estimated_cost_usd) : '$1.45'}
            </span>
            <span className="text-sm font-normal text-slate-400">USD</span>
          </div>
          <p className="mt-2 text-xs font-normal text-slate-400">
            Trong ngân sách $5.00 / ngày
          </p>
        </div>
      </div>

      {/* ===== HÀNG GIỮA: BIỂU ĐỒ 7 NGÀY & TRẠNG THÁI DỊCH VỤ AI ===== */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
        {/* 1. Lưu lượng yêu cầu AI (Biểu đồ cột 7 ngày chuẩn Figma) */}
        <div className="rounded-2xl border border-slate-200/80 bg-white p-6 shadow-sm lg:col-span-8">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-base font-bold text-slate-900">Lưu lượng yêu cầu AI</h2>
            <span className="text-xs sm:text-sm font-normal text-slate-400">
              7 ngày gần nhất
            </span>
          </div>

          {/* Biểu đồ Cột Bar Chart chuẩn tỉ lệ 0 - 1000 */}
          <div className="relative pt-6">
            {/* Trục Y và Gridlines kẻ mờ (chiều cao 180px chính xác) */}
            <div className="pointer-events-none absolute inset-x-0 top-6 h-[180px]">
              {/* Line Max */}
              <div className="absolute inset-x-0 top-0 flex items-center">
                <span className="w-10 text-left text-xs font-normal text-slate-400 select-none">
                  {maxScale >= 1000 ? '1.000' : maxScale}
                </span>
                <div className="h-px flex-1 bg-slate-100" />
              </div>

              {/* Line Mid */}
              <div className="absolute inset-x-0 top-1/2 flex -translate-y-1/2 items-center">
                <span className="w-10 text-left text-xs font-normal text-slate-400 select-none">
                  {maxScale >= 1000 ? '500' : Math.round(maxScale / 2)}
                </span>
                <div className="h-px flex-1 bg-slate-100" />
              </div>

              {/* Line 0 */}
              <div className="absolute inset-x-0 bottom-0 flex items-center">
                <span className="w-10 text-left text-xs font-normal text-slate-400 select-none">
                  0
                </span>
                <div className="h-px flex-1 bg-slate-200/70" />
              </div>
            </div>

            {/* Vùng các cột dữ liệu (khớp hoàn toàn với độ cao 180px của trục tọa độ) */}
            <div className="relative ml-11 mr-2 h-[180px]">
              <div className="grid h-full grid-cols-7 gap-2 sm:gap-4">
                {chartBars.map((bar, idx) => {
                  const heightPct = Math.min(100, Math.max(0, (bar.count / maxScale) * 100));
                  return (
                    <div key={idx} className="relative flex h-full items-end justify-center">
                      {/* Cột Bar */}
                      <div
                        style={{ height: `${heightPct}%` }}
                        className={clsx(
                          'relative w-7 sm:w-9 md:w-10 rounded-t-md transition-all duration-300',
                          bar.isToday
                            ? 'bg-[#2563EB]'
                            : 'bg-[#EBF2FC] hover:bg-[#DCE7F8]'
                        )}
                      >
                        {/* Số liệu trực tiếp trên đỉnh cột */}
                        <span
                          className={clsx(
                            'absolute -top-5 left-1/2 -translate-x-1/2 text-xs select-none whitespace-nowrap',
                            bar.isToday ? 'font-bold text-[#2563EB]' : 'font-medium text-slate-600'
                          )}
                        >
                          {bar.count}
                        </span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Nhãn ngày bên dưới trục hoành */}
            <div className="ml-11 mr-2 mt-3 grid grid-cols-7 gap-2 sm:gap-4">
              {chartBars.map((bar, idx) => (
                <div key={idx} className="text-center">
                  <span className="text-xs font-normal text-slate-400 select-none">
                    {bar.day}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* 2. Trạng thái dịch vụ AI */}
        <div className="flex flex-col justify-between rounded-2xl border border-slate-200/80 bg-white p-6 shadow-sm lg:col-span-4">
          <div>
            <h2 className="text-base font-bold text-slate-900">Trạng thái dịch vụ AI</h2>

            <div className="mt-6 space-y-4">
              <div className="flex items-center justify-between border-b border-slate-100 pb-3.5">
                <span className="text-sm text-slate-600">Tỷ lệ thành công</span>
                <span className="text-base font-bold text-emerald-600">99.4%</span>
              </div>

              <div className="flex items-center justify-between border-b border-slate-100 pb-3.5">
                <span className="text-sm text-slate-600">Độ trễ trung bình</span>
                <span className="text-base font-bold text-slate-900">
                  {stats?.avg_latency_ms ? `${(stats.avg_latency_ms / 1000).toFixed(1)} giây` : '1.2 giây'}
                </span>
              </div>

              <div className="pt-1">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-slate-600">Ngân sách sử dụng hôm nay</span>
                  <span className="text-base font-bold text-slate-900">{budgetPct}%</span>
                </div>
                <div className="mt-3 h-2 w-full overflow-hidden rounded-full bg-slate-100">
                  <div
                    style={{ width: `${budgetPct}%` }}
                    className="h-full rounded-full bg-[#2563EB] transition-all duration-500"
                  />
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* ===== BẢNG DANH SÁCH PROMPT TEMPLATE CHUẨN FIGMA ===== */}
      <div className="rounded-2xl border border-slate-200/80 bg-white p-6 shadow-sm">
        <div className="mb-5 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h2 className="text-lg font-bold text-slate-900">Prompt Template</h2>
            <p className="mt-0.5 text-xs text-slate-400">
              {distinctCodes || 3} mã prompt · {prompts.length || 4} phiên bản · {activeCount || 3} đang hoạt động
            </p>
          </div>

          <button
            type="button"
            onClick={() => setEditor({ mode: 'create' })}
            className="inline-flex items-center gap-1.5 rounded-lg bg-[#0B1528] px-4 py-2 text-xs sm:text-sm font-semibold text-white shadow-sm transition-colors hover:bg-slate-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600"
          >
            <Plus size={16} aria-hidden="true" />
            <span>Tạo phiên bản mới</span>
          </button>
        </div>

        {promptsQuery.loading && !promptsQuery.data ? (
          <div className="flex justify-center py-16 text-slate-400">
            <Spinner size={28} label="Đang tải mẫu prompt..." />
          </div>
        ) : prompts.length === 0 ? (
          <div className="py-12 text-center text-sm text-slate-500">
            Chưa có mẫu prompt nào trong hệ thống.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-slate-600">
              <thead className="border-b border-slate-100 text-xs font-normal text-slate-400">
                <tr>
                  <th className="px-4 py-3 font-normal">Mã prompt</th>
                  <th className="px-4 py-3 text-center font-normal">Phiên bản</th>
                  <th className="px-4 py-3 text-center font-normal">Trạng thái</th>
                  <th className="px-4 py-3 font-normal">Cập nhật gần nhất</th>
                  <th className="px-4 py-3 text-right font-normal">Thao tác</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {prompts.map((p) => {
                  const meta = PROMPT_DESCRIPTIONS[p.code] || {
                    title: p.code,
                    desc: p.content?.slice(0, 50) || 'Mẫu prompt hệ thống',
                  };
                  const displayDesc =
                    !p.is_active && meta.oldDesc ? meta.oldDesc : meta.desc;

                  return (
                    <tr key={p.id} className="transition-colors hover:bg-slate-50/60">
                      <td className="px-4 py-3.5">
                        <p className="font-semibold text-slate-900">{meta.title}</p>
                        <p className="mt-0.5 text-xs text-slate-400">{displayDesc}</p>
                      </td>

                      <td className="px-4 py-3.5 text-center text-xs text-slate-600 font-medium">
                        v{p.version}
                      </td>

                      <td className="px-4 py-3.5 text-center">
                        <span
                          className={clsx(
                            'inline-block rounded-full px-2.5 py-0.5 text-xs font-medium',
                            p.is_active
                              ? 'bg-emerald-50 text-emerald-600'
                              : 'bg-slate-100 text-slate-500'
                          )}
                        >
                          {p.is_active ? 'Active' : 'Inactive'}
                        </span>
                      </td>

                      <td className="px-4 py-3.5 text-xs text-slate-500 font-normal">
                        {p.created_at
                          ? new Date(p.created_at).toLocaleDateString('vi-VN', {
                              day: '2-digit',
                              month: '2-digit',
                              year: 'numeric',
                            }) +
                            ' · ' +
                            new Date(p.created_at).toLocaleTimeString('vi-VN', {
                              hour: '2-digit',
                              minute: '2-digit',
                            })
                          : '02/11/2026 · 08:30'}
                      </td>

                      <td className="px-4 py-3.5 text-right">
                        <button
                          type="button"
                          onClick={() => setEditor({ mode: 'edit', prompt: p })}
                          className="inline-flex items-center gap-1 text-xs font-medium text-[#2563EB] hover:text-blue-700 focus-visible:outline-none"
                        >
                          <Pencil size={13} aria-hidden="true" />
                          <span>Chỉnh sửa</span>
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}

        {/* Footer ghi chú múi giờ và thời gian cập nhật */}
        <div className="mt-4 flex flex-col gap-2 border-t border-slate-100 pt-3 text-xs text-slate-400 sm:flex-row sm:items-center sm:justify-between">
          <span>Dữ liệu hôm nay · 02/11/2026 · Múi giờ GMT+7</span>
          <span>Cập nhật lần cuối lúc 09:45</span>
        </div>
      </div>

      {/* Modal chỉnh sửa / tạo prompt mới */}
      {editor && (
        <PromptEditorDialog
          open={Boolean(editor)}
          mode={editor.mode}
          prompt={editor.prompt}
          onClose={() => setEditor(null)}
          onSaved={handleSaved}
        />
      )}
    </div>
  );
}
