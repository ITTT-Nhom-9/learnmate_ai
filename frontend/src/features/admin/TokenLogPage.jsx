import { useState } from 'react';
import { Activity, BarChart3, Coins, Timer, Zap } from 'lucide-react';
import AlertBox from '../../components/common/AlertBox';
import Badge from '../../components/common/Badge';
import Button from '../../components/common/Button';
import EmptyState from '../../components/common/EmptyState';
import ProgressBar from '../../components/common/ProgressBar';
import Spinner from '../../components/common/Spinner';
import { adminApi } from '../../api/adminApi';
import { AdminPageHeader, FilterSelect, Pagination, Panel } from './AdminCommon';
import { FEATURE_LABELS, daysAgo, formatDateTime, formatNumber, formatUsd, formatVnd, toInputDate } from './adminUtils';
import { useAdminQuery } from './useAdminQuery';

const PAGE_SIZE = 10;
const PRESETS = [
  { label: '7 ngày', days: 7 },
  { label: '30 ngày', days: 30 },
  { label: 'Tất cả', days: null },
];

function StatCard({ icon: Icon, label, value, hint }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex items-center gap-2 text-xs font-medium text-slate-500">
        <Icon size={16} className="text-brand-500" aria-hidden="true" />
        {label}
      </div>
      <p className="mt-2 break-words text-xl font-bold text-navy-800 sm:text-2xl">{value}</p>
      {hint && <p className="mt-1 text-xs text-slate-400">{hint}</p>}
    </div>
  );
}

/** Danh sách nhóm (theo tính năng / nhà cung cấp) kèm thanh tỷ trọng theo tổng token. */
function GroupBreakdown({ groups = [], totalTokens, labelOf }) {
  if (groups.length === 0) return <p className="py-6 text-center text-sm text-slate-400">Chưa có dữ liệu trong khoảng thời gian này.</p>;
  return (
    <ul className="space-y-4">
      {groups.map((g) => {
        const share = totalTokens ? (g.total_tokens / totalTokens) * 100 : 0;
        return (
          <li key={g.key}>
            <div className="mb-1.5 flex items-baseline justify-between gap-3 text-sm">
              <span className="font-medium text-slate-700">{labelOf(g.key)}</span>
              <span className="text-xs text-slate-500">{share.toFixed(1)}% · {formatUsd(g.estimated_cost_usd)}</span>
            </div>
            <ProgressBar value={share} label={`${labelOf(g.key)} chiếm ${share.toFixed(1)}% token`} />
            <p className="mt-1 text-xs text-slate-400">{formatNumber(g.request_count)} lượt · {formatNumber(g.total_tokens)} token · TB {Math.round(g.avg_latency_ms)} ms</p>
          </li>
        );
      })}
    </ul>
  );
}

const MAX_CHART_DAYS = 90;
const EMPTY_DAY = { total_tokens: 0, request_count: 0, estimated_cost_usd: 0 };
const shortDay = (key) => `${key.slice(8, 10)}/${key.slice(5, 7)}`; // 2026-11-22 -> 22/11

/** Dựng trục ngày liên tục từ..đến, ngày không có lượt gọi nào được điền 0 để mỗi ngày luôn là một cột riêng. */
function buildDailySeries(days, from, to) {
  const byKey = new Map(days.map((d) => [d.key, d]));
  const keys = days.map((d) => d.key).sort();
  const start = [from, keys[0]].filter(Boolean).sort()[0]; // mở rộng nếu dữ liệu nằm ngoài khoảng đã chọn (lệch múi giờ UTC)
  const end = [to, keys[keys.length - 1]].filter(Boolean).sort().slice(-1)[0];
  if (!start || !end) return [];
  const series = [];
  const cursor = new Date(`${start}T00:00:00Z`);
  const last = new Date(`${end}T00:00:00Z`);
  while (cursor <= last) {
    const key = cursor.toISOString().slice(0, 10);
    series.push(byKey.get(key) || { key, ...EMPTY_DAY });
    cursor.setUTCDate(cursor.getUTCDate() + 1);
  }
  return series.slice(-MAX_CHART_DAYS);
}

