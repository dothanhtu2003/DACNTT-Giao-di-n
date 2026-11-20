# ĐỀ XUẤT CẤU TRÚC BẢN BÀN GIAO ĐỒ ÁN (SUBMISSION STRUCTURE)
**Dự án:** Nghiên cứu, cài đặt và đánh giá kỹ thuật giấu tin trong ảnh số PVD và DWT  
**Mục tiêu:** Định hình cấu trúc thư mục tối ưu, chuẩn mực công nghệ phần mềm và học thuật để nộp cho Trường Đại học Tôn Đức Thắng và Giảng viên hướng dẫn.

---

## 1. Phân biệt hai loại phiên bản

| Tiêu chí | Bản Repository Phát triển (Full Dev Repo) | Bản Đóng gói Bàn giao (Handover Bundle) |
| :--- | :--- | :--- |
| **Mục đích** | Lưu trữ toàn bộ lịch sử nghiên cứu, code nháp, script sinh báo cáo, kết quả test cũ. | Nộp chấm điểm cho Hội đồng / Giảng viên hướng dẫn; lưu trữ tại thư viện trường. |
| **Dung lượng** | ~245 MB (hơn 1.000 file) | **~8 MB** (tinh gọn, sạch sẽ) |
| **Thành phần** | Chứa cả `output/`, các folder `batch_results/`, file nháp `hihi_...`. | Chỉ chứa mã nguồn chuẩn, bộ ảnh mẫu, test suite và báo cáo chính thức. |

---

## 2. Cấu trúc thư mục tối ưu đề xuất cho Bản Bàn Giao

