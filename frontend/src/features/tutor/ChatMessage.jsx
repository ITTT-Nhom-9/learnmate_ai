import { memo, useEffect, useRef, useState } from 'react';
import { AlertCircle, Check, Copy, RotateCcw, Sparkles } from 'lucide-react';
import MarkdownViewer from '../../components/viewer/MarkdownViewer';
import { formatTime } from '../../utils/formatters';

function UserMessage({ message, initials }) {
  return (
    <div className="flex items-end justify-end gap-3">
      <div className="max-w-[85%] rounded-2xl rounded-br-md bg-navy-800 px-4 py-3 text-white sm:max-w-[75%]">
        <span className="sr-only">Bạn: </span>
        <p className="whitespace-pre-wrap break-words text-[14.5px] leading-6">{message.content}</p>
        <p className="mt-1.5 text-right text-[11px] text-blue-100/70">{formatTime(message.createdAt)} · Đã gửi</p>
      </div>
      <span
        aria-hidden="true"
        className="mb-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-slate-100 text-[11px] font-semibold text-navy-800"
      >
        {initials}
      </span>
    </div>
  );
}

function TypingDots() {
  return (
    <div className="flex items-center gap-1 py-2" role="status" aria-label="Gia sư AI đang suy nghĩ">
      {[0, 150, 300].map((delay) => (
        <span key={delay} className="h-2 w-2 animate-bounce rounded-full bg-slate-300" style={{ animationDelay: `${delay}ms` }} />
      ))}
    </div>
  );
}

function AssistantMessage({ message, onRetry }) {
  const [copied, setCopied] = useState(false);
  const timer = useRef(null);
  useEffect(() => () => clearTimeout(timer.current), []);

  const streaming = message.status === 'streaming';
  const failed = message.status === 'error' || message.status === 'interrupted';
  const hasContent = message.content.length > 0;

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(message.content);
      setCopied(true);
      clearTimeout(timer.current);
      timer.current = setTimeout(() => setCopied(false), 1500);
    } catch {
      /* Clipboard bị chặn -> bỏ qua */
    }
  };

  return (
    <div className="flex items-start gap-3">
      <span aria-hidden="true" className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-blue-50 text-blue-600">
        <Sparkles size={16} />
      </span>
      <div aria-busy={streaming} className="min-w-0 max-w-3xl flex-1 rounded-2xl rounded-tl-md border border-slate-200 bg-white px-4 py-3.5">
        <div className="flex items-center gap-2 text-xs">
          <span className="font-semibold text-navy-800">
            <span className="sr-only">Gia sư AI: </span>LearnMate AI
          </span>
          <span className="text-slate-400">{formatTime(message.createdAt)}</span>
        </div>

        <div className="mt-1.5">
          {hasContent ? <MarkdownViewer source={message.content} variant="chat" /> : streaming ? <TypingDots /> : null}
          {streaming && hasContent && <span aria-hidden="true" className="stream-caret ml-0.5 inline-block h-4 w-0.5 translate-y-0.5 bg-blue-600" />}
        </div>

        {failed && (
          <div role="alert" className="mt-3 flex items-start gap-2 rounded-lg bg-red-50 px-3 py-2.5 text-sm text-red-700">
            <AlertCircle size={16} className="mt-0.5 shrink-0" aria-hidden="true" />
            <span className="min-w-0 flex-1">{message.errorMessage}</span>
            {message.canRetry && (
              <button
                type="button"
                onClick={() => onRetry(message.id)}
                className="flex shrink-0 items-center gap-1 rounded font-semibold text-red-700 underline-offset-2 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-500"
              >
                <RotateCcw size={14} aria-hidden="true" /> Thử lại
              </button>
            )}
          </div>
        )}

        {message.status === 'stopped' && <p className="mt-2 text-xs text-slate-500">Đã dừng tạo câu trả lời.</p>}

        {message.status === 'sent' && hasContent && (
          <div className="mt-2 flex justify-end">
            <button
              type="button"
              onClick={handleCopy}
              className="flex items-center gap-1.5 rounded-md px-2 py-1 text-xs text-slate-500 hover:bg-slate-100 hover:text-navy-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600"
            >
              {copied ? <Check size={14} className="text-emerald-500" aria-hidden="true" /> : <Copy size={14} aria-hidden="true" />}
              {copied ? 'Đã sao chép' : 'Sao chép'}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

function ChatMessage({ message, initials, onRetry }) {
  return message.role === 'user' ? <UserMessage message={message} initials={initials} /> : <AssistantMessage message={message} onRetry={onRetry} />;
}

// memo: chỉ tin nhắn đang stream mới render lại khi có token mới
export default memo(ChatMessage);