/** Biểu đồ cột token theo ngày (thuần CSS, không cần thêm thư viện): mỗi ngày một cột, có nhãn ngày và tổng khoảng chọn. */
function DailyChart({ days = [], from, to }) {
  const series = buildDailySeries(days, from, to);
  if (series.length === 0) return <p className="py-6 text-center text-sm text-slate-400">Chưa có dữ liệu trong khoảng thời gian này.</p>;

  const max = Math.max(...series.map((d) => d.total_tokens), 1);
  const total = series.reduce((sum, d) => sum + d.total_tokens, 0);
  const activeDays = series.filter((d) => d.total_tokens > 0).length;
  const labelEvery = series.length <= 10 ? 1 : series.length <= 31 ? 5 : 10; // thưa nhãn khi nhiều cột để không chồng chữ

  return (
    <div>
      <p className="mb-3 text-sm text-slate-500">
        <span className="font-semibold text-navy-800">{formatNumber(total)}</span> token trong {series.length} ngày · {activeDays} ngày có hoạt động · đỉnh {formatNumber(max)} token/ngày
      </p>
      <div
        role="img"
        aria-label={`Biểu đồ token theo ngày, từ ${series[0].key} đến ${series[series.length - 1].key}, tổng ${formatNumber(total)} token`}
        className="flex h-40 items-end gap-0.5 border-b border-slate-200 sm:gap-1"
      >
        {series.map((d) => (
          <div key={d.key} className="flex h-full min-w-0 flex-1 items-end justify-center" title={`${shortDay(d.key)}: ${formatNumber(d.total_tokens)} token · ${formatNumber(d.request_count)} lượt · ${formatUsd(d.estimated_cost_usd)}`}>
            <div
              className={d.total_tokens > 0 ? 'w-full max-w-[40px] rounded-t bg-brand-500/85 transition-colors hover:bg-brand-600' : 'w-full max-w-[40px] rounded-t bg-slate-200'}
              style={{ height: d.total_tokens > 0 ? `${Math.max(4, (d.total_tokens / max) * 100)}%` : '2px' }}
            />
          </div>
        ))}
      </div>
      <div className="mt-1.5 flex gap-0.5 text-[10px] text-slate-400 sm:gap-1 sm:text-xs" aria-hidden="true">
        {series.map((d, i) => (
          <span key={d.key} className="min-w-0 flex-1 overflow-visible whitespace-nowrap text-center">
            {i % labelEvery === 0 || i === series.length - 1 ? shortDay(d.key) : ''}
          </span>
        ))}
      </div>
    </div>
  );
}

const featureLabel = (key) => FEATURE_LABELS[key] || key;
const providerLabel = (key) => ({ gemini: 'Google Gemini', openai: 'OpenAI' }[key] || key);

