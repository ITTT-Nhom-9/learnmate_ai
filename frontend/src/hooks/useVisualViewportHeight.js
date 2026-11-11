import { useEffect, useState } from 'react';

/**
 * Chiều cao vùng nhìn thấy thực sự của trình duyệt. Khi bàn phím ảo trên điện thoại mở ra, giá trị này
 * thu nhỏ lại (còn 100vh/100dvh thì không đổi trên iOS) -> khung chat co theo và ô nhập luôn nằm trên bàn phím.
 */
export function useVisualViewportHeight() {
  const read = () => Math.round(window.visualViewport?.height ?? window.innerHeight);
  const [height, setHeight] = useState(read);

  useEffect(() => {
    const viewport = window.visualViewport;
    const update = () => {
      setHeight(read());
      if (viewport && viewport.offsetTop > 0) window.scrollTo(0, 0); // iOS đẩy trang lên khi mở bàn phím
    };
    update();
    window.addEventListener('resize', update);
    viewport?.addEventListener('resize', update);
    viewport?.addEventListener('scroll', update);
    return () => {
      window.removeEventListener('resize', update);
      viewport?.removeEventListener('resize', update);
      viewport?.removeEventListener('scroll', update);
    };
  }, []);

  return height;
}
