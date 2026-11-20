# BÁO CÁO DANH MỤC TỆP DỮ LIỆU VÀ PHÂN LOẠI DỌN DẸP (FILE CLEANUP REPORT)
**Dự án:** Nghiên cứu, cài đặt và đánh giá kỹ thuật giấu tin trong ảnh số PVD và DWT  
**Mục tiêu:** Phân loại toàn bộ các file, thư mục, dữ liệu trung gian và artifacts theo 5 nhóm A, B, C, D, E phục vụ chuẩn bị bản bàn giao đồ án.

---

## 1. Phân loại theo 5 nhóm tiêu chuẩn (A, B, C, D, E)

### NHÓM A – BẮT BUỘC GIỮ (Core Requirements)
*Ý nghĩa:* Thuật toán cốt lõi, tầng dịch vụ, giao diện chính và dữ liệu mẫu không thể thiếu để ứng dụng khởi chạy và demo.

| Đường dẫn / Tệp tin | Kích thước | Vai trò / Lý do bắt buộc giữ | Bằng chứng sử dụng |
| :--- | :---: | :--- | :--- |
| `main.py` | 0.2 KB | Điểm khởi chạy ứng dụng Desktop chính | Khởi tạo `MainWindow().mainloop()` |
| `requirements.txt` | 0.1 KB | Khai báo 7 thư viện bắt buộc (numpy, Pillow, PyWavelets, scikit-image, opencv, pytest, matplotlib) | `pip install -r requirements.txt` |
| `core/` (6 files `.py`) | ~11.5 KB | Toàn bộ thuật toán PVD, DWT, đóng gói payload, ma trận ảnh | Được import trực tiếp bởi `services/` |
| `gui/` (12 files `.py`) | ~94.0 KB | Toàn bộ giao diện Tkinter (4 tab, preview ảnh, vẽ biểu đồ) | `main.py` khởi chạy `gui.main_window` |
| `services/` (3 files `.py`)| ~12.5 KB | Tầng dịch vụ điều phối, chạy luồng, validation tham số | GUI giao tiếp với Core qua `StegoService` |
| `storage/` (2 files `.py`) | ~2.7 KB | Quản lý JSON history an toàn | Ghi nhận lịch sử cho ứng dụng |
| `metrics/` (2 files `.py`) | ~2.4 KB | Hàm tính toán PSNR, SSIM, BER, bpp | Được gọi trong cả Core, Service và Test |
| `data/selected_512/` (8 ảnh)| 2.23 MB | Bộ ảnh chuẩn USC-SIPI 512×512 dùng cho demo và thực nghiệm | Được dùng trong Báo cáo Chương 4 và kiểm thử |
| `data/demo/` (3 ảnh) | 0.2 MB | Ảnh tổng hợp (gradient, texture, white) dùng cho test nhanh | Dùng trong unit test và demo nhỏ |

---

### NHÓM B – NÊN GIỮ (Support & Verification)
*Ý nghĩa:* Các kịch bản thực nghiệm, kiểm thử tự động và tài liệu cần thiết để giảng viên kiểm chứng tính đúng đắn và tính khoa học của đề tài.

| Đường dẫn / Tệp tin | Kích thước | Vai trò / Lý do nên giữ | Bằng chứng sử dụng |
| :--- | :---: | :--- | :--- |
| `experiments/attacks.py` | 4.5 KB | 8 phép tấn công OpenCV (JPEG, noise, blur, transform) | Dùng cho tab So sánh và Batch runner |
| `experiments/batch_runner.py`| 14.8 KB | Động cơ chạy hàng loạt ảnh đa luồng cho tab "Bộ ảnh" | Được gọi từ `gui/batch_panel.py` |
| `experiments/experiment_config.py`| 2.1 KB | Cấu hình tham số thực nghiệm chuẩn của Chương 4 | Cung cấp default config cho hệ thống |
| `experiments/extraction.py` | 1.1 KB | Hàm thẩm định chất lượng trích xuất sau tấn công | Được gọi bởi `batch_runner.py` |
| `tests/` (18 files `.py`) | ~110 KB | 238 ca kiểm thử tự động chứng minh độ tin cậy của phần mềm | Chạy bằng lệnh `pytest` |
| `data/history.json` | ~0.1 KB | File lưu lịch sử cục bộ (cần reset rỗng `[]` trước khi bàn giao) | Đọc ghi bởi `history_store.py` |
| Báo cáo đồ án chính thức | ~2.3 MB | Tài liệu thuyết minh đồ án bản hoàn chỉnh nhất | Tài liệu nộp trường |

---

### NHÓM C – CÓ THỂ GỘP / TÁI CẤU TRÚC (Can Merge)
*Ý nghĩa:* Mã nguồn có sự trùng lặp chức năng, có thể hợp nhất để mã nguồn gọn gàng hơn mà không thay đổi hành vi hệ thống.

