# Quy trình thực nghiệm PVD và DWT

## Phạm vi

Thực nghiệm nằm trong `experiments/`, độc lập với `tests/`, không thêm tab GUI.
Các mức attack tại `experiments/experiment_config.py` là **mức thăm dò, chưa chốt cho Chương 4**.
Không thay đổi các thông số thuật toán đã khóa trong tài liệu yêu cầu.

## Tập ảnh demo

Ba ảnh tổng hợp 256 × 256 được sinh tại `data/demo/`:

| File | Loại | Cách sinh / mục đích |
|---|---|---|
| synthetic_gradient_rgb.png | RGB | Gradient và hình sin, vùng tương đối trơn |
| synthetic_texture_gray.bmp | Grayscale | Texture ngẫu nhiên uint8 [24,231], seed 20260919 |
| synthetic_white_rgba.png | RGBA | Các kênh bằng 255, trường hợp bão hòa và alpha |

Không có ảnh tự nhiên trong bộ demo. Đây là dữ liệu kiểm chứng pipeline và giới hạn, không đại diện cho hiệu quả trên tập ảnh nghiên cứu.
Hàm tạo demo giữ nguyên file đã tồn tại; snapshot lưu SHA-256/kích thước để xác định ảnh thật sự được chạy.
Input PNG/BMP uint8; Stego được lưu PNG rồi đọc lại trước attack. JPEG chỉ xuất hiện trong phép encode/decode tác động, không phải output Stego chuẩn.

## Thuật toán

**PVD:** Blue cho RGB/RGBA, intensity cho grayscale; raster trái → phải, trên → dưới; cặp ngang không chồng lấp; width lẻ bỏ pixel cuối hàng. Các khoảng `[0,7], [8,15], [16,31], [32,63], [64,127], [128,255]` mang `3,3,4,5,6,7` bit. Nếu vượt biên, dịch đồng thời hai pixel để giữ chênh lệch, không clip độc lập.

**DWT:** Y=0.299R+0.587G+0.114B hoặc intensity; Haar level 1, extension `symmetric`, nhúng HH. Tái tạo RGB bằng cách cộng thay đổi Y vào R/G/B, tương đương giữ Cb/Cr trước round/clip; alpha giữ nguyên.

```text
Q_b(c) = 18 * round((c - b*9)/18) + b*9
```

Round dùng `numpy.rint` (ties-to-even). Mỗi logical bit lặp 5 lần trên HH raster. Khoảng cách hai lattice bằng nhau chọn 0. Majority vote: >=3 phiếu 1 cho bit 1.
Logical capacity = floor(number_HH_coefficients/5). IDWT cắt về kích thước gốc, round, clip [0,255], uint8.
Ảnh chiều lẻ có thêm hệ số biên do symmetric extension. Capacity theo số hệ số không bảo đảm khôi phục được mọi packet sau tái tạo. Ảnh bão hòa có thể thất bại; không đổi thuật toán để che giới hạn.

## Packet và payload levels

```text
LENGTH (unsigned uint32 big-endian, số byte) || PAYLOAD (UTF-8)
packet_bits = 32 + 8 * payload_bytes
bpp = packet_bits / (width * height)
usage_percent = packet_bits / capacity_bits * 100
```

bpp bao gồm LENGTH, không nhân số kênh hoặc repetition của DWT. Văn bản rỗng hợp lệ, packet vẫn 32 bit. Thiếu capacity bị từ chối trước nhúng.
Mặc định dùng **8 bytes và 32 bytes** cho cả hai methods, payload ASCII xác định do `public_payload` tạo; nội dung không ghi vào CSV/snapshot/history.
Runner hỗ trợ `capacity_fraction`: `payload_bytes = max(0, floor((floor(capacity*fraction)-32)/8))`. Khi đó số byte giữa hai methods có thể khác; không diễn giải như cùng payload. CSV ghi kind/value và payload thực tế.

## Ma trận tác động

