# LearnMate AI - Hệ Thống Trợ Lý Học Tập Cá Nhân Hóa

## 1. Giới thiệu tổng quan dự án

LearnMate AI là nền tảng trợ lý học tập thông minh ứng dụng trí tuệ nhân tạo (AI) và kỹ thuật Retrieval-Augmented Generation (RAG). Hệ thống hỗ trợ sinh viên và người học tiếp cận tài liệu học tập, tra cứu kiến thức theo phương pháp sư phạm Socratic, tự động sinh đề trắc nghiệm thích ứng theo năng lực và quản lý tiến độ học tập một cách trực quan, khoa học.

### 1.1. Thông tin dự án

- Tên dự án: LearnMate AI
- Nhóm thực hiện: Nhóm 9 (ITTT-Nhom-9)
- Repository: https://github.com/ITTT-Nhom-9/learnmate_ai
- Thời gian thực hiện: 3 tuần (02/11/2026 - 22/11/2026)
- Mô hình phát triển: Agile / Scrum (3 Sprints, 34 tasks, tổng 100 điểm)

### 1.2. Danh sách thành viên và phân công vai trò

| STT | Họ và tên           | Mã sinh viên | Vai trò chính                    | Phạm vi trách nhiệm                                                       |
| --- | ------------------- | ------------ | -------------------------------- | ------------------------------------------------------------------------- |
| 1   | Trần Văn Khiêm      | N25DTCN129   | Nhóm trưởng / Backend Lead       | Quản lý dự án, Kiến trúc Backend, Quản lý phân nhánh & Duyệt Pull Request |
| 2   | Huỳnh Quốc Huy      | N25DTCN127   | BA Lead / Frontend Developer     | Đặc tả yêu cầu nghiệp vụ (SRS), Thiết kế giao diện người dùng             |
| 3   | Tăng Mạnh Khang     | 1627         | Software Architect / AI Engineer | Thiết kế kiến trúc hệ thống (SDD), Module AI RAG, Database & Docker       |
| 4   | Phạm Ngọc Quỳnh Như | 1691         | QA Lead / Tester                 | Đảm bảo chất lượng, Kế hoạch & Kịch bản kiểm thử (Test Case), Báo cáo QA  |

---

## 2. Kiến trúc kỹ thuật và Công nghệ sử dụng

- Backend Core: Python 3.11+, FastAPI, SQLAlchemy 2.0 ORM, Pydantic v2, PyJWT, Alembic Migration
- AI Microservice: Python 3.11+, FastAPI (Stateless), Adapter Pattern (OpenAI GPT-4o, Google Gemini 1.5 Pro), RAG Pipeline
- Cơ sở dữ liệu: MySQL 8.0 (Charset: utf8mb4, Collation: utf8mb4_unicode_ci)
- Frontend SPA: React 18, Vite, Tailwind CSS, Axios Client, Lucide Icons
- DevOps & CI/CD: Docker, Docker Compose đa container, GitHub Actions tự động kiểm thử

---

## 3. Cấu trúc thư mục Monorepo

