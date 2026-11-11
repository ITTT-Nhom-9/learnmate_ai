// Bộ đọc Server-Sent Events cho API chat (POST /tutor/chat).
// Không dùng EventSource vì EventSource chỉ hỗ trợ GET và không gửi được header Authorization.

const FRAME_END = /\r\n\r\n|\n\n|\r\r/;

/** Tách một khung SSE thành { event, data }. Trả về null nếu khung chỉ chứa chú thích/không có dữ liệu. */
export function parseSseFrame(frame) {
  let event = 'message';
  const data = [];
  frame.split(/\r\n|\n|\r/).forEach((line) => {
    if (!line || line.startsWith(':')) return; // dòng trống hoặc chú thích (keep-alive)
    const colon = line.indexOf(':');
    const field = colon === -1 ? line : line.slice(0, colon);
    let value = colon === -1 ? '' : line.slice(colon + 1);
    if (value.startsWith(' ')) value = value.slice(1);
    if (field === 'event') event = value || 'message';
    else if (field === 'data') data.push(value);
  });
  return data.length === 0 && event === 'message' ? null : { event, data: data.join('\n') };
}

/** Đọc ReadableStream (response.body) và trả về từng khung SSE đã hoàn chỉnh. */
export async function* readSseStream(body) {
  const reader = body.getReader();
  const decoder = new TextDecoder('utf-8');
  let buffer = '';
  try {
    for (;;) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      let match = FRAME_END.exec(buffer);
      while (match) {
        const frame = parseSseFrame(buffer.slice(0, match.index));
        buffer = buffer.slice(match.index + match[0].length);
        if (frame) yield frame;
        match = FRAME_END.exec(buffer);
      }
    }
    buffer += decoder.decode();
    const last = buffer.trim() ? parseSseFrame(buffer) : null;
    if (last) yield last;
  } finally {
    reader.cancel().catch(() => {}); // giải phóng kết nối khi người dùng dừng/rời trang
  }
}