```text
DoAn_PVD_DWT_DoThanhTu_PhamDangKhoi/
│
├── core/                               # THUẬT TOÁN CỐT LÕI (Spatial & Frequency)
│   ├── __init__.py
│   ├── dwt.py                          # Biến đổi Haar Wavelet mức 1 + QIM (Delta 18, lặp 5)
│   ├── pvd.py                          # Pixel Value Differencing (Kênh Blue/Gray, 6 khoảng)
│   ├── payload.py                      # Đóng gói packet [LENGTH (uint32) || UTF-8]
│   ├── engine_utils.py                 # Kiểm tra ma trận uint8, dung lượng CapacityError
│   └── image_utils.py                  # Đọc ảnh PNG/BMP, lưu PNG lossless, thumbnail
│
├── metrics/                            # ĐO LƯỜNG VÀ ĐÁNH GIÁ CHẤT LƯỢNG
│   ├── __init__.py
│   └── metrics.py                      # PSNR, MSE, SSIM, BER, bpp, dung lượng
│
├── services/                           # TẦNG DỊCH VỤ VÀ ĐIỀU PHỐI (Services)
│   ├── __init__.py
│   ├── stego_service.py                # Điều phối Embed, Extract, Compare, Batch
│   └── robustness.py                   # Cấu hình và thẩm định tham số tấn công
│
├── storage/                            # LƯU TRỮ LỊCH SỬ DỮ LIỆU
│   ├── __init__.py
│   └── history_store.py                # Ghi nhận JSON nguyên tử (Atomic Write)
│
├── gui/                                # GIAO DIỆN NGƯỜI DÙNG DESKTOP (Tkinter/ttk)
│   ├── __init__.py
│   ├── main_window.py                  # Khung cửa sổ chính 4 tab, đa luồng nền
│   ├── embed_tab.py                    # Tab 1: Nhúng dữ liệu vào ảnh cover
│   ├── extract_tab.py                  # Tab 2: Trích xuất thông điệp từ ảnh stego
│   ├── compare_tab.py                  # Tab 3: So sánh PVD vs DWT (1 ảnh & Bộ ảnh)
│   ├── history_tab.py                  # Tab 4: Quản lý lịch sử thực hiện
│   ├── batch_panel.py                  # Bảng điều khiển chạy thử nghiệm hàng loạt
│   ├── batch_chart.py                  # Trực quan hóa kết quả phân phối dạng biểu đồ
│   ├── compare_chart.py                # Biểu đồ so sánh trực tiếp các chỉ số
│   ├── dwt_view.py                     # Cửa sổ trực quan hóa 4 dải LL, LH, HL, HH
│   ├── image_view.py                   # Cửa sổ xem ảnh phóng to, thanh trượt so sánh
│   └── common.py                       # Các widget dùng chung, định dạng nhãn
│
├── experiments/                        # MÔ-ĐUN THỰC NGHIỆM VÀ ĐÁNH GIÁ ĐỘ BỀN
│   ├── __init__.py
│   ├── attacks.py                      # 8 phép tấn công OpenCV (JPEG, Noise, Blur, Crop...)
│   ├── batch_runner.py                 # Bộ chạy thực nghiệm hàng loạt cho GUI
│   ├── benchmark_runner.py             # Script chạy benchmark qua dòng lệnh CLI
│   ├── experiment_config.py            # Cấu hình tham số chuẩn Chương 4 (Seed 20260919)
│   ├── extraction.py                   # Đánh giá tỷ lệ khôi phục và BER sau tấn công
│   ├── robustness_runner.py            # Runner dòng lệnh kiểm thử độ bền
│   └── summarize_results.py            # Tổng hợp thống kê kết quả ra bảng
│
├── data/                               # TẬP DỮ LIỆU MẪU
│   ├── selected_512/                   # 8 ảnh chuẩn USC-SIPI kích thước 512×512
│   │   ├── 4.2.01.png                  # Splash
│   │   ├── 4.2.03.png                  # Mandrill (Baboon)
│   │   ├── 4.2.05.png                  # Airplane (F-16)
│   │   ├── 4.2.06.png                  # Sailboat on lake
│   │   ├── 5.2.10.png                  # Stream and bridge (Ảnh xám)
│   │   ├── 7.1.02.png                  # Airplane (Ảnh xám)
│   │   ├── gray21.512.png              # 21 level step wedge (Ảnh xám)
│   │   └── ruler.512.png               # Pixel ruler (Ảnh xám)
│   ├── demo/                           # Ảnh tổng hợp dùng cho kiểm thử nhanh
│   │   ├── synthetic_gradient_rgb.png
│   │   ├── synthetic_texture_gray.bmp
│   │   └── synthetic_white_rgba.png
│   └── history.json                    # Khởi tạo mảng rỗng [] sạch sẽ
│
├── tests/                              # BỘ KIỂM THỬ TỰ ĐỘNG (238 test cases)
│   ├── __init__.py
│   ├── test_pvd.py
│   ├── test_dwt.py
│   ├── test_payload.py
│   ├── test_metrics.py
│   ├── test_image_utils.py
│   ├── test_service.py
│   ├── test_attacks.py
│   ├── test_robustness.py
│   ├── test_history.py
│   ├── test_integration.py
│   ├── test_batch.py
│   ├── test_experiments.py
│   ├── test_noise_observations.py
│   ├── test_compare_chart.py
│   ├── test_batch_chart.py
│   ├── test_batch_ui.py
│   ├── test_gui.py
│   └── fixtures/
│       └── legacy_quantitative.json
│
├── audit_reports/                      # BÁO CÁO RÀ SOÁT CHẤT LƯỢNG MÃ NGUỒN
│   ├── CODE_AUDIT.md
│   ├── UNUSED_CODE_REPORT.md
│   ├── DUPLICATE_CODE_REPORT.md
│   ├── FILE_CLEANUP_REPORT.md
│   ├── REPORT_CODE_CONSISTENCY.md
│   ├── TEST_AUDIT.md
│   └── SUBMISSION_STRUCTURE.md
│
├── BaoCao_DoAnCNTT_PVD_DWT.docx        # BÁO CÁO THUYẾT MINH CHÍNH THỨC HOÀN CHỈNH
├── main.py                             # Điểm khởi chạy chính: `python main.py`
├── requirements.txt                    # Danh sách thư viện phụ thuộc
├── .gitignore                          # Cấu hình bỏ qua cache và file tạm
└── README.md                           # Hướng dẫn cài đặt môi trường và vận hành demo
```

---

## 3. Các thành phần loại bỏ hoàn toàn khỏi bản bàn giao

1. **Thư mục `output/` (120 MB):** Toàn bộ file ảnh QA (`tables_qa/`), script can thiệp Word một lần, log lỗi trung gian.
2. **Các folder ảnh stego cũ trong `experiments/` (118 MB):** `results/`, `results_baseline_512/`, `batch_results/`.
3. **Các file Word nháp:** `hihi_chuong_4_bo_sung_hinh_DWT.docx`, `output/chapter4/hihi_*.docx`.
4. **Các thư mục cache hệ thống:** `__pycache__/`, `.pytest_cache/`.

---

## 4. Hướng dẫn đóng gói (Packaging Checklist)

Trước khi nén thư mục dự án thành file `.zip` để nộp:
- [ ] Chạy lệnh `python main.py` để bảo đảm ứng dụng khởi chạy bình thường.
- [ ] Reset nội dung file `data/history.json` về mảng rỗng `[]`.
- [ ] Đổi tên file báo cáo Word chính thức thành tên trang trọng, loại bỏ các ký hiệu tải về như `(2) (1)`.
- [ ] Chạy lệnh dọn cache: `Get-ChildItem -Path . -Include __pycache__,.pytest_cache -Recurse -Force | Remove-Item -Recurse -Force` (trên PowerShell).
- [ ] Tạo file nén `DoAn_PVD_DWT_DoThanhTu_PhamDangKhoi.zip` và kiểm tra dung lượng (đạt mức ~8 MB là chuẩn).
