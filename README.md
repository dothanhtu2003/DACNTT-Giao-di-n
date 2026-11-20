# HỆ THỐNG GIẤU TIN TRONG ẢNH SỐ PVD & DWT
*(Image Steganography using Pixel Value Differencing & Discrete Wavelet Transform)*

---

## 📌 THÔNG TIN ĐỒ ÁN
* **Tên đề tài:** Nghiên cứu, cài đặt và đánh giá kỹ thuật giấu tin trong ảnh số PVD và DWT
* **Sinh viên thực hiện:**
  * Đỗ Thanh Tú – MSSV: 52200240
  * Phạm Đăng Khôi – MSSV: 52000678
* **Giảng viên hướng dẫn:** TS. Bùi Quy Anh
* **Đơn vị:** Khoa Công nghệ Thông tin – Trường Đại học Tôn Đức Thắng
* **Năm thực hiện:** 2026

---

## 📖 GIỚI THIỆU TỔNG QUAN

Dự án nghiên cứu, hiện thực và so sánh độc lập hai kỹ thuật giấu tin tiêu biểu trong ảnh số:
1. **PVD (Pixel Value Differencing - Miền không gian):**
   * Hoạt động trên các cặp điểm ảnh ngang không chồng lấp (kênh Blue của ảnh RGB hoặc ma trận ảnh xám).
   * Phân dải 6 khoảng sai phân chênh lệch: $[0,7], [8,15], [16,31], [32,63], [64,127], [128,255]$ tương ứng với khả năng nhúng $3, 3, 4, 5, 6, 7$ bit/cặp.
   * Ưu điểm: Dung lượng giấu (Capacity) rất lớn, PSNR cao, tốc độ xử lý nhanh.
   * Hạn chế: Kém bền vững (fragile), dễ mất tin khi ảnh bị can thiệp.
2. **DWT-QIM (Discrete Wavelet Transform - Miền tần số):**
   * Biến đổi sóng con Haar 2 chiều mức 1 trên kênh độ chói $Y$.
   * Nhúng thông điệp vào dải tần số cao $HH$ bằng phương pháp điều chế chỉ số lượng tử **QIM** với bước lượng tử $\Delta = 18$.
   * Tích hợp mã lặp (Repetition factor $k = 5$) và giải mã bằng biểu quyết đa số (Majority Voting $\ge 3$).
   * Ưu điểm: Độ bền vững cao trước một số biến đổi quang học và nhiễu (Gaussian, Salt & Pepper, độ sáng, tương phản).
   * Hạn chế: Dung lượng giấu thấp hơn.

Định dạng gói tin nhúng chuẩn hóa: `[LENGTH (uint32 big-endian) || PAYLOAD (UTF-8 bytes)]`. Ảnh sau nhúng (stego) bắt buộc lưu định dạng **PNG lossless** để bảo toàn dữ liệu.

---

## ⚙️ YÊU CẦU HỆ THỐNG & CÀI ĐẶT

### 1. Yêu cầu môi trường
* Hệ điều hành: Windows 10/11, Linux, macOS.
* Python: Phiên bản **3.10** đến **3.12** (Khuyến nghị 3.12).

### 2. Cài đặt các thư viện phụ thuộc
Mở terminal tại thư mục gốc của dự án và chạy lệnh:
```bash
pip install -r requirements.txt
```

Danh mục thư viện chính trong `requirements.txt`:
* `numpy>=1.24,<3`: Tính toán ma trận số học.
* `Pillow>=10,<13`: Đọc, xử lý và lưu trữ ảnh định dạng PNG/BMP.
* `PyWavelets>=1.4,<2`: Biến đổi Wavelet DWT 2D và biến đổi ngược IDWT.
* `scikit-image>=0.21,<1`: Đánh giá độ tương đồng cấu trúc SSIM.
* `opencv-python>=4.8,<6`: Cài đặt các kịch bản tấn công và xử lý ảnh thực nghiệm.
* `matplotlib>=3.8,<4`: Trực quan hóa biểu đồ so sánh trên GUI.
* `pytest>=7,<10`: Hệ thống kiểm thử tự động.

