import { useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  Archive,
  ArrowLeft,
  BookOpen,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  FileCode,
  FileText,
  Layers,
  ListTree,
  Pencil,
  Plus,
  Search,
  Trash2,
} from 'lucide-react';
import clsx from 'clsx';
import AlertBox from '../../components/common/AlertBox';
import Badge from '../../components/common/Badge';
import Button from '../../components/common/Button';
import EmptyState from '../../components/common/EmptyState';
import Modal from '../../components/common/Modal';
import Spinner from '../../components/common/Spinner';
import TextField from '../../components/common/TextField';
import { courseApi } from '../../api/courseApi';
import RagWorkspace from '../rag/RagWorkspace';
import { AdminPageHeader, FilterSelect, Panel } from './AdminCommon';
import { useAdminQuery } from './useAdminQuery';
import { getErrorMessage } from '../../utils/apiError';

// =============================================================================
// 1. MODAL THÊM / SỬA MÔN HỌC (GỌI API THỰC TẾ)
// =============================================================================
function CourseModal({ open, onClose, course, onSaved }) {
  const isEdit = Boolean(course);
  const [form, setForm] = useState({
    code: '',
    title: '',
    description: '',
    status: 'ACTIVE',
  });
  const [errors, setErrors] = useState({});
  const [submitting, setSubmitting] = useState(false);
  const [apiError, setApiError] = useState(null);

  useEffect(() => {
    if (course) {
      setForm({
        code: course.code || '',
        title: course.title || '',
        description: course.description || '',
        status: course.status || 'ACTIVE',
      });
    } else {
      setForm({ code: '', title: '', description: '', status: 'ACTIVE' });
    }
    setErrors({});
    setApiError(null);
  }, [course, open]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    const newErrors = {};
    if (!form.code.trim()) newErrors.code = 'Mã môn học không được để trống.';
    if (!form.title.trim()) newErrors.title = 'Tên môn học không được để trống.';
    if (Object.keys(newErrors).length > 0) {
      setErrors(newErrors);
      return;
    }

    setSubmitting(true);
    setApiError(null);
    try {
      let saved;
      if (isEdit) {
        saved = await courseApi.updateCourse(course.id, form);
      } else {
        saved = await courseApi.createCourse(form);
      }
      onSaved(saved, isEdit);
      onClose();
    } catch (err) {
      setApiError(getErrorMessage(err));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={isEdit ? 'Chỉnh sửa môn học' : 'Thêm môn học mới'}
    >
      <form onSubmit={handleSubmit} noValidate className="space-y-4">
        {apiError && (
          <AlertBox tone="error" className="text-xs">
            {apiError}
          </AlertBox>
        )}

        <TextField
          label="Mã môn học"
          value={form.code}
          onChange={(e) => {
            setForm((f) => ({ ...f, code: e.target.value.toUpperCase() }));
            if (errors.code) setErrors((err) => ({ ...err, code: null }));
          }}
          error={errors.code}
          placeholder="Ví dụ: CS101, IT203..."
          disabled={isEdit}
        />

        <TextField
          label="Tên môn học"
          value={form.title}
          onChange={(e) => {
            setForm((f) => ({ ...f, title: e.target.value }));
            if (errors.title) setErrors((err) => ({ ...err, title: null }));
          }}
          error={errors.title}
          placeholder="Ví dụ: Cơ sở dữ liệu nâng cao..."
        />

        <div>
          <label className="mb-1.5 block text-sm font-medium text-slate-700">Mô tả tóm tắt</label>
          <textarea
            value={form.description}
            onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
            rows={3}
            placeholder="Mô tả nội dung chương trình đào tạo..."
            className="w-full rounded-lg border border-slate-300 p-2.5 text-sm focus:border-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-100"
          />
        </div>

        <div>
          <label className="mb-1.5 block text-sm font-medium text-slate-700">Trạng thái công khai</label>
          <select
            value={form.status}
            onChange={(e) => setForm((f) => ({ ...f, status: e.target.value }))}
            className="h-10 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm focus:border-blue-600 focus:outline-none"
          >
            <option value="ACTIVE">Hoạt động / Công khai (ACTIVE)</option>
            <option value="INACTIVE">Lưu trữ / Tạm ẩn (INACTIVE)</option>
          </select>
        </div>

        <div className="mt-6 flex justify-end gap-2">
          <Button variant="outline" type="button" onClick={onClose} disabled={submitting}>
            Hủy
          </Button>
          <Button type="submit" loading={submitting}>
            {isEdit ? 'Lưu cập nhật' : 'Tạo môn học'}
          </Button>
        </div>
      </form>
    </Modal>
  );
}

// =============================================================================
// 2. MODAL XÁC NHẬN XÓA / ẨN MÔN HỌC (GỌI API THỰC TẾ)
// =============================================================================
function DeleteCourseModal({ open, onClose, course, onConfirmed }) {
  const [submitting, setSubmitting] = useState(false);
  const [apiError, setApiError] = useState(null);

  if (!course) return null;

  const handleConfirm = async () => {
    setSubmitting(true);
    setApiError(null);
    try {
      const res = await courseApi.deleteCourse(course.id);
      onConfirmed(res, course);
      onClose();
    } catch (err) {
      setApiError(getErrorMessage(err));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Modal open={open} onClose={onClose} title="Xác nhận xóa môn học">
      <div className="space-y-4">
        {apiError && (
          <AlertBox tone="error" className="text-xs">
            {apiError}
          </AlertBox>
        )}

        <p className="text-sm text-slate-600">
          Bạn có chắc chắn muốn xóa môn học <strong>{course.code} – {course.title}</strong>?
        </p>

        <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-xs text-amber-800">
          <p className="font-semibold">Cơ chế bảo toàn toàn vẹn dữ liệu:</p>
          <p className="mt-1">
            Nếu môn học đã có sinh viên ghi danh hoặc có dữ liệu học tập, hệ thống sẽ tự động chuyển môn học sang trạng thái <strong>Lưu trữ (INACTIVE)</strong> để ẩn khỏi sinh viên mà không làm mất lịch sử học tập.
          </p>
        </div>

        <div className="flex justify-end gap-2 pt-2">
          <Button variant="outline" onClick={onClose} disabled={submitting}>
            Hủy bỏ
          </Button>
          <Button variant="danger" icon={Trash2} loading={submitting} onClick={handleConfirm}>
            Xác nhận xóa
          </Button>
        </div>
      </div>
    </Modal>
  );
}

// =============================================================================
// 3. MODAL THÊM / SỬA BÀI HỌC (LESSON MODAL)
// =============================================================================
function LessonModal({ open, onClose, courseId, lesson, onSaved }) {
  const isEdit = Boolean(lesson);
  const [title, setTitle] = useState('');
  const [orderIndex, setOrderIndex] = useState(1);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (lesson) {
      setTitle(lesson.title || '');
      setOrderIndex(lesson.order_index || 1);
    } else {
      setTitle('');
      setOrderIndex(1);
    }
    setError(null);
  }, [lesson, open]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!title.trim()) {
      setError('Tiêu đề bài học không được để trống.');
      return;
    }

    setSubmitting(true);
    setError(null);
    try {
      if (isEdit) {
        await courseApi.updateLesson(courseId, lesson.id, { title, orderIndex });
      } else {
        await courseApi.createLesson(courseId, { title, orderIndex });
      }
      onSaved();
      onClose();
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Modal open={open} onClose={onClose} title={isEdit ? 'Sửa bài học' : 'Thêm bài học mới'}>
      <form onSubmit={handleSubmit} noValidate className="space-y-4">
        {error && <AlertBox tone="error" className="text-xs">{error}</AlertBox>}

        <TextField
          label="Tiêu đề bài học"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="Ví dụ: Bài 3: Mô hình Dữ liệu Quan hệ"
          required
        />

        <div>
          <label className="mb-1.5 block text-sm font-medium text-slate-700">Số thứ tự bài học</label>
          <input
            type="number"
            min={1}
            value={orderIndex}
            onChange={(e) => setOrderIndex(Number(e.target.value))}
            className="h-10 w-full rounded-lg border border-slate-300 px-3 text-sm focus:border-blue-600 focus:outline-none"
          />
        </div>

        <div className="mt-6 flex justify-end gap-2">
          <Button variant="outline" type="button" onClick={onClose} disabled={submitting}>Hủy</Button>
          <Button type="submit" loading={submitting}>{isEdit ? 'Lưu thay đổi' : 'Tạo bài học'}</Button>
        </div>
      </form>
    </Modal>
  );
}

