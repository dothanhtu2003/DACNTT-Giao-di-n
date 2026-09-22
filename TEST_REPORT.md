# Báo cáo kiểm thử phần mềm

## Kết quả cuối sau cleanup

- Ngày: 20/09/2026 (Asia/Bangkok).
- **121 passed, 0 failed, 0 errors, 0 skipped, 0 warnings**.
- Lệnh: `python -m pytest -q -W error --junitxml=tests/artifacts/pytest_results.xml`.
- Thời gian suite: 4.18 giây; bằng chứng máy đọc được tại `tests/artifacts/pytest_results.xml`.
- Compile/import check: đạt (`python -m compileall -q main.py core gui services metrics storage experiments tests`).
- GUI thực tế đã mở, render và được kiểm tra qua ảnh chụp 4 tab cùng cửa sổ DWT trong `tests/artifacts/`.

## Môi trường

- OS: Windows-10-10.0.19045-SP0.
- Python: 3.12.10; Tk 8.6.
- numpy: 2.4.6.
- Pillow: 12.1.1.
- PyWavelets: 1.9.0.
- scikit-image: 0.26.0.
- opencv-python: 5.0.0.93.
- pytest: 8.4.2.

## Nhóm kiểm thử

| Module | Số test | Kết quả |
|---|---:|---|
| tests.test_attacks | 58 | Pass |
| tests.test_dwt | 9 | Pass |
| tests.test_experiments | 5 | Pass |
| tests.test_gui | 3 | Pass |
| tests.test_history | 5 | Pass |
| tests.test_image_utils | 4 | Pass |
| tests.test_integration | 7 | Pass |
| tests.test_metrics | 6 | Pass |
| tests.test_payload | 10 | Pass |
| tests.test_pvd | 8 | Pass |
| tests.test_service | 6 | Pass |

## Phạm vi kiểm tra

- Payload: ASCII, tiếng Việt, emoji, rỗng, dài, unsigned LENGTH, dữ liệu thiếu và UTF-8 hỏng.
- PVD: grayscale/RGB/RGBA, width chẵn/lẻ, capacity, overcapacity, bit roundtrip, giữ R/G/alpha và ảnh gốc; kiểm tra mọi 65.536 cặp pixel ở hai cực khoảng.
- DWT: PNG roundtrip grayscale/RGB/RGBA, kích thước chẵn/lẻ, capacity, overcapacity, alpha, Delta 18, repeat 5, majority vote và visualization bands.
- Metrics: packet bits/bpp gồm LENGTH, usage, MSE, PSNR infinity, SSIM đa kênh/ảnh nhỏ, BER và điều kiện không được tính.
- Service/integration: embed/save/load/extract, cùng message cho compare, success/partial/failed, malformed LENGTH, UTF-8 lỗi, ảnh không hợp lệ/không tồn tại, JPEG bị từ chối, output lỗi.
- History: CRUD, JSON trống/hỏng, metadata allowlist, không chứa message/extracted content/raw payload.
- GUI: cửa sổ thật, 4 tab, chọn BMP, nhúng PVD/DWT, lưu PNG, extract UTF-8, Copy, compare, history detail/delete/clear, mở DWT. Các nút chính được kiểm tra không bị khuất ở kích thước mặc định.
- GUI tests thay file dialogs và xác nhận xóa bằng fixture; không kiểm tra hộp thoại hệ điều hành bằng chuột. Worker và Tk widget thật chạy. Môi trường không có Tk display có thể skip GUI, nhưng lần chạy này không skip.
- Attacks: 17 cấu hình gồm baseline trên grayscale/RGB/RGBA; output dtype/shape, không mutate, parameter tạo thay đổi, seed tái lập, tham số sai.
- Runner: ma trận, baseline, privacy CSV, config snapshot, seed tái lập, BER NA khi mất đồng bộ, UTF-8 lỗi vẫn đo BER khi đủ cơ sở, capacity failure và CLI đường dẫn tiếng Việt.

## Các lỗi đã sửa trong quá trình

- CLI không in được đường dẫn tiếng Việt khi stdout Windows dùng cp1252: đặt stdout UTF-8; có regression test subprocess.
- Cảnh báo Tk Variable được thu gom trên worker khi test tạo nhiều cửa sổ: worker chỉ giữ service; test thu gom Tk trên main thread. Suite cuối chạy `-W error` không có warning.
- Nút Copy, cấu hình và lưu/so sánh từng bị khuất ở kích thước mặc định: điều chỉnh bố cục, giới hạn kích thước preview/text và dành chỗ cho status/actions; xác minh bằng screenshot và assertions.
- Ngăn hiển thị kết quả của lựa chọn cũ nếu người dùng đổi input trong lúc worker chạy; ngăn lưu đồng thời khi service đang ghi history.
- Lịch sử chỉ nhận metadata qua allowlist, serialize infinity đúng JSON; nội dung nhạy cảm không lọt qua result object vào history.

## Giới hạn còn lại

- **DWT bão hòa:** ảnh trắng RGBA trong benchmark có 2 baseline thất bại; test kiểm tra service phát hiện/chặn lưu. Đây là giới hạn thuật toán sau round/clip, không phải đã sửa nhờ test pass.
- **DWT biên lẻ:** probe audit 129×129 grayscale 128, nhúng 845 logical bits toàn 1 tới capacity, đọc lại sai 13 bit. Giữ nguyên symmetric extension và cấu hình đã khóa; xem FINAL_AUDIT.md.
- **Packet không xác thực:** ảnh không nhúng có thể cho LENGTH=0 và UTF-8 rỗng hợp lệ. Không có magic/checksum trong spec để phân biệt chắc chắn.
- Chưa kiểm tra ma trận nhiều hệ điều hành/DPI hoặc hiệu năng ảnh rất lớn. Kiểm tra GUI thực tế trên màn hình Windows hiện tại.
- Robustness không phải unit tests: CSV có **204 ca**, baseline **10/12** đúng, **140 dòng BER NA**. Bộ demo là 3 ảnh tổng hợp, thông số thăm dò, một seed mỗi mức; chưa đủ kết luận khoa học tổng quát.

## Mốc triển khai

Bước 1: 10 tests; bước 2: 18; bước 3: 27; bước 4: 37; bước 5: 48; GUI/end-to-end bước 12: 58; attacks bước 13: 116; runner và cleanup: 121. Không có test fail trong kết quả cuối.
