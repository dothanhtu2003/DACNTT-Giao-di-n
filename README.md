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

1. **Nhúng dữ liệu:** chọn PNG/BMP, chọn PVD/DWT, nhập UTF-8, nhúng, xem metrics, lưu PNG. Dung lượng được kiểm tra tự động khi chọn ảnh, đổi phương pháp hoặc sửa văn bản. Tự trích xuất lại để xác nhận packet khớp trước khi cho lưu.
2. **Trích xuất dữ liệu:** chọn ảnh và đúng phương pháp, xem văn bản chỉ đọc, Sao chép. **Lưu ý trích xuất** giải thích giới hạn LENGTH/UTF-8 và xác thực dữ liệu.
3. **So sánh PVD – DWT:** chọn **Một ảnh** để so sánh chất lượng nhúng trên cùng ảnh/message, hoặc **Bộ ảnh** để chạy ma trận qua service và xem bảng tổng hợp. Hai nhánh độc lập, hỗ trợ partial, lưu PNG baseline.
4. **Lịch sử:** metadata local, Làm mới, xem chi tiết, xóa bản ghi hoặc xóa tất cả có xác nhận.

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
Với DWT, **Xem phân rã DWT** mở cửa sổ LL/LH/HL/HH, đánh dấu HH. Normalization từng dải chỉ để hiển thị.

PSNR/SSIM đo cover so với Stego; RGBA chỉ đo RGB. MSE=0 cho PSNR infinity. BER chỉ tính trên packet đã xác lập đồng bộ.

## Kiểm thử phần mềm

```powershell
python -m pytest -q -W error
python -m compileall -q main.py core gui services metrics storage experiments tests
```

Tests bao gồm engines, payload, metrics, utilities, service, privacy/history, GUI và experiments. GUI tests cần desktop/Tk display; skip nếu không có display. File dialogs trong tests được thay bằng đường dẫn fixture, widget và worker thật vẫn chạy.
Xem [TEST_REPORT.md](TEST_REPORT.md).

## Robustness và benchmark

Thử nghiệm độ bền được thực hiện trong chế độ **Bộ ảnh**. Chế độ **Một ảnh** hiển thị ảnh sau nhúng, bảng chỉ số, biểu đồ so sánh và lưu Stego PVD/DWT.

### Bộ ảnh trong tab So sánh

Chọn **Bộ ảnh**, thư mục nguồn và thư mục đầu ra. Chỉ đọc PNG/BMP trực tiếp trong thư mục, không đệ quy. Giao diện báo số ảnh hợp lệ và số file bị loại. Khuyến nghị **10–20 ảnh thật**, có ảnh xám, màu, vùng phẳng và nhiều chi tiết; dưới 10 ảnh vẫn cho chạy và có lưu ý. Chương trình không tự phân loại hay tải thêm ảnh.

Nhập danh sách payload **theo byte** và seed nguyên không âm, cách nhau dấu phẩy. Seed trùng được loại, mặc định là 5 seed liên tiếp từ `SEED`. Chọn tác động và nhập nhiều mức tham số; mặc định payload/mức lấy toàn bộ `experiment_config.py`. Baseline **Không tác động** luôn có. Chỉ Gaussian/muối tiêu lặp theo seed; tác động xác định chạy một lần mỗi mức. Bộ ảnh dùng trực tiếp seed đã nhập cho cả PVD/DWT; **CLI cũ vẫn giữ cách sinh seed bằng hash**, nên hai chế độ không có cùng seed mặc định. Payload là chuỗi ASCII công khai từ `public_payload()`, cùng ảnh/payload thì hai phương pháp nhận cùng dữ liệu. Không dùng văn bản bí mật từ Một ảnh.

Danh sách ảnh được kiểm tra khi chọn thư mục ảnh; cấu hình được kiểm tra lại tự động trước khi chạy. GUI dùng giới hạn kernel lẻ 1–51 và scale trong (0,4], có ghi ngay trên nhãn; payload tối đa uint32, nhưng kiểm tra dung lượng trước khi tạo dữ liệu. Không có giới hạn riêng về số ảnh hoặc số ca. Baseline lỗi làm số ca thực chạy nhỏ hơn dự kiến.

