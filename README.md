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
3. **So sánh PVD – DWT:** cùng ảnh/message; capacity, payload, packet bits, usage, bpp, PSNR, SSIM, BER kiểm tra nhúng, extract status; hai nhánh độc lập, hỗ trợ partial, lưu từng PNG trước tác động. Phần **Thử nghiệm độ bền** nằm trong tab này.
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

### Thử độ bền trong tab So sánh

Chọn ảnh PNG/BMP và nhập thông điệp, bấm **Chạy so sánh**, sau đó cuộn xuống phần **Thử nghiệm độ bền**. Chọn tác động, nhập tham số đang hiển thị và bấm **Thử độ bền**. Mỗi lần thử độc lập từ ảnh Stego trước tác động đã kiểm tra thành công. Nếu một phương pháp nhúng thất bại, phương pháp còn lại vẫn được thử; phương pháp thất bại ghi “Không thử được — nhúng thất bại”. Nút thử bị khóa khi chưa có kết quả hợp lệ hoặc có tác vụ đang chạy.

Giá trị tham số mặc định là mức đầu tiên của từng tác động trong `experiments/experiment_config.py`. Chỉ Gaussian và muối tiêu dùng seed; mặc định là `SEED` trong cùng cấu hình, có thể nhập số nguyên không âm. Seed được kiểm tra bằng NumPy `SeedSequence`, không áp trần 32 bit. Hai phương pháp nhận cùng seed thực tế; các tác động khác ghi seed `null` trong lịch sử. Benchmark vẫn sinh seed cho từng trường hợp bằng cách hiện có; muốn đối chiếu GUI với một dòng CSV phải nhập **seed thực tế của dòng đó**, cùng ảnh, payload và tham số.

Tham số thực phải hữu hạn, không nhận NaN/vô cực. Miền tham số theo `attacks.py`, với hai **giới hạn riêng của GUI/dịch vụ tương tác**: kernel là số nguyên lẻ từ **1 đến 51**, scale **0 < scale ≤ 4** để hạn chế kích thước tác vụ. Những giới hạn này không áp dụng cho chương trình benchmark. JPEG quality là số nguyên 1–100; sigma ≥ 0; amount trong [0,1]; delta hữu hạn; alpha ≥ 0; fraction trong (0,1]. Tham số sai được báo trước khi gửi tác vụ nền.

Ảnh sau tác động, kích thước, cấu hình, seed, BER và trạng thái khớp toàn bộ packet được hiển thị riêng cho PVD/DWT. PSNR/SSIM và biểu đồ so sánh thuộc **trước tác động**. Đánh giá dùng nguyên `assess_extraction()` với `engine.extract()`: chỉ tính BER khi độ dài dãy bit và 32 bit LENGTH khớp packet gốc; LENGTH sai hoặc thiếu dữ liệu hiển thị **Không xác định**, không thay bằng 0 hoặc 1. UTF-8 hợp lệ không chứng minh khớp packet; nếu UTF-8 lỗi sau khi tính BER thì giữ BER và báo thất bại. Nội dung thông điệp không hiển thị trong kết quả độ bền.

Resize giữ kích thước đã đổi; crop cắt giữa và giữ phần ảnh còn lại. Không phục hồi kích thước hoặc căn chỉnh, nên thuật toán có thể mất đồng bộ. Tác động quang học, kể cả JPEG encode/decode trong bộ nhớ, giữ alpha gốc; resize/crop biến đổi alpha cùng ảnh. Chỉ có chức năng lưu Stego **trước** tác động.

Đổi ảnh/thông điệp xóa kết quả nhúng và độ bền; chạy lại so sánh cũng vô hiệu hóa kết quả cũ ngay. Đổi tác động/tham số/seed chỉ xóa kết quả độ bền, giữ Stego để thử lại. Token phiên bản loại bỏ kết quả cũ ngay cả khi đổi lựa chọn rồi đổi lại. Worker chỉ dùng bản chụp dữ liệu/cấu hình, không truy cập Tkinter.

Mỗi phương pháp thực sự được thử ghi một metadata với `operation=robustness`, tên tác động, `attack_parameters` JSON chuẩn hóa, seed hoặc null, BER, trạng thái, kích thước và lỗi nếu có. Không ghi thông điệp, packet gốc, byte payload hoặc mảng ảnh. Packet đối chiếu chỉ ở bộ nhớ. Bản ghi cũ thiếu trường mới vẫn đọc được; tab Lịch sử ghi nhãn **Thử độ bền**, cấu hình xem qua **Xem chi tiết**. Tác vụ hoàn tất cho cấu hình cũ vẫn ghi lịch sử của bản chụp đó, nhưng không hiển thị như kết quả lựa chọn mới. Lỗi ghi lịch sử không xóa kết quả và được hiển thị thành cảnh báo.

### Chạy hàng loạt bằng lệnh

`experiments/` tiếp tục hỗ trợ CLI; GUI chỉ tái sử dụng hàm áp dụng tác động và đánh giá packet, không chạy ma trận benchmark. OpenCV thực sự dùng cho JPEG encode/decode, Gaussian blur và resize; NumPy hỗ trợ noise và biến đổi cường độ.
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
services/stego_service.py, services/robustness.py
metrics/metrics.py
storage/history_store.py
experiments/
  experiment_config.py, attacks.py, extraction.py, robustness_runner.py
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