/** SCR-08 · Giám sát Token AI & chi phí (API-18) kèm nhật ký gọi AI chi tiết. */
export default function TokenLogPage() {
  const [range, setRange] = useState({ from: daysAgo(30), to: toInputDate(new Date()) });
  const [feature, setFeature] = useState('');
  const [page, setPage] = useState(1);

  const dates = {
    startDate: range.from ? `${range.from}T00:00:00` : undefined,
    endDate: range.to ? `${range.to}T23:59:59` : undefined,
  };
  const stats = useAdminQuery(() => adminApi.getTokenStats(dates), [range.from, range.to]);
  const logs = useAdminQuery(() => adminApi.getLogs({ page, pageSize: PAGE_SIZE, feature, ...dates }), [page, feature, range.from, range.to]);

  const applyRange = (next) => {
    setRange(next);
    setPage(1);
  };
  // Giữ "từ ngày" <= "đến ngày"
  const setFrom = (from) => applyRange({ from, to: range.to && from && range.to < from ? from : range.to });
  const setTo = (to) => applyRange({ to, from: range.from && to && range.from > to ? to : range.from });

  const summary = stats.data?.summary;
  const items = logs.data?.items ?? [];

  const dateInput = 'h-10 rounded-lg border border-slate-300 bg-white px-3 text-sm shadow-sm focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/20';

  return (
    <>
      <AdminPageHeader title="Token AI & chi phí" description="Theo dõi lượng token tiêu thụ và chi phí ước tính khi gọi mô hình AI." />

      {/* Bộ lọc thời gian */}
      <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-end">
        <label className="text-xs font-medium text-slate-500">
          Từ ngày
          <input type="date" value={range.from} max={range.to || undefined} onChange={(e) => setFrom(e.target.value)} className={`${dateInput} mt-1 block w-full`} />
        </label>
        <label className="text-xs font-medium text-slate-500">
          Đến ngày
          <input type="date" value={range.to} min={range.from || undefined} onChange={(e) => setTo(e.target.value)} className={`${dateInput} mt-1 block w-full`} />
        </label>
        <div className="flex gap-2">
          {PRESETS.map(({ label, days }) => (
            <Button key={label} variant="outline" size="sm" className="h-10" onClick={() => applyRange(days ? { from: daysAgo(days), to: toInputDate(new Date()) } : { from: '', to: '' })}>
              {label}
            </Button>
          ))}
        </div>
      </div>

      {stats.error && <AlertBox tone="error" className="mb-4" action={<Button variant="outline" size="sm" onClick={stats.reload}>Thử lại</Button>}>{stats.error}</AlertBox>}
      {stats.loading && !stats.data && <div className="flex justify-center py-16 text-slate-400"><Spinner size={28} label="Đang tải thống kê" /></div>}

      {summary && (
        <div className={`space-y-6 ${stats.loading ? 'opacity-60 transition-opacity' : ''}`}>
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
            <StatCard icon={Activity} label="Tổng lượt gọi AI" value={formatNumber(summary.total_requests)} hint={`Độ trễ TB ${Math.round(summary.avg_latency_ms)} ms`} />
            <StatCard icon={Zap} label="Tổng token" value={formatNumber(summary.total_tokens)} hint={`Prompt ${formatNumber(summary.total_tokens_prompt)} · Trả lời ${formatNumber(summary.total_tokens_completion)}`} />
            <StatCard icon={Coins} label="Chi phí ước tính (USD)" value={formatUsd(summary.estimated_cost_usd)} hint="Theo bảng giá từng nhà cung cấp" />
            <StatCard icon={Timer} label="Chi phí ước tính (VND)" value={formatVnd(summary.estimated_cost_vnd)} hint={`Tỷ giá ${formatNumber(stats.data.exchange_rate_vnd)} ₫/USD`} />
          </div>

          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            <Panel title="Phân bổ theo tính năng" icon={BarChart3}>
              <GroupBreakdown groups={stats.data.by_feature} totalTokens={summary.total_tokens} labelOf={featureLabel} />
            </Panel>
            <Panel title="Phân bổ theo nhà cung cấp" icon={BarChart3}>
              <GroupBreakdown groups={stats.data.by_provider} totalTokens={summary.total_tokens} labelOf={providerLabel} />
            </Panel>
          </div>

          <Panel title="Token theo ngày" icon={Activity}>
            <DailyChart days={stats.data.by_date} from={range.from} to={range.to} />
          </Panel>
        </div>
      )}

      {/* Nhật ký gọi AI chi tiết */}
      <Panel
        title="Nhật ký gọi AI"
        className="mt-6"
        aside={
          <FilterSelect label="Lọc theo tính năng" value={feature} onChange={(v) => { setFeature(v); setPage(1); }}>
            <option value="">Mọi tính năng</option>
            {Object.entries(FEATURE_LABELS).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
          </FilterSelect>
        }
      >
        {logs.error && <AlertBox tone="error" action={<Button variant="outline" size="sm" onClick={logs.reload}>Thử lại</Button>}>{logs.error}</AlertBox>}
        {logs.loading && !logs.data && <div className="flex justify-center py-12 text-slate-400"><Spinner size={24} label="Đang tải nhật ký" /></div>}
        {logs.data && items.length === 0 && <EmptyState icon={Activity} title="Chưa có lượt gọi AI" description="Không có bản ghi nào khớp bộ lọc hiện tại." />}

        {items.length > 0 && (
          <div className={logs.loading ? 'opacity-60 transition-opacity' : 'transition-opacity'}>
            {/* Desktop / tablet: bảng, cuộn ngang khi hẹp */}
            <div className="hidden overflow-x-auto md:block">
              <table className="w-full min-w-[760px] text-left text-sm">
                <thead>
                  <tr className="border-b border-slate-200 text-xs font-semibold uppercase tracking-wide text-slate-500">
                    <th className="px-3 py-2.5">Thời gian</th>
                    <th className="px-3 py-2.5">Người dùng</th>
                    <th className="px-3 py-2.5">Tính năng</th>
                    <th className="px-3 py-2.5">Nhà cung cấp</th>
                    <th className="px-3 py-2.5 text-right">Token (vào / ra)</th>
                    <th className="px-3 py-2.5 text-right">Độ trễ</th>
                    <th className="px-3 py-2.5 text-right">Chi phí</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {items.map((l) => (
                    <tr key={l.id} className="hover:bg-slate-50">
                      <td className="whitespace-nowrap px-3 py-2.5 text-slate-500">{formatDateTime(l.created_at)}</td>
                      <td className="max-w-[180px] px-3 py-2.5">
                        <p className="truncate font-medium text-slate-700">{l.user_full_name || 'Hệ thống'}</p>
                        {l.user_email && <p className="truncate text-xs text-slate-400">{l.user_email}</p>}
                      </td>
                      <td className="px-3 py-2.5"><Badge tone="blue">{featureLabel(l.feature)}</Badge></td>
                      <td className="px-3 py-2.5 text-slate-600">{providerLabel(l.provider)}</td>
                      <td className="whitespace-nowrap px-3 py-2.5 text-right">
                        <span className="font-semibold text-slate-700">{formatNumber(l.total_tokens)}</span>
                        <span className="block text-xs text-slate-400">{formatNumber(l.tokens_prompt)} / {formatNumber(l.tokens_completion)}</span>
                      </td>
                      <td className="whitespace-nowrap px-3 py-2.5 text-right text-slate-600">{formatNumber(l.latency_ms)} ms</td>
                      <td className="whitespace-nowrap px-3 py-2.5 text-right">
                        <span className="font-semibold text-slate-700">{formatUsd(l.estimated_cost_usd)}</span>
                        <span className="block text-xs text-slate-400">{formatVnd(l.estimated_cost_vnd)}</span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Mobile: Detail Card View hiển thị số token và chi phí USD */}
            <ul className="space-y-3 md:hidden">
              {items.map((l) => (
                <li key={l.id} className="rounded-xl border border-slate-200 p-4">
                  <div className="flex items-center justify-between gap-2">
                    <Badge tone="blue">{featureLabel(l.feature)}</Badge>
                    <span className="text-xs text-slate-400">{formatDateTime(l.created_at)}</span>
                  </div>
                  <p className="mt-2 truncate text-sm font-medium text-slate-700">{l.user_full_name || 'Hệ thống'} <span className="font-normal text-slate-400">· {providerLabel(l.provider)}</span></p>
                  <dl className="mt-3 grid grid-cols-3 gap-2 text-xs">
                    <div>
                      <dt className="text-slate-400">Token</dt>
                      <dd className="mt-0.5 text-sm font-semibold text-slate-700">{formatNumber(l.total_tokens)}</dd>
                    </div>
                    <div>
                      <dt className="text-slate-400">Chi phí</dt>
                      <dd className="mt-0.5 text-sm font-semibold text-slate-700">{formatUsd(l.estimated_cost_usd)}</dd>
                    </div>
                    <div>
                      <dt className="text-slate-400">Độ trễ</dt>
                      <dd className="mt-0.5 text-sm font-semibold text-slate-700">{formatNumber(l.latency_ms)} ms</dd>
                    </div>
                  </dl>
                </li>
              ))}
            </ul>

            <Pagination page={logs.data.page} totalPages={logs.data.total_pages} total={logs.data.total} pageSize={logs.data.page_size} onChange={setPage} disabled={logs.loading} />
          </div>
        )}
      </Panel>
    </>
  );
}
