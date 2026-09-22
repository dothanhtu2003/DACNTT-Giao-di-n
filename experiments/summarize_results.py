"""Generate descriptive Markdown tables from measured CSV rows only."""

import argparse
from collections import defaultdict, Counter
import csv
from pathlib import Path
from statistics import mean


def _success(row):
    return row['extract_success'].lower() == 'true'


def _mean(rows, key):
    values = [float(row[key]) for row in rows if row.get(key) not in ('', None, 'NA')]
    return f'{mean(values):.6f}' if values else 'NA'


def _cell(value):
    return str(value).replace('|', '\\|').replace('\n', ' ')


def summarize(csv_path, output_path):
    with Path(csv_path).open(encoding='utf-8', newline='') as handle:
        rows = list(csv.DictReader(handle))
    baseline = [row for row in rows if row['attack'] == 'none']
    lines = ['# Tóm tắt kết quả thực nghiệm', '',
             f'Nguồn: `{Path(csv_path).name}`. Số dòng: **{len(rows)}**. Run IDs: ' + ', '.join(sorted({row['run_id'] for row in rows})), '',
             'Đây là thống kê mô tả cho đúng tập ảnh, payload và mức tác động ghi trong snapshot. '
             'Bộ demo tổng hợp không đại diện cho tập ảnh tự nhiên. Không dùng kết quả này để kết luận tổng quát phương pháp nào tốt hơn.', '',
             '## Baseline sau lưu/đọc PNG', '',
             '| Ảnh | Method | Payload bytes | Capacity bits | Packet bits | bpp | PSNR dB | SSIM | BER | Khớp packet | Lỗi |',
             '|---|---|---:|---:|---:|---:|---:|---:|---:|---|---|']
    for row in baseline:
        keys = ['image_name', 'method', 'payload_bytes', 'capacity_bits', 'packet_bits', 'bpp',
                'psnr_before_attack', 'ssim_before_attack', 'ber_after_attack', 'extract_success', 'error_type']
        lines.append('| ' + ' | '.join(_cell(row.get(key) or 'NA') for key in keys) + ' |')
    lines += ['', f'Baseline khớp packet: **{sum(_success(row) for row in baseline)}/{len(baseline)}**. '
              'Baseline thất bại là giới hạn tái tạo ảnh của cấu hình, không được gộp thành thành công.', '',
              '## BER và tỷ lệ trích xuất đúng theo attack / parameter', '',
              'BER trung bình chỉ tính trên các dòng có LENGTH khớp và đủ bit. Cột NA cho biết số dòng không tính được BER; '
              'không coi NA là 0 hoặc 1. Success yêu cầu toàn bộ packet khớp, không chỉ UTF-8 hợp lệ.', '',
              '| Method | Attack | Parameter | Số ca | Khớp packet | Tỷ lệ % | BER TB có cơ sở | BER NA |',
              '|---|---|---|---:|---:|---:|---:|---:|']
    groups = defaultdict(list)
    for row in rows:
        groups[(row['method'], row['attack'], row['attack_parameter'])].append(row)
    for (method, attack, parameter), group in sorted(groups.items()):
        successes = sum(_success(row) for row in group)
        missing = sum(not row['ber_after_attack'] for row in group)
        lines.append(f'| {method} | {attack} | {_cell(parameter)} | {len(group)} | {successes} | '
                     f'{100 * successes / len(group):.2f} | {_mean(group, "ber_after_attack")} | {missing} |')
    lines += ['', '## Capacity và chất lượng trước attack', '',
              'Mỗi cấu hình ảnh/method/payload được tính một lần từ baseline, không nhân lặp theo số attacks.', '',
              '| Method | Số ca | Capacity TB (bit) | PSNR TB (dB) | SSIM TB |',
              '|---|---:|---:|---:|---:|']
    for method in sorted({row['method'] for row in baseline}):
        group = [row for row in baseline if row['method'] == method]
        lines.append(f'| {method} | {len(group)} | {_mean(group, "capacity_bits")} | '
                     f'{_mean(group, "psnr_before_attack")} | {_mean(group, "ssim_before_attack")} |')
    lines += ['', '## Trường hợp không tính được BER', '', '| Error type | Số dòng BER NA |', '|---|---:|']
    errors = Counter(row['error_type'] or 'Unspecified' for row in rows if not row['ber_after_attack'])
    for error, count in sorted(errors.items()):
        lines.append(f'| {_cell(error)} | {count} |')
    lines += ['', 'Resize giữ kích thước đã đổi; crop cắt giữa ảnh và không phục hồi/đăng ký hình học. '
              'Kết quả của các phép này chỉ áp dụng cho chính sách đó. Mỗi mức nhiễu chỉ có một seed trong lần chạy này; '
              'chưa có khoảng tin cậy từ nhiều lần lặp độc lập.', '']
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    Path(output_path).write_text('\n'.join(lines), encoding='utf-8')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('csv', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    summarize(args.csv, args.output)
