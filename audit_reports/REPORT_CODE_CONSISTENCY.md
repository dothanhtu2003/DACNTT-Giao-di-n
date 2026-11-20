# BÁO CÁO ĐỐI CHIẾU MÃ NGUỒN VÀ THUYẾT MINH BÁO CÁO (REPORT - CODE CONSISTENCY)
**Dự án:** Nghiên cứu, cài đặt và đánh giá kỹ thuật giấu tin trong ảnh số PVD và DWT  
**Mục tiêu:** Kiểm tra sự nhất quán giữa các phương trình, bảng biểu, tham số mô tả trong Báo cáo đồ án với mã nguồn Python thực tế.

---

## 1. Đối chiếu thuật toán PVD (Pixel Value Differencing)

| Nội dung đối chiếu | Mô tả trong Báo cáo (Mục 2.3 & 3.3) | Cài đặt trong Code thực tế | Đánh giá |
| :--- | :--- | :--- | :---: |
| **Quy tắc chia cặp pixel** | Cặp điểm ảnh liên tiếp không chồng lấp theo hàng ngang; bỏ điểm ảnh cuối nếu chiều rộng lẻ. | `core/pvd.py:12-16` (`_pairs`): `width = channel.shape[1] // 2 * 2; channel[:, :width].reshape(-1, 2)`. | **Khớp 100%** |
| **Kênh ảnh sử dụng** | Ảnh xám: ma trận cường độ; Ảnh RGB: chỉ nhúng trên kênh **Blue (B)**; Red và Green giữ nguyên. | `core/pvd.py:14`: `channel = image if image.ndim == 2 else image[:, :, 2]`. Kênh chỉ số 2 trong RGB là Blue. | **Khớp 100%** |
| **Bảng phân dải chênh lệch** | 6 khoảng: $[0,7], [8,15], [16,31], [32,63], [64,127], [128,255]$ tương ứng với số bit nhúng: $3, 3, 4, 5, 6, 7$ bit. | `core/pvd.py:8-9`: `LOWER = [0, 8, 16, 32, 64, 128]`, `BITS = [3, 3, 4, 5, 6, 7]`. | **Khớp 100%** |
| **Xử lý tràn biên (Boundary clipping)** | Phân phối độ chênh lệch mới cho cả hai điểm ảnh và hiệu chỉnh để không vượt ngoài $[0, 255]$. | `core/pvd.py:49-52`: Dùng công thức trung bình làm tròn và tính bù `shift = max(0, -min) - max(0, max - 255)`. | **Khớp 100%** |

---

## 2. Đối chiếu thuật toán DWT (Discrete Wavelet Transform + QIM)

| Nội dung đối chiếu | Mô tả trong Báo cáo (Mục 2.4 & 3.4) | Cài đặt trong Code thực tế | Đánh giá |
| :--- | :--- | :--- | :---: |
| **Loại Wavelet & Mức** | Biến đổi Wavelet **Haar mức 1** hai chiều. | `core/dwt.py:15`: `WAVELET = 'haar'`, `pywt.dwt2(..., WAVELET, mode='symmetric')`. | **Khớp 100%** |
| **Kênh xử lý màu** | Chuyển ảnh màu sang kênh độ sáng **$Y$** theo chuẩn ITU-R BT.601; sau đó tái tạo ngược. | `core/dwt.py:24`: `rgb @ np.array([0.299, 0.587, 0.114])`. Sau khi IDWT, cộng hiệu số $Y$ vào các kênh RGB. | **Khớp 100%** |
| **Dải tần số nhúng** | Chỉ nhúng vào dải tần số cao **$HH$**; các dải $LL, LH, HL$ giữ nguyên cấu trúc. | `core/dwt.py:64-66`: Lấy `hh.ravel().copy()`, lượng tử hóa các hệ số đầu tiên trong mảng $HH$. | **Khớp 100%** |
| **Phương pháp lượng tử** | **QIM** (Quantization Index Modulation) với bước lượng tử $\Delta = 18$. | `core/dwt.py:13, 38`: `DELTA = 18`, công thức `DELTA * np.rint((c - bits * DELTA / 2) / DELTA) + bits * DELTA / 2`. | **Khớp 100%** |
| **Mã lặp & Bỏ phiếu** | Mã lặp **$k = 5$** (mỗi bit logic nhúng trên 5 hệ số liên tiếp); giải mã bằng **biểu quyết đa số $\ge 3$**. | `core/dwt.py:14, 52, 63`: `REPEAT = 5`, `np.repeat(bits, REPEAT)`, `(bits.reshape(-1, REPEAT).sum(axis=1) >= 3)`. | **Khớp 100%** |
| **Tái tạo & Giới hạn** | Tái tạo bằng IDWT, làm tròn số thực và chặn ngưỡng về $[0, 255]$. | `core/dwt.py:69, 73`: `np.clip(np.rint(...), 0, 255).astype(np.uint8)`. | **Khớp 100%** |

---

## 3. Đối chiếu cấu trúc gói dữ liệu (Payload Packet)

