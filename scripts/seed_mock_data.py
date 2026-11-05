#!/usr/bin/env python3
"""
Dự án: LearnMate AI - Hệ thống Gia sư Hỏi đáp Socratic & Học tập Thích ứng
Tệp: learnmate_ai/scripts/seed_mock_data.py
Mã Task: TK-03 | Phân hệ 2: Dữ liệu mẫu (Tầng Nghiệp vụ BA)
Người phụ trách: Huỳnh Quốc Huy - MSSV: N25DTCN127 (Deadline: 04/11/2026)
Database mục tiêu: seed_mock_data
Mô tả: Tự động kiểm tra kết nối MySQL 8.0, khởi tạo database `seed_mock_data`,
       tạo 4 bảng (courses, lessons, topics, lesson_contents), nạp dữ liệu mẫu
       (2 môn học CNTT, 8 bài học, 16 chủ đề lý thuyết) và in báo cáo kiểm thử.
"""

import argparse
import logging
import sys
from datetime import datetime
from typing import Any

import pymysql
import sqlalchemy
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Connection, Engine, URL
from sqlalchemy.exc import SQLAlchemyError

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

TARGET_DB_NAME = "seed_mock_data"

MYSQL_CONFIG = {
    "user": "root",
    "password": "",
    "host": "127.0.0.1",
    "port": 3306,
    "database": TARGET_DB_NAME,
}


def get_mysql_connection_params() -> dict[str, Any]:
    """Lấy cấu hình kết nối MySQL, không sử dụng mật khẩu."""
    return MYSQL_CONFIG.copy()