```text
learnmate_ai/
├── .github/
│   └── workflows/              # Kịch bản CI/CD tự động kiểm thử trên GitHub Actions
│       ├── backend-ci.yml      # Tự động chạy Pytest cho Backend Core
│       ├── ai-service-ci.yml   # Tự động chạy Pytest cho AI Microservice
│       └── frontend-ci.yml     # Tự động kiểm tra build & lint cho Frontend
├── backend/                    # Dịch vụ nghiệp vụ chính (FastAPI, Port 8080)
│   ├── app/
│   │   ├── api/                # Router định tuyến API phân rã theo chức năng (/api/v1)
│   │   ├── core/               # Cấu hình hệ thống, kết nối DB, bảo mật JWT
│   │   ├── models/             # Khai báo thực thể CSDL SQLAlchemy ORM (21 bảng)
│   │   ├── schemas/            # Lớp DTO Pydantic xác thực dữ liệu vào/ra
│   │   ├── services/           # Tầng nghiệp vụ (Mastery EMA, Socratic, QuotaGuard)
│   │   └── main.py             # Điểm khởi tạo ứng dụng FastAPI, middleware CORS
│   ├── tests/                  # Kịch bản kiểm thử tự động Pytest
│   ├── alembic/                # Quản lý các phiên bản di chuyển lược đồ CSDL
│   ├── alembic.ini             # Tệp cấu hình migration Alembic
│   ├── pytest.ini              # Cấu hình môi trường chạy kiểm thử Pytest
│   ├── requirements.txt        # Danh mục thư viện phụ thuộc Python
│   └── Dockerfile              # Đóng gói container Backend (Python 3.11-slim)
├── ai-service/                 # Dịch vụ trí tuệ nhân tạo phi trạng thái (FastAPI, Port 8000)
│   ├── app/
│   │   ├── core/               # Cấu hình Pydantic Settings, xác thực Header X-API-Key
│   │   ├── routers/            # Các endpoint AI (Hỏi đáp, Gia sư gợi mở, Sinh đề)
│   │   ├── schemas/            # Khai báo cấu trúc JSON trắc nghiệm và Socratic DTO
│   │   ├── adapters/           # Bộ chuyển đổi kết nối OpenAI API & Google Gemini SDK
│   │   ├── prompts/            # Mẫu System Prompts sư phạm chuẩn hóa
│   │   ├── services/           # Xử lý Prompt kết hợp ngữ cảnh học viên và kiểm tra JSON
│   │   └── main.py             # Khởi tạo ứng dụng FastAPI AI Microservice
│   ├── tests/                  # Kịch bản kiểm thử tự động AI Service
│   ├── pytest.ini              # Cấu hình Pytest cho AI Service
│   ├── requirements.txt        # Thư viện phụ thuộc cho AI
│   └── Dockerfile              # Đóng gói container AI Service
├── frontend/                   # Ứng dụng giao diện người dùng SPA (React 18, Port 5173/80)
│   ├── public/                 # Tài nguyên tĩnh
│   ├── src/                    # Mã nguồn giao diện React (Components, Hooks, Routes, Store)
│   ├── index.html              # Trang gốc ứng dụng
│   ├── nginx.conf              # Cấu hình máy chủ web Nginx định tuyến SPA
│   ├── package.json            # Danh mục thư viện phụ thuộc Node.js
│   ├── tailwind.config.js      # Cấu hình màu sắc, kiểu dáng Tailwind CSS
│   ├── vite.config.js          # Cấu hình máy chủ phát triển và đóng gói Vite
│   └── Dockerfile              # Multi-stage build (Node build sang Nginx Alpine)
├── docs/                       # Bộ tài liệu kỹ thuật hoàn chỉnh của dự án
│   ├── LearnMate_AI_SRS.docx   # Tài liệu Đặc tả Yêu cầu Phần mềm (SRS v1.0)
│   ├── LearnMate_AI_Thiet_ke_he_thong(csdl, model).docx # Tài liệu Thiết kế Hệ thống (SDD)
│   └── diagrams/               # Tệp nguồn sơ đồ kiến trúc Draw.io và hình ảnh PNG
├── scripts/                    # Kịch bản tự động hóa hỗ trợ phát triển
│   └── init_db.sql             # Kịch bản khởi tạo database và phân quyền MySQL
├── docker-compose.yml          # Điều phối 4 container độc lập trên mạng learnmate-net
├── .env.example                # Khai báo danh mục biến môi trường mẫu
├── .env                        # Biến môi trường cục bộ (được .gitignore bảo vệ tuyệt đối)
├── .gitignore                  # Khai báo loại trừ các tệp nhạy cảm và thư mục sinh tự động
└── README.md                   # Tài liệu hướng dẫn thiết lập và quy chuẩn phát triển
```

---

## 4. Hướng dẫn cài đặt và Khởi chạy hệ thống

### 4.1. Chuẩn bị môi trường

- Hệ điều hành: Windows, macOS hoặc Linux
- Git: Phiên bản 2.30 trở lên
- Python: Phiên bản 3.11 trở lên
- Node.js: Phiên bản 18 LTS trở lên cùng npm
- Docker Desktop: Bật sẵn Docker Engine

### 4.2. Khởi chạy bằng Docker Compose (Khuyến nghị)

