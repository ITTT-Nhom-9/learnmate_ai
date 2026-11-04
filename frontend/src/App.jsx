import React from 'react';

function App() {
  return (
    <div className="min-h-screen bg-slate-50 flex flex-col items-center justify-center p-6">
      <div className="max-w-2xl w-full bg-white rounded-xl shadow-md border border-slate-200 p-8">
        <div className="border-b border-slate-200 pb-4 mb-6">
          <h1 className="text-2xl font-bold text-slate-800">LearnMate AI</h1>
          <p className="text-sm text-slate-600 mt-1">Hệ Thống Trợ Lý Học Tập Cá Nhân Hóa</p>
        </div>

        <div className="space-y-4">
          <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-lg text-emerald-800 text-sm">
            <span className="font-semibold">Trạng thái hệ thống:</span> Monorepo & 4 Docker Containers đã được thiết lập thành công (Task TK-01).
          </div>

          <div className="grid grid-cols-2 gap-4 text-xs text-slate-700">
            <div className="p-3 bg-slate-50 rounded border border-slate-200">
              <span className="font-semibold block text-slate-900">Backend Core:</span>
              <span>FastAPI (Port 8080)</span>
            </div>
            <div className="p-3 bg-slate-50 rounded border border-slate-200">
              <span className="font-semibold block text-slate-900">AI Microservice:</span>
              <span>FastAPI & RAG (Port 8000)</span>
            </div>
            <div className="p-3 bg-slate-50 rounded border border-slate-200">
              <span className="font-semibold block text-slate-900">Database:</span>
              <span>MySQL 8.0 (Host Port 3307 : 3306)</span>
            </div>
            <div className="p-3 bg-slate-50 rounded border border-slate-200">
              <span className="font-semibold block text-slate-900">Frontend:</span>
              <span>React 18 + Vite (Port 5173 / 80)</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;

