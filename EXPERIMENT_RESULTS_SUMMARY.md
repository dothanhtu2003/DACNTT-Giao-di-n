# Tóm tắt kết quả thực nghiệm

Nguồn: `robustness_results.csv`. Số dòng: **204**. Run IDs: 20260919T170018Z_dd694870

Đây là thống kê mô tả cho đúng tập ảnh, payload và mức tác động ghi trong snapshot. Bộ demo tổng hợp không đại diện cho tập ảnh tự nhiên. Không dùng kết quả này để kết luận tổng quát phương pháp nào tốt hơn.

## Baseline sau lưu/đọc PNG

| Ảnh | Method | Payload bytes | Capacity bits | Packet bits | bpp | PSNR dB | SSIM | BER | Khớp packet | Lỗi |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|---|
| synthetic_gradient_rgb.png | PVD | 8 | 98304 | 96 | 0.00146484375 | 81.77262620496978 | 0.9999990447275652 | 0.0 | True | NA |
| synthetic_gradient_rgb.png | PVD | 32 | 98304 | 288 | 0.00439453125 | 75.5890684082345 | 0.9999960121233947 | 0.0 | True | NA |
| synthetic_gradient_rgb.png | DWT | 8 | 3276 | 96 | 0.00146484375 | 57.48004461698298 | 0.9987008540977128 | 0.0 | True | NA |
| synthetic_gradient_rgb.png | DWT | 32 | 3276 | 288 | 0.00439453125 | 50.51138856304262 | 0.9926807571720152 | 0.0 | True | NA |
| synthetic_texture_gray.bmp | PVD | 8 | 170843 | 96 | 0.00146484375 | 60.32084501621232 | 0.9999986585690772 | 0.0 | True | NA |
| synthetic_texture_gray.bmp | PVD | 32 | 170843 | 288 | 0.00439453125 | 55.20555783950225 | 0.999995933642627 | 0.0 | True | NA |
| synthetic_texture_gray.bmp | DWT | 8 | 3276 | 96 | 0.00146484375 | 55.1752534031818 | 0.9999823719689852 | 0.0 | True | NA |
| synthetic_texture_gray.bmp | DWT | 32 | 3276 | 288 | 0.00439453125 | 50.32820287019372 | 0.9999242011854117 | 0.0 | True | NA |
| synthetic_white_rgba.png | PVD | 8 | 98304 | 96 | 0.00146484375 | 77.90711200754355 | 0.99999741514892 | 0.0 | True | NA |
| synthetic_white_rgba.png | PVD | 32 | 98304 | 288 | 0.00439453125 | 70.95957680819498 | 0.9999873340995848 | 0.0 | True | NA |
| synthetic_white_rgba.png | DWT | 8 | 3276 | 96 | 0.00146484375 | 60.830176280134786 | 0.9993704263904203 | NA | False | LengthMismatch |
| synthetic_white_rgba.png | DWT | 32 | 3276 | 288 | 0.00439453125 | 53.92016553348735 | 0.9967086290751098 | NA | False | LengthMismatch |

Baseline khớp packet: **10/12**. Baseline thất bại là giới hạn tái tạo ảnh của cấu hình, không được gộp thành thành công.

## BER và tỷ lệ trích xuất đúng theo attack / parameter

BER trung bình chỉ tính trên các dòng có LENGTH khớp và đủ bit. Cột NA cho biết số dòng không tính được BER; không coi NA là 0 hoặc 1. Success yêu cầu toàn bộ packet khớp, không chỉ UTF-8 hợp lệ.

