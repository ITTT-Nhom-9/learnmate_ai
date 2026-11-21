// Dữ liệu mock cho SCR-08 · Tab RAG (TK-26): giả lập Upload PDF, danh sách tài liệu và Hỏi đáp có trích dẫn số trang.
// Mô phỏng hợp đồng API của Backend (TK-24 / TK-25): /rag/upload, /rag/documents, /rag/query.
import { normalizeText } from '../utils/formatters';

const delay = (ms = 300) => new Promise((resolve) => setTimeout(resolve, ms));
const MAX_BYTES = 20 * 1024 * 1024;

function httpError(status, detail) {
  return Object.assign(new Error(detail), { response: { status, data: { detail } } });
}

const documents = [
  { id: 1, course_id: 1, file_name: 'Giao_trinh_Co_so_du_lieu.pdf', file_size: 4194304, total_chunks: 42, created_at: new Date(Date.now() - 8 * 86400000).toISOString() },
];
let nextId = 2;

export async function getDocuments(courseId) {
  await delay();
  const items = documents.filter((d) => d.course_id === Number(courseId)).sort((a, b) => b.created_at.localeCompare(a.created_at));
  return { total: items.length, items: items.map((d) => ({ ...d })) };
}

export async function uploadDocument({ courseId, file, onProgress }) {
  for (const percent of [20, 45, 75, 100]) {
    await delay(150);
    onProgress?.(percent); // giả lập tiến trình tải lên
  }
  await delay(1000); // giả lập trích xuất văn bản + tạo embedding
  if (!file.name.toLowerCase().endsWith('.pdf')) throw httpError(400, 'Chỉ chấp nhận tệp định dạng .pdf (theo quy tắc BR-09).');
  if (file.size > MAX_BYTES) throw httpError(400, 'Kích thước tệp vượt quá giới hạn 20MB (BR-09).');

  const total_pages = Math.max(1, Math.round(file.size / 45000)); // ~45KB mỗi trang
  const total_chunks = Math.max(1, Math.round(total_pages * 0.9)); // ~500 từ mỗi đoạn, gối đầu 50 từ
  const doc = { id: nextId++, course_id: Number(courseId), file_name: file.name, file_size: file.size, total_chunks, created_at: new Date().toISOString() };
  documents.push(doc);
  return {
    document_id: doc.id,
    course_id: doc.course_id,
    file_name: doc.file_name,
    file_size: doc.file_size,
    total_pages,
    total_chunks,
    embedding_dim: 1536,
    created_at: doc.created_at,
    message: 'Tải lên và xử lý vector embedding 1536 chiều thành công.',
  };
}

export async function deleteDocument(documentId) {
  await delay();
  const index = documents.findIndex((d) => d.id === Number(documentId));
  if (index < 0) throw httpError(404, `Không tìm thấy tài liệu có ID ${documentId}.`);
  documents.splice(index, 1);
  return { status: 'success', message: `Đã xóa tài liệu có ID ${documentId} và toàn bộ vector embedding liên quan thành công.` };
}

const OFF_TOPIC = ['thoi tiet', 'bong da', 'nau an', 'gia vang', 'phim'];

export async function queryDocuments({ courseId, query, documentIds, topK = 3 }) {
  await delay(900);
  const docs = documents.filter((d) => d.course_id === Number(courseId) && (!documentIds?.length || documentIds.includes(d.id)));
  if (docs.length === 0) throw httpError(404, 'Môn học này chưa có tài liệu nào được lập chỉ mục.');

  if (OFF_TOPIC.some((k) => normalizeText(query).includes(k))) {
    return {
      query,
      answer: 'Nội dung câu hỏi của bạn nằm ngoài phạm vi tài liệu giáo trình được cung cấp. Vui lòng đặt câu hỏi liên quan đến nội dung bài giảng để được giải đáp chính xác kèm trích dẫn số trang.',
      is_out_of_scope: true,
      citations: [],
      total_sources: 0,
    };
  }

  const doc = docs[0];
  const citations = [
    { chunk_id: 101, document_id: doc.id, file_name: doc.file_name, page_number: 45, similarity_score: 0.89, snippet: 'Dạng chuẩn 1NF (First Normal Form) yêu cầu mọi thuộc tính chỉ chứa giá trị nguyên tố, không có thuộc tính đa trị hay nhóm lặp...' },
    { chunk_id: 102, document_id: doc.id, file_name: doc.file_name, page_number: 46, similarity_score: 0.84, snippet: 'Dạng chuẩn 2NF yêu cầu quan hệ đạt 1NF và mọi thuộc tính không khóa phụ thuộc hàm đầy đủ vào khóa chính...' },
    { chunk_id: 103, document_id: doc.id, file_name: doc.file_name, page_number: 48, similarity_score: 0.78, snippet: 'Dạng chuẩn 3NF loại bỏ phụ thuộc bắc cầu: thuộc tính không khóa không được phụ thuộc vào thuộc tính không khóa khác...' },
  ].slice(0, topK);

  return {
    query,
    answer:
      '(Dữ liệu mô phỏng) Theo giáo trình: 1NF yêu cầu các thuộc tính chỉ chứa giá trị nguyên tố (Trang 45). 2NF yêu cầu đạt 1NF và không có phụ thuộc hàm riêng phần vào khóa chính (Trang 46). 3NF yêu cầu đạt 2NF và loại bỏ phụ thuộc bắc cầu (Trang 48).',
    is_out_of_scope: false,
    citations,
    total_sources: citations.length,
  };
}
