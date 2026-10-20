"""Snapshot-only charts of measured image_success_mean; no experiment calls."""

from copy import deepcopy
import json
import math
from pathlib import Path
import re
import textwrap
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk

from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.patches import Patch

from gui.compare_chart import METHODS, COLORS
from gui.batch_panel import summary_sort_key, parameter_text
from services.robustness import ATTACK_LABELS

SCOPE_NOTES = {
    'common': 'Ảnh có baseline hợp lệ ở cả PVD và DWT, theo từng payload.',
    'all': 'Baseline hợp lệ riêng từng phương pháp; PVD/DWT có thể dùng tập ảnh đủ điều kiện khác nhau.',
}
LIMIT_NOTE = 'Tỷ lệ chỉ áp dụng cho tập ảnh và cấu hình đã thử; thất bại baseline được báo riêng trong bảng chi tiết.'


def number(value):
    return f'{value:g}'.replace('.', ',') if isinstance(value, (int, float)) else str(value)


def attack_label(name, raw):
    try:
        p = json.loads(raw)
    except (ValueError, TypeError):
        return ATTACK_LABELS.get(name, name) + '\n' + str(raw)
    known = {
        'none': ('Không tác động', None, ''),
        'jpeg': ('JPEG Q', 'quality', ''),
        'gaussian_noise': ('Gaussian σ=', 'sigma', ''),
        'salt_pepper': ('Muối tiêu ', 'amount', '%'),
        'contrast': ('Tương phản ×', 'alpha', ''),
        'brightness': ('Độ sáng Δ=', 'delta', ''),
        'blur': ('Mờ Gaussian k=', 'kernel_size', ''),
        'resize': ('Đổi kích thước ×', 'scale', ''),
        'crop': ('Cắt giữa ', 'fraction', '%'),
    }
    prefix, key, suffix = known.get(name, (ATTACK_LABELS.get(name, name) + ' ', None, ''))
    if name == 'none' and not p:
        return prefix
    if key in p:
        value = p[key]
        if name in ('salt_pepper', 'crop') and isinstance(value, (int, float)):
            value *= 100
        label = prefix + number(value) + suffix
        extra = {k: v for k, v in p.items() if k != key}
        if extra:
            label += '\n' + ', '.join(f'{k}={v}' for k, v in extra.items())
        return label
    return ATTACK_LABELS.get(name, name) + '\n' + parameter_text(raw)


def run_config(result):
    """Read optional saved config only; never infer seeds from case counts."""
    if isinstance(result.get('config'), dict):
        return deepcopy(result['config'])
    if result.get('output_dir'):
        try:
            data = json.loads((Path(result['output_dir']) / 'config.json').read_text(encoding='utf-8'))
            if data.get('run_id') == result.get('run_id') and isinstance(data.get('config'), dict):
                return data['config']
        except (OSError, ValueError):
            pass
    return {}


def prepare_charts(rows, result, filters, config=None):
    """Copy already-filtered rows, separate scopes/payloads; never aggregate metrics."""
    rows = deepcopy(rows)
    if len({r['scope'] for r in rows}) > 1:
        raise ValueError('Biểu đồ chỉ nhận một tập all hoặc common.')
    if not rows:
        return []
    config = config or {}
    methods = [m for m in METHODS if any(r.get('method') == m for r in rows)]
    scope = rows[0]['scope']
    groups_by_payload = {}
    for row in sorted(rows, key=summary_sort_key):
        if row.get('method') not in methods:
            continue
        try:
            params = json.dumps(json.loads(row['attack_parameter']), sort_keys=True, ensure_ascii=False)
        except (ValueError, TypeError):
            params = str(row['attack_parameter'])
        groups = groups_by_payload.setdefault(row['payload_bytes'], {})
        key = (row['attack'], params)
        group = groups.setdefault(key, {'attack': row['attack'], 'label': attack_label(row['attack'], params), 'values': {}, 'images': {}})
        if row['method'] in group['values']:
            raise ValueError('Có dòng tổng hợp trùng cấu hình; không tự gộp dữ liệu.')
        rate = row.get('image_success_mean')
        group['values'][row['method']] = (float(rate) * 100 if isinstance(rate, (int, float))
            and not isinstance(rate, bool) and math.isfinite(rate) and 0 <= rate <= 1 else None)
        group['images'][row['method']] = row.get('eligible_images')
    plots = []
    warning = '' if result.get('status') == 'completed' and not result.get('incomplete') else 'KẾT QUẢ CHƯA ĐẦY ĐỦ — ' + (
        'Đã hủy' if result.get('status') == 'cancelled' else str(result.get('status') or 'chưa xác định trạng thái'))
    seeds = config.get('seeds')
    seed_note = ('Seed nhiễu từ cấu hình: ' + ', '.join(map(str, seeds)) + '; tác động xác định không dùng seed.'
                 if isinstance(seeds, list) and seeds else '')
    for payload, groups in groups_by_payload.items():
        items = list(groups.values())
        plots.append({'run_id': result.get('run_id') or 'Thiếu run ID', 'scope': scope,
            'scope_note': SCOPE_NOTES.get(scope, 'Thiếu thông tin tập ảnh'), 'payload': payload,
            'methods': methods[:], 'groups': items, 'warning': warning, 'seed_note': seed_note,
            'filters': deepcopy(filters), 'attacks': list(dict.fromkeys(ATTACK_LABELS.get(g['attack'], g['attack']) for g in items)),
            'limit_note': LIMIT_NOTE})
    return plots