def create_database_if_not_exists(params: dict[str, Any]) -> URL:
    """
    Kiểm tra MySQL Server và tạo database nếu chưa tồn tại.
    Database luôn được cố định là seed_mock_data.
    """

    logger.info(
        "Bước 1/4: Kiểm tra kết nối MySQL Server tại %s:%s...",
        params["host"],
        params["port"],
    )

    server_url = URL.create(
        drivername="mysql+pymysql",
        username=params["user"],
        password=params["password"],
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
        with server_engine.connect() as conn:

            # Kiểm tra kết nối MySQL
            mysql_version = conn.execute(
                text("SELECT VERSION();")
            ).scalar_one()

            logger.info(
                "PASS: Kết nối MySQL thành công!"
            )
            logger.info(
                "Phiên bản MySQL: %s",
                mysql_version,
            )

            # Tạo database nếu chưa tồn tại
            conn.execute(
                text(
                    f"CREATE DATABASE IF NOT EXISTS `{TARGET_DB_NAME}` "
                    "CHARACTER SET utf8mb4 "
                    "COLLATE utf8mb4_unicode_ci"
                )
            )

            logger.info(
                "PASS: Database `%s` đã sẵn sàng.",
                TARGET_DB_NAME,
            )

    finally:
        server_engine.dispose()

    # Tạo URL kết nối trực tiếp vào database mục tiêu
    db_url = URL.create(
        drivername="mysql+pymysql",
        username=params["user"],
        password=params["password"],
        host=params["host"],
        port=params["port"],
        database=TARGET_DB_NAME,
        query={"charset": "utf8mb4"},
    )

    return db_url

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
# 4. KHỞI TẠO BẢNG, NẠP DỮ LIỆU VÀ KIỂM THỬ
# ==============================================================================

def ensure_tables_exist(conn: Connection) -> None:
    """Tạo 4 bảng nếu chưa tồn tại."""

    logger.info(
        "Bước 2/4: Khởi tạo cấu trúc 4 bảng..."
    )

    statements = [
        """
        CREATE TABLE IF NOT EXISTS courses (
            id INT AUTO_INCREMENT PRIMARY KEY,
            code VARCHAR(32) NOT NULL UNIQUE,
            title VARCHAR(255) NOT NULL,
            description TEXT NULL,
            is_active TINYINT(1) NOT NULL DEFAULT 1,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                ON UPDATE CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
          COLLATE=utf8mb4_unicode_ci;
        """,

        """
        CREATE TABLE IF NOT EXISTS lessons (
            id INT AUTO_INCREMENT PRIMARY KEY,
            course_id INT NOT NULL,
            title VARCHAR(255) NOT NULL,
            description TEXT NULL,
            order_index INT NOT NULL DEFAULT 1,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                ON UPDATE CURRENT_TIMESTAMP,
            CONSTRAINT fk_lessons_course
                FOREIGN KEY (course_id)
                REFERENCES courses(id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
          COLLATE=utf8mb4_unicode_ci;
        """,

        """
        CREATE TABLE IF NOT EXISTS topics (
            id INT AUTO_INCREMENT PRIMARY KEY,
            lesson_id INT NOT NULL,
            title VARCHAR(255) NOT NULL,
            slug VARCHAR(255) NULL,
            order_index INT NOT NULL DEFAULT 1,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                ON UPDATE CURRENT_TIMESTAMP,
            CONSTRAINT fk_topics_lesson
                FOREIGN KEY (lesson_id)
                REFERENCES lessons(id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
          COLLATE=utf8mb4_unicode_ci;
        """,

        """
        CREATE TABLE IF NOT EXISTS lesson_contents (
            id INT AUTO_INCREMENT PRIMARY KEY,
            topic_id INT NOT NULL,
            content_type VARCHAR(50) NOT NULL DEFAULT 'markdown',
            summary TEXT NULL,
            content_markdown LONGTEXT NOT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                ON UPDATE CURRENT_TIMESTAMP,
            CONSTRAINT fk_contents_topic
                FOREIGN KEY (topic_id)
                REFERENCES topics(id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
          COLLATE=utf8mb4_unicode_ci;
        """,
    ]

    for statement in statements:
        conn.execute(text(statement))

    logger.info("PASS: Đã kiểm tra đủ 4 bảng.")


def reset_tables(conn: Connection) -> None:
    """Xóa dữ liệu cũ trong 4 bảng khi có --reset."""

    logger.warning("Đang reset dữ liệu cũ...")

    try:
        conn.execute(text("SET FOREIGN_KEY_CHECKS = 0"))

        for table_name in (
            "lesson_contents",
            "topics",
            "lessons",
            "courses",
        ):
            conn.execute(
                text(f"TRUNCATE TABLE `{table_name}`")
            )

    finally:
        conn.execute(text("SET FOREIGN_KEY_CHECKS = 1"))

    logger.info("PASS: Đã làm sạch dữ liệu cũ.")


def seed_all_data(engine: Engine, reset: bool = False) -> None:
    """Nạp dữ liệu mẫu và tự động kiểm thử database."""

    with engine.begin() as conn:

        # ----------------------------------------------------------
        # KIỂM TRA DATABASE ĐANG KẾT NỐI
        # ----------------------------------------------------------

        active_db = conn.execute(
            text("SELECT DATABASE()")
        ).scalar_one()

        if active_db != TARGET_DB_NAME:
            raise RuntimeError(
                f"Sai database! Đang kết nối: {active_db}"
            )

        logger.info(
            "PASS: Đang kết nối đúng database `%s`.",
            active_db,
        )

        # ----------------------------------------------------------
        # KHỞI TẠO BẢNG
        # ----------------------------------------------------------

        ensure_tables_exist(conn)

        if reset:
            reset_tables(conn)

        logger.info(
            "Bước 3/4: Đang nạp dữ liệu mẫu..."
        )

        # ----------------------------------------------------------
        # NẠP COURSES
        # ----------------------------------------------------------

        conn.execute(
            text("""
                INSERT INTO courses
                    (id, code, title, description, is_active)
                VALUES
                    (:id, :code, :title, :description, :is_active)
                ON DUPLICATE KEY UPDATE
                    code = VALUES(code),
                    title = VALUES(title),
                    description = VALUES(description),
                    is_active = VALUES(is_active)
            """),
            COURSES_DATA,
        )

        # ----------------------------------------------------------
        # NẠP LESSONS
        # ----------------------------------------------------------

        conn.execute(
            text("""
                INSERT INTO lessons
                    (id, course_id, title, description, order_index)
                VALUES
                    (:id, :course_id, :title, :description, :order_index)
                ON DUPLICATE KEY UPDATE
                    course_id = VALUES(course_id),
                    title = VALUES(title),
                    description = VALUES(description),
                    order_index = VALUES(order_index)
            """),
            LESSONS_DATA,
        )

        # ----------------------------------------------------------
        # NẠP TOPICS
        # ----------------------------------------------------------

        conn.execute(
            text("""
                INSERT INTO topics
                    (id, lesson_id, title, slug, order_index)
                VALUES
                    (:id, :lesson_id, :title, :slug, :order_index)
                ON DUPLICATE KEY UPDATE
                    lesson_id = VALUES(lesson_id),
                    title = VALUES(title),
                    slug = VALUES(slug),
                    order_index = VALUES(order_index)
            """),
            TOPICS_DATA,
        )

        # ----------------------------------------------------------
        # NẠP LESSON CONTENTS
        # ----------------------------------------------------------

        conn.execute(
            text("""
                INSERT INTO lesson_contents
                    (id, topic_id, content_type, summary, content_markdown)
                VALUES
                    (:id, :topic_id, :content_type, :summary, :content_markdown)
                ON DUPLICATE KEY UPDATE
                    topic_id = VALUES(topic_id),
                    content_type = VALUES(content_type),
                    summary = VALUES(summary),
                    content_markdown = VALUES(content_markdown)
            """),
            LESSON_CONTENTS_DATA,
        )

        logger.info("PASS: Đã thực hiện nạp dữ liệu.")

        # ----------------------------------------------------------
        # BƯỚC 4: KIỂM THỬ DỮ LIỆU
        # ----------------------------------------------------------

        logger.info("Bước 4/4: Kiểm thử dữ liệu database...")

        expected_counts = {
            "courses": 2,
            "lessons": 8,
            "topics": 16,
            "lesson_contents": 16,
        }

        actual_counts = {}

        for table_name, expected in expected_counts.items():

            total = conn.execute(
                text(f"SELECT COUNT(*) FROM `{table_name}`")
            ).scalar_one()

            actual_counts[table_name] = total

            if total != expected:
                raise RuntimeError(
                    f"FAIL: Bảng {table_name} có {total} bản ghi, "
                    f"mong đợi {expected}."
                )

            logger.info(
                "PASS: %-20s %s/%s bản ghi",
                table_name,
                total,
                expected,
            )

        # ----------------------------------------------------------
        # KIỂM TRA LIÊN KẾT GIỮA 4 BẢNG
        # ----------------------------------------------------------

        join_count = conn.execute(
            text("""
                SELECT COUNT(*)
                FROM courses c
                INNER JOIN lessons l
                    ON c.id = l.course_id
                INNER JOIN topics t
                    ON l.id = t.lesson_id
                INNER JOIN lesson_contents lc
                    ON t.id = lc.topic_id
            """)
        ).scalar_one()

        if join_count != 16:
            raise RuntimeError(
                f"FAIL: JOIN trả về {join_count} dòng, mong đợi 16."
            )

        logger.info(
            "PASS: Quan hệ khóa ngoại và JOIN (%s dòng).",
            join_count,
        )

        # ----------------------------------------------------------
        # BÁO CÁO TỔNG HỢP
        # ----------------------------------------------------------

        summary_rows = conn.execute(
            text("""
                SELECT
                    c.id,
                    c.code,
                    c.title AS course_title,
                    COUNT(DISTINCT l.id) AS total_lessons,
                    COUNT(DISTINCT t.id) AS total_topics,
                    COUNT(DISTINCT lc.id) AS total_contents
                FROM courses c
                LEFT JOIN lessons l
                    ON c.id = l.course_id
                LEFT JOIN topics t
                    ON l.id = t.lesson_id
                LEFT JOIN lesson_contents lc
                    ON t.id = lc.topic_id
                GROUP BY c.id, c.code, c.title
                ORDER BY c.id
            """)
        ).mappings().all()

        print("\n" + "=" * 100)
        print(" BÁO CÁO KIỂM THỬ DATABASE - TASK TK-03")
        print(f" Thời gian: {datetime.now():%d/%m/%Y %H:%M:%S}")
        print(f" Database: {active_db}")
        print("=" * 100)

        print(
            f"{'ID':<5} {'Mã môn':<10} {'Tên môn học':<42}"
            f"{'Bài học':<10} {'Chủ đề':<10} {'Nội dung':<10}"
        )

        print("-" * 100)

        for row in summary_rows:
            print(
                f"{row['id']:<5} "
                f"{row['code']:<10} "
                f"{row['course_title']:<42} "
                f"{row['total_lessons']:<10} "
                f"{row['total_topics']:<10} "
                f"{row['total_contents']:<10}"
            )

        print("-" * 100)

        print(
            f"TỔNG: {sum(actual_counts.values())} bản ghi"
        )

        print("KẾT QUẢ: PASS - DATABASE HOẠT ĐỘNG TỐT")
        print("=" * 100 + "\n")

       # ==============================================================================
# 5. THAM SỐ DÒNG LỆNH VÀ HÀM MAIN
# ==============================================================================

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Nạp dữ liệu mẫu LearnMate AI - Task TK-03."
    )

    parser.add_argument(
        "--reset",
        action="store_true",
        help="Xóa dữ liệu cũ và nạp lại toàn bộ dữ liệu mẫu.",
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    params = get_mysql_connection_params()
    engine = None

    try:
        # Kiểm tra và tạo database
        db_url = create_database_if_not_exists(params)

        # Kết nối trực tiếp vào database mục tiêu
        engine = create_engine(
            db_url,
            pool_pre_ping=True,
            connect_args={"connect_timeout": 10},
        )

        # Kiểm tra kết nối thực tế
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))

        # Tạo bảng, nạp dữ liệu, kiểm thử
        seed_all_data(engine, reset=args.reset)

        logger.info(
            "HOÀN TẤT 100%%! Task TK-03 thành công trên database `%s`.",
            TARGET_DB_NAME,
        )

        return 0

    except SQLAlchemyError as exc:
        logger.error(
            "LỖI MYSQL / SQLALCHEMY: %s",
            exc,
        )
        return 1

    except Exception as exc:
        logger.error(
            "LỖI KHÔNG XÁC ĐỊNH: %s",
            exc,
        )
        return 1

    finally:
        if engine is not None:
            engine.dispose()


if __name__ == "__main__":
    sys.exit(main())