import { BookOpen, Check, ShieldCheck, Sparkles } from 'lucide-react';
import Logo from '../../components/common/Logo';

/** Minh họa gia sư AI ở panel trái (chỉ hiện trên màn hình lớn). */
function TutorIllustration() {
  return (
    <div className="relative mx-auto mt-10 h-[290px] w-full max-w-[540px]" aria-hidden="true">
      <div className="absolute left-[18%] top-[2%] h-[270px] w-[270px] rounded-full border border-white/10" />
      <div className="absolute left-[26%] top-[10%] h-[230px] w-[230px] rounded-full border border-white/10" />

      <div className="absolute left-0 top-0 flex w-[220px] items-center gap-3 rounded-xl border border-white/15 bg-white/10 px-4 py-3">
        <BookOpen size={20} className="text-blue-200" />
        <div>
          <p className="text-xs font-semibold text-white">Giải thích dễ hiểu</p>
          <p className="text-[11px] text-blue-100/80">Từng bước, theo cách bạn</p>
        </div>
      </div>

      <div className="absolute left-[23%] top-[28%] w-[230px] rounded-3xl bg-blue-50 p-5 shadow-xl">
        <p className="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wide text-navy-800">
          <Sparkles size={14} className="text-blue-600" /> Gia sư AI của bạn
        </p>
        <div className="mt-3 flex h-[88px] items-center justify-center gap-5 rounded-2xl bg-navy-800">
          <span className="h-6 w-2.5 rounded-full bg-blue-200" />
          <span className="h-6 w-2.5 rounded-full bg-blue-200" />
        </div>
        <p className="mt-3 text-sm font-semibold text-navy-800">Mình cùng học nhé!</p>
      </div>

      <div className="absolute bottom-[4%] right-0 flex w-[225px] items-center gap-3 rounded-xl bg-white px-4 py-3 shadow-xl">
        <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-emerald-50 text-emerald-500">
          <Check size={18} />
        </span>
        <div>
          <p className="text-xs font-semibold text-navy-800">Tiến bộ mỗi ngày</p>
          <p className="text-[11px] text-slate-500">Lộ trình dành riêng cho bạn</p>
        </div>
      </div>

      <Sparkles size={26} strokeWidth={1.5} className="absolute right-[14%] top-[2%] text-blue-300" />
      <span className="absolute bottom-[10%] left-[8%] h-2.5 w-2.5 rounded-full bg-blue-300" />
    </div>
  );
}

/**
 * Bố cục 2 cột dùng chung cho Đăng nhập / Đăng ký (SCR-01).
 * Desktop: panel thương hiệu bên trái + form bên phải.
 * Mobile (< lg): một cột, ẩn banner lớn, giữ logo phía trên form.
 */
export default function AuthLayout({ children }) {
  return (
    <div className="grid min-h-screen bg-white lg:grid-cols-2">
      <aside className="hidden flex-col justify-between bg-navy-800 px-12 py-12 text-white lg:flex xl:px-16">
        <Logo tone="light" />

        <div>
          <p className="flex items-center gap-3 text-xs font-semibold uppercase tracking-wide text-blue-200">
            <span className="h-0.5 w-6 bg-blue-300" aria-hidden="true" />
            Học chủ động. Hiểu sâu hơn.
          </p>
          <h2 className="mt-5 max-w-[500px] text-4xl font-bold leading-tight xl:text-[40px]">
            Nền tảng trợ lý học tập thông minh cá nhân hóa
          </h2>
          <p className="mt-4 max-w-[480px] text-base leading-relaxed text-blue-100/90">
            Biến kiến thức thành năng lực. Cùng gia sư AI xây dựng lộ trình học phù hợp với riêng bạn.
          </p>
          <TutorIllustration />
        </div>

        <div className="flex items-center justify-between text-xs text-blue-100/80">
          <span>© 2026 LearnMate AI</span>
          <span>Đồng hành cùng tri thức</span>
        </div>
      </aside>

      <main className="flex flex-col px-4 py-8 sm:px-8 lg:px-12">
        <Logo tone="dark" className="mb-8 lg:hidden" />

        <div className="mx-auto flex w-full max-w-[424px] flex-1 flex-col justify-center py-4">{children}</div>

        <p className="mt-6 flex items-center justify-center gap-1.5 text-xs text-slate-500">
          <ShieldCheck size={14} aria-hidden="true" /> Thông tin của bạn luôn được bảo vệ
        </p>
      </main>
    </div>
  );
}