---

## 🚀 HƯỚNG DẪN SỬ DỤNG

### 1. Khởi chạy ứng dụng đồ họa (GUI)
Để mở ứng dụng Desktop với đầy đủ 4 thẻ chức năng:
```bash
python main.py
```

Ứng dụng gồm 4 tab chính:
* **Nhúng dữ liệu (Embed):** Chọn ảnh cover (PNG/BMP), nhập văn bản bí mật, chọn PVD hoặc DWT, xem tính toán dung lượng tức thời, xem ảnh stego và lưu ảnh kết quả. Có nút xem trực quan 4 dải phân rã Wavelet $LL, LH, HL, HH$.
* **Trích xuất dữ liệu (Extract):** Nạp ảnh stego đã lưu, chọn đúng thuật toán và trích xuất lại thông điệp UTF-8 gốc (kèm nút Copy).
* **So sánh PVD – DWT (Compare):**
  * *Chế độ Một ảnh:* So sánh song song PVD và DWT trên cùng ảnh nguồn và cùng thông điệp (PSNR, SSIM, dung lượng, bpp, BER, biểu đồ cột). Cho phép thử nhanh các tác động tấn công (JPEG, noise, blur...).
  * *Chế độ Bộ ảnh (Batch):* Chạy thực nghiệm tự động trên toàn bộ thư mục ảnh với nhiều mức payload và phép tác động; trực quan hóa bảng kết quả và biểu đồ phân phối.
* **Lịch sử (History):** Xem lại các phiên làm việc và thông số đánh giá định lượng.

### 2. Chạy kiểm thử tự động (Unit & Integration Tests)
Dự án được xây dựng với hệ thống kiểm thử toàn diện gồm **238 test cases**:
```bash
python -m pytest -v
```
Hoặc chạy tóm tắt:
```bash
python -m pytest -q
```
*(Tất cả 238 ca kiểm thử bao phủ từ kiểm tra biên dung lượng, tính toàn vẹn packet, ma trận Haar Wavelet, QIM, BER cho đến luồng giao diện đều đạt kết quả 100% Passed).*

### 3. Chạy thực nghiệm Benchmark qua dòng lệnh (CLI)
Để chạy thực nghiệm kiểm thử độ bền qua dòng lệnh và xuất file `robustness_results.csv`:
* Chạy nhanh trên bộ ảnh demo tổng hợp:
  ```bash
  python -m experiments.benchmark_runner --demo --output experiments/results
  ```
* Chạy trên bộ ảnh chuẩn USC-SIPI 512×512:
  ```bash
  python -m experiments.benchmark_runner --images data/selected_512 --output experiments/results --summary experiments/results/summary.csv
  ```

---

## 📂 CẤU TRÚC THƯ MỤC DỰ ÁN

