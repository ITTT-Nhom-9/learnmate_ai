import { useCallback, useEffect, useState } from 'react';
import { progressApi } from '../api/progressApi';
import { getErrorMessage } from '../utils/apiError';

/**
 * Hook tải dữ liệu tiến độ Dashboard (SCR-07) cho một môn học.
 * Trả về summary (% hoàn thành, stats, cảnh báo, lịch sử) và radar (labels, scores, axes).
 */
export function useProgress(courseId) {
  const [summary, setSummary] = useState(null);
  const [radar, setRadar] = useState(null);
  const [loading, setLoading] = useState(Boolean(courseId));
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    if (!courseId) {
      setLoading(false);
      setSummary(null);
      setRadar(null);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const [summaryData, radarData] = await Promise.all([
        progressApi.getSummary(courseId),
        progressApi.getRadar(courseId),
      ]);
      setSummary(summaryData);
      setRadar(radarData);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }, [courseId]);

  useEffect(() => { load(); }, [load]);

  return { summary, radar, loading, error, reload: load };
}