// =============================================================================
// 4. MODAL THÊM / SỬA CHỦ ĐỀ KIẾN THỨC (TOPIC MODAL)
// =============================================================================
function TopicModal({ open, onClose, courseId, lessonId, topic, onSaved }) {
  const isEdit = Boolean(topic);
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (topic) {
      setName(topic.name || '');
      setDescription(topic.description || '');
    } else {
      setName('');
      setDescription('');
    }
    setError(null);
  }, [topic, open]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!name.trim()) {
      setError('Tên chủ đề không được để trống.');
      return;
    }

    setSubmitting(true);
    setError(null);
    try {
      if (isEdit) {
        await courseApi.updateTopic(courseId, topic.id, { name, description });
      } else {
        await courseApi.createTopic(courseId, lessonId, { name, description });
      }
      onSaved();
      onClose();
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Modal open={open} onClose={onClose} title={isEdit ? 'Sửa chủ đề kiến thức' : 'Thêm chủ đề mới'}>
      <form onSubmit={handleSubmit} noValidate className="space-y-4">
        {error && <AlertBox tone="error" className="text-xs">{error}</AlertBox>}

        <TextField
          label="Tên chủ đề"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Ví dụ: Thực thể, Thuộc tính và Khóa chính"
          required
        />

        <div>
          <label className="mb-1.5 block text-sm font-medium text-slate-700">Mô tả chủ đề</label>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={3}
            placeholder="Mục tiêu kiến thức sinh viên cần nắm vững..."
            className="w-full rounded-lg border border-slate-300 p-2.5 text-sm focus:border-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-100"
          />
        </div>

        <div className="mt-6 flex justify-end gap-2">
          <Button variant="outline" type="button" onClick={onClose} disabled={submitting}>Hủy</Button>
          <Button type="submit" loading={submitting}>{isEdit ? 'Lưu thay đổi' : 'Tạo chủ đề'}</Button>
        </div>
      </form>
    </Modal>
  );
}

