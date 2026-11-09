import { useEffect, useRef, useState } from 'react';
import { Check, Copy } from 'lucide-react';
import { PrismLight as SyntaxHighlighter } from 'react-syntax-highlighter';
import oneDark from 'react-syntax-highlighter/dist/esm/styles/prism/one-dark';
import bash from 'react-syntax-highlighter/dist/esm/languages/prism/bash';
import c from 'react-syntax-highlighter/dist/esm/languages/prism/c';
import cpp from 'react-syntax-highlighter/dist/esm/languages/prism/cpp';
import java from 'react-syntax-highlighter/dist/esm/languages/prism/java';
import javascript from 'react-syntax-highlighter/dist/esm/languages/prism/javascript';
import json from 'react-syntax-highlighter/dist/esm/languages/prism/json';
import python from 'react-syntax-highlighter/dist/esm/languages/prism/python';
import sql from 'react-syntax-highlighter/dist/esm/languages/prism/sql';

// Chỉ đăng ký các ngôn ngữ môn học dùng để bundle nhỏ. Muốn thêm ngôn ngữ: import và registerLanguage tại đây.
const LANGUAGES = { bash, c, cpp, java, javascript, json, python, sql };
Object.entries(LANGUAGES).forEach(([name, grammar]) => SyntaxHighlighter.registerLanguage(name, grammar));

const ALIASES = { js: 'javascript', py: 'python', sh: 'bash', shell: 'bash', 'c++': 'cpp', mysql: 'sql' };

export default function CodeBlock({ code, language }) {
  const [copied, setCopied] = useState(false);
  const timer = useRef(null);
  const normalized = ALIASES[language] || language;
  const supported = normalized && LANGUAGES[normalized];

  useEffect(() => () => clearTimeout(timer.current), []);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      clearTimeout(timer.current);
      timer.current = setTimeout(() => setCopied(false), 1500);
    } catch {
      /* Clipboard API bị chặn (HTTP/không có quyền) -> bỏ qua */
    }
  };

  return (
    <div className="my-5 overflow-hidden rounded-xl bg-navy-950 text-slate-200">
      <div className="flex items-center justify-between px-4 pt-3">
        <span className="font-mono text-[11px] uppercase tracking-wider text-slate-400">{language || 'code'}</span>
        <button
          type="button"
          onClick={handleCopy}
          aria-label={copied ? 'Đã sao chép' : 'Sao chép mã'}
          className="rounded p-1 text-slate-400 hover:text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-400"
        >
          {copied ? <Check size={16} className="text-emerald-400" /> : <Copy size={16} />}
        </button>
      </div>
      {supported ? (
        <SyntaxHighlighter
          language={normalized}
          style={oneDark}
          customStyle={{ margin: 0, padding: '12px 16px 16px', background: 'transparent', fontSize: 13, lineHeight: 1.7 }}
          codeTagProps={{ style: { fontFamily: "'JetBrains Mono', ui-monospace, Menlo, Consolas, monospace" } }}
        >
          {code}
        </SyntaxHighlighter>
      ) : (
        <pre className="thin-scroll overflow-x-auto px-4 pb-4 pt-3 font-mono text-[13px] leading-[1.7]">
          <code>{code}</code>
        </pre>
      )}
    </div>
  );
}
