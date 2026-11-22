# Kiểm tra chỉ mục MySQL cho NFR-06

Migration `005_recommendation_index` hoàn tất bộ năm chỉ mục theo tài liệu thiết kế. Sau khi nâng cấp lên `head`, MySQL 8.0.46 có 22 bảng nghiệp vụ (yêu cầu ghi 21), cộng bảng `alembic_version`. Đã kiểm tra tạo schema từ đầu và chu trình hạ từ 005 về 004 rồi nâng cấp lại.

| Bảng | Chỉ mục | Thứ tự cột | Kết quả `EXPLAIN ANALYZE` |
| --- | --- | --- | --- |
| `chat_messages` | `idx_session_created` | `session_id, created_at` | Duyệt ngược theo chỉ mục và dừng sau 10 dòng, hỗ trợ thứ tự `created_at DESC, id DESC`. |
| `topic_mastery` | `idx_user_topic_mastery` | `user_id, status, mastery_score` | Lọc theo người dùng và trạng thái `WEAK`, đọc ba dòng theo điểm tăng dần. |
| `ai_request_logs` | `idx_user_feature_date` | `user_id, feature, created_at` | Đếm bằng phép quét khoảng trên chỉ mục theo người dùng, tính năng và ngày. |
| `recommendations` | `idx_user_status_prio` | `user_id, status, priority` | Đọc 100 đề xuất `PENDING` của người dùng. Khi dùng `IGNORE INDEX` để đối chiếu, MySQL đọc 2.000 dòng qua chỉ mục người dùng rồi lọc trạng thái. |
| `document_chunks` | `idx_doc_page` | `document_id, page_number` | Tra theo tài liệu và trang, trả về bốn đoạn. |

Truy vấn đề xuất trong bảng tiến độ tiếp tục sắp xếp theo `priority ASC, id DESC` sau khi lọc chủ đề. Truy vấn lấy đề xuất theo `priority ASC, created_at DESC` cũng còn bước sắp xếp để giữ đúng thứ tự khi trùng độ ưu tiên.

## Độ trễ truy vấn

Đo trên một kết nối MySQL cục bộ, với 100.000 dòng ở mỗi bảng đích trong bảng trên và 100.000 lượt làm quiz. Người dùng được đo có 2.000 tin nhắn trong phiên và 2.000 lượt làm quiz, trong đó 200 lượt thuộc 10 chủ đề được lọc. Mỗi truy vấn được làm nóng 10 lần, sau đó đo 100 lần, tính cả thời gian gửi truy vấn và đọc kết quả qua PyMySQL.

| Truy vấn | P95 | Kế hoạch thực thi |
| --- | ---: | --- |
| 10 tin nhắn gần nhất | 1,17 ms | Duyệt ngược `idx_session_created`. |
| 10 lượt làm quiz gần nhất | 1,98 ms | Duyệt ngược `ix_quiz_attempts_user_id`, nối khóa chính tới quiz và chủ đề. |
| Tổng hợp điểm quiz theo chủ đề | 6,90 ms | Đọc 2.000 lượt qua `ix_quiz_attempts_user_id`, nối theo khóa chính của quiz rồi gom nhóm bằng bảng tạm. |

Ba truy vấn đạt ngưỡng 500 ms trong phép đo CSDL này. NFR-06 trong SRS đo P95 ở mức API, cần đo riêng với tải đồng thời và dữ liệu đại diện cho môi trường triển khai.

## Kiểm tra lại trên schema đã migrate

Chạy `python -m alembic upgrade head` trong thư mục `backend`. Trong MySQL, đổi các ID và khoảng ngày dưới đây cho phù hợp với dữ liệu của schema kiểm thử.

```sql
SELECT table_name, index_name,
       GROUP_CONCAT(column_name ORDER BY seq_in_index) AS indexed_columns
FROM information_schema.statistics
WHERE table_schema = DATABASE()
  AND index_name IN ('idx_user_topic_mastery', 'idx_session_created',
                     'idx_user_feature_date', 'idx_user_status_prio', 'idx_doc_page')
GROUP BY table_name, index_name;

EXPLAIN ANALYZE
SELECT * FROM chat_messages WHERE session_id = 1
ORDER BY created_at DESC, id DESC LIMIT 10;

EXPLAIN ANALYZE
SELECT * FROM topic_mastery WHERE user_id = 1 AND status = 'WEAK'
ORDER BY mastery_score LIMIT 3;

EXPLAIN ANALYZE
SELECT COUNT(id) FROM ai_request_logs WHERE user_id = 1 AND feature = 'TUTOR'
  AND created_at >= '2026-01-02' AND created_at < '2026-01-03';

EXPLAIN ANALYZE
SELECT * FROM recommendations WHERE user_id = 1 AND status = 'PENDING'
ORDER BY priority ASC, created_at DESC LIMIT 10;

EXPLAIN ANALYZE
SELECT * FROM document_chunks WHERE document_id = 1 AND page_number = 5;

EXPLAIN ANALYZE
SELECT a.*, q.*, t.name
FROM quiz_attempts a JOIN quizzes q ON q.id = a.quiz_id
JOIN topics t ON t.id = q.topic_id
WHERE a.user_id = 1 AND a.status = 'SUBMITTED'
  AND q.topic_id IN (1, 2, 3, 4, 5, 6, 7, 8, 9, 10)
ORDER BY a.id DESC LIMIT 10;

EXPLAIN ANALYZE
SELECT q.topic_id, COUNT(a.id), COALESCE(SUM(a.score), 0),
       COALESCE(SUM(a.duration_sec), 0), MAX(a.id)
FROM quiz_attempts a JOIN quizzes q ON q.id = a.quiz_id
WHERE a.user_id = 1 AND a.status = 'SUBMITTED'
  AND q.topic_id IN (1, 2, 3, 4, 5, 6, 7, 8, 9, 10)
GROUP BY q.topic_id;
```