def wrapped(text, width):
    return '\n'.join(textwrap.fill(line, width=width, break_long_words=True, break_on_hyphens=False)
                     for line in text.split('\n'))


def chart_display_groups(plot):
    """Partition presentation only; missing methods/NA never count as zero."""
    visible, zero = [], []
    for group in plot['groups']:
        target = zero if all(group['values'].get(m) == 0 for m in plot['methods']) else visible
        target.append(deepcopy(group))
    return visible, zero


def chart_figure(plot):
    """Same figure for GUI and PNG; complete labels, no relative normalization."""
    groups, zero_groups = chart_display_groups(plot)
    methods = plot['methods']
    all_groups = plot['groups']
    label_width = 12 if len(groups) > 6 else 24
    labels = []
    varying_counts = any(len({g['images'].get(m) for g in all_groups}) > 1 for m in methods)
    for group in groups:
        counts = '; '.join(f'{m}: {group["images"].get(m) if group["images"].get(m) is not None else "NA"} ảnh' for m in methods)
        labels.append(wrapped(group['label'], label_width) + ('\n' + wrapped(counts, label_width) if varying_counts else ''))
    title = f'Payload {plot["payload"]} byte: tỷ lệ khôi phục đúng toàn bộ packet (%)'
    notes = [f'Run ID: {plot["run_id"]}', 'Tập: ' + plot['scope_note'],
             'Tác động trong biểu đồ: ' + ', '.join(plot['attacks']),
             'Bộ lọc lúc mở: ' + '; '.join(f'{k}: {v}' for k, v in plot['filters'].items())]
    for method in methods:
        counts = {g['images'].get(method) for g in all_groups}
        notes.append(f'{method}, payload {plot["payload"]} byte: ' +
                     (f'{next(iter(counts))} ảnh đủ điều kiện.' if len(counts) == 1 and None not in counts else 'Số ảnh đủ điều kiện ghi ở từng nhóm.'))
    if plot['seed_note']:
        notes.append(plot['seed_note'])
    if plot['warning']:
        notes.append(plot['warning'])
    counts_note = '; '.join(f'{m}: {next(iter({g["images"].get(m) for g in all_groups})) if all_groups[0]["images"].get(m) is not None else "NA"} ảnh' for m in methods) if not varying_counts else 'Số ảnh đủ điều kiện ghi ở từng nhóm.'
    header = wrapped('Đúng TB theo ảnh (%) · ' + ('Baseline chung PVD/DWT' if plot['scope'] == 'common' else 'Baseline hợp lệ riêng từng phương pháp')
                     + ' · ' + counts_note, 105)
    if plot['warning']:
        header += '\n' + plot['warning']
    zero_note = ''
    if zero_groups:
        entries = []
        for group in zero_groups:
            counts = '; '.join(f'{m}: {group["images"].get(m) if group["images"].get(m) is not None else "NA"} ảnh' for m in methods)
            entries.append(group['label'].replace('\n', ' ') + (f' ({counts})' if varying_counts else ''))
        zero_note = ('Tất cả đều 0% — ' + '/'.join(methods) + f', {len(zero_groups)} cấu hình: '
                     + '; '.join(entries) + '.\nChỉ rút gọn cách vẽ; bảng tổng hợp vẫn giữ đầy đủ từng cấu hình.\n')
    footer = wrapped(zero_note + '\n'.join(notes) + '\n' + plot['limit_note'] + '\nKhông xác định: giá trị thiếu/NA; không phải 0%.', 120)
    top_inches = .75 + .17 * (header.count('\n') + 1)
    footer_inches = .17 * (footer.count('\n') + 1) + .3
    bottom_inches = footer_inches + .6 + .19 * max((label.count('\n') + 1 for label in labels), default=1)
    height = top_inches + 3.5 + bottom_inches
    fig = Figure(figsize=(max(10, len(groups) * 1.15), height), dpi=100, facecolor='white')
    FigureCanvasAgg(fig)
    fig.text(.04, 1 - .16 / height, title, ha='left', va='top', fontsize=13, weight='bold')
    fig.text(.04, 1 - .5 / height, header, ha='left', va='top', fontsize=9,
             color='#b42318' if plot['warning'] else '#1d2939')
    ax = fig.add_axes([.09, bottom_inches / height, .87, 3.5 / height])
    ax.set_ylim(0, 100)
    ax.set_yticks([0, 20, 40, 60, 80, 100], labels=['0%', '20%', '40%', '60%', '80%', '100%'])
    ax.set_ylabel('Tỷ lệ khôi phục đúng TB theo ảnh (%)')
    ax.set_axisbelow(True)
    ax.grid(axis='y', color='#e4e7ec')
    width = .32 if len(methods) == 2 else .48
    for method in methods:
        color = COLORS[METHODS.index(method)]
        for index, group in enumerate(groups):
            x = index + (methods.index(method) - (len(methods) - 1) / 2) * width
            value = group['values'].get(method)
            if value is not None:
                ax.bar(x, value, width=width * .9, color=color)
                label = f'{value:.2f}'.rstrip('0').rstrip('.') + '%'
                ax.annotate(label, (x, value), xytext=(0, -14 if value >= 95 else 5), textcoords='offset points',
                            ha='center', va='top' if value >= 95 else 'bottom', fontsize=8, color='#1d2939')
            else:
                ax.annotate('Không xác định', (x, 0), xytext=(0, 8), textcoords='offset points',
                            ha='center', va='bottom', rotation=90, fontsize=8, color='#596579')
    ax.set_xlim(-.65, max(1, len(groups)) - .35)
    if not groups:
        ax.text(.5, .5, 'Tất cả cấu hình đang chọn đều 0%\nDanh sách đầy đủ ở dưới biểu đồ.',
                transform=ax.transAxes, ha='center', va='center', color='#596579')
    ax.set_xticks(range(len(groups)), labels=labels, fontsize=9)
    ax.legend(handles=[Patch(facecolor=COLORS[METHODS.index(m)], label=m) for m in methods],
              loc='upper left', bbox_to_anchor=(0, -(bottom_inches - footer_inches - .4) / 3.5), ncols=len(methods), frameon=False)
    fig.text(.04, .18 / height, footer, ha='left', va='bottom', fontsize=9, color='#596579')
    return fig


