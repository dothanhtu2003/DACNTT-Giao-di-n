"""CLI: python -m experiments.benchmark_runner --demo or --images DIRECTORY."""

import argparse
from pathlib import Path
import sys

import numpy as np
from PIL import Image

from experiments.experiment_config import default_config
from experiments.robustness_runner import run_experiments

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def generate_demo_images(folder):
    """Small synthetic pipeline study, not a representative natural-image dataset."""
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(20260919)
    y, x = np.mgrid[:256, :256]
    gray = np.clip(40 + 0.4 * x + 0.2 * y + 15 * np.sin(x / 9), 0, 255).astype(np.uint8)
    rgb = np.dstack((gray, np.roll(gray, 32, axis=0), np.roll(gray, 16, axis=1)))
    textures = rng.integers(24, 232, (256, 256), dtype=np.uint8)
    white = np.full((256, 256, 4), 255, dtype=np.uint8)
    paths = []
    for name, image in [('synthetic_gradient_rgb.png', rgb), ('synthetic_texture_gray.bmp', textures),
                        ('synthetic_white_rgba.png', white)]:
        path = folder / name
        # Existing covers belong to the user: never overwrite them implicitly.
        if not path.exists():
            Image.fromarray(image).save(path)
        paths.append(path)
    return paths


def main():
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser(description='Thu dữ liệu PVD/DWT; không kết luận phương pháp tốt hơn.')
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--demo', action='store_true', help='Tạo/chạy 3 ảnh tổng hợp 256×256 để minh họa pipeline.')
    source.add_argument('--images', type=Path, help='Thư mục ảnh nguồn PNG/BMP.')
    parser.add_argument('--output', type=Path, default=PROJECT_ROOT / 'experiments' / 'results')
    parser.add_argument('--seed', type=int, default=None)
    parser.add_argument('--payload-bytes', type=int, nargs='+', help='Thay các mức payload bằng số byte cụ thể.')
    parser.add_argument('--summary', type=Path, help='Xuất tóm tắt Markdown từ CSV vừa tạo.')
    args = parser.parse_args()
    paths = generate_demo_images(PROJECT_ROOT / 'data' / 'demo') if args.demo else [
        path for path in args.images.iterdir() if path.suffix.lower() in ('.png', '.bmp')]
    config = default_config()
    config['dataset_kind'] = 'synthetic_demo_not_representative' if args.demo else 'user_supplied'
    if args.seed is not None:
        config['seed'] = args.seed
    if args.payload_bytes is not None:
        config['payload_levels'] = [{'kind': 'bytes', 'value': value} for value in args.payload_bytes]
    rows = run_experiments(paths, args.output, config)
    print(f'{len(rows)} rows saved: {args.output / "robustness_results.csv"}')
    if args.summary:
        from experiments.summarize_results import summarize
        summarize(args.output / 'robustness_results.csv', args.summary)
        print(f'Summary: {args.summary}')


if __name__ == '__main__':
    main()
