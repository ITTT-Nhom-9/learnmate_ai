import { MAX_PDF_BYTES } from '../../api/ragApi';
import { formatBytes } from '../admin/adminUtils';

/** BR-09: chỉ nhận PDF, tối đa 20MB. Trả về thông báo lỗi hoặc null nếu hợp lệ. */
export function validatePdf(file) {
  if (!file) return 'Vui lòng chọn một tệp PDF.';
  const isPdf = file.type === 'application/pdf' || file.name.toLowerCase().endsWith('.pdf');
  if (!isPdf) return 'Chỉ chấp nhận tệp định dạng .pdf (BR-09).';
  if (file.size === 0) return 'Tệp rỗng, vui lòng chọn tệp khác.';
  if (file.size > MAX_PDF_BYTES) return `Tệp ${formatBytes(file.size)} vượt quá giới hạn 20 MB (BR-09).`;
  return null;
}

/** Tên tài liệu hợp lệ: 1-255 ký tự, không chứa / hoặc \ (khớp kiểm tra của Backend). Trả về lỗi hoặc null. */
export function validateDocumentName(name) {
  const value = (name || '').trim();
  if (!value) return 'Tên tài liệu không được để trống.';
  if (value.length > 255) return 'Tên tài liệu tối đa 255 ký tự.';
  if (/[/\\]/.test(value)) return 'Tên tài liệu không được chứa ký tự / hoặc \\.';
  return null;
}