| Method | Attack | Parameter | Số ca | Khớp packet | Tỷ lệ % | BER TB có cơ sở | BER NA |
|---|---|---|---:|---:|---:|---:|---:|
| DWT | blur | {"kernel_size":3} | 6 | 0 | 0.00 | NA | 6 |
| DWT | blur | {"kernel_size":5} | 6 | 0 | 0.00 | NA | 6 |
| DWT | brightness | {"delta":-10} | 6 | 4 | 66.67 | 0.000000 | 2 |
| DWT | brightness | {"delta":10} | 6 | 4 | 66.67 | 0.000000 | 2 |
| DWT | contrast | {"alpha":0.9} | 6 | 2 | 33.33 | 0.000000 | 4 |
| DWT | contrast | {"alpha":1.1} | 6 | 2 | 33.33 | 0.000000 | 4 |
| DWT | crop | {"fraction":0.75} | 6 | 0 | 0.00 | NA | 6 |
| DWT | crop | {"fraction":0.9} | 6 | 0 | 0.00 | NA | 6 |
| DWT | gaussian_noise | {"sigma":1.0} | 6 | 4 | 66.67 | 0.000000 | 2 |
| DWT | gaussian_noise | {"sigma":3.0} | 6 | 2 | 33.33 | 0.002315 | 3 |
| DWT | jpeg | {"quality":70} | 6 | 0 | 0.00 | NA | 6 |
| DWT | jpeg | {"quality":90} | 6 | 0 | 0.00 | NA | 6 |
| DWT | none | {} | 6 | 4 | 66.67 | 0.000000 | 2 |
| DWT | resize | {"scale":0.75} | 6 | 0 | 0.00 | NA | 6 |
| DWT | resize | {"scale":1.25} | 6 | 0 | 0.00 | NA | 6 |
| DWT | salt_pepper | {"amount":0.001} | 6 | 4 | 66.67 | 0.000000 | 2 |
| DWT | salt_pepper | {"amount":0.01} | 6 | 4 | 66.67 | 0.000000 | 2 |
| PVD | blur | {"kernel_size":3} | 6 | 0 | 0.00 | NA | 6 |
| PVD | blur | {"kernel_size":5} | 6 | 0 | 0.00 | NA | 6 |
| PVD | brightness | {"delta":-10} | 6 | 6 | 100.00 | 0.000000 | 0 |
| PVD | brightness | {"delta":10} | 6 | 2 | 33.33 | 0.023438 | 2 |
| PVD | contrast | {"alpha":0.9} | 6 | 0 | 0.00 | 0.180556 | 2 |
| PVD | contrast | {"alpha":1.1} | 6 | 0 | 0.00 | 0.121528 | 4 |
| PVD | crop | {"fraction":0.75} | 6 | 0 | 0.00 | NA | 6 |
| PVD | crop | {"fraction":0.9} | 6 | 0 | 0.00 | NA | 6 |
| PVD | gaussian_noise | {"sigma":1.0} | 6 | 0 | 0.00 | NA | 6 |
| PVD | gaussian_noise | {"sigma":3.0} | 6 | 0 | 0.00 | NA | 6 |
| PVD | jpeg | {"quality":70} | 6 | 0 | 0.00 | NA | 6 |
| PVD | jpeg | {"quality":90} | 6 | 0 | 0.00 | NA | 6 |
| PVD | none | {} | 6 | 6 | 100.00 | 0.000000 | 0 |
| PVD | resize | {"scale":0.75} | 6 | 0 | 0.00 | NA | 6 |
| PVD | resize | {"scale":1.25} | 6 | 0 | 0.00 | NA | 6 |
| PVD | salt_pepper | {"amount":0.001} | 6 | 6 | 100.00 | 0.000000 | 0 |
| PVD | salt_pepper | {"amount":0.01} | 6 | 2 | 33.33 | 0.133333 | 1 |

## Capacity và chất lượng trước attack

Mỗi cấu hình ảnh/method/payload được tính một lần từ baseline, không nhân lặp theo số attacks.

| Method | Số ca | Capacity TB (bit) | PSNR TB (dB) | SSIM TB |
|---|---:|---:|---:|---:|
| DWT | 6 | 3276.000000 | 54.707539 | 0.997895 |
| PVD | 6 | 122483.666667 | 70.292464 | 0.999996 |

## Trường hợp không tính được BER

| Error type | Số dòng BER NA |
|---|---:|
| LengthError | 70 |
| LengthMismatch | 70 |

Resize giữ kích thước đã đổi; crop cắt giữa ảnh và không phục hồi/đăng ký hình học. Kết quả của các phép này chỉ áp dụng cho chính sách đó. Mỗi mức nhiễu chỉ có một seed trong lần chạy này; chưa có khoảng tin cậy từ nhiều lần lặp độc lập.
