import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import 'katex/dist/katex.min.css';
import CodeBlock from './CodeBlock';

// react-markdown KHÔNG render HTML thô trong Markdown (an toàn trước XSS), chỉ render phần tử đã khai báo dưới đây.
const components = {
  h1: (props) => <h2 className="mb-3 mt-8 text-xl font-bold text-navy-800 first:mt-0" {...props} />,
  h2: (props) => <h3 className="mb-3 mt-7 text-lg font-semibold text-navy-800" {...props} />,
  h3: (props) => <h4 className="mb-2 mt-6 text-base font-semibold text-navy-800" {...props} />,
  h4: (props) => <h5 className="mb-2 mt-5 text-sm font-semibold text-navy-800" {...props} />,
  p: (props) => <p className="my-3 leading-7 text-slate-600" {...props} />,
  strong: (props) => <strong className="font-semibold text-slate-800" {...props} />,
  ul: (props) => <ul className="my-3 list-disc space-y-1.5 pl-6 text-slate-600 marker:text-slate-400" {...props} />,
  ol: (props) => <ol className="my-3 list-decimal space-y-1.5 pl-6 text-slate-600 marker:text-slate-400" {...props} />,
  li: (props) => <li className="leading-7" {...props} />,
  blockquote: (props) => (
    <blockquote className="my-4 rounded-r-lg border-l-4 border-blue-200 bg-blue-50/60 px-4 py-1 text-slate-600" {...props} />
  ),
  hr: () => <hr className="my-6 border-slate-200" />,
  a: ({ href, ...props }) => (
    <a href={href} target="_blank" rel="noopener noreferrer" className="font-medium text-blue-600 underline underline-offset-2" {...props} />
  ),
  img: ({ alt, ...props }) => <img alt={alt || ''} loading="lazy" className="my-4 h-auto max-w-full rounded-lg" {...props} />,
  table: (props) => (
    <div className="thin-scroll my-4 overflow-x-auto rounded-lg border border-slate-200">
      <table className="w-full border-collapse text-left text-sm" {...props} />
    </div>
  ),
  thead: (props) => <thead className="bg-slate-50 text-slate-700" {...props} />,
  th: (props) => <th className="border-b border-slate-200 px-3 py-2 font-semibold" {...props} />,
  td: (props) => <td className="border-b border-slate-100 px-3 py-2 text-slate-600" {...props} />,
  // <pre> do CodeBlock tự dựng nên bỏ lớp bọc mặc định
  pre: ({ children }) => <>{children}</>,
  code({ className, children, ...props }) {
    const language = /language-([\w+-]+)/.exec(className || '')?.[1];
    const text = String(children).replace(/\n$/, '');
    if (language || text.includes('\n')) return <CodeBlock code={text} language={language} />;
    return (
      <code className="rounded bg-slate-100 px-1.5 py-0.5 font-mono text-[0.85em] text-navy-800" {...props}>
        {children}
      </code>
    );
  },
};

/** Hiển thị Markdown bài giảng: bảng/danh sách (GFM), công thức KaTeX ($...$, $$...$$), khối mã Prism. */
export default function MarkdownViewer({ source }) {
  return (
    <div className="min-w-0 break-words text-[15px]">
      <ReactMarkdown remarkPlugins={[remarkGfm, remarkMath]} rehypePlugins={[rehypeKatex]} components={components}>
        {source || ''}
      </ReactMarkdown>
    </div>
  );
}