Mỗi ảnh × phương pháp × payload nhúng một lần, lưu/đọc lại PNG và kiểm tra toàn bộ packet. `baselines.csv` phân biệt `capacity`, `embed_io_error`, `mismatch` và `valid`; chỉ `valid` mới chạy các tác động. Mỗi tác động bắt đầu từ cùng Stego baseline, không cộng dồn, resize/crop không căn chỉnh. Một ảnh/phương pháp lỗi không dừng ảnh tiếp theo. Xử lý tuần tự và giải phóng mảng từng ảnh; giữ metadata/ca thử trong RAM, không giữ mảng ảnh toàn bộ dữ liệu.

**Chạy Bộ ảnh** dùng worker và busy chung với các tab khác. Cấu hình được chụp trước khi gửi worker; worker không đọc/cập nhật widget Tkinter. Tiến độ báo số ca hoàn tất/tổng dự kiến, số baseline đã xử lý và ảnh hiện tại. **Hủy** hợp tác giữa các ca; tác vụ không bị cưỡng chế dừng. Kết quả đã hoàn tất vẫn được lưu, trạng thái `cancelled` và nhãn **KẾT QUẢ CHƯA ĐẦY ĐỦ**; ca chưa chạy không tính là thất bại. Không tắt ứng dụng giữa ca. Đổi cấu hình hoặc chế độ làm token cũ mất hiệu lực, nên kết quả cũ không ghi đè lựa chọn mới; file xuất và lịch sử vẫn thuộc cấu hình chụp khi bắt đầu.

Cấu hình có thể thu gọn/mở lại và giữ nguyên giá trị; khi có kết quả, tự thu gọn để dành chiều cao cho bảng. Chạy/Hủy và tiến độ luôn ở thanh trên cùng. Chế độ xem kết quả không cần cuộn toàn trang.

Bảng chính dùng **một Treeview với 8 cột**, vừa 1000 × 760, có cuộn dọc: phương pháp (PP), payload byte, tác động, tham số, ảnh đủ điều kiện, tỷ lệ đúng TB theo ảnh (%), BER TB theo ảnh (0–1), ca BER NA. Tham số dài rút gọn bằng `…`; **Xem chi tiết** hoặc nhấp đúp cho đầy đủ tham số và các chỉ số còn lại: ảnh dự kiến, baseline hợp lệ/lỗi/chưa chạy, ca hoàn tất/đúng, tỷ lệ gộp, SD mẫu, số ca BER hợp lệ/NA và số ảnh góp BER/không có BER hợp lệ. Cửa sổ chi tiết xuống dòng, có thanh cuộn và đường dẫn kết quả đầy đủ. SD tỷ lệ được nhân 100, ghi **điểm phần trăm** (ví dụ 0,46291 → 46,291 điểm phần trăm).

Bộ lọc phương pháp/payload/tác động/tập ảnh chỉ chọn dòng đã có, không tính lại, không gộp nhóm và không sửa thứ tự CSV. Mặc định chọn **baseline chung PVD/DWT**; có nhãn giải thích tập đang hiển thị và số dòng phù hợp. Số ảnh đủ điều kiện nằm ở từng dòng, không suy ra một số ảnh cố định cho toàn bảng. Thứ tự hiển thị là **payload → tác động (thứ tự danh mục) → mức tham số → PVD/DWT**; payload và tham số số sắp theo giá trị số.

Khi `completed`, tiến độ đạt 100% và ghi số ảnh nguồn chạy thành công/thất bại, mỗi ảnh tính một lần. Ảnh thành công khi toàn bộ baseline PVD/DWT ở các mức payload đã chọn đều hợp lệ; nếu có baseline lỗi, ảnh được tính thất bại. Đây là kết quả nhúng/đối chiếu baseline, không phải tỷ lệ khôi phục sau tác động. Thiếu metadata thì không suy đoán số ảnh. Khi hủy, giữ tiến độ ca thực chạy và ghi **Đã hủy — kết quả chưa đầy đủ**. SD giữa ảnh bằng 0 không tự chứng minh độ ổn định tổng quát. Xem [BATCH_UI_REPORT.md](BATCH_UI_REPORT.md) về kiểm chứng mặt nạ muối tiêu, vị trí nhúng PVD và ảnh chụp GUI.

