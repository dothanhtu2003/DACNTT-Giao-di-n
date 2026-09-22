# Hệ thống giấu tin trong ảnh số PVD & DWT

Ứng dụng desktop Python phục vụ đề tài **Nghiên cứu, cài đặt và đánh giá kỹ thuật giấu tin trong ảnh số PVD và DWT**.
GUI dùng tkinter + ttk, đúng 4 tab; hai thuật toán độc lập, không hybrid, AES/RSA, tài khoản, cloud hoặc database.

## Cài đặt và chạy

Đã kiểm thử trên Windows, Python 3.12.10, Tk 8.6. Cần Python có Tkinter.
Từ thư mục dự án:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

Nếu Python hiện tại đã cài dependencies:

```powershell
python main.py
```

## Bốn tab

1. **Nhúng dữ liệu:** chọn PNG/BMP, chọn PVD/DWT, nhập UTF-8, kiểm tra dung lượng, nhúng, xem metrics, lưu PNG. Tự trích xuất lại để xác nhận packet khớp trước khi cho lưu.
2. **Trích xuất dữ liệu:** chọn ảnh và đúng method, xem message chỉ đọc, Copy; báo lỗi LENGTH/UTF-8.
3. **So sánh PVD – DWT:** cùng ảnh/message; capacity, payload, packet bits, usage, bpp, PSNR, SSIM, BER, extract status; hai nhánh độc lập, hỗ trợ partial, lưu từng PNG.
4. **Lịch sử:** metadata local, refresh, xem chi tiết, xóa bản ghi hoặc xóa tất cả có xác nhận.

Message rỗng hợp lệ, cần packet 32 bit. History **không lưu secret message, extracted message hoặc raw payload**; `data/history.json` hỏng/trống được khôi phục thành danh sách rỗng. Nội dung trích xuất chỉ ở bộ nhớ GUI, trừ khi người dùng chủ động Copy.

## Cấu hình đã khóa

| Thành phần | Cấu hình |
|---|---|
| PVD | Blue cho RGB/RGBA; intensity cho grayscale; raster; cặp ngang không chồng lấp; width lẻ bỏ pixel cuối |
| PVD ranges | [0,7], [8,15], [16,31], [32,63], [64,127], [128,255] → 3/3/4/5/6/7 bit |
| DWT | Y/intensity, Haar, level 1, HH, QIM Delta=18, repeat=5, majority vote 3/5 |
| Packet | LENGTH unsigned 32-bit big-endian (số byte UTF-8) + PAYLOAD |
| Packet bits | `32 + 8 * payload_bytes` |
| bpp | `packet_bits / (width * height)`; bao gồm LENGTH, không nhân channel/repetition |
| Ảnh | Input PNG/BMP uint8, output Stego chỉ PNG lossless |

**JPEG chỉ là attack trong robustness, không phải Stego output chuẩn và không nhận làm input nhúng trong GUI.**
DWT dùng Y=0.299R+0.587G+0.114B, giữ các thành phần màu còn lại trước round/clip, alpha không đổi.
Nút **Xem cấu hình** chỉ đọc. Với DWT, **Xem phân rã DWT** mở cửa sổ LL/LH/HL/HH, đánh dấu HH. Normalization từng dải chỉ để hiển thị.

PSNR/SSIM đo cover so với Stego; RGBA chỉ đo RGB. MSE=0 cho PSNR infinity. BER chỉ tính trên packet đã xác lập đồng bộ.

## Kiểm thử phần mềm

```powershell
python -m pytest -q -W error
python -m compileall -q main.py core gui services metrics storage experiments tests
```

Tests bao gồm engines, payload, metrics, utilities, service, privacy/history, GUI và experiments. GUI tests cần desktop/Tk display; skip nếu không có display. File dialogs trong tests được thay bằng đường dẫn fixture, widget và worker thật vẫn chạy.
Xem [TEST_REPORT.md](TEST_REPORT.md).

