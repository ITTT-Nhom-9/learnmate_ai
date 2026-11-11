import { useEffect, useRef } from 'react';

/**
 * Hành vi chung của Drawer / Bottom Sheet: Esc để đóng, khóa cuộn nền,
 * chuyển tiêu điểm vào khung khi mở và trả tiêu điểm về nút đã mở khi đóng.
 */
export function useModalBehavior(open, onClose) {
  const panelRef = useRef(null);

  useEffect(() => {
    if (!open) return undefined;
    const opener = document.activeElement;
    const onKeyDown = (event) => event.key === 'Escape' && onClose();
    document.addEventListener('keydown', onKeyDown);
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    panelRef.current?.focus();
    return () => {
      document.removeEventListener('keydown', onKeyDown);
      document.body.style.overflow = previousOverflow;
      if (opener instanceof HTMLElement) opener.focus();
    };
  }, [open, onClose]);

  return panelRef;
}
