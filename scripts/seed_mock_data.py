#!/usr/bin/env python3
"""
Dự án: LearnMate AI - Hệ thống Gia sư Hỏi đáp Socratic & Học tập Thích ứng
Tệp: learnmate_ai/scripts/seed_mock_data.py
Mã Task: TK-03 | Phân hệ 2: Dữ liệu mẫu (Tầng Nghiệp vụ BA)
Database mục tiêu: learnmate
Mô tả: Tạo schema theo ORM backend, nạp 2 môn học, 8 bài học, 16 chủ đề,
       16 nội dung và in báo cáo kiểm thử.
"""

import argparse
import logging
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from sqlalchemy import create_engine, func, select
from sqlalchemy.engine import Engine, URL
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker

ROOT_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = ROOT_DIR / "backend"
sys.path.insert(0, str(BACKEND_DIR))
load_dotenv(ROOT_DIR / ".env")

from app.models import Base, Course, Lesson, LessonContent, Topic

# ==============================================================================
# CẤU HÌNH LOGGING
# ==============================================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger("seed_mock_data")


# ==============================================================================
# 2. CẤU HÌNH VÀ KHỞI TẠO KẾT NỐI MYSQL
# ==============================================================================

TARGET_DB_NAME = os.getenv("DB_NAME", "learnmate")
DB_USER = os.getenv("DB_USER", "learnmate_user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "learnmate_pass")
DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = int(os.getenv("MYSQL_HOST_PORT", "3307"))
DB_ROOT_USER = os.getenv("DB_ROOT_USER", "root")
DB_ROOT_PASSWORD = os.getenv("DB_ROOT_PASSWORD")


def get_mysql_connection_params(args: argparse.Namespace | None = None) -> dict[str, Any]:
    """Lấy cấu hình MySQL từ môi trường, có thể ghi đè bằng tham số CLI."""
    return {
        "user": getattr(args, "user", DB_USER),
        "password": getattr(args, "password", DB_PASSWORD),
        "host": getattr(args, "host", DB_HOST),
        "port": getattr(args, "port", DB_PORT),
        "database": getattr(args, "database", TARGET_DB_NAME),
        "root_user": getattr(args, "root_user", DB_ROOT_USER),
        "root_password": getattr(args, "root_password", DB_ROOT_PASSWORD),
    }


def create_database_if_not_exists(params: dict[str, Any]) -> None:
    """Tạo database mục tiêu bằng tài khoản quản trị MySQL nếu cần."""
    database_name = params["database"]
    if not re.fullmatch(r"[A-Za-z0-9_]+", database_name):
        raise ValueError("Tên database chỉ được chứa chữ, số và dấu gạch dưới.")

    if not params["root_password"]:
        return

    server_url = URL.create(
        drivername="mysql+pymysql",
        username=params["root_user"],
        password=params["root_password"],
        host=params["host"],
        port=params["port"],
        query={"charset": "utf8mb4"},
    )
    server_engine = create_engine(
        server_url,
        pool_pre_ping=True,
        connect_args={"connect_timeout": 10},
    )
    try:
        with server_engine.begin() as conn:
            conn.exec_driver_sql(
                f"CREATE DATABASE IF NOT EXISTS `{database_name}` "
                "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
    finally:
        server_engine.dispose()

    logger.info("PASS: Database `%s` đã sẵn sàng.", database_name)


def create_database_url(params: dict[str, Any]) -> URL:
    """Tạo URL SQLAlchemy cho database được chọn."""
    return URL.create(
        drivername="mysql+pymysql",
        username=params["user"],
        password=params["password"],
        host=params["host"],
        port=params["port"],
        database=params["database"],
        query={"charset": "utf8mb4"},
    )

# ==============================================================================
# 3. BỘ DỮ LIỆU MẪU CHUẨN NGHIỆP VỤ BA (2 MÔN HỌC, 8 BÀI HỌC, 16 CHỦ ĐỀ)
# ==============================================================================
COURSES_DATA: list[dict[str, Any]] = [
    {
        "id": 1,
        "code": "IT201",
        "title": "Cơ sở dữ liệu",
        "description": (
            "Học phần cung cấp kiến thức nền tảng về Hệ quản trị cơ sở dữ liệu (DBMS), "
            "thiết kế lược đồ Thực thể - Kết hợp (ERD), Đại số quan hệ, ngôn ngữ truy vấn "
            "SQL và các dạng chuẩn hóa dữ liệu."
        ),
        "is_active": 1,
    },
    {
        "id": 2,
        "code": "IT202",
        "title": "Cấu trúc dữ liệu và giải thuật",
        "description": (
            "Học phần trang bị tư duy tổ chức dữ liệu trong bộ nhớ, đánh giá độ phức tạp "
            "thuật toán qua ký pháp Big-O, cài đặt Danh sách liên kết, Ngăn xếp, Hàng đợi "
            "và Cây tìm kiếm nhị phân."
        ),
        "is_active": 1,
    },
]

LESSONS_DATA: list[dict[str, Any]] = [
    # --- Môn 1: Cơ sở dữ liệu (course_id = 1) ---
    {
        "id": 1,
        "course_id": 1,
        "title": "Bài 1: Tổng quan về Hệ Cơ sở dữ liệu",
        "description": "Khái niệm CSDL, Hệ quản trị CSDL (DBMS) và kiến trúc 3 lược đồ ANSI-SPARC.",
        "order_index": 1,
    },
    {
        "id": 2,
        "course_id": 1,
        "title": "Bài 2: Mô hình Thực thể - Mối kết hợp (ERD)",
        "description": "Phương pháp phân tích và thiết kế CSDL ở mức khái niệm bằng sơ đồ ER.",
        "order_index": 2,
    },
    {
        "id": 3,
        "course_id": 1,
        "title": "Bài 3: Mô hình Dữ liệu Quan hệ & Đại số Quan hệ",
        "description": "Biểu diễn dữ liệu dạng bảng, ràng buộc toàn vẹn và các phép toán đại số quan hệ.",
        "order_index": 3,
    },
    {
        "id": 4,
        "course_id": 1,
        "title": "Bài 4: Ngôn ngữ Truy vấn Có cấu trúc (SQL)",
        "description": "Sử dụng nhóm lệnh DDL, DML và truy vấn kết nối nhiều bảng trong MySQL 8.0.",
        "order_index": 4,
    },
    # --- Môn 2: Cấu trúc dữ liệu và giải thuật (course_id = 2) ---
    {
        "id": 5,
        "course_id": 2,
        "title": "Bài 1: Độ phức tạp Thuật toán & Kiểu dữ liệu Trừu tượng",
        "description": "Phân tích thời gian thực thi, không gian bộ nhớ và ký pháp tiệm cận Big-O.",
        "order_index": 1,
    },
    {
        "id": 6,
        "course_id": 2,
        "title": "Bài 2: Danh sách Liên kết (Linked List)",
        "description": "Cấu trúc cấp phát động, thao tác con trỏ trên danh sách liên kết đơn và đôi.",
        "order_index": 2,
    },
    {
        "id": 7,
        "course_id": 2,
        "title": "Bài 3: Ngăn xếp (Stack) và Hàng đợi (Queue)",
        "description": "Nguyên lý hoạt động LIFO, FIFO và ứng dụng trong trình biên dịch, lập lịch CPU.",
        "order_index": 3,
    },
    {
        "id": 8,
        "course_id": 2,
        "title": "Bài 4: Cấu trúc Cây và Cây Tìm kiếm Nhị phân (BST)",
        "description": "Tổ chức dữ liệu phân cấp, các phép duyệt cây đệ quy và thao tác trên cây BST.",
        "order_index": 4,
    },
]

TOPICS_DATA: list[dict[str, Any]] = [
    # Bài 1 - CSDL
    {
        "id": 1,
        "lesson_id": 1,
        "title": "Hệ quản trị CSDL (DBMS) và Hệ thống Tập tin truyền thống",
        "slug": "dbms-va-he-thong-tap-tin",
        "order_index": 1,
    },
    {
        "id": 2,
        "lesson_id": 1,
        "title": "Kiến trúc 3 lược đồ ANSI-SPARC và Tính độc lập dữ liệu",
        "slug": "kien-truc-3-luoc-do-ansi-sparc",
        "order_index": 2,
    },
    # Bài 2 - CSDL
    {
        "id": 3,
        "lesson_id": 2,
        "title": "Thực thể, Thuộc tính và Các loại Khóa định danh",
        "slug": "thuc-the-thuoc-tinh-va-khoa",
        "order_index": 1,
    },
    {
        "id": 4,
        "lesson_id": 2,
        "title": "Mối kết hợp (Relationship) và Bản số (Cardinality)",
        "slug": "moi-ket-hop-va-ban-so",
        "order_index": 2,
    },
    # Bài 3 - CSDL
    {
        "id": 5,
        "lesson_id": 3,
        "title": "Lược đồ Quan hệ và Ràng buộc Toàn vẹn (Integrity Constraints)",
        "slug": "luoc-do-quan-he-va-rang-buoc",
        "order_index": 1,
    },
    {
        "id": 6,
        "lesson_id": 3,
        "title": "Các phép toán Đại số Quan hệ cốt lõi",
        "slug": "cac-phep-toan-dai-so-quan-he",
        "order_index": 2,
    },
    # Bài 4 - CSDL
    {
        "id": 7,
        "lesson_id": 4,
        "title": "Ngôn ngữ Định nghĩa Dữ liệu (DDL) và Ràng buộc Bảng",
        "slug": "ngon-ngu-dinh-nghia-du-lieu-ddl",
        "order_index": 1,
    },
    {
        "id": 8,
        "lesson_id": 4,
        "title": "Ngôn ngữ Thao tác Dữ liệu (DML) và Truy vấn JOIN, GROUP BY",
        "slug": "ngon-ngu-thao-tac-du-lieu-dml",
        "order_index": 2,
    },
    # Bài 5 - CTDL&GT
    {
        "id": 9,
        "lesson_id": 5,
        "title": "Kiểu dữ liệu Trừu tượng (ADT) và Mô hình Bộ nhớ",
        "slug": "kieu-du-lieu-truu-tuong-adt",
        "order_index": 1,
    },
    {
        "id": 10,
        "lesson_id": 5,
        "title": "Đánh giá Độ phức tạp Thuật toán với Ký pháp Big-O",
        "slug": "danh-gia-do-phuc-tap-big-o",
        "order_index": 2,
    },
    # Bài 6 - CTDL&GT
    {
        "id": 11,
        "lesson_id": 6,
        "title": "Danh sách Liên kết Đơn (Singly Linked List)",
        "slug": "danh-sach-lien-ket-don",
        "order_index": 1,
    },
    {
        "id": 12,
        "lesson_id": 6,
        "title": "Danh sách Liên kết Đôi (Doubly Linked List)",
        "slug": "danh-sach-lien-ket-doi",
        "order_index": 2,
    },
    # Bài 7 - CTDL&GT
    {
        "id": 13,
        "lesson_id": 7,
        "title": "Ngăn xếp (Stack) và Nguyên lý LIFO",
        "slug": "ngan-xep-stack-va-lifo",
        "order_index": 1,
    },
    {
        "id": 14,
        "lesson_id": 7,
        "title": "Hàng đợi (Queue) và Nguyên lý FIFO",
        "slug": "hang-doi-queue-va-fifo",
        "order_index": 2,
    },
    # Bài 8 - CTDL&GT
    {
        "id": 15,
        "lesson_id": 8,
        "title": "Cây Nhị phân và 3 Phương pháp Duyệt Cây (Pre/In/Post-order)",
        "slug": "cay-nhi-phan-va-duyet-cay",
        "order_index": 1,
    },
    {
        "id": 16,
        "lesson_id": 8,
        "title": "Cây Tìm kiếm Nhị phân (Binary Search Tree - BST)",
        "slug": "cay-tim-kiem-nhi-phan-bst",
        "order_index": 2,
    },
]

LESSON_CONTENTS_DATA: list[dict[str, Any]] = [
    {
        "id": 1,
        "topic_id": 1,
        "content_type": "markdown",
        "summary": "So sánh DBMS với hệ thống quản lý file truyền thống và 4 tính chất giao dịch ACID.",
        "content_markdown": (
            "### 1. Khái niệm Cơ sở dữ liệu và DBMS\n"
            "**Cơ sở dữ liệu (CSDL)** là một tập hợp dữ liệu có cấu trúc, liên quan chặt chẽ với nhau. "
            "**Hệ quản trị CSDL (DBMS)** (như MySQL, PostgreSQL) là phần mềm giúp khởi tạo, truy vấn và bảo mật CSDL.\n\n"
            "### 2. Tính chất Giao dịch ACID\n"
            "Mọi giao dịch (Transaction) trong DBMS chuẩn đều đảm bảo 4 tính chất $ACID$:\n"
            "* **Atomicity (Tính nguyên tố):** Thực hiện toàn bộ ($100\\%$) hoặc không thực hiện gì cả ($0\\%$). \n"
            "* **Consistency (Tính nhất quán):** Bảo toàn mọi ràng buộc toàn vẹn dữ liệu.\n"
            "* **Isolation (Tính cô lập):** Các giao dịch đồng thời không làm sai lệch kết quả của nhau.\n"
            "* **Durability (Tính bền vững):** Dữ liệu sau khi `COMMIT` được lưu trữ bền vững."
        ),
    },
    {
        "id": 2,
        "topic_id": 2,
        "content_type": "markdown",
        "summary": "Ba mức trừu tượng dữ liệu ANSI-SPARC và tính độc lập dữ liệu vật lý/logic.",
        "content_markdown": (
            "### 1. Kiến trúc 3 lược đồ ANSI-SPARC\n"
            "Hệ thống CSDL chuẩn được chia thành $3$ tầng trừu tượng:\n"
            "1. **Mức trong (Physical Level):** Mô tả cách lưu trữ vật lý trên đĩa (B-Tree index, byte).\n"
            "2. **Mức khái niệm (Conceptual Level):** Mô tả cấu trúc logic toàn bộ CSDL (bảng, khóa).\n"
            "3. **Mức ngoài (External/View Level):** Các khung nhìn (`VIEW`) cho từng nhóm người dùng.\n\n"
            "### 2. Tính Độc lập Dữ liệu\n"
            "* **Độc lập mức vật lý:** Thay đổi cấu trúc lưu trữ vật lý không làm ảnh hưởng lược đồ khái niệm.\n"
            "* **Độc lập mức logic:** Thay đổi cấu trúc bảng ở mức khái niệm không làm hỏng các `VIEW` của ứng dụng."
        ),
    },
    {
        "id": 3,
        "topic_id": 3,
        "content_type": "markdown",
        "summary": "Phân loại thuộc tính trên ERD và cách xác định Siêu khóa, Khóa dự tuyển, Khóa chính.",
        "content_markdown": (
            "### 1. Thực thể và Thuộc tính\n"
            "* **Tập thực thể (Entity Set):** Nhóm các đối tượng cùng đặc trưng (VD: `SinhVien`, `MonHoc`).\n"
            "* **Các loại thuộc tính:** Đơn (Simple), Phức hợp (Composite), Đa trị (Multi-valued) và Suy diễn (Derived).\n\n"
            "### 2. Hệ thống Khóa định danh\n"
            "Trên tập thực thể $E$:\n"
            "* **Siêu khóa (Super Key - $SK$):** Tập thuộc tính phân biệt duy nhất hai thực thể: "
            "$\\forall e_1, e_2 \\in E, e_1 \\neq e_2 \\Rightarrow e_1[SK] \\neq e_2[SK]$.\n"
            "* **Khóa dự tuyển (Candidate Key - $CK$):** Siêu khóa tối tiểu (không chứa tập con thực sự nào là siêu khóa).\n"
            "* **Khóa chính (Primary Key - $PK$):** Khóa dự tuyển được chọn làm định danh chính thức."
        ),
    },
    {
        "id": 4,
        "topic_id": 4,
        "content_type": "markdown",
        "summary": "Bản số liên kết (1:1, 1:N, M:N) và quy tắc ánh xạ sang lược đồ cơ sở dữ liệu quan hệ.",
        "content_markdown": (
            "### 1. Bản số của Mối kết hợp (Cardinality)\n"
            "* **Quan hệ $1:1$:** Một thực thể nhóm A liên kết tối đa với một thực thể nhóm B.\n"
            "* **Quan hệ $1:N$:** Một Khoa quản lý nhiều Sinh viên ($N \\ge 0$).\n"
            "* **Quan hệ $M:N$:** Một Sinh viên đăng ký nhiều Môn học và ngược lại.\n\n"
            "### 2. Quy tắc chuyển đổi sang Bảng Quan hệ\n"
            "* Quan hệ **$1:N$**: Đưa khóa chính phía $1$ sang làm **Khóa ngoại (`FOREIGN KEY`)** ở bảng phía $N$.\n"
            "* Quan hệ **$M:N$**: Tách thành **bảng trung gian thứ 3** (như bảng `enrollments`) chứa cặp khóa ngoại."
        ),
    },
    {
        "id": 5,
        "topic_id": 5,
        "content_type": "markdown",
        "summary": "Định nghĩa toán học của Quan hệ và 3 ràng buộc toàn vẹn: Miền giá trị, Thực thể, Tham chiếu.",
        "content_markdown": (
            "### 1. Định nghĩa Toán học của Quan hệ\n"
            "Một quan hệ $R$ trên các miền giá trị $D_1, D_2, \\dots, D_n$ là một tập con của tích Đề-các:\n"
            "$$R \\subseteq D_1 \\times D_2 \\times \\dots \\times D_n$$\n\n"
            "### 2. Ba Ràng buộc Toàn vẹn Cốt lõi\n"
            "1. **Toàn vẹn Miền giá trị (Domain Integrity):** Mỗi ô chứa giá trị nguyên tố (Atomic - chuẩn $1NF$).\n"
            "2. **Toàn vẹn Thực thể (Entity Integrity):** Khóa chính không bao giờ nhận giá trị rỗng (`PK IS NOT NULL`).\n"
            "3. **Toàn vẹn Tham chiếu (Referential Integrity):** Khóa ngoại ($FK$) phải tham chiếu đến $PK$ hợp lệ hoặc bằng `NULL`."
        ),
    },
    {
        "id": 6,
        "topic_id": 6,
        "content_type": "markdown",
        "summary": "Công thức biểu thức của phép Chọn, Chiếu, Tích Đề-các và Kết nối trong Đại số quan hệ.",
        "content_markdown": (
            "### 1. Phép Chọn và Phép Chiếu\n"
            "* **Phép Chọn (Selection - $\\sigma$):** Lọc các bộ (dòng) thỏa điều kiện $F$:\n"
            "  $$\\sigma_{F}(R) = \\{ t \\in R \\mid F(t) = \\text{true} \\}$$\n"
            "* **Phép Chiếu (Projection - $\\pi$):** Trích xuất tập cột $A_1, \\dots, A_k$ và loại bỏ dòng trùng:\n"
            "  $$\\pi_{A_1, A_2, \\dots, A_k}(R)$$\n\n"
            "### 2. Phép Kết nối (Join - $\\bowtie$)\n"
            "Kết hợp hai quan hệ $R$ và $S$ theo điều kiện $\\theta$:\n"
            "$$R \\bowtie_{\\theta} S = \\sigma_{\\theta}(R \\times S)$$"
        ),
    },
    {
        "id": 7,
        "topic_id": 7,
        "content_type": "markdown",
        "summary": "Cú pháp SQL DDL chuẩn khởi tạo bảng, khóa chính và khóa ngoại trong MySQL 8.0.",
        "content_markdown": (
            "### 1. Nhóm lệnh DDL (Data Definition Language)\n"
            "Bao gồm các câu lệnh định nghĩa cấu trúc CSDL: `CREATE`, `ALTER`, `DROP`, `TRUNCATE`.\n\n"
            "### 2. Ví dụ Tạo Bảng với Ràng buộc Khóa ngoại\n"
            "```sql\n"
            "CREATE TABLE courses (\n"
            "    id INT AUTO_INCREMENT PRIMARY KEY,\n"
            "    code VARCHAR(20) NOT NULL UNIQUE,\n"
            "    title VARCHAR(255) NOT NULL\n"
            ") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;\n"
            "```"
        ),
    },
    {
        "id": 8,
        "topic_id": 8,
        "content_type": "markdown",
        "summary": "Thứ tự thực thi câu lệnh SELECT và kỹ thuật truy vấn kết nối JOIN kèm GROUP BY.",
        "content_markdown": (
            "### 1. Thứ tự Thực thi Logic của Câu lệnh SELECT\n"
            "`FROM` $\\rightarrow$ `JOIN` $\\rightarrow$ `WHERE` $\\rightarrow$ `GROUP BY` "
            "$\\rightarrow$ `HAVING` $\\rightarrow$ `SELECT` $\\rightarrow$ `ORDER BY` $\\rightarrow$ `LIMIT`.\n\n"
            "### 2. Ví dụ Truy vấn Thống kê với LEFT JOIN\n"
            "```sql\n"
            "SELECT c.code, c.title, COUNT(l.id) AS total_lessons\n"
            "FROM courses c\n"
            "LEFT JOIN lessons l ON c.id = l.course_id\n"
            "GROUP BY c.id, c.code, c.title\n"
            "HAVING COUNT(l.id) >= 4;\n"
            "```"
        ),
    },
    {
        "id": 9,
        "topic_id": 9,
        "content_type": "markdown",
        "summary": "Khái niệm Kiểu dữ liệu trừu tượng (ADT) và so sánh cấp phát tĩnh với cấp phát động.",
        "content_markdown": (
            "### 1. Kiểu Dữ liệu Trừu tượng (ADT)\n"
            "**ADT (Abstract Data Type)** xác định bản chất toán học của kiểu dữ liệu và các phép toán "
            "mà không phụ thuộc vào ngôn ngữ cài đặt cụ thể.\n\n"
            "### 2. Cấp phát Mảng Tĩnh vs Cấp phát Động\n"
            "* **Mảng tĩnh (Array):** Các phần tử nằm liên tiếp trong RAM, truy cập ngẫu nhiên chỉ mất $O(1)$:\n"
            "  $$\\text{Address}(A[i]) = \\text{Base\\_Address} + i \\times \\text{sizeof(Element)}$$\n"
            "* **Cấp phát động (Heap):** Xin vùng nhớ linh hoạt lúc chạy chương trình thông qua con trỏ."
        ),
    },
    {
        "id": 10,
        "topic_id": 10,
        "content_type": "markdown",
        "summary": "Định nghĩa toán học của ký pháp Big-O và phân cấp độ phức tạp thời gian thực thi.",
        "content_markdown": (
            "### 1. Định nghĩa Toán học Ký pháp Big-O\n"
            "Hàm thời gian $T(n)$ thuộc $O(g(n))$ nếu tồn tại hằng số $c > 0$ và $n_0 \\ge 1$ sao cho:\n"
            "$$0 \\le T(n) \\le c \\cdot g(n), \\quad \\forall n \\ge n_0$$\n\n"
            "### 2. Phân cấp Độ phức tạp Phổ biến\n"
            "$$O(1) < O(\\log_2 n) < O(n) < O(n \\log_2 n) < O(n^2) < O(2^n)$$\n\n"
            "```c\n"
            "// Vòng lặp lồng nhau có độ phức tạp O(n log n)\n"
            "for (int i = 1; i <= n; i++) {\n"
            "    for (int j = 1; j <= n; j *= 2) {\n"
            "        sum += i + j;\n"
            "    }\n"
            "}\n"
            "```"
        ),
    },
    {
        "id": 11,
        "topic_id": 11,
        "content_type": "markdown",
        "summary": "Cấu trúc Node của Danh sách liên kết đơn và đánh giá độ phức tạp chèn/xóa phần tử.",
        "content_markdown": (
            "### 1. Cấu trúc Node trong Danh sách Liên kết Đơn\n"
            "Mỗi `Node` lưu giá trị `data` và một con trỏ `next` trỏ tới phần tử kế tiếp.\n"
            "```c\n"
            "typedef struct Node {\n"
            "    int data;\n"
            "    struct Node* next;\n"
            "} Node;\n"
            "```\n\n"
            "### 2. Độ phức tạp Thao tác\n"
            "* Thêm/Xóa tại đầu danh sách (`head`): $O(1)$.\n"
            "* Tìm kiếm hoặc truy cập phần tử thứ $k$: $O(n)$."
        ),
    },
    {
        "id": 12,
        "topic_id": 12,
        "content_type": "markdown",
        "summary": "Cấu trúc Node hai con trỏ (prev, next) và ưu thế xóa Node bất kỳ trong thời gian O(1).",
        "content_markdown": (
            "### 1. Cấu trúc Danh sách Liên kết Đôi\n"
            "Mỗi `Node` có hai con trỏ `prev` và `next` giúp duyệt danh sách theo cả hai chiều.\n"
            "```c\n"
            "typedef struct DNode {\n"
            "    int data;\n"
            "    struct DNode* prev;\n"
            "    struct DNode* next;\n"
            "} DNode;\n"
            "```\n\n"
            "### 2. Xóa Node $p$ Đã Biết Địa chỉ trong $O(1)$\n"
            "```c\n"
            "if (p->prev != NULL) p->prev->next = p->next;\n"
            "if (p->next != NULL) p->next->prev = p->prev;\n"
            "free(p);\n"
            "```"
        ),
    },
    {
        "id": 13,
        "topic_id": 13,
        "content_type": "markdown",
        "summary": "Nguyên lý LIFO (Vào sau - Ra trước) của Ngăn xếp (Stack) và ứng dụng Call Stack.",
        "content_markdown": (
            "### 1. Nguyên lý Hoạt động LIFO (Last In, First Out)\n"
            "**Stack** chỉ cho phép thêm (`push`) và lấy phần tử (`pop`) tại một đầu duy nhất gọi là đỉnh (`top`).\n"
            "* `push(x)`: Thêm phần tử vào đỉnh — Độ phức tạp $O(1)$.\n"
            "* `pop()`: Lấy phần tử khỏi đỉnh — Độ phức tạp $O(1)$.\n\n"
            "### 2. Ứng dụng Thực tế\n"
            "* Quản lý địa chỉ trả về của hàm đệ quy (**Call Stack**).\n"
            "* Kiểm tra cặp dấu ngoặc hợp lệ và tính giá trị biểu thức hậu tố (Postfix)."
        ),
    },
    {
        "id": 14,
        "topic_id": 14,
        "content_type": "markdown",
        "summary": "Nguyên lý FIFO (Vào trước - Ra trước) của Hàng đợi (Queue) và công thức Hàng đợi vòng.",
        "content_markdown": (
            "### 1. Nguyên lý Hoạt động FIFO (First In, First Out)\n"
            "**Queue** thêm phần tử ở cuối hàng (`rear` - `enqueue`) và lấy ra ở đầu hàng (`front` - `dequeue`).\n\n"
            "### 2. Công thức Hàng đợi Vòng (Circular Queue)\n"
            "Sử dụng phép toán chia lấy dư modulo $N$ để tái sử dụng không gian mảng:\n"
            "$$\\text{rear} = (\\text{rear} + 1) \\bmod N$$\n"
            "$$\\text{front} = (\\text{front} + 1) \\bmod N$$"
        ),
    },
    {
        "id": 15,
        "topic_id": 15,
        "content_type": "markdown",
        "summary": "Tính chất toán học của Cây nhị phân và 3 phép duyệt cây đệ quy NLR, LNR, LRN.",
        "content_markdown": (
            "### 1. Tính chất Cây Nhị phân (Binary Tree)\n"
            "Mỗi nút có tối đa $2$ nút con. Cây nhị phân có chiều cao $h$ ($h \\ge 0$) có tổng số nút tối đa:\n"
            "$$N_{\\max} = 2^{h+1} - 1$$\n\n"
            "### 2. Ba Phép Duyệt Cây Theo Chiều Sâu\n"
            "* **Pre-order (NLR):** Gốc $\\rightarrow$ Trái $\\rightarrow$ Phải.\n"
            "* **In-order (LNR):** Trái $\\rightarrow$ Gốc $\\rightarrow$ Phải.\n"
            "* **Post-order (LRN):** Trái $\\rightarrow$ Phải $\\rightarrow$ Gốc."
        ),
    },
    {
        "id": 16,
        "topic_id": 16,
        "content_type": "markdown",
        "summary": "Bất biến của Cây tìm kiếm nhị phân (BST) và phân tích độ phức tạp tìm kiếm O(log n).",
        "content_markdown": (
            "### 1. Tính chất Bất biến của Cây BST\n"
            "Tại mọi nút $u$: Mọi khóa thuộc cây con trái đều nhỏ hơn `u->key`, và mọi khóa thuộc cây con phải "
            "đều lớn hơn `u->key`. Duyệt **In-order (LNR)** trên BST luôn cho dãy giá trị tăng dần.\n\n"
            "### 2. Giải thuật Tìm kiếm Đệ quy\n"
            "```c\n"
            "Node* searchBST(Node* root, int target) {\n"
            "    if (root == NULL || root->key == target) return root;\n"
            "    if (target < root->key) return searchBST(root->left, target);\n"
            "    return searchBST(root->right, target);\n"
            "}\n"
            "```\n"
            "* **Độ phức tạp trung bình:** $O(\\log_2 n)$.\n"
            "* **Trường hợp suy biến (cây lệch):** $O(n)$."
        ),
    },
]


# ==============================================================================
# 4. NẠP DỮ LIỆU VÀ KIỂM THỬ BẰNG ORM
# ==============================================================================

def seed_all_data(engine: Engine, reset: bool = False) -> None:
    """Tạo schema theo ORM, nạp dữ liệu mẫu và kiểm tra quan hệ dữ liệu."""
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    with SessionLocal() as session:
        with session.begin():
            courses_by_seed_id: dict[int, Course] = {}
            for course_data in COURSES_DATA:
                course = session.scalar(
                    select(Course).where(Course.code == course_data["code"])
                )
                if course is None:
                    course = Course(
                        code=course_data["code"],
                        title=course_data["title"],
                        description=course_data["description"],
                        status="ACTIVE",
                    )
                    session.add(course)
                else:
                    course.title = course_data["title"]
                    course.description = course_data["description"]
                    course.status = "ACTIVE"
                session.flush()
                courses_by_seed_id[course_data["id"]] = course

            lessons_by_seed_id: dict[int, Lesson] = {}
            for lesson_data in LESSONS_DATA:
                course = courses_by_seed_id[lesson_data["course_id"]]
                lessons = session.scalars(
                    select(Lesson).where(
                        Lesson.course_id == course.id,
                        Lesson.order_index == lesson_data["order_index"],
                    )
                ).all()
                if len(lessons) > 1:
                    raise RuntimeError(
                        f"Có nhiều bài học thứ {lesson_data['order_index']} "
                        f"trong môn {course.code}; không thể xác định bản ghi seed."
                    )

                lesson = lessons[0] if lessons else Lesson(course_id=course.id)
                lesson.title = lesson_data["title"]
                lesson.order_index = lesson_data["order_index"]
                if not lessons:
                    session.add(lesson)
                session.flush()
                lessons_by_seed_id[lesson_data["id"]] = lesson

            if reset:
                for topic_data in TOPICS_DATA:
                    lesson = lessons_by_seed_id[topic_data["lesson_id"]]
                    marker = f"# {topic_data['title']}\n\n"
                    contents = session.scalars(
                        select(LessonContent).where(
                            LessonContent.lesson_id == lesson.id
                        )
                    ).all()
                    for content in contents:
                        if content.body.startswith(marker):
                            session.delete(content)

                    topic = session.scalar(
                        select(Topic).where(
                            Topic.lesson_id == lesson.id,
                            Topic.name == topic_data["title"],
                        )
                    )
                    if topic is not None:
                        session.delete(topic)
                session.flush()

            topics_by_seed_id: dict[int, Topic] = {}
            for topic_data in TOPICS_DATA:
                lesson = lessons_by_seed_id[topic_data["lesson_id"]]
                topic = session.scalar(
                    select(Topic).where(
                        Topic.lesson_id == lesson.id,
                        Topic.name == topic_data["title"],
                    )
                )
                if topic is None:
                    topic = Topic(lesson_id=lesson.id, name=topic_data["title"])
                    session.add(topic)
                topics_by_seed_id[topic_data["id"]] = topic

            session.flush()
            topics_data_by_id = {item["id"]: item for item in TOPICS_DATA}
            lessons_data_by_id = {item["id"]: item for item in LESSONS_DATA}
            for content_data in LESSON_CONTENTS_DATA:
                topic = topics_by_seed_id[content_data["topic_id"]]
                topic_data = topics_data_by_id[content_data["topic_id"]]
                lesson = lessons_by_seed_id[topic_data["lesson_id"]]
                marker = f"# {topic.name}\n\n"
                lesson_description = ""
                if topic_data["order_index"] == 1:
                    lesson_description = (
                        f"**Mô tả bài học:** "
                        f"{lessons_data_by_id[topic_data['lesson_id']]['description']}\n\n"
                    )
                body = (
                    f"{marker}{lesson_description}"
                    f"**Tóm tắt:** {content_data['summary']}\n\n"
                    f"{content_data['content_markdown']}"
                )
                matching_contents = [
                    content
                    for content in session.scalars(
                        select(LessonContent).where(
                            LessonContent.lesson_id == lesson.id
                        )
                    ).all()
                    if content.body.startswith(marker)
                ]
                if len(matching_contents) > 1:
                    raise RuntimeError(
                        f"Có nhiều nội dung seed cho chủ đề {topic_data['title']}."
                    )

                content = (
                    matching_contents[0]
                    if matching_contents
                    else LessonContent(lesson_id=lesson.id)
                )
                content.content_type = "MARKDOWN"
                content.body = body
                if not matching_contents:
                    session.add(content)

            session.flush()
            course_ids = [course.id for course in courses_by_seed_id.values()]
            lesson_ids = [lesson.id for lesson in lessons_by_seed_id.values()]
            actual_counts = {
                "courses": session.scalar(
                    select(func.count(Course.id)).where(Course.id.in_(course_ids))
                ),
                "lessons": session.scalar(
                    select(func.count(Lesson.id)).where(Lesson.id.in_(lesson_ids))
                ),
                "topics": session.scalar(
                    select(func.count(Topic.id)).where(Topic.lesson_id.in_(lesson_ids))
                ),
                "lesson_contents": session.scalar(
                    select(func.count(LessonContent.id)).where(
                        LessonContent.lesson_id.in_(lesson_ids)
                    )
                ),
            }
            expected_counts = {
                "courses": len(COURSES_DATA),
                "lessons": len(LESSONS_DATA),
                "topics": len(TOPICS_DATA),
                "lesson_contents": len(LESSON_CONTENTS_DATA),
            }
            for table_name, expected in expected_counts.items():
                actual = actual_counts[table_name]
                if actual != expected:
                    raise RuntimeError(
                        f"Bảng {table_name} có {actual} bản ghi seed, "
                        f"mong đợi {expected}."
                    )
                logger.info("PASS: %-20s %s/%s bản ghi", table_name, actual, expected)

            topic_count = actual_counts["topics"]
            content_count = actual_counts["lesson_contents"]
            if topic_count != content_count:
                raise RuntimeError(
                    f"Số chủ đề ({topic_count}) không khớp số nội dung ({content_count})."
                )

            logger.info("PASS: Khóa ngoại của các bản ghi seed hợp lệ.")
            print("\n" + "=" * 100)
            print(" BÁO CÁO KIỂM THỬ DATABASE - TASK TK-03")
            print(f" Thời gian: {datetime.now():%d/%m/%Y %H:%M:%S}")
            print(f" Database: {engine.url.database}")
            print("=" * 100)
            print(
                f"{'Mã môn':<10} {'Tên môn học':<42}"
                f"{'Bài học':<10} {'Chủ đề':<10} {'Nội dung':<10}"
            )
            print("-" * 100)
            for course_data in COURSES_DATA:
                course = courses_by_seed_id[course_data["id"]]
                course_lesson_ids = [
                    lesson.id
                    for lesson in lessons_by_seed_id.values()
                    if lesson.course_id == course.id
                ]
                course_topics = session.scalar(
                    select(func.count(Topic.id)).where(
                        Topic.lesson_id.in_(course_lesson_ids)
                    )
                )
                course_contents = session.scalar(
                    select(func.count(LessonContent.id)).where(
                        LessonContent.lesson_id.in_(course_lesson_ids)
                    )
                )
                print(
                    f"{course.code:<10} {course.title:<42}"
                    f"{len(course_lesson_ids):<10} {course_topics:<10} "
                    f"{course_contents:<10}"
                )
            print("-" * 100)
            print(f"TỔNG: {sum(actual_counts.values())} bản ghi")
            print("KẾT QUẢ: PASS - DATABASE HOẠT ĐỘNG TỐT")
            print("=" * 100 + "\n")


# ==============================================================================
# 5. THAM SỐ DÒNG LỆNH VÀ HÀM MAIN
# ==============================================================================

def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Nạp dữ liệu mẫu LearnMate AI - Task TK-03."
    )
    parser.add_argument("--host", default=DB_HOST, help="Địa chỉ MySQL Host")
    parser.add_argument(
        "--port", type=int, default=DB_PORT, help="Cổng kết nối MySQL"
    )
    parser.add_argument("--user", default=DB_USER, help="Tài khoản MySQL")
    parser.add_argument(
        "--password", default=DB_PASSWORD, help="Mật khẩu MySQL"
    )
    parser.add_argument(
        "--database", default=TARGET_DB_NAME, help="Database mục tiêu"
    )
    parser.add_argument(
        "--root-user", default=DB_ROOT_USER, help="Tài khoản quản trị MySQL"
    )
    parser.add_argument(
        "--root-password",
        default=DB_ROOT_PASSWORD,
        help="Mật khẩu quản trị (hoặc đặt DB_ROOT_PASSWORD trong .env)",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Xóa và nạp lại dữ liệu seed của hai môn IT201/IT202.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    params = get_mysql_connection_params(args)
    engine = None

    try:
        create_database_if_not_exists(params)
        engine = create_engine(
            create_database_url(params),
            pool_pre_ping=True,
            connect_args={"connect_timeout": 10},
        )
        with engine.connect() as conn:
            version, active_database = conn.exec_driver_sql(
                "SELECT VERSION(), DATABASE()"
            ).one()
        logger.info("PASS: Kết nối MySQL %s tại %s:%s", version, params["host"], params["port"])
        if active_database != params["database"]:
            raise RuntimeError(
                f"Kết nối nhầm database `{active_database}`, "
                f"mong đợi `{params['database']}`."
            )

        seed_all_data(engine, reset=args.reset)
        logger.info(
            "HOÀN TẤT! Dữ liệu mẫu đã được nạp vào database `%s`.",
            params["database"],
        )
        return 0
    except SQLAlchemyError as exc:
        logger.error("LỖI MYSQL / SQLALCHEMY: %s", exc)
        if getattr(exc.orig, "args", ())[:1] == (1049,):
            logger.error(
                "Database chưa tồn tại. Hãy khởi tạo database hoặc cấu hình "
                "DB_ROOT_PASSWORD để script tự tạo database."
            )
        return 1
    except (RuntimeError, ValueError) as exc:
        logger.error("LỖI CẤU HÌNH / DỮ LIỆU: %s", exc)
        return 1
    finally:
        if engine is not None:
            engine.dispose()


if __name__ == "__main__":
    sys.exit(main())