## Robustness và benchmark

`experiments/` tách khỏi unit tests, không thêm tab GUI. OpenCV thực sự dùng cho JPEG encode/decode, Gaussian blur và resize; NumPy hỗ trợ noise và biến đổi cường độ.
Đủ baseline none, JPEG, Gaussian noise, Salt & Pepper, blur, brightness, contrast, resize, crop.

```powershell
python -m experiments.benchmark_runner --demo --summary EXPERIMENT_RESULTS_SUMMARY.md
python -m experiments.benchmark_runner --images data/my_covers --output experiments/results_study --payload-bytes 8 32 --seed 20260919
python -m experiments.summarize_results experiments/results_study/robustness_results.csv experiments/results_study/summary.md
```

Levels tập trung trong `experiments/experiment_config.py`. Mặc định 8/32 payload bytes; còn hỗ trợ capacity_fraction qua cấu hình Python.
CSV ghi parameter, seed, payload thực tế và error type; snapshot lưu cấu hình, hash ảnh, môi trường. Không ghi nội dung payload vào CSV.

Kết quả đã chạy:

- `experiments/results/robustness_results.csv`: 204 trường hợp demo.
- `experiments/results/experiment_config_snapshot.json`: cấu hình lần chạy.
- `experiments/results/stego/`: PNG trước attack, có run ID.
- [EXPERIMENT_PROTOCOL.md](EXPERIMENT_PROTOCOL.md): định nghĩa phép đo và chính sách attack.
- [EXPERIMENT_RESULTS_SUMMARY.md](EXPERIMENT_RESULTS_SUMMARY.md): bảng sinh từ CSV.

Cùng output directory sẽ cập nhật CSV/snapshot. Chọn thư mục output khác để giữ riêng các lần nghiên cứu.

## Giới hạn đã xác nhận

- DWT theo cấu hình đã khóa có thể mất bit sau tái tạo/clip trên ảnh bão hòa hoặc biên ảnh lẻ. Service kiểm tra packet, báo thất bại và chặn lưu kết quả đó như nhúng thành công; không tự đổi thuật toán.
- Baseline demo: **10/12** ca khớp; 2 ca DWT trên ảnh trắng RGBA thất bại. Kết quả này khác với pass/fail của tests kiểm tra cách code xử lý giới hạn.
- Packet không có magic/checksum: không thể chứng minh ảnh đã nhúng chỉ từ LENGTH/UTF-8. Ảnh đồng nhất có thể được đọc thành message rỗng. Nhúng/so sánh có packet gốc kiểm tra integrity, trích xuất độc lập thì không.
- Bộ demo chỉ 3 ảnh tổng hợp, một seed mỗi mức nhiễu; levels chưa chốt Chương 4. Cần tập ảnh thật và nhiều lần lặp trước khi kết luận tổng quát.

## Cấu trúc dự án

```text
main.py
core/
  payload.py, engine_utils.py, pvd.py, dwt.py, image_utils.py
gui/
  main_window.py, common.py, embed_tab.py, extract_tab.py
  compare_tab.py, history_tab.py, dwt_view.py
services/stego_service.py
metrics/metrics.py
storage/history_store.py
experiments/
  experiment_config.py, attacks.py, robustness_runner.py
  benchmark_runner.py, summarize_results.py
  results/
    robustness_results.csv, experiment_config_snapshot.json, stego/
tests/
  test_payload.py, test_pvd.py, test_dwt.py, test_image_utils.py
  test_metrics.py, test_history.py, test_service.py, test_integration.py
  test_gui.py, test_attacks.py, test_experiments.py
  artifacts/
data/
  history.json
  demo/
requirements.txt
TEST_REPORT.md
EXPERIMENT_PROTOCOL.md
EXPERIMENT_RESULTS_SUMMARY.md
```

Các package có `__init__.py`.