### Xem và lưu biểu đồ Bộ ảnh

Nút **Xem biểu đồ** cạnh **Xem chi tiết** được bật khi bộ lọc đang có dòng tổng hợp. Không cần chọn một dòng: biểu đồ dùng toàn bộ các dòng đang lọc, chụp dữ liệu/bộ lọc tại thời điểm mở và không chạy lại thực nghiệm. Đổi bộ lọc hoặc cấu hình sau đó không làm thay đổi cửa sổ biểu đồ đã mở; mở lại để xem phạm vi mới.

Biểu đồ cột nhóm vẽ **`image_success_mean × 100`**, trục Y cố định **0–100%**, PVD xanh và DWT cam. Đây là tỷ lệ khôi phục toàn bộ packet TB theo ảnh, không phải điểm chuẩn hóa tương đối của biểu đồ Một ảnh. Nhãn cột có tối đa hai chữ số thập phân; cột 0% vẫn có nhãn. Nhóm có đủ giá trị và tất cả phương pháp đang chọn đều đạt đúng 0% được liệt kê dưới hình ở mục **Tất cả đều 0%**, với đầy đủ tác động/mức tham số, tách riêng theo payload và tập đang lọc. Khi chỉ chọn một phương pháp, điều kiện này áp dụng cho phương pháp đó. Nhóm có NA hoặc thiếu phương pháp vẫn vẽ riêng: NA ghi **Không xác định**, không thành 0%. Bảng tổng hợp giữ đầy đủ mọi cấu hình; rút gọn chỉ thay đổi cách trình bày biểu đồ và PNG, không sửa dữ liệu. Không có thanh sai số, biểu đồ BER hay kết luận tự động.

Mỗi payload có đúng một biểu đồ tổng quát trong cùng cửa sổ: chọn payload 8 và 32 byte sẽ có hai biểu đồ. Các tác động/mức tham số đang lọc nằm trên cùng trục X hoặc trong danh sách toàn 0% dưới hình, không chia thành nhiều hình theo tác động. Các mức tham số được sắp theo số, nhãn đầy đủ xuống dòng; cửa sổ có cuộn dọc/ngang để đọc hình lớn. Chỉ phương pháp/tác động/tập all hoặc common đang lọc được vẽ; không tính lại hoặc gộp giá trị thống kê. Mỗi hình có run ID, payload, tác động, bộ lọc lúc mở, ý nghĩa tập ảnh và số ảnh đủ điều kiện theo phương pháp (hoặc từng nhóm nếu khác nhau, kể cả nhóm toàn 0%). Với all, ghi rõ PVD/DWT có thể dùng tập ảnh khác nhau. Seed chỉ lấy từ cấu hình được cung cấp hoặc `config.json` của đúng run ID, không suy từ số ca; thiếu cấu hình thì bỏ chú thích seed.

Kết quả hủy/lỗi/chưa đầy đủ được cảnh báo trong từng hình và PNG. Bấm **Lưu biểu đồ PNG** trên từng biểu đồ để chọn vị trí lưu; tên gợi ý gồm run ID, tập ảnh, payload, mã tác động và số phần. Chỉ lưu khi người dùng chủ động chọn; không sửa CSV/JSON/Markdown/lịch sử. PNG chứa tiêu đề, đơn vị, chú giải, phạm vi và cảnh báo, dùng cùng hình với GUI và có lề xuất đầy đủ.

Dependency mới: **`matplotlib>=3.8,<4`** trong `requirements.txt`; cập nhật bằng `python -m pip install -r requirements.txt`. Xem [BATCH_CHART_REPORT.md](BATCH_CHART_REPORT.md) về kiểm thử và PNG minh họa.

