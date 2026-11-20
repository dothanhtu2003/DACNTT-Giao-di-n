# BÁO CÁO TỔNG QUAN KIẾN TRÚC VÀ RÀ SOÁT MÃ NGUỒN (CODE AUDIT)
**Dự án:** Nghiên cứu, cài đặt và đánh giá kỹ thuật giấu tin trong ảnh số PVD và DWT  
**Thời điểm rà soát:** 20/11/2026  
**Chuyên gia rà soát:** Senior Python Engineer / Software Auditor  
**Phạm vi:** Toàn bộ repository (`core/`, `gui/`, `metrics/`, `services/`, `storage/`, `experiments/`, `output/`, `data/`, `tests/`)

---

## 1. Đánh giá tổng quan kiến trúc (Architectural Overview)

Dự án được xây dựng theo kiến trúc phân tầng (Layered Architecture) với sự phân định trách nhiệm tương đối rõ ràng giữa các phân hệ:
1. **Lớp Thuật toán cốt lõi (`core/`)**:
   - Triển khai độc lập hai thuật toán giấu tin: `pvd.py` (miền không gian) và `dwt.py` (miền tần số).
   - Đóng gói dữ liệu chuẩn hóa tại `payload.py` và các tiện ích ma trận ảnh tại `engine_utils.py`, `image_utils.py`.
   - **Đánh giá:** Các module trong `core/` đạt chất lượng rất cao: không chứa print debug, không có code thừa, typing và docstring rõ ràng, bám sát các phương trình toán học trong bài báo gốc của Wu & Tsai (2003) và biến đổi Haar Wavelet / QIM.
2. **Lớp Đo lường chất lượng (`metrics/`)**:
   - Triển khai tập trung tại `metrics.py`, cung cấp các hàm đo lường chuẩn hóa: MSE, PSNR, SSIM, BER, bpp và tỷ lệ sử dụng dung lượng.
   - **Đánh giá:** Nhất quán, chính xác, xử lý tốt các trường hợp biên như MSE = 0 (PSNR = Infinity).
3. **Lớp Dịch vụ & Điều phối (`services/`)**:
   - `stego_service.py`: Cầu nối điều phối giữa giao diện GUI và các engine xử lý; quản lý luồng xử lý nền qua ThreadPool, thực thi kiểm thử độ bền và đồng bộ lịch sử. Đặc biệt tuân thủ nguyên tắc an toàn: văn bản bí mật chỉ lưu trên RAM, không ghi vào log/history.
   - `robustness.py`: Định nghĩa và kiểm tra tính hợp lệ của các tham số tấn công trước khi chuyển xuống luồng xử lý.
4. **Lớp Giao diện người dùng (`gui/`)**:
   - Xây dựng trên nền tảng Tkinter/ttk với 4 thẻ chức năng: `embed_tab.py`, `extract_tab.py`, `compare_tab.py`, `history_tab.py`.
   - Có cơ chế đa luồng tránh treo giao diện (`ThreadPoolExecutor`), hỗ trợ visual hóa phân rã DWT (`dwt_view.py`), xem ảnh phóng to (`image_view.py`) và vẽ biểu đồ so sánh (`compare_chart.py`, `batch_chart.py`).
5. **Lớp Lưu trữ (`storage/`)**:
   - `history_store.py`: Quản lý file `history.json` với kỹ thuật ghi nguyên tử (Atomic Write qua temporary file), chống hỏng dữ liệu khi tắt app đột ngột.
6. **Lớp Thực nghiệm khoa học (`experiments/`)**:
   - `attacks.py`: Hiện thực hóa 8 kịch bản tấn công/xử lý ảnh thực tế bằng OpenCV.
   - `batch_runner.py`: Quản lý chạy batch đa ảnh, hỗ trợ hủy tác vụ (cancellable) và báo cáo tiến độ.
   - `robustness_runner.py` & `benchmark_runner.py`: Kịch bản chạy thực nghiệm qua dòng lệnh (CLI).

---

## 2. Bảng kiểm kê số lượng tệp theo danh mục

