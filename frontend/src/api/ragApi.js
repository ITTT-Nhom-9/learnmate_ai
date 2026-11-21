import axiosClient from './axiosClient';

// VITE_USE_MOCK=true: giả lập Upload/Hỏi đáp PDF khi chưa chạy AI Service + MySQL (TK-24, TK-25).
const USE_MOCK = import.meta.env.VITE_USE_MOCK === 'true';
const loadMock = () => import('../mocks/mockRagApi.js');

/** BR-09: tệp PDF tối đa 20MB. */
export const MAX_PDF_BYTES = 20 * 1024 * 1024;

export const ragApi = {
  /**
   * API-14: POST /rag/upload (multipart/form-data: course_id, file)
   * -> { document_id, course_id, file_name, file_size, total_pages, total_chunks, embedding_dim, created_at, message }
   * Backend trích xuất chữ + tạo embedding trong cùng request nên có thể mất vài chục giây -> nới timeout 3 phút.
   */
  uploadDocument: ({ courseId, file, onProgress }) => {
    if (USE_MOCK) return loadMock().then((m) => m.uploadDocument({ courseId, file, onProgress }));
    const form = new FormData();
    form.append('course_id', String(courseId));
    form.append('file', file);
    return axiosClient.post('/rag/upload', form, {
      timeout: 180000,
      // axiosClient mặc định gửi JSON và axios sẽ biến FormData thành JSON -> phải ghi đè để trình duyệt tự gắn boundary.
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: (event) => event.total && onProgress?.(Math.round((event.loaded * 100) / event.total)),
    });
  },

  /** GET /rag/documents?course_id= -> { total, items: [{ id, course_id, file_name, file_size, total_chunks, created_at }] } */
  getDocuments: (courseId) =>
    USE_MOCK ? loadMock().then((m) => m.getDocuments(courseId)) : axiosClient.get('/rag/documents', { params: { course_id: courseId } }),

  /** DELETE /rag/documents/{id}: xóa tài liệu và cascade toàn bộ vector embedding. */
  deleteDocument: (documentId) =>
    USE_MOCK ? loadMock().then((m) => m.deleteDocument(documentId)) : axiosClient.delete(`/rag/documents/${documentId}`),

  /**
   * API-15: POST /rag/query { course_id, query, document_ids?, top_k }
   * -> { query, answer, is_out_of_scope, citations: [{ chunk_id, document_id, file_name, page_number, similarity_score, snippet }], total_sources }
   */
  query: ({ courseId, query, documentIds, topK = 3 }) =>
    USE_MOCK
      ? loadMock().then((m) => m.queryDocuments({ courseId, query, documentIds, topK }))
      : axiosClient.post('/rag/query', {
          course_id: courseId,
          query,
          top_k: topK,
          ...(documentIds?.length ? { document_ids: documentIds } : {}),
        }),
};
