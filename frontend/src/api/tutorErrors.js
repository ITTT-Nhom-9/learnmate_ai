/** Lỗi khi gọi API chat. status: mã HTTP (nếu có); interrupted: luồng bị ngắt giữa chừng. */
export class TutorStreamError extends Error {
  constructor(message, { status = null, interrupted = false } = {}) {
    super(message);
    this.name = 'TutorStreamError';
    this.status = status;
    this.interrupted = interrupted;
  }
}