| Tệp tin liên quan | Kích thước | Đề xuất hợp nhất | Lý do kỹ thuật |
| :--- | :---: | :--- | :--- |
| `experiments/robustness_runner.py` và `experiments/batch_runner.py` | ~21.7 KB | Gộp logic chạy thử nghiệm vào `batch_runner.py`, biến `benchmark_runner.py` thành CLI wrapper của `batch_runner.py` | Cả hai cùng thực hiện một ma trận thực nghiệm giống nhau, tránh duy trì 2 runner song song |
| `services/robustness.py` và `experiments/batch_runner.py` | ~18.0 KB | Đưa logic kiểm tra tham số tấn công `validate_configuration` về `experiment_config.py` | Tránh lặp lại cùng các ngưỡng kiểm tra `quality`, `sigma`, `amount`, `scale` |

---

### NHÓM D – LOẠI KHỎI BẢN BÀN GIAO CHO TRƯỜNG (Prune from Handover Bundle)
*Ý nghĩa:* Dữ liệu kết quả chạy thử nghiệm cũ, ảnh stego tạm sinh ra trong quá trình nghiên cứu. Giữ lại trên máy nghiên cứu nhưng **không nén vào file nộp cho trường** để tránh làm nặng file zip và gây rối mắt người chấm.

| Thư mục / Tệp tin | Kích thước | Số lượng | Lý do loại khỏi bản nộp | Khả năng tái lập |
| :--- | :---: | :---: | :--- | :--- |
| `experiments/results/` | 0.65 MB | 27 files | Kết quả chạy thử từ ngày 19/09/2026 (cũ hơn cấu hình báo cáo) | Có thể tái lập bằng `benchmark_runner.py` |
| `experiments/results_baseline_512/` | 18.34 MB | 66 files | Kết quả chạy thử từ ngày 22/09/2026 (bản nháp trước) | Đã được thay thế bởi đợt chạy chính thức |
| `experiments/batch_results/` | 99.87 MB | 397 files | Các lần chạy thử nghiệm batch trước đó | Có thể tái lập bất kỳ lúc nào từ tab "Bộ ảnh" |
| `tests/artifacts/` | 1.79 MB | 23 files | Ảnh chụp màn hình GUI do test tự động sinh ra | Pytest tự sinh lại khi chạy test UI |

---

### NHÓM E – XÓA HOẶC TÁCH KHỎI SOURCE CODE (Unused / Office Automation Artifacts)
*Ý nghĩa:* Toàn bộ thư mục `output/` chứa gần 500 file trung gian sinh văn bản Word và các bản nháp có tên không trang trọng. Đây là sản phẩm phụ của quá trình soạn thảo văn bản, hoàn toàn không phục vụ phần mềm.

| Đường dẫn / Tệp tin | Kích thước | Số lượng | Chi tiết nội dung | Đề xuất xử lý |
| :--- | :---: | :---: | :--- | :--- |
| `output/chapter4/tables_qa/` | 15.25 MB | 81 files | Ảnh chụp các trang bảng biểu PDF (`page-*.png`, `overview-*.jpg`) | **Xóa hoàn toàn** |
| `output/chapter4/*.py` (8 script) | ~45 KB | 8 files | Script dùng `zipfile` chèn bảng/ảnh vào file Word | **Chuyển ra thư mục công cụ cá nhân** |
| `output/chapter4/*.json`, `*.log`, `*.txt` | ~0.5 MB | 14 files | Log audit văn bản: `app_error.log`, `window.txt`, `tables_audit.json`... | **Xóa hoàn toàn** |
| `output/chapter4/*.pdf` | ~45 MB | 5 files | Các file PDF xuất tạm để kiểm tra format in ấn | **Xóa hoặc lưu kho cá nhân** |
| `output/chapter4/hihi_*.docx` | ~15 MB | 3 files | Các bản Word nháp của Chương 4 | **Xóa hoàn toàn** |
| `hihi_chuong_4_bo_sung_hinh_DWT.docx` | 3.95 MB | 1 file | File nháp ở thư mục gốc có tên không trang trọng | **Xóa khỏi repo nộp** |

---

## 2. Tổng kết dung lượng giải phóng

- **Dung lượng hiện tại của toàn repository:** ~245 MB (hơn 1.000 files).
- **Dung lượng sau khi lọc bỏ Nhóm D và Nhóm E:** **~8 MB** (chỉ còn mã nguồn Python, bộ ảnh mẫu 512×512 và 01 file báo cáo chính thức).
- **Lợi ích:** Gói nộp đồ án nhẹ hơn 30 lần, chuyên nghiệp, đúng chuẩn mực công nghệ phần mềm, không còn file rác.
