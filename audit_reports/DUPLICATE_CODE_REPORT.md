# BÁO CÁO MÃ TRÙNG LẶP VÀ ĐỀ XUẤT HỢP NHẤT (DUPLICATE CODE REPORT)
**Dự án:** Nghiên cứu, cài đặt và đánh giá kỹ thuật giấu tin trong ảnh số PVD và DWT  
**Phạm vi:** Phân tích trùng lặp logic (DRY principle) giữa các tầng `experiments/`, `services/`, `core/`.

---

## 1. Trùng lặp lớn nhất: Hai động cơ chạy thực nghiệm hàng loạt

### Vị trí:
1. `experiments/robustness_runner.py` (Hàm `run_experiments`, dòng 51–122)
2. `experiments/batch_runner.py` (Hàm `run_batch`, dòng 127–248)

### Bằng chứng kỹ thuật:
Cả hai hàm đều giải quyết cùng một bài toán: **Tích Descartes giữa (Danh sách ảnh) × (Phương pháp PVD, DWT) × (Các mức Payload) × (Các phép tấn công Robustness)**.

So sánh chi tiết logic:
- Cả hai đều đọc ảnh qua `load_image`, tính băm `hashlib.sha256()`.
- Cả hai đều lấy capacity qua `engine.calculate_capacity()`.
- Cả hai đều sinh chuỗi payload thông qua `public_payload()`.
- Cả hai đều nhúng bằng `engine.embed()`, lưu file ảnh stego tạm, tính PSNR và SSIM trước tấn công.
- Cả hai đều lặp qua danh sách tấn công trong `config['attacks']`, gọi `apply_attack()`, sau đó gọi `assess_extraction()` để tính BER và tỷ lệ thành công.

### Điểm khác biệt:
- `robustness_runner.py` là phiên bản đồng bộ cũ (legacy), chạy thẳng từ đầu đến cuối không thể hủy, xuất ra duy nhất file `robustness_results.csv` và `experiment_config_snapshot.json`.
- `batch_runner.py` là phiên bản nâng cấp hoàn thiện hơn: hỗ trợ callback hủy tác vụ (`cancel()`), callback tiến độ (`progress()`), xuất dữ liệu chi tiết thành 3 file CSV riêng biệt (`cases.csv`, `summary.csv`, `baselines.csv`) và file `config.json`.

### Đề xuất giải pháp (Refactoring Proposal):
- **Ngắn hạn (Trước nộp bài):** Giữ nguyên cả hai để không làm hỏng CLI benchmark hoặc các ca kiểm thử trong `tests/test_experiments.py`.
- **Dài hạn:** Hợp nhất `robustness_runner.py` vào `batch_runner.py`. CLI script `benchmark_runner.py` nên chuyển sang gọi trực tiếp `batch_runner.run_batch()` ở chế độ headless (không cần GUI).

---

## 2. Trùng lặp kiểm tra tính hợp lệ của tham số tấn công

### Vị trí:
1. `services/robustness.py` (Hàm `validate_configuration`, dòng 31–70)
2. `experiments/batch_runner.py` (Hàm `batch_config`, dòng 60–108)

### Bằng chứng kỹ thuật:
Cả hai module đều lặp qua các tham số của từng phép tấn công và kiểm tra miền giá trị hợp lệ:
- Kiểm tra `quality` trong khoảng [1, 100].
- Kiểm tra `kernel_size` là số lẻ trong khoảng [1, 51].
- Kiểm tra `amount` trong khoảng [0, 1].
- Kiểm tra `scale` trong khoảng (0, 4].
- Kiểm tra `fraction` trong khoảng (0, 1].
- Kiểm tra Seed có phải số nguyên không âm hợp lệ với `np.random.SeedSequence`.

### Đề xuất giải pháp:
- Logic kiểm tra này thuộc về tầng domain logic của các phép biến đổi ảnh. Nên chuyển toàn bộ hàm `validate_configuration` về `experiments/experiment_config.py` làm một Single Source of Truth (SSOT). Cả `services/robustness.py` và `experiments/batch_runner.py` chỉ cần import và gọi hàm này thay vì viết lại các đoạn if/else kiểm tra tương đương.

---

## 3. Trùng lặp mô hình xử lý ngoại lệ trong `services/stego_service.py`

### Vị trí:
- `services/stego_service.py:96` (Hàm `embed`):
  ```python
  except (OSError, ValueError, TypeError, OverflowError) as exc:
      result.update(error=str(exc), error_type=type(exc).__name__)
  ```
- `services/stego_service.py:113` (Hàm `extract`):
  ```python
  except (OSError, ValueError, TypeError, OverflowError) as exc:
      result.update(error=str(exc), error_type=type(exc).__name__, status='extraction_failed', ...)
  ```

### Bằng chứng kỹ thuật:
Tuple 4 ngoại lệ `(OSError, ValueError, TypeError, OverflowError)` được lặp lại nhiều lần trong file để chuẩn hóa cấu trúc lỗi trả về cho GUI.

### Đề xuất giải pháp:
- Có thể tạo một decorator `@handle_stego_exceptions` hoặc hàm helper `_format_error(exc)` trong `stego_service.py` để quy chuẩn hóa việc bắt lỗi và ghi nhận `error_type`, giúp code ngắn gọn và dễ bảo trì hơn.

---

## 4. Tóm tắt đánh giá

Mức độ trùng lặp mã nguồn trong dự án ở mức **Thấp đến Trung bình** (chủ yếu tập trung ở phân hệ thực nghiệm giữa công cụ dòng lệnh cũ và công cụ GUI mới). Lớp thuật toán cốt lõi (`core/`) hoàn toàn không có sự trùng lặp code và tuân thủ rất tốt nguyên tắc phân tách trách nhiệm.