1. Tải mã nguồn dự án về máy (Clone):

   ```bash
   # Lựa chọn 1: Sử dụng SSH (Khuyến nghị nếu đã cấu hình SSH Key)
   git clone git@github.com:ITTT-Nhom-9/learnmate_ai.git

   # Lựa chọn 2: Sử dụng HTTPS
   git clone https://github.com/ITTT-Nhom-9/learnmate_ai.git

   # Di chuyển vào thư mục dự án
   cd learnmate_ai
   ```

2. Tạo tệp cấu hình môi trường từ tệp mẫu (nếu chưa có):
   ```bash
   copy .env.example .env    # Trên Windows PowerShell / CMD
   # hoặc: cp .env.example .env  # Trên Linux / macOS
   ```
3. Khởi động đồng thời 4 container dịch vụ:
   ```bash
   docker compose up -d --build
   ```
4. Kiểm tra trạng thái hoạt động của các container:
   ```bash
   docker compose ps
   ```
5. Địa chỉ truy cập các dịch vụ:
   - Giao diện người dùng (Frontend): http://localhost:5173 (hoặc http://localhost:80)
   - Máy chủ nghiệp vụ (Backend API Docs): http://localhost:8080/api/v1/docs
   - Kiểm tra sức khỏe Backend: http://localhost:8080/api/v1/health
   - Dịch vụ trí tuệ nhân tạo (AI Health): http://localhost:8000/ai/health
   - Cơ sở dữ liệu MySQL: Cổng kết nối ngoài `3307` (tránh xung đột với MySQL cài sẵn cổng 3306)

### 4.3. Chạy từng dịch vụ trực tiếp (Local Development)

- **Backend Core**:
  ```bash
  cd backend
  pip install -r requirements.txt
  uvicorn app.main:app --reload --port 8080
  ```
- **AI Microservice**:
  ```bash
  cd ai-service
  pip install -r requirements.txt
  uvicorn app.main:app --reload --port 8000
  ```
- **Frontend SPA**:
  ```bash
  cd frontend
  npm install
  npm run dev
  ```

---

## 5. Quy chuẩn làm việc trên Git và Hướng dẫn Push Code

Tất cả thành viên trong nhóm thực hiện nghiêm ngặt quy trình dưới đây để đảm bảo an toàn mã nguồn và đồng bộ tiến độ.

### 5.1. Nguyên tắc cốt lõi

1. **Tuyệt đối không commit hoặc push trực tiếp lên nhánh `main`**. Nhánh `main` là nhánh sản phẩm chính thức, được bảo vệ nghiêm ngặt (Protected Branch).
2. Mọi công việc (tính năng mới, sửa lỗi, cập nhật tài liệu) đều phải tạo nhánh riêng (feature branch) theo đúng mã task trong bảng kế hoạch.
3. Mọi thay đổi đưa vào nhánh `main` đều phải thông qua Pull Request (PR) trên GitHub và được Nhóm trưởng (Trần Văn Khiêm) xem xét, phê duyệt.
4. Tuyệt đối không commit các tệp chứa thông tin nhạy cảm (.env, khóa API cá nhân, mật khẩu) hoặc các thư mục mã sinh tự động (.venv, node_modules, **pycache**).

### 5.2. Quy ước đặt tên nhánh (Branch Naming)

Tên nhánh bắt buộc phải chứa tiền tố phân loại và mã task:

- Tính năng mới: `feature/<mã-task>-<tên-ngắn-gọn>`
  - Ví dụ: `feature/TK-01-setup-monorepo-docker`
  - Ví dụ: `feature/TK-02-setup-database-models`
  - Ví dụ: `feature/TK-05-auth-api`
  - Ví dụ: `feature/TK-24-rag-pipeline`
- Sửa lỗi phần mềm: `fix/<mã-task>-<mô-tả-lỗi>`
  - Ví dụ: `fix/TK-02-fix-mysql-connection`
- Tài liệu kỹ thuật: `docs/<mã-task>-<nội-dung>`
  - Ví dụ: `docs/TK-01-update-system-spec`

### 5.3. Quy ước thông điệp Commit (Conventional Commits)

Cấu trúc thông điệp commit:

```text
<loại>(<mã-task>): <mô tả ngắn gọn nội dung thay đổi>
```

Các từ khóa phân loại hợp lệ:

- `feat`: Thêm tính năng mới.
- `fix`: Sửa lỗi phần mềm hoặc cấu hình.
- `docs`: Cập nhật tài liệu kỹ thuật, README.
- `style`: Định dạng code, không ảnh hưởng logic vận hành.
- `refactor`: Tái cấu trúc mã nguồn mà không thay đổi hành vi nghiệp vụ.
- `test`: Thêm mới hoặc chỉnh sửa kịch bản kiểm thử (Pytest, Unit test).
- `chore`: Thay đổi cấu hình build, cập nhật gói phụ thuộc, kịch bản CI/CD.

Ví dụ thông điệp commit chuẩn:

- `feat(TK-01): thiet lap cau truc monorepo va docker-compose 4 container`
- `feat(TK-02): khoi tao 7 bang csdl va script migration alembic`
- `fix(TK-01): dieu chinh cong mysql host sang 3307 tranh xung dot`
- `test(TK-01): bo sung unit test kiem tra endpoint health cho backend va ai service`

---

### 5.4. Quy trình Git Workflow & Push Code chi tiết

Quy trình làm việc được phân rã thành 2 giai đoạn rõ ràng:

#### Giai đoạn A: Khởi tạo mã nguồn (Dành cho thành viên mới bắt đầu dự án)

Nếu thành viên chưa có thư mục dự án trên máy tính, thực hiện thao tác clone một lần duy nhất:

```bash
# 1. Tải toàn bộ mã nguồn dự án từ GitHub về máy
# Cách 1 (Khuyến nghị dùng SSH):
git clone git@github.com:ITTT-Nhom-9/learnmate_ai.git

# Hoặc Cách 2 (Dùng HTTPS):
# git clone https://github.com/ITTT-Nhom-9/learnmate_ai.git

# 2. Di chuyển vào thư mục dự án
cd learnmate_ai
```

---

#### Giai đoạn B: Các bước thực hiện Task và Push Code lên GitHub

Sau khi đã ở trong thư mục `learnmate_ai`, mỗi thành viên thao tác theo đúng 6 bước chuẩn sau:

##### Bước 1: Cập nhật nhánh main mới nhất từ GitHub

Trước khi bắt đầu thực hiện task mới hoặc trước khi push, luôn đảm bảo nhánh `main` ở trạng thái mới nhất:

```bash
git checkout main
git pull origin main
```

##### Bước 2: Tạo và chuyển sang nhánh làm việc của task

Thay thế mã task và tên ngắn gọn tương ứng với công việc được phân công:

```bash
git checkout -b feature/TK-01-setup-monorepo-docker
```

Kiểm tra lại xem đã đứng đúng nhánh mới chưa:

```bash
git branch
```

_(Dấu sao `_` sẽ nằm trước tên nhánh bạn vừa tạo).\*

##### Bước 3: Kiểm tra trạng thái các tệp đã chỉnh sửa

Sau khi hoàn thành phần việc mã hóa hoặc sửa đổi tài liệu:

```bash
git status
```

Lệnh này hiển thị danh sách các tệp đã thay đổi hoặc tệp mới chưa theo dõi.

##### Bước 4: Đưa các tệp thay đổi vào vùng chuẩn bị commit (Staging Area)

- Thêm toàn bộ các thay đổi hợp lệ trong dự án:
  ```bash
  git add .
  ```
- Hoặc chỉ thêm các thư mục, tệp cụ thể của task:
  ```bash
  git add backend/
  git add docker-compose.yml
  ```
  Kiểm tra lại bằng `git status` (các tệp sẵn sàng commit sẽ hiển thị màu xanh lá cây).

##### Bước 5: Tạo commit theo đúng quy ước kỹ thuật

```bash
git commit -m "feat(TK-01): thiet lap cau truc monorepo va docker-compose 4 container"
```

##### Bước 6: Đẩy nhánh lên GitHub (Git Push)

- Với lần push đầu tiên của một nhánh mới, sử dụng cờ `-u` (hoặc `--set-upstream`):
  ```bash
  git push -u origin feature/TK-01-setup-monorepo-docker
  ```
- Từ các lần push tiếp theo trên cùng nhánh này, chỉ cần thực hiện:
  ```bash
  git push
  ```

---