// =============================================================================
// 5. MODAL SOẠN / SỬA NỘI DUNG LÝ THUYẾT BÀI HỌC (CONTENT MODAL)
// =============================================================================
function ContentModal({ open, onClose, courseId, lessonId, content, onSaved }) {
  const [body, setBody] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    setBody(content?.body || '');
    setError(null);
  }, [content, open]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!body.trim()) {
      setError('Nội dung bài học không được để trống.');
      return;
    }

    setSubmitting(true);
    setError(null);
    try {
      await courseApi.saveLessonContent(courseId, lessonId, {
        body,
        contentType: 'MARKDOWN',
        contentId: content?.id,
      });
      onSaved();
      onClose();
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Modal open={open} size="lg" onClose={onClose} title="Soạn / Chỉnh sửa nội dung lý thuyết (Markdown)">
      <form onSubmit={handleSubmit} noValidate className="space-y-4">
        {error && <AlertBox tone="error" className="text-xs">{error}</AlertBox>}

        <div>
          <div className="mb-1.5 flex items-center justify-between">
            <label className="text-sm font-medium text-slate-700">Nội dung bài giảng (Hỗ trợ định dạng Markdown & LaTeX)</label>
            <span className="text-xs text-slate-400">{body.length} ký tự</span>
          </div>
          <textarea
            value={body}
            onChange={(e) => setBody(e.target.value)}
            rows={14}
            spellCheck={false}
            placeholder="# Tiêu đề chính&#10;&#10;Nội dung giải thích kiến thức lý thuyết chi tiết..."
            className="w-full rounded-lg border border-slate-300 p-3.5 font-mono text-sm leading-relaxed focus:border-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-100"
          />
        </div>

        <div className="mt-6 flex justify-end gap-2">
          <Button variant="outline" type="button" onClick={onClose} disabled={submitting}>Hủy</Button>
          <Button type="submit" loading={submitting}>Lưu nội dung bài giảng</Button>
        </div>
      </form>
    </Modal>
  );
}

