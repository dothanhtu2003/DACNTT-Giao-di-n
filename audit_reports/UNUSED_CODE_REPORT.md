# BÁO CÁO DANH SÁCH CODE VÀ MODULE KHÔNG SỬ DỤNG (UNUSED CODE REPORT)
**Dự án:** Nghiên cứu, cài đặt và đánh giá kỹ thuật giấu tin trong ảnh số PVD và DWT  
**Phạm vi:** Rà soát AST và Call-graph toàn bộ mã nguồn Python.

---

## 1. Import không sử dụng (ĐÃ XỬ LÝ)

Qua phân tích cây cú pháp trừu tượng (AST) trên toàn bộ các tệp Python nghiệp vụ, phát hiện 3 trường hợp import dư thừa và **đã được loại bỏ an toàn**:

### Vị trí: `experiments/robustness_runner.py`
1. **Dòng 12:** `import numpy as np` -> **Đã xóa**.
2. **Dòng 15:** `decode_message` trong `from core.payload import ...` -> **Đã xóa**.
3. **Dòng 19:** `ber` trong `from metrics.metrics import ...` -> **Đã xóa**.

*Kiểm chứng sau xử lý:* Chạy lại toàn bộ 238 ca kiểm thử pytest, tất cả 238 ca test đều PASS 100%, xác nhận không có module nào bị phụ thuộc ngầm vào các import này.

---

## 2. Hàm và Logic ít được sử dụng hoặc có tính chất dự phòng (Potentially Dead/Redundant Logic)

### 2.1. Logic `capacity_fraction` trong `experiments/robustness_runner.py`
- **Vị trí:** `experiments/robustness_runner.py:42-47`
  ```python
  if level['kind'] == 'capacity_fraction':
      fraction = level['value']
      if not 0 < fraction <= 1:
          raise ValueError('Capacity fraction phải thuộc (0,1].')
      return max(0, (int(capacity * fraction) - 32) // 8)
  ```
- **Bằng chứng:** Trong `experiments/experiment_config.py:6` và `experiments/batch_runner.py:51-55`, cấu hình chuẩn của đề tài đã cố định:
  ```python
  PAYLOAD_LEVELS = [{'kind': 'bytes', 'value': 8}, {'kind': 'bytes', 'value': 32}]
  # và trên GUI: 128, 512, 1024, 1500 bytes (tất cả đều là kind == 'bytes')
  ```
  Nhánh `capacity_fraction` chỉ được gọi trong một ca kiểm thử đơn vị tại `tests/test_experiments.py`, không bao giờ được kích hoạt trong luồng thực tế của ứng dụng hay bộ dữ liệu Chương 4.

### 2.2. Lệnh in gỡ lỗi (Debug Prints)
- **Vị trí:** `experiments/benchmark_runner.py:58, 62`
  ```python
  print(f'{len(rows)} rows saved: {args.output / "robustness_results.csv"}')
  ...
  print(f'Summary: {args.summary}')
  ```
- **Bằng chứng:** Đây là hai lệnh print duy nhất còn sót lại trong toàn bộ mã nguồn của dự án (ngoài thư mục `output/`). Mặc dù file này là một CLI script, nhưng việc in ra console chuẩn nên được chuyển sang logging nếu muốn chuyên nghiệp hóa.

---

## 3. Các Script Python phụ trợ không thuộc hệ thống vận hành (Non-Operational Utility Scripts)

Trong thư mục `output/chapter4/` có 8 file Python được nhóm tác giả viết nhằm tự động hóa việc đưa dữ liệu vào tài liệu Microsoft Word:

| Đường dẫn tệp | Kích thước | Mục đích thực tế | Bằng chứng không thuộc runtime app |
| :--- | :---: | :--- | :--- |
| `output/chapter4/capture_steps.py` | 1.0 KB | Tự động hóa chụp màn hình ứng dụng | Chạy độc lập qua command line |
| `output/chapter4/run_capture.py` | 4.0 KB | Script khởi chạy giao diện để chụp ảnh màn hình | Chạy độc lập |
| `output/chapter4/diagnose_baselines.py` | 2.1 KB | Chuẩn đoán 5 ca lỗi baseline của DWT | Đọc kết quả JSON, phân tích nguyên nhân |
| `output/chapter4/fill_tables.py` | 8.0 KB | Đọc CSV/JSON và chèn bảng số liệu vào file Word | Dùng `zipfile` can thiệp `word/document.xml` |
| `output/chapter4/insert_images.py` | 3.2 KB | Chèn các ảnh chụp màn hình vào file Word | Dùng `zipfile` can thiệp Word |
| `output/chapter4/revise_chapter4.py` | 20.1 KB | Biên tập, thay thế nội dung chương 4 trong Word | Script tự động hóa văn bản Word |
| `output/chapter4/dwt_addition/capture_dwt.py` | 0.9 KB | Chụp màn hình cửa sổ phân rã DWT | Script hỗ trợ chụp ảnh minh họa |
| `output/chapter4/dwt_addition/edit_doc.py` | 4.2 KB | Chèn hình DWT vào file Word bổ sung | Script tự động hóa văn bản Word |

**Đánh giá:** Cả 8 file script này **hoàn toàn không được import hoặc sử dụng bởi `main.py`, `services`, `core` hay `gui`**. Chúng là các công cụ một lần (one-off automation scripts) phục vụ việc làm báo cáo tốt nghiệp. Không nên để các file này lẫn lộn với mã nguồn chính khi nộp cho nhà trường.

---

## 4. Xác minh các hàm GUI và Callbacks (Không phải Dead Code)

Qua phân tích động và tĩnh, một số hàm trong GUI trông có vẻ như không được gọi bằng cú pháp `func()`, nhưng đã được xác minh là **đang hoạt động** thông qua cơ chế Callback và Event Binding của Tkinter:

1. `fit_layout`, `resize_columns` (`gui/batch_panel.py:307, 334`): Được đăng ký qua sự kiện `<Configure>`.
2. `choose_source`, `choose_destination`, `open_output` (`gui/batch_panel.py:414, 420, 593`): Được gán vào thuộc tính `command=...` của các nút bấm Tkinter (`ttk.Button`).
3. `poll` (`gui/main_window.py:89`, `gui/batch_panel.py:490`): Hàm đệ quy qua `self.after(60, poll)` để theo dõi trạng thái tác vụ nền bất đồng bộ.
4. `scroll_wheel` (`gui/compare_tab.py:116`): Được liên kết với sự kiện lăn chuột `<MouseWheel>`.
5. Các hàm tấn công trong `experiments/attacks.py` (`jpeg_compression`, `gaussian_noise`, v.v.): Được triệu gọi gián tiếp thông qua bảng ánh xạ `ATTACKS = {...}` trong `apply_attack`.