### 5.5. Quy trình tạo Pull Request (PR) và Phê duyệt mã nguồn

Sau khi đã push nhánh thành công lên GitHub:

1. Mở trình duyệt và truy cập vào repository của dự án: https://github.com/ITTT-Nhom-9/learnmate_ai
2. GitHub sẽ tự động hiển thị thông báo màu vàng:
   `feature/<tên-nhánh> had recent pushes less than a minute ago` -> Nhấn nút **Compare & pull request**.
3. Điền tiêu đề và nội dung mô tả cho PR theo mẫu:
   - **Tiêu đề (Title)**: `[TK-01] Thiết lập cấu trúc Monorepo và Docker Compose 4 dịch vụ`
   - **Nội dung (Description)**:

     ```markdown
     ## Nội dung công việc thực hiện

     - Thiết lập cấu trúc thư mục Monorepo cho 4 dịch vụ: Backend, AI Service, Frontend, Database
     - Viết docker-compose.yml điều phối 4 container trên mạng bridge learnmate-net
     - Tạo tệp cấu hình mẫu .env.example và .gitignore chuẩn
     - Bổ sung kịch bản kiểm thử health check cho Backend Core và AI Microservice

     ## Kết quả kiểm thử

     - [ ] docker compose config: Hợp lệ 100%
     - [ ] Pytest Backend: 2/2 tests passed
     - [ ] Pytest AI Service: 2/2 tests passed

     ## Thành viên thực hiện

     - Phụ trách: Tăng Mạnh Khang (1627)
     - Người duyệt (Reviewer): Trần Văn Khiêm (N25DTCN129 - Nhóm trưởng)
     ```

4. Mục **Reviewers**: Chọn `Trần Văn Khiêm` (Nhóm trưởng).
5. Nhấn nút **Create pull request**.
6. Đợi hệ thống GitHub Actions CI chạy hoàn tất (toàn bộ các mục kiểm tra chuyển sang trạng thái xanh).
7. Nhóm trưởng tiến hành kiểm tra mã nguồn, yêu cầu chỉnh sửa nếu cần, sau đó thực hiện **Squash and merge** vào nhánh `main` và xóa nhánh tính năng trên remote.

---

### 5.6. Hướng dẫn xử lý một số tình huống thường gặp

#### Tình huống 1: Nhánh main trên remote có cập nhật mới trong khi bạn đang làm việc

Trước khi push nhánh của bạn lên, cần đồng bộ nhánh `main` mới vào nhánh hiện tại để tránh xung đột:

```bash
git fetch origin
git rebase origin/main
```

Nếu có xung đột (conflict):

1. Mở các tệp báo conflict, chỉnh sửa lại mã nguồn về trạng thái mong muốn.
2. Đánh dấu tệp đã giải quyết xong:
   ```bash
   git add <tên-tệp-đã-sửa>
   ```
3. Tiếp tục tiến trình rebase:
   ```bash
   git rebase --continue
   ```
4. Đẩy lại lên GitHub:
   ```bash
   git push --force-with-lease origin feature/<mã-task>-<tên-task>
   ```

#### Tình huống 2: Lỡ commit nhầm tệp nhưng chưa thực hiện lệnh push

Hủy commit gần nhất nhưng vẫn giữ nguyên toàn bộ thay đổi của tệp trong thư mục:

```bash
git reset HEAD~1
```

Loại bỏ tệp không mong muốn ra khỏi vùng theo dõi của Git:

```bash
git rm --cached <tên-tệp-nhầm>
```

#### Tình huống 3: Xem lại lịch sử các commit trên nhánh hiện tại

```bash
git log --oneline -n 5
```

---

## 6. Liên hệ và Kênh quản trị dự án

Mọi thắc mắc về phân công nhiệm vụ, kiến trúc kỹ thuật hoặc quy trình phối hợp, các thành viên trao đổi qua kênh làm việc chung hoặc tạo Issue tại:

- Nhóm trưởng / Quản lý dự án: Trần Văn Khiêm (Mã sinh viên: N25DTCN129)
- Kiến trúc sư hệ thống: Tăng Mạnh Khang (Mã sinh viên: 1627)
- Kênh quản trị mã nguồn: https://github.com/ITTT-Nhom-9/learnmate_ai/issues
