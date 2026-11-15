import { useEffect, useRef, useState } from 'react';
import { getRemainingSec } from '../features/quiz/quizUtils';

/**
 * Đồng hồ đếm ngược cho SCR-05, tính theo mốc hạn chót tuyệt đối (deadline, mili-giây) thay vì trừ dần mỗi giây.
 * Nhờ vậy đồng hồ vẫn đúng khi tab bị ẩn/trình duyệt giảm tốc setInterval, và khôi phục chính xác sau khi tải lại trang.
 *
 * - deadline = null: đồng hồ chưa chạy (đang tải đề).
 * - onExpire được gọi ĐÚNG 1 LẦN khi về 0 (kể cả khi mở lại trang lúc đã quá hạn) -> trang tự nộp bài.
 * - paused = true: tạm dừng kiểm tra hết giờ (đang nộp bài), không đổi hạn chót.
 */
export function useQuizTimer({ deadline, onExpire, paused = false }) {
  const [remainingSec, setRemainingSec] = useState(() => (deadline == null ? null : getRemainingSec(deadline)));
  const onExpireRef = useRef(onExpire);
  const expiredRef = useRef(false);

  useEffect(() => {
    onExpireRef.current = onExpire;
  }, [onExpire]);

  useEffect(() => {
    expiredRef.current = false; // đổi hạn chót (đề mới) -> cho phép hết giờ lại
  }, [deadline]);

  useEffect(() => {
    if (deadline == null) {
      setRemainingSec(null);
      return undefined;
    }

    const tick = () => {
      const left = getRemainingSec(deadline);
      setRemainingSec((prev) => (prev === left ? prev : left)); // cùng giá trị -> không render lại
      if (left === 0 && !paused && !expiredRef.current) {
        expiredRef.current = true;
        onExpireRef.current?.();
      }
    };

    tick();
    const id = setInterval(tick, 250); // 4 lần/giây để đồng hồ không bị trễ nhịp so với giây thực
    document.addEventListener('visibilitychange', tick); // quay lại tab -> cập nhật ngay
    return () => {
      clearInterval(id);
      document.removeEventListener('visibilitychange', tick);
    };
  }, [deadline, paused]);

  // Render đầu tiên sau khi có deadline: state chưa kịp cập nhật -> tính trực tiếp để không nháy "00:00"
  const current = deadline == null ? null : remainingSec ?? getRemainingSec(deadline);
  return {
    remainingSec: current,
    isRunning: current != null && current > 0,
    isExpired: current === 0,
  };
}