- Tỷ lệ đúng gộp = ca khớp toàn bộ packet / ca hoàn tất. Với từng ảnh, tính tỷ lệ trên các ca đã hoàn tất của ảnh, rồi lấy trung bình giữa các ảnh được thử; mỗi ảnh có trọng số bằng nhau.
- SD là độ lệch chuẩn **mẫu** giữa tỷ lệ theo ảnh; dưới 2 ảnh → `NA`. Mẫu số 0 → `NA`, không phải 0%.
- BER chỉ tính khi LENGTH và độ dài khớp, dùng nguyên `assess_extraction()`. Tính BER trung bình trên ca hợp lệ của từng ảnh, rồi trung bình giữa ảnh có BER. Không gán ảnh không có BER là 0. Tỷ lệ khôi phục đúng là chỉ số chính; đọc BER cùng số ca/ảnh NA vì có thể có lệch chọn lọc.
- Lựa chọn **Ảnh baseline hợp lệ ở cả hai phương pháp** dùng cùng tập ảnh tại từng payload (`scope=common`). Các số baseline thất bại vẫn đếm trên toàn bộ tập dự kiến, không âm thầm loại ảnh khó. `scope=all` là thống kê theo từng phương pháp trên toàn tập.

Mỗi lần chạy tạo thư mục mới `experiments/batch_results/<run_id>/` (hoặc thư mục đầu ra đã chọn):

| File | Nội dung |
|---|---|
| `cases.csv` | Từng ca thực sự hoàn tất, seed thực tế; seed tác động xác định và BER không xác định ghi NA |
| `baselines.csv` | Mỗi cấu hình nhúng đã xử lý, trạng thái và đường dẫn PNG kể cả baseline không khớp |
| `summary.csv` | Toàn bộ các nhóm ở cả `all` và `common` |
| `config.json` | Cấu hình, seed, danh sách/hash SHA-256 ảnh, môi trường, số ca và trạng thái |
| `summary.md` | Bảng tổng hợp và giải thích mẫu số/NA/kết quả chưa đầy đủ |
| `stego/*.png` | PNG baseline đã tạo được; xem trạng thái trong `baselines.csv` trước khi gọi nhúng thành công |

Không lưu nội dung payload/packet vào metadata, CSV/JSON/Markdown, không tự lưu ảnh sau tác động. PNG baseline chứa dữ liệu nhúng công khai theo bản chất phép thử. **Mở thư mục kết quả** hoạt động sau hoàn tất/hủy. Chỉ ghi **một** metadata lịch sử cho mỗi lần chạy, gồm run ID, trạng thái, số ảnh, số ca hoàn tất/dự kiến và thư mục kết quả; lịch sử cũ vẫn đọc được.

Ví dụ kiểm tra: 2 ảnh, payload `0,8`, seed `7,8,7` (còn 7 và 8), độ sáng `0,1`, Gaussian `0,1`, tắt các tác động khác → **8 cấu hình nhúng, 56 ca tối đa**, gồm baseline. Đây là kiểm tra pipeline, không phải bộ đánh giá đại diện. Ví dụ thực tế dùng 8 ảnh có sẵn tại `data/selected_512`, payload mặc định `8,32`, toàn bộ mức tác động mặc định và 5 seed → **32 cấu hình, 1056 ca tối đa**. Xem [BATCH_TEST_REPORT.md](BATCH_TEST_REPORT.md) về kết quả thực chạy và mục Chương 3/4 cần cập nhật.

### Chạy hàng loạt bằng lệnh

`experiments/` tiếp tục hỗ trợ CLI cũ. GUI Bộ ảnh gọi `StegoService.run_batch()` → `experiments.batch_runner.run_batch()`, dùng chung thuật toán, tác động và đánh giá packet, không gọi CLI bằng subprocess. OpenCV thực sự dùng cho JPEG encode/decode, Gaussian blur và resize; NumPy hỗ trợ noise và biến đổi cường độ.
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
"# DACNTT" 