def save_png(figure, path):
    figure.savefig(path, format='png', dpi=160, bbox_inches='tight', pad_inches=.25)


class BatchChartWindow(tk.Toplevel):
    def __init__(self, parent, plots):
        super().__init__(parent)
        self.title('Biểu đồ Bộ ảnh — bản chụp kết quả đang lọc')
        self.geometry('1000x760')
        self.minsize(650, 450)
        self.plots = deepcopy(plots)
        self.figures = []
        self.photos = []
        self.transient(parent.winfo_toplevel())
        container = ttk.Frame(self)
        container.pack(fill='both', expand=True)
        container.rowconfigure(0, weight=1)
        container.columnconfigure(0, weight=1)
        self.scroll_canvas = tk.Canvas(container, background='white', highlightthickness=0)
        self.scroll_canvas.grid(row=0, column=0, sticky='nsew')
        vertical = ttk.Scrollbar(container, command=self.scroll_canvas.yview)
        horizontal = ttk.Scrollbar(container, orient='horizontal', command=self.scroll_canvas.xview)
        vertical.grid(row=0, column=1, sticky='ns')
        horizontal.grid(row=1, column=0, sticky='ew')
        self.scroll_canvas.configure(yscrollcommand=vertical.set, xscrollcommand=horizontal.set)
        content = ttk.Frame(self.scroll_canvas)
        self.scroll_canvas.create_window((0, 0), window=content, anchor='nw')
        content.bind('<Configure>', lambda e: self.scroll_canvas.configure(scrollregion=self.scroll_canvas.bbox('all')))
        for index, plot in enumerate(self.plots):
            panel = ttk.Frame(content)
            panel.pack(fill='x', pady=10)
            ttk.Button(panel, text=f'Lưu biểu đồ tổng quát PNG — Payload {plot["payload"]} byte',
                       command=lambda i=index: self.choose_save(i)).pack(anchor='w', padx=10)
            fig = chart_figure(plot)
            self.figures.append(fig)
            # Agg pixels keep the preview's size predictable on scaled Windows displays.
            fig.canvas.draw()
            preview = Image.frombytes('RGBA', fig.canvas.get_width_height(), bytes(fig.canvas.buffer_rgba()))
            photo = ImageTk.PhotoImage(preview, master=self)
            self.photos.append(photo)
            ttk.Label(panel, image=photo).pack()
        self.protocol('WM_DELETE_WINDOW', self.close)

    def choose_save(self, index):
        plot = self.plots[index]
        run_id = re.sub(r'[^\w-]', '_', plot['run_id'])
        attacks = re.sub(r'[^\w-]', '_', '_'.join(dict.fromkeys(g['attack'] for g in plot['groups'])))
        path = filedialog.asksaveasfilename(parent=self, title='Lưu biểu đồ PNG', defaultextension='.png',
            filetypes=[('Ảnh PNG', '*.png')], initialfile=f'{run_id}_{plot["scope"]}_payload_{plot["payload"]}_{attacks}_{index + 1}.png')
        if path:
            try:
                save_png(self.figures[index], path)
            except OSError as exc:
                messagebox.showerror('Không lưu được biểu đồ', str(exc), parent=self)

    def close(self):
        for figure in self.figures:
            figure.clear()
        self.destroy()
        self.photos.clear()