// =============================================================================
// 6. GIAO DIỆN QUẢN LÝ CHƯƠNG TRÌNH ĐÀO TẠO & CHỦ ĐỀ (CURRICULUM VIEW)
// =============================================================================
function CourseCurriculumView({ course, onBack, onCourseUpdated }) {
  const [refreshKey, setRefreshKey] = useState(0);
  const [lessonModal, setLessonModal] = useState(null); // { mode: 'create' } | { mode: 'edit', lesson }
  const [topicModal, setTopicModal] = useState(null); // { mode: 'create', lessonId } | { mode: 'edit', topic, lessonId }
  const [contentModal, setContentModal] = useState(null); // { lessonId, content }
  const [notice, setNotice] = useState(null);

  // Tải chi tiết cây bài học + chủ đề + nội dung từ backend
  const detailQuery = useAdminQuery(
    () => courseApi.getCourseDetail(course.id),
    [course.id, refreshKey]
  );

  const courseDetail = detailQuery.data;
  const lessons = courseDetail?.lessons || [];

  const reloadData = () => {
    setRefreshKey((k) => k + 1);
    if (onCourseUpdated) onCourseUpdated();
  };

  const handleDeleteLesson = async (lessonId) => {
    if (!window.confirm('Bạn có chắc chắn muốn xóa bài học này? Tất cả chủ đề và nội dung thuộc bài học sẽ bị xóa.')) return;
    try {
      await courseApi.deleteLesson(course.id, lessonId);
      setNotice('Đã xóa bài học thành công.');
      reloadData();
    } catch (err) {
      alert(getErrorMessage(err));
    }
  };

  const handleDeleteTopic = async (topicId) => {
    if (!window.confirm('Bạn có chắc chắn muốn xóa chủ đề kiến thức này?')) return;
    try {
      await courseApi.deleteTopic(course.id, topicId);
      setNotice('Đã xóa chủ đề thành công.');
      reloadData();
    } catch (err) {
      alert(getErrorMessage(err));
    }
  };

  return (
    <div className="space-y-6">
      {/* Header điều hướng quay lại */}
      <div className="flex flex-col gap-3 rounded-2xl border border-slate-200/80 bg-white p-5 shadow-sm sm:flex-row sm:items-center sm:justify-between">
        <div>
          <button
            type="button"
            onClick={onBack}
            className="inline-flex items-center gap-1.5 text-xs font-semibold text-blue-600 hover:text-blue-700 hover:underline"
          >
            <ArrowLeft size={14} />
            <span>Quay lại danh mục môn học</span>
          </button>
          <div className="mt-1.5 flex items-center gap-3">
            <h1 className="text-xl font-bold tracking-tight text-slate-900">
              {course.code} – {course.title}
            </h1>
            <Badge tone={course.status === 'ACTIVE' ? 'green' : 'gray'}>
              {course.status === 'ACTIVE' ? 'Hoạt động' : 'Lưu trữ'}
            </Badge>
          </div>
          <p className="mt-0.5 text-xs text-slate-500">
            {course.description || 'Chương trình đào tạo, danh sách chủ đề và nội dung bài học.'}
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            icon={Plus}
            onClick={() => setLessonModal({ mode: 'create' })}
          >
            Thêm bài học mới
          </Button>
        </div>
      </div>

      {notice && (
        <AlertBox
          tone="success"
          action={
            <button type="button" onClick={() => setNotice(null)} className="text-xs font-semibold underline">
              Đóng
            </button>
          }
        >
          {notice}
        </AlertBox>
      )}

      {/* Cây cấu trúc bài giảng & chủ đề */}
      {detailQuery.loading && !courseDetail ? (
        <div className="flex justify-center py-16 text-slate-400">
          <Spinner size={28} label="Đang tải chương trình học..." />
        </div>
      ) : lessons.length === 0 ? (
        <EmptyState
          icon={BookOpen}
          title="Môn học chưa có bài học nào"
          description='Bấm "Thêm bài học mới" ở góc trên để bắt đầu xây dựng chương trình giảng dạy và chủ đề kiến thức.'
        />
      ) : (
        <div className="space-y-5">
          {lessons.map((lesson) => {
            const topics = lesson.topics || [];
            const contents = lesson.contents || [];
            const mainContent = contents[0];

            return (
              <div
                key={lesson.id}
                className="overflow-hidden rounded-2xl border border-slate-200/80 bg-white shadow-sm transition-all"
              >
                {/* Header của bài học */}
                <div className="flex flex-col gap-3 border-b border-slate-100 bg-slate-50/70 p-4 sm:flex-row sm:items-center sm:justify-between">
                  <div className="flex items-center gap-3">
                    <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-blue-100 text-xs font-bold text-blue-700">
                      {lesson.order_index}
                    </span>
                    <div>
                      <h2 className="text-base font-bold text-slate-900">{lesson.title}</h2>
                      <p className="text-xs text-slate-400">
                        {topics.length} chủ đề kiến thức · {contents.length > 0 ? 'Đã có nội dung' : 'Chưa có nội dung'}
                      </p>
                    </div>
                  </div>

                  <div className="flex flex-wrap items-center gap-1.5">
                    <Button
                      variant="outline"
                      size="sm"
                      icon={Plus}
                      onClick={() => setTopicModal({ mode: 'create', lessonId: lesson.id })}
                    >
                      Thêm chủ đề
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      icon={Pencil}
                      onClick={() => setContentModal({ lessonId: lesson.id, content: mainContent })}
                    >
                      {mainContent ? 'Sửa nội dung' : 'Soạn nội dung'}
                    </Button>
                    <button
                      type="button"
                      onClick={() => setLessonModal({ mode: 'edit', lesson })}
                      title="Sửa tên bài học"
                      className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-200/70 hover:text-slate-700"
                    >
                      <Pencil size={15} />
                    </button>
                    <button
                      type="button"
                      onClick={() => handleDeleteLesson(lesson.id)}
                      title="Xóa bài học"
                      className="rounded-lg p-1.5 text-red-400 hover:bg-red-50 hover:text-red-600"
                    >
                      <Trash2 size={15} />
                    </button>
                  </div>
                </div>

                <div className="p-5 space-y-5">
                  {/* DANH SÁCH CHỦ ĐỀ KIẾN THỨC CỦA BÀI HỌC */}
                  <div>
                    <div className="mb-2.5 flex items-center justify-between">
                      <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                        Danh sách chủ đề kiến thức ({topics.length})
                      </span>
                    </div>

                    {topics.length === 0 ? (
                      <p className="rounded-xl border border-dashed border-slate-200 p-4 text-center text-xs text-slate-400">
                        Chưa có chủ đề nào trong bài học này. Bấm &quot;Thêm chủ đề&quot; để tạo.
                      </p>
                    ) : (
                      <div className="overflow-x-auto rounded-xl border border-slate-100">
                        <table className="w-full text-left text-xs text-slate-600">
                          <thead className="bg-slate-50 text-[11px] font-semibold uppercase text-slate-400">
                            <tr>
                              <th className="px-3.5 py-2.5">Tên chủ đề</th>
                              <th className="px-3.5 py-2.5">Mục tiêu / Mô tả kiến thức</th>
                              <th className="px-3.5 py-2.5 text-right">Thao tác</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-slate-100">
                            {topics.map((t) => (
                              <tr key={t.id} className="hover:bg-slate-50/50">
                                <td className="px-3.5 py-2.5 font-semibold text-slate-800">
                                  {t.name}
                                </td>
                                <td className="px-3.5 py-2.5 text-slate-500">
                                  {t.description || 'Chưa có mô tả'}
                                </td>
                                <td className="px-3.5 py-2.5 text-right">
                                  <div className="flex items-center justify-end gap-2">
                                    <button
                                      type="button"
                                      onClick={() => setTopicModal({ mode: 'edit', topic: t, lessonId: lesson.id })}
                                      className="font-medium text-blue-600 hover:text-blue-700 hover:underline"
                                    >
                                      Sửa
                                    </button>
                                    <button
                                      type="button"
                                      onClick={() => handleDeleteTopic(t.id)}
                                      className="font-medium text-red-500 hover:text-red-700 hover:underline"
                                    >
                                      Xóa
                                    </button>
                                  </div>
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    )}
                  </div>

                  {/* XEM TRƯỚC NỘI DUNG LÝ THUYẾT BÀI HỌC */}
                  <div>
                    <div className="mb-2 flex items-center justify-between">
                      <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                        Nội dung bài giảng lý thuyết
                      </span>
                    </div>

                    {mainContent ? (
                      <div className="rounded-xl border border-slate-200 bg-slate-50/60 p-4 font-mono text-xs text-slate-700 max-h-40 overflow-y-auto leading-relaxed whitespace-pre-wrap">
                        {mainContent.body}
                      </div>
                    ) : (
                      <p className="rounded-xl border border-dashed border-slate-200 p-3 text-center text-xs text-slate-400">
                        Chưa có nội dung lý thuyết. Bấm &quot;Soạn nội dung&quot; để bổ sung bài giảng.
                      </p>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Modals */}
      {lessonModal && (
        <LessonModal
          open={Boolean(lessonModal)}
          onClose={() => setLessonModal(null)}
          courseId={course.id}
          lesson={lessonModal.lesson}
          onSaved={() => {
            setNotice('Đã cập nhật bài học thành công.');
            reloadData();
          }}
        />
      )}

      {topicModal && (
        <TopicModal
          open={Boolean(topicModal)}
          onClose={() => setTopicModal(null)}
          courseId={course.id}
          lessonId={topicModal.lessonId}
          topic={topicModal.topic}
          onSaved={() => {
            setNotice('Đã cập nhật chủ đề kiến thức thành công.');
            reloadData();
          }}
        />
      )}

      {contentModal && (
        <ContentModal
          open={Boolean(contentModal)}
          onClose={() => setContentModal(null)}
          courseId={course.id}
          lessonId={contentModal.lessonId}
          content={contentModal.content}
          onSaved={() => {
            setNotice('Đã lưu nội dung lý thuyết bài giảng thành công.');
            reloadData();
          }}
        />
      )}
    </div>
  );
}

// =============================================================================
// 7. TRANG CHÍNH: QUẢN LÝ KHÓA HỌC (MAIN PAGE)
// =============================================================================
export default function CourseManagementPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const paramCourseId = searchParams.get('course_id');
  const paramView = searchParams.get('view'); // 'rag' | 'curriculum'

  const [managingRagCourse, setManagingRagCourse] = useState(null);
  const [curriculumCourse, setCurriculumCourse] = useState(null);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [modalOpen, setModalOpen] = useState(false);
  const [editingCourse, setEditingCourse] = useState(null);
  const [deletingCourse, setDeletingCourse] = useState(null);
  const [toast, setToast] = useState(null);

  // Tải danh sách môn học từ API backend (bao gồm cả môn ẩn/lưu trữ để Admin quản lý)
  const coursesQuery = useAdminQuery(
    () => courseApi.getCourses({ limit: 100, include_inactive: true }),
    []
  );

  const rawCourses = coursesQuery.data?.courses ?? [];

  // Tự động mở theo URL query param nếu có
  useEffect(() => {
    if (paramCourseId && rawCourses.length > 0) {
      const found = rawCourses.find((c) => String(c.id) === String(paramCourseId));
      if (found) {
        if (paramView === 'curriculum') {
          setCurriculumCourse(found);
          setManagingRagCourse(null);
        } else {
          setManagingRagCourse(found);
          setCurriculumCourse(null);
        }
      }
    }
  }, [paramCourseId, paramView, rawCourses]);

  const filteredCourses = useMemo(() => {
    return rawCourses.filter((c) => {
      const matchSearch =
        !search.trim() ||
        c.code?.toLowerCase().includes(search.toLowerCase()) ||
        c.title?.toLowerCase().includes(search.toLowerCase());
      const matchStatus = !statusFilter || c.status === statusFilter;
      return matchSearch && matchStatus;
    });
  }, [rawCourses, search, statusFilter]);

  const handleOpenCurriculum = (course) => {
    setCurriculumCourse(course);
    setManagingRagCourse(null);
    setSearchParams({ course_id: course.id, view: 'curriculum' });
  };

  const handleOpenRag = (course) => {
    setManagingRagCourse(course);
    setCurriculumCourse(null);
    setSearchParams({ course_id: course.id, view: 'rag' });
  };

  const handleBackToList = () => {
    setCurriculumCourse(null);
    setManagingRagCourse(null);
    setSearchParams({});
    coursesQuery.reload();
  };

  const handleCourseSaved = (saved, wasEdit) => {
    coursesQuery.reload();
    if (wasEdit) {
      setToast(`Đã cập nhật thông tin môn học ${saved.code} thành công.`);
    } else {
      setToast(`Đã tạo thành công môn học mới ${saved.code}. Tự động mở chương trình học.`);
      // Tự động mở ngay màn hình chủ đề & nội dung để Admin soạn thảo ngay!
      handleOpenCurriculum(saved);
    }
  };

  const handleCourseDeleted = (res, course) => {
    coursesQuery.reload();
    setToast(res.message || `Đã xóa môn học ${course.code}.`);
  };

  return (
    <div className="space-y-6">
      {/* Toast thông báo */}
      {toast && (
        <AlertBox
          tone="success"
          action={
            <button
              type="button"
              onClick={() => setToast(null)}
              className="text-xs font-semibold underline"
            >
              Đóng
            </button>
          }
        >
          {toast}
        </AlertBox>
      )}

      {/* CHẾ ĐỘ 1: QUẢN LÝ CHƯƠNG TRÌNH ĐÀO TẠO & CHỦ ĐỀ & NỘI DUNG */}
      {curriculumCourse ? (
        <CourseCurriculumView
          course={curriculumCourse}
          onBack={handleBackToList}
          onCourseUpdated={coursesQuery.reload}
        />
      ) : managingRagCourse ? (
        /* CHẾ ĐỘ 2: QUẢN LÝ TÀI LIỆU RAG CỦA MỘT MÔN */
        <div className="space-y-6">
          <div className="flex flex-col gap-3 rounded-2xl border border-slate-200/80 bg-white p-5 shadow-sm sm:flex-row sm:items-center sm:justify-between">
            <div>
              <button
                type="button"
                onClick={handleBackToList}
                className="inline-flex items-center gap-1.5 text-xs font-semibold text-blue-600 hover:text-blue-700 hover:underline"
              >
                <ArrowLeft size={14} />
                <span>Quay lại danh mục môn học</span>
              </button>
              <h1 className="mt-1.5 text-xl font-bold tracking-tight text-slate-900">
                Tài liệu giáo trình RAG · {managingRagCourse.code} – {managingRagCourse.title}
              </h1>
              <p className="mt-0.5 text-xs text-slate-500">
                Tải lên giáo trình PDF và quản lý tri thức phục vụ AI trả lời có trích dẫn số trang.
              </p>
            </div>

            {rawCourses.length > 1 && (
              <FilterSelect
                label="Chuyển môn"
                value={managingRagCourse.id}
                onChange={(id) => {
                  const next = rawCourses.find((c) => c.id === Number(id));
                  if (next) handleOpenRag(next);
                }}
                className="w-full sm:max-w-xs"
              >
                {rawCourses.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.code} – {c.title}
                  </option>
                ))}
              </FilterSelect>
            )}
          </div>

          <RagWorkspace courseId={managingRagCourse.id} hideAskTab={true} />
        </div>
      ) : (
        /* CHẾ ĐỘ 3: BẢNG DANH MỤC MÔN HỌC */
        <div className="space-y-6">
          <AdminPageHeader
            title="Quản lý Khóa học"
            description="Quản lý danh mục chương trình đào tạo, danh sách bài học, chủ đề kiến thức và tài liệu giáo trình RAG."
            actions={
              <Button
                icon={Plus}
                onClick={() => {
                  setEditingCourse(null);
                  setModalOpen(true);
                }}
              >
                Thêm môn học mới
              </Button>
            }
          />

          <Panel>
            <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <div className="relative flex-1">
                <Search
                  size={16}
                  className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-400"
                  aria-hidden="true"
                />
                <input
                  type="search"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  placeholder="Tìm môn học theo mã hoặc tên môn..."
                  className="h-10 w-full rounded-lg border border-slate-300 bg-white pl-9 pr-3 text-sm shadow-sm focus:border-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-100"
                />
              </div>

              <div className="flex gap-2">
                <FilterSelect
                  label="Lọc trạng thái"
                  value={statusFilter}
                  onChange={setStatusFilter}
                >
                  <option value="">Tất cả trạng thái</option>
                  <option value="ACTIVE">Hoạt động (ACTIVE)</option>
                  <option value="INACTIVE">Lưu trữ (INACTIVE)</option>
                </FilterSelect>
              </div>
            </div>

            {coursesQuery.error && (
              <AlertBox tone="error" className="mb-4">
                {coursesQuery.error}
              </AlertBox>
            )}

            {coursesQuery.loading && !coursesQuery.data ? (
              <div className="flex justify-center py-16 text-slate-400">
                <Spinner size={28} label="Đang tải danh sách môn học..." />
              </div>
            ) : filteredCourses.length === 0 ? (
              <EmptyState
                icon={BookOpen}
                title="Không tìm thấy môn học nào"
                description={
                  search || statusFilter
                    ? 'Không có môn học nào khớp với bộ lọc tìm kiếm.'
                    : 'Hệ thống chưa có môn học nào. Hãy bấm "Thêm môn học mới" để tạo.'
                }
              />
            ) : (
              <div className="overflow-x-auto rounded-xl border border-slate-200">
                <table className="w-full min-w-[900px] text-left text-sm text-slate-600">
                  <thead className="border-b border-slate-200 bg-slate-50/70 text-xs font-semibold uppercase tracking-wider text-slate-500">
                    <tr>
                      <th className="px-4 py-3 whitespace-nowrap w-24">Mã môn</th>
                      <th className="px-4 py-3 whitespace-nowrap min-w-[200px]">Tên môn học</th>
                      <th className="px-4 py-3 whitespace-nowrap text-center w-28">Số bài học</th>
                      <th className="px-4 py-3 whitespace-nowrap text-center w-24">Chủ đề</th>
                      <th className="px-4 py-3 whitespace-nowrap text-center w-28">Trạng thái</th>
                      <th className="px-4 py-3 whitespace-nowrap text-right min-w-[340px]">Thao tác</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {filteredCourses.map((c) => (
                      <tr key={c.id} className="transition-colors hover:bg-slate-50/60">
                        <td className="px-4 py-3.5 font-semibold text-slate-900 whitespace-nowrap">
                          {c.code}
                        </td>
                        <td className="px-4 py-3.5">
                          <button
                            type="button"
                            onClick={() => handleOpenCurriculum(c)}
                            className="font-medium text-slate-900 hover:text-blue-600 text-left"
                            title="Bấm để xem và sửa chủ đề & nội dung"
                          >
                            {c.title}
                          </button>
                          {c.description && (
                            <p className="line-clamp-1 text-xs text-slate-400">
                              {c.description}
                            </p>
                          )}
                        </td>
                        <td className="px-4 py-3.5 text-center font-medium whitespace-nowrap">
                          {c.total_lessons || 0}
                        </td>
                        <td className="px-4 py-3.5 text-center font-medium whitespace-nowrap">
                          {c.topic_count || 0}
                        </td>
                        <td className="px-4 py-3.5 text-center whitespace-nowrap">
                          <Badge tone={c.status === 'ACTIVE' ? 'green' : 'gray'}>
                            {c.status === 'ACTIVE' ? 'Hoạt động' : 'Lưu trữ'}
                          </Badge>
                        </td>
                        <td className="px-4 py-3.5 text-right whitespace-nowrap">
                          <div className="flex items-center justify-end gap-2 whitespace-nowrap">
                            <Button
                              variant="primary"
                              size="sm"
                              icon={ListTree}
                              className="whitespace-nowrap shrink-0"
                              title="Xem danh sách chủ đề và soạn nội dung"
                              onClick={() => handleOpenCurriculum(c)}
                            >
                              Chủ đề & Nội dung
                            </Button>
                            <Button
                              variant="outline"
                              size="sm"
                              icon={FileText}
                              className="whitespace-nowrap shrink-0"
                              title="Quản lý tài liệu RAG của môn này"
                              onClick={() => handleOpenRag(c)}
                            >
                              Tài liệu RAG
                            </Button>
                            <Button
                              variant="ghost"
                              size="sm"
                              icon={Pencil}
                              className="shrink-0"
                              title="Chỉnh sửa thông tin môn học"
                              onClick={() => {
                                setEditingCourse(c);
                                setModalOpen(true);
                              }}
                            />
                            <Button
                              variant="ghost"
                              size="sm"
                              icon={Trash2}
                              title="Xóa / Ẩn môn học"
                              className="text-red-500 hover:text-red-700 shrink-0"
                              onClick={() => setDeletingCourse(c)}
                            />
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Panel>
        </div>
      )}

      {/* Modal chỉnh sửa / tạo môn */}
      <CourseModal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        course={editingCourse}
        onSaved={handleCourseSaved}
      />

      {/* Modal xác nhận ẩn / xóa */}
      <DeleteCourseModal
        open={Boolean(deletingCourse)}
        onClose={() => setDeletingCourse(null)}
        course={deletingCourse}
        onConfirmed={handleCourseDeleted}
      />
    </div>
  );
}