| Thư mục | Số file Python | Các loại file khác | Chức năng chính |
| :--- | :---: | :--- | :--- |
| `core/` | 6 | Không | Thuật toán PVD, DWT, payload, ma trận ảnh |
| `metrics/` | 2 | Không | Đo lường PSNR, SSIM, BER, bpp |
| `services/` | 3 | Không | Điều phối nghiệp vụ, validation tham số |
| `storage/` | 2 | Không | Quản lý JSON history nguyên tử |
| `gui/` | 12 | Không | Giao diện đồ họa Tkinter 4 tab và biểu đồ |
| `experiments/` | 8 | 440 PNG, 35 CSV, 13 JSON | Kịch bản tấn công, batch runner, benchmark CLI |
| `data/` | 0 | 10 PNG, 1 BMP, 1 JSON | Bộ ảnh chuẩn USC-SIPI 512×512, ảnh demo, history |
| `tests/` | 18 | 21 PNG, 2 JSON, 1 XML | 238 ca kiểm thử tự động (unit, integration, GUI) |
| `output/` | 8 | 430 PNG, 20 JPG, 5 PDF, 3 DOCX, 12 JSON, 3 CSV, 1 LOG | Dữ liệu trung gian sinh báo cáo Word Chương 4 |
| `root` | 1 | 2 DOCX, 1 TXT, 1 GITIGNORE | `main.py`, requirements, báo cáo đồ án |

---

## 3. Điểm mạnh nổi bật của hệ thống

1. **Tính độc lập cao giữa Core và GUI:** Có thể nhập và sử dụng `core` độc lập hoàn toàn mà không cần khởi động Tkinter hay bất kỳ thư viện UI nào.
2. **Khả năng tái lập kết quả (Reproducibility):** Tất cả các phép toán ngẫu nhiên (nhiễu Gaussian, nhiễu muối tiêu, sinh payload deterministic) đều được kiểm soát bằng Seed cố định (`SEED = 20260919`), đảm bảo mỗi lần chạy lại đều cho ra cùng một kết quả số liệu.
3. **Độ bao phủ kiểm thử cao:** Sở hữu 238 test cases tự động, bao quát từ kiểm thử tính toán ma trận, biến đổi Wavelet ngược, kiểm tra lỗi tràn/thiếu bit đến tương tác trên giao diện người dùng.

---

## 4. Các điểm hạn chế và vấn đề kỹ thuật phát hiện qua rà soát

1. **Sự tồn tại song song của hai hệ thống chạy thực nghiệm (Runner Duplication):**
   - Hệ thống có cả `experiments/robustness_runner.py` (legacy CLI runner) và `experiments/batch_runner.py` (modern batch runner phục vụ GUI). Cả hai đều có logic lặp qua các ảnh/tấn công/payload nhưng ghi ra định dạng file khác nhau.
2. **Các import không sử dụng:**
   - Trong `experiments/robustness_runner.py` có 3 import dư thừa (`np`, `decode_message`, `ber`).
3. **Thư mục `output/` chứa quá nhiều file tạm văn phòng:**
   - Hơn 140 file ảnh QA (`tables_qa/page-*.png`, `overview-*.jpg`), các file JSON audit và 8 file Python chỉ dùng để tự động chèn bảng/hình vào file Word.
4. **Tồn tại các file tài liệu nháp có tên không trang trọng:**
   - File `hihi_chuong_4_bo_sung_hinh_DWT.docx` tại thư mục gốc và các file `hihi_...` trong `output/chapter4/`.
5. **Thư mục `tests/artifacts/` lưu trữ ảnh chụp màn hình:**
   - Việc commit các ảnh chụp GUI test vào Git làm tăng dung lượng kho chứa không cần thiết.

---

## 5. Kết luận sơ bộ

Mã nguồn nghiệp vụ và thuật toán của dự án đạt chuẩn kỹ thuật cao, hoạt động chính xác và phản ánh trung thực kết quả trong báo cáo khoa học. Tuy nhiên, repository cần một đợt dọn dẹp các tệp dữ liệu trung gian và file phụ trợ văn phòng trước khi đóng gói nộp chính thức.