| Nội dung | Mô tả trong Báo cáo (Mục 3.2.4) | Cài đặt trong Code | Đánh giá |
| :--- | :--- | :--- | :---: |
| **Cấu trúc gói** | `LENGTH (32 bit) \|\| PAYLOAD (N byte)` | `core/payload.py:57`: `len(payload).to_bytes(4, 'big') + payload`. | **Khớp 100%** |
| **Định dạng độ dài** | Số nguyên không dấu 32-bit Big-Endian (uint32). | `core/payload.py:47, 57`: Kiểm tra `0 <= length <= 0xFFFFFFFF`, chuyển đổi `to_bytes(4, 'big')`. | **Khớp 100%** |
| **Mã hóa chuỗi** | Mã hóa và giải mã chuẩn UTF-8 nghiêm ngặt (`strict`). | `core/payload.py:25, 80`: `message.encode('utf-8')` và `decode('utf-8', errors='strict')`. | **Khớp 100%** |
| **Công thức tổng bit** | $B_{\text{required}} = 32 + 8 \times N$ | `metrics/metrics.py:18`: `packet_bits = 32 + 8 * payload_bytes`. | **Khớp 100%** |

---

## 4. Đối chiếu các chỉ số đo lường (Metrics)

| Chỉ số | Định nghĩa trong Báo cáo (Mục 2.6 & 3.6) | Hàm trong Code (`metrics/metrics.py`) | Đánh giá |
| :--- | :--- | :--- | :---: |
| **MSE** | Sai số bình phương trung bình trên toàn bộ mẫu điểm ảnh (RGB hoặc Gray). | `metrics.py:34-36` (`mse`): `float(np.mean((original - modified) ** 2))`. | **Khớp 100%** |
| **PSNR** | $10 \log_{10}(255^2 / \text{MSE})$. Nếu MSE = 0 thì PSNR = $\infty$. | `metrics.py:39-41` (`psnr`): `math.inf if error == 0 else 10 * math.log10(255**2 / error)`. | **Khớp 100%** |
| **SSIM** | Tính bằng thư viện scikit-image trên cửa sổ trượt, data range 255. | `metrics.py:44-52` (`ssim`): Gọi `skimage.metrics.structural_similarity` với `data_range=255`. | **Khớp 100%** |
| **BER** | Tỷ lệ bit sai so với tổng số bit packet gốc (khi đủ 2 chuỗi cùng độ dài). | `metrics.py:55-59` (`ber`): `np.count_nonzero(expected != extracted) / len(expected)`. | **Khớp 100%** |
| **bpp** | Số bit packet (gồm cả 32 bit tiêu đề) chia cho số điểm ảnh $(W \times H)$. | `metrics.py:22`: `packet_bits / (width * height)`. | **Khớp 100%** |

---

## 5. Đối chiếu kết quả thực nghiệm Chương 4

### 5.1. Bộ dữ liệu chuẩn
- **Báo cáo (Bảng 4.1):** 8 ảnh chuẩn kích thước 512×512 từ cơ sở dữ liệu USC-SIPI (mục Miscellaneous): `4.2.01.png` (Splash), `4.2.03.png` (Mandrill), `4.2.05.png` (Airplane), `4.2.06.png` (Sailboat), `5.2.10.png` (Stream), `7.1.02.png` (Airplane gray), `gray21.512.png`, `ruler.512.png`.
- **Thực tế:** Thư mục `data/selected_512/` chứa đầy đủ chính xác 8 tệp ảnh này, định dạng PNG lossless, kích thước chuẩn 512×512.

### 5.2. Các kịch bản tấn công Robustness (Bảng 4.2 & Bảng 4.6)
Tất cả 8 phép tấn công và 16 mức tham số mô tả trong báo cáo khớp hoàn toàn với cấu hình trong `experiments/experiment_config.py` và triển khai trong `experiments/attacks.py`:
1. Nén JPEG: `quality = 90` và `quality = 70`.
2. Nhiễu Gaussian: `sigma = 1.0` và `sigma = 3.0` (Seed = 20260919).
3. Nhiễu muối tiêu: `amount = 0.001` và `amount = 0.01` (Seed = 20260919).
4. Làm mờ Gaussian: `kernel_size = 3` và `kernel_size = 5`.
5. Độ sáng: `delta = -10.0` và `delta = 10.0`.
6. Độ tương phản: `alpha = 0.9` và `alpha = 1.1`.
7. Thay đổi kích thước: `scale = 0.75` và `scale = 1.25` (Interpolation INTER_AREA / INTER_LINEAR).
8. Cắt ảnh: `fraction = 0.9` và `fraction = 0.75` (Cắt từ tâm).

### 5.3. Hiện tượng 5 ca lỗi Baseline của DWT (Mục 4.3.4)
- **Báo cáo phân tích:** DWT bị lỗi trích xuất ngay tại baseline trên ảnh `ruler.512.png` (ở cả 4 mức payload) và ảnh `gray21.512.png` (ở mức 1500 byte). Nguyên nhân do bước làm tròn và cắt ngưỡng $[0, 255]$ làm biến dạng một số hệ số $HH$ sau IDWT trên các ảnh đồ họa có độ tương phản bậc thang nhân tạo.
- **Thực tế:** Hoàn toàn trùng khớp với kết quả chẩn đoán trong `output/chapter4/baseline_diagnostics.json` và kiểm thử tự động tại `tests/test_integration.py::test_dwt_clipping_detected`.

---

## 6. Kết luận về tính nhất quán

Mã nguồn Python và Báo cáo thuyết minh đồ án có **độ khớp đạt 100%** trên tất cả các khía cạnh: công thức toán học, thuật toán, tham số cấu hình, tập dữ liệu thực nghiệm và diễn giải kết quả. Không phát hiện bất kỳ sự mâu thuẫn hay số liệu nào bị bịa đặt.
