import { useEffect } from 'react';
import { BrowserRouter } from 'react-router-dom';
import AppRoutes from './routes/AppRoutes';
import { authApi } from './api/authApi';

function App() {
  // Mở lại trang: khôi phục phiên bằng refresh token đã lưu (Access Token chỉ nằm trong bộ nhớ)
  useEffect(() => {
    authApi.restoreSession();
  }, []);

  return (
    <BrowserRouter>
      <AppRoutes />
    </BrowserRouter>
  );
}

export default App;