| Attack | Mức | Chính sách |
|---|---|---|
| none | Không tham số | Baseline PNG đã đọc lại |
| jpeg | quality 90, 70 | OpenCV imencode/imdecode, RGB ↔ BGR |
| gaussian_noise | sigma 1.0, 3.0 | Nhiễu độc lập theo phần tử, round/clip |
| salt_pepper | amount 0.001, 0.01 | Xác suất mỗi pixel, nửa đen/nửa trắng, cùng mask các kênh |
| blur | kernel_size 3, 5 | OpenCV GaussianBlur, sigma=0 tự suy ra, border REFLECT_101 |
| brightness | delta -10, +10 | Cộng delta, round/clip |
| contrast | alpha 0.9, 1.1 | `(pixel-127.5)*alpha+127.5`, round/clip |
| resize | scale 0.75, 1.25 | INTER_AREA khi giảm, INTER_LINEAR khi tăng, giữ kích thước mới |
| crop | fraction 0.9, 0.75 | Crop giữa, fraction trên mỗi chiều, không padding/resize |

Các tác động quang học giữ alpha; JPEG encode RGB rồi gắn lại alpha gốc (không hàm ý JPEG lưu alpha). Resize/crop biến đổi hình học cả alpha.
Crop fraction=0.9 giữ khoảng 81% diện tích. Resize/crop không có bước đăng ký hình học hoặc tái đồng bộ.

## Tái lập

Seed gốc **20260919**. Seed từng ca là 32-bit từ SHA-256 của seed gốc, hash ảnh, payload bytes, attack và JSON tham số. Seed không phụ thuộc method: cùng ảnh/payload/attack nhận cùng hiện thực nhiễu.
CSV lưu seed ca; snapshot lưu levels, cấu hình, hash ảnh, run ID, phiên bản Python/thư viện/hệ điều hành. Run ID và tên PNG thay đổi giữa các lần chạy; số đo được kiểm thử tái lập trong cùng môi trường.
Mỗi mức chỉ có một hiện thực nhiễu; cần nhiều seed độc lập trước khi suy luận thống kê.

## Metrics và extraction failure

- PSNR/MSE/SSIM đo cover với PNG trước attack. RGBA chỉ đo RGB, alpha kiểm tra riêng.
- `PSNR = 10*log10(255²/MSE)`; MSE=0 cho infinity.
- SSIM: scikit-image, data_range=255, channel_axis=-1 cho màu, cửa sổ lẻ tối đa 7. Chiều nhỏ hơn 3 cho SSIM=NA.
- BER trên toàn logical packet gồm LENGTH. Chỉ tính khi đọc đủ packet và header LENGTH khớp gốc.
- LENGTH sai/thiếu bit/mất đồng bộ: BER trống trong CSV, NA trong báo cáo; không tự gán 1.
- Header khớp nhưng UTF-8 lỗi: BER vẫn có cơ sở trên hai dãy bằng độ dài; success=False, error_type=UTF8Error.
- Success chỉ khi toàn packet khớp và UTF-8 hợp lệ; packet khác nhưng decode được vẫn thất bại.
- Baseline thất bại được giữ trong dữ liệu. Không loại ảnh khó sau khi thấy kết quả.
- Packet không có magic/checksum: trích xuất độc lập không xác thực được nguồn gốc chỉ từ LENGTH/UTF-8. Nhúng/so sánh có packet gốc để kiểm tra integrity.

## Chạy và lưu kết quả

```powershell
python -m experiments.benchmark_runner --demo --summary EXPERIMENT_RESULTS_SUMMARY.md
python -m experiments.benchmark_runner --images data/my_covers --output experiments/results_study --seed 20260919 --payload-bytes 8 32
python -m experiments.summarize_results experiments/results_study/robustness_results.csv experiments/results_study/summary.md
```

Demo: 3 ảnh × 2 methods × 2 payload levels × 17 cấu hình attack/baseline = **204 dòng**, gồm **12 baseline**.
CSV/snapshot cùng output directory được cập nhật bởi lần chạy mới; PNG có run ID riêng. Dùng output directory khác cho các thí nghiệm cần giữ riêng.

## Tài liệu API

- [PyWavelets dwt2/idwt2](https://pywavelets.readthedocs.io/en/latest/ref/2d-dwt-and-idwt.html): GUI quy ước LL=cA, LH=cH, HL=cV, HH=cD.
- [scikit-image structural_similarity](https://scikit-image.org/docs/stable/api/skimage.metrics.html#skimage.metrics.structural_similarity): data_range, channel_axis, win_size.
