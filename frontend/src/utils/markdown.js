// Chuẩn hóa công thức toán trong câu trả lời của AI trước khi đưa vào remark-math.
// remark-math chỉ coi là công thức DẠNG KHỐI khi "$$" nằm riêng trên các dòng của nó. Trong khi LLM hay viết:
//   - $$ ... $$ trên một dòng duy nhất  (bị hiểu là công thức nằm trong dòng)
//   - \[ ... \]  và  \( ... \)          (kiểu LaTeX, không được nhận)
// Không động vào khối code (```...```, ~~~...~~~) và code trong dòng (`...`), kể cả khối code chưa đóng khi đang stream.

const CODE_PARTS = /(```[\s\S]*?(?:```|$)|~~~[\s\S]*?(?:~~~|$)|`[^`\n]+`)/g;

function fixMath(text) {
  return text
    // 1. Block math: \\[ ... \\] hoặc \\[\ ... \\] (hỗ trợ cả 1 hoặc nhiều dấu gạch chéo ngược)
    .replace(/(?:\\+\[)([\s\S]+?)(?:\\+\])/g, (_, body) => `\n\n$$\n${body.trim()}\n$$\n\n`)
    // 2. Inline math: \( ... \) hoặc \\( ... \\)
    .replace(/(?:\\+\()([\s\S]+?)(?:\\+\))/g, (_, body) => `$${body.trim()}$`)
    // 3. Đưa $$ nằm trên một dòng duy nhất xuống các dòng riêng biệt cho remark-math
    .replace(/^[ \t]*\$\$([^\n$]+?)\$\$[ \t]*$/gm, (_, body) => `\n$$\n${body.trim()}\n$$\n`);
}

export function normalizeMath(source) {
  if (!source) return '';
  return source
    .split(CODE_PARTS)
    .map((part, index) => (index % 2 === 1 ? part : fixMath(part)))
    .join('');
}