```text
├── core/                               # Thuật toán cốt lõi (PVD, DWT, payload, ma trận ảnh)
│   ├── dwt.py                          # Haar Wavelet mức 1 + QIM (Delta 18, lặp 5)
│   ├── pvd.py                          # Pixel Value Differencing (Kênh Blue/Gray, 6 khoảng)
│   ├── payload.py                      # Đóng gói packet [LENGTH (uint32) || UTF-8]
│   ├── engine_utils.py                 # Kiểm tra ma trận uint8, ngoại lệ CapacityError
│   └── image_utils.py                  # Đọc nạp PNG/BMP, lưu ảnh PNG lossless
├── metrics/                            # Đo lường chất lượng
│   └── metrics.py                      # MSE, PSNR, SSIM, BER, bpp
├── services/                           # Tầng dịch vụ điều phối
│   ├── stego_service.py                # Điều phối Embed, Extract, Compare, Batch
│   └── robustness.py                   # Thẩm định tham số kịch bản tấn công
├── storage/                            # Quản lý lưu trữ
│   └── history_store.py                # Ghi nhận JSON nguyên tử (Atomic Write)
├── gui/                                # Giao diện người dùng Tkinter/ttk
│   ├── main_window.py                  # Khung cửa sổ chính 4 tab
│   ├── embed_tab.py                    # Tab nhúng dữ liệu
│   ├── extract_tab.py                  # Tab trích xuất dữ liệu
│   ├── compare_tab.py                  # Tab so sánh song song PVD - DWT
│   ├── history_tab.py                  # Tab xem lịch sử
│   ├── batch_panel.py                  # Bảng điều khiển chạy bộ ảnh hàng loạt
│   ├── batch_chart.py                  # Biểu đồ kết quả bộ ảnh
│   ├── compare_chart.py                # Biểu đồ so sánh chất lượng nhúng
│   ├── dwt_view.py                     # Cửa sổ trực quan hóa 4 dải Wavelet
│   └── image_view.py                   # Cửa sổ phóng to xem ảnh và thanh trượt so sánh
├── experiments/                        # Thực nghiệm và kiểm thử độ bền (Robustness)
│   ├── attacks.py                      # 8 phép tấn công OpenCV (JPEG, Noise, Blur, Crop...)
│   ├── batch_runner.py                 # Động cơ chạy batch đa luồng có thể hủy
│   ├── benchmark_runner.py             # CLI runner cho benchmark
│   ├── experiment_config.py            # Cấu hình tham số chuẩn (Seed = 20260919)
│   ├── extraction.py                   # Đánh giá tỷ lệ khôi phục sau tấn công
│   └── robustness_runner.py            # Động cơ kiểm thử độ bền dòng lệnh
├── data/                               # Dữ liệu thử nghiệm
│   ├── selected_512/                   # 8 ảnh chuẩn USC-SIPI 512×512 (Splash, Baboon, Airplane...)
│   ├── demo/                           # 3 ảnh tổng hợp kiểm thử nhanh
│   └── history.json                    # Lịch sử thao tác của phần mềm
├── tests/                              # Bộ kiểm thử tự động (238 ca test)
├── audit_reports/                      # Báo cáo kỹ thuật và kiểm toán mã nguồn
├── main.py                             # Điểm khởi chạy chính của ứng dụng
├── requirements.txt                    # Khai báo các thư viện phụ thuộc
└── README.md                           # Tài liệu hướng dẫn sử dụng này
```

---

## 📊 KẾT QUẢ THỰC NGHIỆM TÓM TẮT

| Tiêu chí so sánh | PVD (Pixel Value Differencing) | DWT (Haar mức 1 + QIM $\Delta=18$) |
| :--- | :--- | :--- |
| **Miền giấu tin** | Không gian (Spatial Domain) | Tần số (Frequency Domain - Haar Wavelet) |
| **Dung lượng (Ảnh 512×512)** | **394.607 – 476.319 bit** (~49–59 KB) | **13.107 bit** (~1.6 KB) cố định |
| **Chất lượng ảnh (PSNR)** | **58.29 – 70.20 dB** (Rất cao) | **40.28 – 50.95 dB** (Tốt) |
| **Chất lượng cấu trúc (SSIM)**| **0.9998 – 0.9999** (Gần như tuyệt đối) | **0.9696 – 0.9973** (Rất cao) |
| **Nhiễu Gaussian ($\sigma=1.0$)**| 0% khôi phục | **85.71% khôi phục đúng** |
| **Nhiễu muối tiêu ($0.01$)** | 0% khôi phục | **100% khôi phục đúng** |
| **Độ sáng ($\Delta = \pm 10$)** | 71.43% – 85.71% khôi phục | **71.43% – 100% khôi phục đúng** |
| **Độ tương phản ($\alpha=0.9, 1.1$)**| 0% khôi phục | **57.14% – 71.43% khôi phục đúng** |
| **Nén JPEG / Làm mờ / Resize**| 0% khôi phục (Dễ vỡ) | 0% khôi phục (Cần cơ chế đồng bộ) |
