import { useCallback, useEffect, useRef, useState } from 'react';
import { getErrorMessage } from '../../utils/apiError';

/**
 * Tải dữ liệu cho các trang Admin. Giữ lại dữ liệu cũ khi đang tải lại (đổi trang, đổi bộ lọc)
 * để bảng không bị nháy trống. Truyền `deps` là các giá trị làm thay đổi kết quả (trang, bộ lọc...).
 * `fetcher` có thể trả về null để bỏ qua (ví dụ chưa chọn môn học).
 */
export function useAdminQuery(fetcher, deps) {
  const [state, setState] = useState({ data: null, loading: true, error: null });
  const [tick, setTick] = useState(0);
  const fetcherRef = useRef(fetcher);
  fetcherRef.current = fetcher;

  useEffect(() => {
    let cancelled = false;
    const request = fetcherRef.current();
    if (!request) {
      setState({ data: null, loading: false, error: null });
      return undefined;
    }
    setState((s) => ({ ...s, loading: true, error: null }));
    request
      .then((data) => !cancelled && setState({ data, loading: false, error: null }))
      .catch((err) => !cancelled && setState((s) => ({ ...s, loading: false, error: getErrorMessage(err) })));
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, tick]);

  const reload = useCallback(() => setTick((t) => t + 1), []);
  return { ...state, reload };
}
