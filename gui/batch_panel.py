"""Dataset controls; queue polling and all widgets live on the Tk thread."""

from copy import deepcopy
from decimal import Decimal, InvalidOperation
import json
import os
from pathlib import Path
from queue import Queue, Empty, Full
from threading import Event
import tkinter as tk
from tkinter import ttk, filedialog
from tkinter.font import Font

from experiments.batch_runner import scan_directory, batch_config, planned_counts
from experiments.experiment_config import default_config
from services.robustness import ATTACK_LABELS, PARAMETER_HELP

SUMMARY_COLUMNS = [
    ('method', 'PP'), ('payload_bytes', 'Byte'), ('attack', 'Tác động'),
    ('attack_parameter', 'Tham số'), ('eligible_images', 'Ảnh'),
    ('image_success_mean', 'Đúng TB (%)'), ('image_ber_mean', 'BER TB'),
    ('ber_na_cases', 'Ca BER NA'),
]
ALL = 'Tất cả'
COMMON_SCOPE = 'Baseline chung PVD/DWT'
ALL_SCOPE = 'Toàn bộ ảnh'
MISSING = 'Thiếu dữ liệu'


def numeric_key(value):
    try:
        number = Decimal(str(value))
        if number.is_finite():
            return (0, number)
    except InvalidOperation:
        pass
    return (1, str(value))


def summary_sort_key(row):
    try:
        parameters = json.loads(row.get('attack_parameter', '{}'))
        levels = tuple((key, numeric_key(value)) for key, value in sorted(parameters.items()))
    except (ValueError, AttributeError):
        levels = (('', numeric_key(row.get('attack_parameter', ''))),)
    attacks = list(ATTACK_LABELS)
    name = row.get('attack', '')
    return (numeric_key(row.get('payload_bytes')), attacks.index(name) if name in attacks else len(attacks),
            name, levels, {'PVD': 0, 'DWT': 1}.get(row.get('method'), 2))


def display_number(value, percent=False, sd=False):
    if value is None or value == 'NA':
        return 'NA'
    if value == MISSING:
        return MISSING
    if percent or sd:
        return f'{value * 100:.3f}'.replace('.', ',') + ' điểm phần trăm' if sd else f'{value * 100:.2f}%'
    return f'{value:.6f}' if isinstance(value, float) else str(value)


def parameter_text(raw):
    if raw is None:
        return MISSING
    try:
        parameters = json.loads(raw)
        return ', '.join(f'{k}={v}' for k, v in parameters.items()) or '—'
    except (ValueError, AttributeError):
        return str(raw)


def detail_text(row, result):
    labels = [
        ('method', 'Phương pháp'), ('payload_bytes', 'Payload (byte)'),
        ('expected_images', 'Tổng số ảnh dự kiến'), ('eligible_images', 'Ảnh đủ điều kiện trong tập chọn'),
        ('baseline_valid', 'Baseline hợp lệ'), ('baseline_capacity', 'Baseline không đủ dung lượng'),
        ('baseline_embed_io_error', 'Baseline lỗi nhúng/lưu/đọc'), ('baseline_mismatch', 'Baseline không khớp'),
        ('baseline_unprocessed', 'Baseline chưa xử lý'), ('completed_cases', 'Ca hoàn tất'),
        ('success_cases', 'Ca khôi phục đúng toàn bộ packet'), ('pooled_success_rate', 'Tỷ lệ đúng gộp'),
        ('image_success_mean', 'Tỷ lệ đúng TB theo ảnh'), ('image_success_std', 'SD mẫu giữa các ảnh'),
        ('image_ber_mean', 'BER TB theo ảnh (0–1)'), ('ber_valid_cases', 'Ca BER hợp lệ'),
        ('ber_na_cases', 'Ca BER không xác định'), ('ber_contributing_images', 'Ảnh góp BER'),
        ('ber_no_valid_images', 'Ảnh đã thử nhưng không có BER hợp lệ'),
    ]
    lines = ['Tập ảnh: ' + (COMMON_SCOPE if row.get('scope') == 'common' else
                           ALL_SCOPE if row.get('scope') == 'all' else MISSING),
             'Tác động: ' + ATTACK_LABELS.get(row.get('attack'), str(row.get('attack', MISSING))),
             'Tham số đầy đủ: ' + str(row.get('attack_parameter', MISSING)), '']
    for key, title in labels:
        lines.append(title + ': ' + display_number(row.get(key, MISSING),
            percent=key in ('pooled_success_rate', 'image_success_mean'), sd=key == 'image_success_std'))
    lines += ['', 'Các số lượng baseline đếm trên TOÀN TẬP DỰ KIẾN, kể cả khi chọn tập common.',
              'NA: Không xác định; không phải 0 hoặc 1. SD dưới 2 ảnh là NA.',
              'SD = 0 không tự chứng minh độ ổn định tổng quát hoặc nguyên nhân do seed.',
              'Tỷ lệ đúng toàn bộ packet là chỉ số chính. BER chỉ trên ca đủ điều kiện; đọc cùng số ca BER NA.',
              '', 'Trạng thái lần chạy: ' + str(result.get('status', MISSING)),
              'Thư mục kết quả: ' + str(result.get('output_dir', MISSING))]
    return '\n'.join(lines)


def completed_caption(result):
    """Attribute omissions only when the supplied baseline inventory supports it."""
    completed = result.get('completed_cases', MISSING)
    counts = result.get('counts', {})
    baselines = result.get('baselines')
    embeddings, cases = counts.get('embeddings'), counts.get('cases')
    known = {'valid', 'capacity', 'embed_io_error', 'mismatch'}
    if (isinstance(embeddings, int) and embeddings > 0 and isinstance(cases, int)
            and cases % embeddings == 0 and isinstance(baselines, list) and len(baselines) == embeddings
            and all(b.get('baseline_status') in known for b in baselines)
            and len({(b.get('image_id'), b.get('method'), b.get('payload_bytes')) for b in baselines}) == embeddings):
        skipped = sum(b['baseline_status'] != 'valid' for b in baselines) * (cases // embeddings)
        text = f'Hoàn tất: {completed} ca đã chạy; {skipped} ca không chạy do baseline không hợp lệ.'
        if isinstance(completed, int) and cases != completed + skipped:
            text += f' Chênh lệch khác: {cases - completed - skipped} ca; chưa xác định nguyên nhân.'
        return text
    return f'Hoàn tất: {completed} ca đã chạy; thiếu dữ liệu để xác định số ca bỏ do baseline.'


def integer_list(text):
    values = [int(v.strip()) for v in text.replace(';', ',').split(',') if v.strip()]
    if not values or any(v < 0 for v in values):
        raise ValueError('Nhập danh sách số nguyên không âm, cách nhau bằng dấu phẩy.')
    return list(dict.fromkeys(values))


def scroll_table(parent, columns, height):
    frame = ttk.Frame(parent)
    frame.pack(fill='x', pady=4)
    table = ttk.Treeview(frame, columns=[k for k, _ in columns], show='headings', height=height)
    for key, label in columns:
        table.heading(key, text=label)
        table.column(key, width=150, minwidth=90, stretch=False)
    vertical = ttk.Scrollbar(frame, command=table.yview)
    horizontal = ttk.Scrollbar(frame, orient='horizontal', command=table.xview)
    table.configure(yscrollcommand=vertical.set, xscrollcommand=horizontal.set)
    table.grid(row=0, column=0, sticky='nsew')
    vertical.grid(row=0, column=1, sticky='ns')
    horizontal.grid(row=1, column=0, sticky='ew')
    frame.columnconfigure(0, weight=1)
    return table


class BatchPanel(ttk.Frame):
    def __init__(self, parent, compare):
        super().__init__(parent)
        self.compare, self.app = compare, compare.app
        self.version = 0
        self.entries, self.result = [], None
        self.cancel_event = None
        self.active = False
        self.row_data = {}
        self.config_expanded = True
        self.columnconfigure(0, weight=1)
        self.rowconfigure(6, weight=1)
        style = ttk.Style(self)
        style.configure('Batch.TButton', padding=(8, 4))
        style.configure('Batch.Horizontal.TProgressbar', background='#176b78', troughcolor='#e4e7ec',
                        bordercolor='#c8d2d8', lightcolor='#176b78', darkcolor='#176b78')
        self.top_actions = ttk.Frame(self)
        self.top_actions.grid(row=0, column=0, sticky='ew', pady=(0, 4))
        self.toggle_button = ttk.Button(self.top_actions, text='Thu gọn cấu hình ▴',
                                        command=self.toggle_config, style='Batch.TButton')
        self.toggle_button.pack(side='left', padx=(0, 8))
        self.config_container = ttk.Frame(self, height=250)
        self.config_container.grid(row=1, column=0, sticky='ew')
        self.config_container.grid_propagate(False)
        self.config_container.columnconfigure(0, weight=1)
        self.config_container.rowconfigure(0, weight=1)
        self.config_canvas = tk.Canvas(self.config_container, background='#f4f6f8', highlightthickness=0)
        self.config_canvas.grid(row=0, column=0, sticky='nsew')
        config_scroll = ttk.Scrollbar(self.config_container, command=self.config_canvas.yview)
        config_scroll.grid(row=0, column=1, sticky='ns')
        cfg = ttk.Frame(self.config_canvas)
        config_window = self.config_canvas.create_window((0, 0), window=cfg, anchor='nw')
        self.config_canvas.configure(yscrollcommand=config_scroll.set)
        cfg.bind('<Configure>', lambda e: self.config_canvas.configure(scrollregion=self.config_canvas.bbox('all')))
        self.config_canvas.bind('<Configure>', lambda e: self.config_canvas.itemconfigure(config_window, width=e.width))
        self.source = tk.StringVar()
        self.destination = tk.StringVar(value=str(Path(__file__).resolve().parents[1] / 'experiments' / 'batch_results'))
        config = default_config()
        self.payloads = tk.StringVar(value=', '.join(str(l['value']) for l in config['payload_levels']))
        self.seeds = tk.StringVar(value=', '.join(str(s) for s in range(config['seed'], config['seed'] + 5)))
        for title, variable, command in [('Thư mục ảnh', self.source, self.choose_source),
                                         ('Thư mục đầu ra', self.destination, self.choose_destination)]:
            row = ttk.Frame(cfg)
            row.pack(fill='x', pady=2)
            ttk.Button(row, text=title, command=command).pack(side='left')
            ttk.Entry(row, textvariable=variable).pack(side='left', fill='x', expand=True, padx=6)
        ttk.Button(cfg, text='Đọc danh sách / kiểm tra cấu hình', command=self.inspect).pack(anchor='w')
        self.inventory = scroll_table(cfg, [('name', 'Tên file'), ('size', 'Kích thước'),
                                   ('mode', 'Mode gốc → xử lý'), ('status', 'Trạng thái / lỗi')], 3)
        self.notice = ttk.Label(cfg, wraplength=850, text='Chọn ảnh PNG/BMP trực tiếp trong thư mục; không đọc đệ quy.')
        self.notice.pack(fill='x')
        for title, variable in [('Payload bytes (dấu phẩy)', self.payloads), ('Seed (dấu phẩy; chỉ dùng cho nhiễu)', self.seeds)]:
            row = ttk.Frame(cfg)
            row.pack(fill='x', pady=2)
            ttk.Label(row, text=title, width=42).pack(side='left')
            ttk.Entry(row, textvariable=variable).pack(side='left', fill='x', expand=True)
        ttk.Label(cfg, text='Baseline “Không tác động” luôn được thêm. Chọn tác động và nhập nhiều mức, cách nhau dấu phẩy.').pack(anchor='w')
        self.attacks = {}
        grid = ttk.Frame(cfg)
        grid.pack(fill='x')
        for index, (name, label) in enumerate(ATTACK_LABELS.items()):
            if name == 'none':
                continue
            levels = [a['parameters'] for a in config['attacks'] if a['name'] == name]
            key = next(iter(levels[0]))
            enabled = tk.BooleanVar(value=True)
            values = tk.StringVar(value=', '.join(str(l[key]) for l in levels))
            row = index - 1
            ttk.Checkbutton(grid, text=label, variable=enabled).grid(row=row, column=0, sticky='w')
            ttk.Entry(grid, textvariable=values, width=23).grid(row=row, column=1, sticky='ew', padx=6)
            ttk.Label(grid, text=PARAMETER_HELP[key]).grid(row=row, column=2, sticky='w')
            self.attacks[name] = (key, enabled, values)
        grid.columnconfigure(1, weight=1)
        self.plan = ttk.Label(cfg, text='Chưa kiểm tra cấu hình.', wraplength=850)
        self.plan.pack(fill='x', pady=5)
        actions = self.top_actions
        self.run_button = ttk.Button(actions, text='Chạy Bộ ảnh', command=self.start, style='Batch.TButton')
        self.run_button.pack(side='left')
        self.cancel_button = ttk.Button(actions, text='Hủy', command=self.cancel, state='disabled', style='Batch.TButton')
        self.cancel_button.pack(side='left', padx=8)
        self.progress = ttk.Progressbar(actions, style='Batch.Horizontal.TProgressbar', mode='determinate')
        self.progress.pack(side='left', fill='x', expand=True, padx=(12, 0))
        self.progress_text = ttk.Label(self, text='Chưa chạy.', wraplength=850)
        self.progress_text.grid(row=3, column=0, sticky='ew')
        self.common = tk.BooleanVar(value=True)
        self.filter_method = tk.StringVar(value=ALL)
        self.filter_payload = tk.StringVar(value=ALL)
        self.filter_attack = tk.StringVar(value=ALL)
        self.filter_scope = tk.StringVar(value=COMMON_SCOPE)
        filters = ttk.Frame(self)
        filters.grid(row=4, column=0, sticky='ew', pady=(6, 3))
        self.filters = {}
        for key, label, variable, values, width in [
            ('method', 'PP:', self.filter_method, [ALL, 'PVD', 'DWT'], 8),
            ('payload', 'Byte:', self.filter_payload, [ALL], 8),
            ('attack', 'Tác động:', self.filter_attack, [ALL], 19),
            ('scope', 'Tập:', self.filter_scope, [COMMON_SCOPE, ALL_SCOPE], 23),
        ]:
            ttk.Label(filters, text=label).pack(side='left', padx=(0, 3))
            combo = ttk.Combobox(filters, textvariable=variable, values=values, state='readonly', width=width)
            combo.pack(side='left', padx=(0, 8))
            self.filters[key] = combo
        self.scope_label = ttk.Label(self, wraplength=900)
        self.scope_label.grid(row=5, column=0, sticky='ew', pady=(0, 4))
        table_frame = ttk.Frame(self)
        table_frame.grid(row=6, column=0, sticky='nsew')
        table_frame.columnconfigure(0, weight=1)
        table_frame.rowconfigure(0, weight=1)
        self.table = ttk.Treeview(table_frame, columns=[k for k, _ in SUMMARY_COLUMNS], show='headings', height=3,
                                  selectmode='browse')
        for key, label in SUMMARY_COLUMNS:
            self.table.heading(key, text=label)
            self.table.column(key, stretch=False, anchor='w' if key in ('method', 'attack', 'attack_parameter') else 'e')
        self.table.grid(row=0, column=0, sticky='nsew')
        self.body_font = Font(self, font=ttk.Style(self).lookup('Treeview', 'font'))
        self.heading_font = Font(self, font=ttk.Style(self).lookup('Treeview.Heading', 'font'))
        vertical = ttk.Scrollbar(table_frame, command=self.table.yview)
        vertical.grid(row=0, column=1, sticky='ns')
        self.table.configure(yscrollcommand=vertical.set)
        self.table.bind('<Configure>', self.resize_columns)
        self.table.bind('<<TreeviewSelect>>', self.selection_changed)
        self.table.bind('<Double-1>', self.show_detail)
        self.legend = ttk.Label(self, wraplength=900, text=
            'Đúng TB: khôi phục toàn bộ packet TB theo ảnh — chỉ số chính. BER TB (0–1): đọc cùng Ca BER NA.\n'
            'NA: Không xác định; không phải 0 hoặc 1. SD = 0 không tự chứng minh ổn định tổng quát. PP/Ảnh: phương pháp/ảnh đủ điều kiện.')
        self.legend.grid(row=7, column=0, sticky='ew', pady=4)
        footer = ttk.Frame(self)
        footer.grid(row=8, column=0, sticky='ew')
        self.detail_button = ttk.Button(footer, text='Xem chi tiết', command=self.show_detail, state='disabled', style='Batch.TButton')
        self.detail_button.pack(side='left')
        self.chart_button = ttk.Button(footer, text='Xem biểu đồ', command=self.show_chart,
                                        state='disabled', style='Batch.TButton')
        self.chart_button.pack(side='left', padx=(8, 0))
        self.open_button = ttk.Button(footer, text='Mở thư mục kết quả', command=self.open_output, state='disabled', style='Batch.TButton')
        self.open_button.pack(side='left', padx=8)
        self.row_count = ttk.Label(footer, text='Chưa có kết quả.')
        self.row_count.pack(side='right')
        self.filter_scope.trace_add('write', self.scope_changed)
        for variable in (self.filter_method, self.filter_payload, self.filter_attack):
            variable.trace_add('write', self.show_summary)
        self.show_summary()
        self.bind('<Configure>', self.fit_layout)
        for variable in (self.source, self.destination, self.payloads, self.seeds):
            variable.trace_add('write', self.changed)
        for _, enabled, values in self.attacks.values():
            enabled.trace_add('write', self.changed)
            values.trace_add('write', self.changed)

    def changed(self, *args):
        self.version += 1
        self.result = None
        self.table.delete(*self.table.get_children())
        self.open_button.configure(state='disabled')
        self.row_data = {}
        self.detail_button.configure(state='disabled')
        self.chart_button.configure(state='disabled')
        self.row_count.configure(text='Chưa có kết quả cho cấu hình này.')
        self.plan.configure(text='Cấu hình đã đổi; kiểm tra lại trước khi chạy.')
        self.progress.configure(value=0)
        self.progress_text.configure(text='Đang chạy cấu hình đã chụp; lựa chọn mới chưa có kết quả.'
                                      if self.active else 'Cấu hình đã đổi; chưa có kết quả.')

    def fit_layout(self, event):
        if event.widget != self:
            return
        self.legend.configure(wraplength=max(100, event.width - 4))
        self.scope_label.configure(wraplength=max(100, event.width - 4))
        self.progress_text.configure(wraplength=max(100, event.width - 4))
        fixed = sum(max(w.winfo_reqheight() for w in self.grid_slaves(row=row))
                    for row in (0, 3, 4, 5, 7, 8)) + 32
        height = min(250, max(70, event.height - fixed - 80))
        if int(self.config_container.cget('height')) != height:
            self.config_container.configure(height=height)

    def toggle_config(self):
        self.set_config_expanded(not self.config_expanded)

    def set_config_expanded(self, expanded):
        self.config_expanded = expanded
        if expanded:
            self.config_container.grid()
        else:
            self.config_container.grid_remove()
        self.toggle_button.configure(text='Thu gọn cấu hình ▴' if expanded else 'Mở cấu hình ▾')

    def scope_changed(self, *args):
        self.common.set(self.filter_scope.get() == COMMON_SCOPE)
        self.show_summary()

    def resize_columns(self, event):
        # A single table fits the viewport, so the four identifiers never scroll away.
        minimums = [self.heading_font.measure(label) + 18 for _, label in SUMMARY_COLUMNS]
        minimums[1] = max(minimums[1], 55)
        minimums[2] = max(minimums[2], 165)
        minimums[3] = max(minimums[3], 110)
        minimums[6] = max(minimums[6], 100)
        available = max(1, event.width - 4)
        extra = max(0, available - sum(minimums))
        weights = [1, 1, 3, 3, 1, 1, 1, 1]
        widths = [w + extra * weight // sum(weights) for w, weight in zip(minimums, weights)]
        widths[-1] += available - sum(widths)
        for (key, _), width in zip(SUMMARY_COLUMNS, widths):
            self.table.column(key, width=max(1, width), minwidth=max(1, width))
        self.refresh_cells()

    def short_text(self, text, key):
        font = self.body_font
        available = int(self.table.column(key, 'width')) - 12
        if font.measure(text) <= available:
            return text
        while text and font.measure(text + '…') > available:
            text = text[:-1]
        return text + '…'

    def row_values(self, row):
        values = []
        for key, _ in SUMMARY_COLUMNS:
            value = row.get(key, MISSING)
            if key == 'attack':
                value = self.short_text(ATTACK_LABELS.get(value, str(value)), key)
            elif key == 'attack_parameter':
                value = self.short_text(parameter_text(value), key)
            else:
                value = display_number(value, percent=key == 'image_success_mean')
            values.append(value)
        return values

    def refresh_cells(self):
        for iid in self.table.get_children():
            if iid in self.row_data:
                self.table.item(iid, values=self.row_values(self.row_data[iid]))

    def selection_changed(self, event=None):
        self.detail_button.configure(state='normal' if self.table.selection() else 'disabled')

    def show_detail(self, event=None):
        selection = self.table.selection()
        if not selection or not self.result:
            return None
        row = self.row_data[selection[0]]
        window = tk.Toplevel(self)
        window.title('Chi tiết nhóm thực nghiệm')
        window.transient(self.app)
        window.geometry(f'740x650+{max(0, self.app.winfo_rootx() + 80)}+{max(0, self.app.winfo_rooty() + 20)}')
        window.minsize(480, 360)
        frame = ttk.Frame(window, padding=12)
        frame.pack(fill='both', expand=True)
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)
        text = tk.Text(frame, wrap='word', font=('Segoe UI', 10), padx=10, pady=8)
        vertical = ttk.Scrollbar(frame, command=text.yview)
        text.configure(yscrollcommand=vertical.set)
        text.grid(row=0, column=0, sticky='nsew')
        vertical.grid(row=0, column=1, sticky='ns')
        text.insert('1.0', detail_text(row, self.result))
        text.configure(state='disabled')
        window.detail_text = text
        window.detail_scroll = vertical
        return window

    def show_chart(self):
        if not self.result or not self.row_data:
            return None
        from gui.batch_chart import prepare_charts, run_config, BatchChartWindow
        filters = {'Phương pháp': self.filter_method.get(), 'Payload': self.filter_payload.get(),
                   'Tác động': self.filter_attack.get(), 'Tập': self.filter_scope.get()}
        plots = prepare_charts(list(self.row_data.values()), self.result, filters, run_config(self.result))
        return BatchChartWindow(self, plots) if plots else None

    def choose_source(self):
        folder = filedialog.askdirectory(parent=self)
        if folder:
            self.source.set(folder)
            self.inspect()

    def choose_destination(self):
        folder = filedialog.askdirectory(parent=self)
        if folder:
            self.destination.set(folder)

    def capture_config(self):
        config = default_config()
        config['payload_levels'] = [{'kind': 'bytes', 'value': v} for v in integer_list(self.payloads.get())]
        config['seeds'] = integer_list(self.seeds.get())
        config['attacks'] = []
        for name, (key, enabled, values) in self.attacks.items():
            if enabled.get():
                tokens = [s.strip() for s in values.get().split(',') if s.strip()]
                if not tokens:
                    raise ValueError('Cần ít nhất một mức cho ' + ATTACK_LABELS[name])
                config['attacks'].extend({'name': name, 'parameters': {key: token}} for token in tokens)
        return batch_config(config)

    def inspect(self):
        try:
            entries = scan_directory(self.source.get())
            self.entries = entries
            self.inventory.delete(*self.inventory.get_children())
            for e in entries:
                self.inventory.insert('', 'end', values=(e['name'], f'{e.get("width", "?")} × {e.get("height", "?")}',
                    f'{e.get("mode", "?")} → {e.get("effective_mode", "?")}', e.get('error', 'Đọc được')))
            config = self.capture_config()
            if not self.destination.get().strip():
                raise ValueError('Cần thư mục đầu ra.')
            paths = [e['path'] for e in entries if e['status'] == 'ready']
            if not paths:
                raise ValueError('Không có ảnh đọc được; xem lỗi trong danh sách file.')
            counts = planned_counts(len(paths), config)
            self.notice.configure(text=f'{len(paths)} ảnh đọc được; {len(entries) - len(paths)} file bị loại. '
                'Khuyến nghị 10–20 ảnh thật gồm xám, màu, vùng phẳng và nhiều chi tiết. Không tự phân loại ảnh.' +
                (' Lưu ý: ít hơn 10 ảnh; vẫn cho phép chạy kiểm tra.' if len(paths) < 10 else ''))
            self.plan.configure(text=f'{counts["images"]} ảnh × 2 phương pháp: {counts["embeddings"]} cấu hình nhúng; '
                f'tối đa {counts["cases"]} ca (gồm baseline). Baseline lỗi sẽ bỏ tác động. Seed trùng được loại.')
            return paths, config, str(Path(self.destination.get()).resolve())
        except (OSError, ValueError) as exc:
            self.compare.show_error(str(exc))
            return None

    def update_busy(self):
        self.run_button.configure(state='disabled' if self.app.busy else 'normal')
        self.cancel_button.configure(state='normal' if self.active and self.app.busy else 'disabled')

    def start(self):
        if self.app.busy:
            return
        captured = self.inspect()
        if captured is None:
            return
        paths, config, destination = captured
        self.changed()
        # Keep the validated plan visible after clearing the previous result.
        counts = planned_counts(len(paths), config)
        self.plan.configure(text=f'{len(paths)} ảnh; {counts["embeddings"]} cấu hình nhúng; {counts["cases"]} ca dự kiến.')
        token, compare_token = self.version, self.compare.version
        self.cancel_event = Event()
        event = self.cancel_event
        queue = Queue(maxsize=1)
        self.active = True
        self.progress.configure(value=0, maximum=counts['cases'])
        self.progress_text.configure(text='Đang chạy; kết quả chưa đầy đủ.')
        service = self.app.service
        def report(value):
            try:
                queue.put_nowait(value)
            except Full:
                try:
                    queue.get_nowait()
                except Empty:
                    pass
                queue.put_nowait(value)
        def poll():
            if not self.active or not self.app.busy:
                return
            try:
                p = queue.get_nowait()
                if token == self.version and compare_token == self.compare.version:
                    self.progress.configure(value=p['completed'])
                    self.progress_text.configure(text=f'{p["completed"]}/{p["total"]} ca hoàn tất; '
                        f'{p["baselines"]}/{p["embeddings"]} baseline; ảnh: {p["image"]}. Kết quả chưa đầy đủ.')
            except Empty:
                pass
            if self.active and self.app.busy:
                self.after(80, poll)
        def completed(result):
            self.active = False
            self.update_busy()
            if token != self.version or compare_token != self.compare.version:
                self.progress_text.configure(text='Cấu hình cũ đã hoàn tất; lựa chọn hiện tại chưa có kết quả.')
                self.app.set_status('Bộ ảnh cấu hình cũ hoàn tất; bỏ hiển thị. File được giữ tại thư mục đã chọn.')
                return
            self.present_result(result)
        def failed(exc):
            self.active = False
            self.update_busy()
            if token != self.version or compare_token != self.compare.version:
                self.progress_text.configure(text='Cấu hình cũ bị lỗi; lựa chọn hiện tại chưa có kết quả.')
                return
            self.progress_text.configure(text='Lỗi lần chạy; đầu ra có thể chưa đầy đủ: ' + str(exc))
        self.app.run_job(lambda: service.run_batch(paths, destination, deepcopy(config), event, report), completed, failed)
        self.update_busy()
        self.after(80, poll)

    def cancel(self):
        if self.active:
            self.cancel_event.set()
            self.progress_text.configure(text='Đang hủy sau ca hiện tại; sẽ lưu các ca đã hoàn tất.')

    def present_result(self, result):
        self.result = result
        total = result.get('counts', {}).get('cases', 0)
        completed = result.get('completed_cases', 0)
        self.progress.configure(maximum=max(1, total), value=completed)
        status = result.get('status')
        if status == 'completed':
            self.progress.configure(value=max(1, total))
            caption = completed_caption(result)
        elif status == 'cancelled':
            caption = f'Đã hủy — kết quả chưa đầy đủ: {completed}/{total} ca đã chạy.'
        else:
            caption = f'Lỗi lần chạy ({status or MISSING}); đầu ra có thể chưa đầy đủ: {completed}/{total} ca.'
        self.progress_text.configure(text=caption + (' ' + result['history_warning'] if result.get('history_warning') else ''))
        self.open_button.configure(state='normal' if result.get('output_dir') else 'disabled')
        self.set_filter_options()
        self.show_summary()
        if result.get('summary'):
            self.set_config_expanded(False)
        self.app.set_status('Đã hoàn tất Bộ ảnh.' if status == 'completed' else
                            'Đã hủy — kết quả chưa đầy đủ.' if status == 'cancelled' else 'Lỗi Bộ ảnh; đầu ra có thể chưa đầy đủ.')

    def set_filter_options(self):
        rows = self.result.get('summary', []) if self.result else []
        payloads = [ALL, *[str(v) for v in sorted({r['payload_bytes'] for r in rows if 'payload_bytes' in r}, key=numeric_key)]]
        attacks = {r['attack'] for r in rows if 'attack' in r}
        attack_values = [ALL, *[ATTACK_LABELS.get(a, a) for a in sorted(attacks, key=lambda a:
            (list(ATTACK_LABELS).index(a) if a in ATTACK_LABELS else len(ATTACK_LABELS), a))]]
        for key, variable, values in [('payload', self.filter_payload, payloads),
                                      ('attack', self.filter_attack, attack_values)]:
            self.filters[key].configure(values=values)
            if variable.get() not in values:
                variable.set(ALL)

    def show_summary(self, *args):
        selected = self.table.selection()
        self.table.delete(*self.table.get_children())
        self.row_data = {}
        self.scope_label.configure(text='Đang hiển thị: ' + (
            'Ảnh có baseline hợp lệ ở cả PVD và DWT, theo từng payload' if self.common.get() else
            'Toàn bộ ảnh có baseline hợp lệ của từng phương pháp'))
        if not self.result:
            self.chart_button.configure(state='disabled')
            self.row_count.configure(text='Chưa có kết quả.')
            self.selection_changed()
            return
        rows = sorted(enumerate(self.result.get('summary', [])), key=lambda item: summary_sort_key(item[1]))
        for index, row in rows:
            if (row['scope'] == 'common') != self.common.get():
                continue
            if self.filter_method.get() != ALL and row.get('method') != self.filter_method.get():
                continue
            if self.filter_payload.get() != ALL and str(row.get('payload_bytes')) != self.filter_payload.get():
                continue
            if self.filter_attack.get() != ALL and ATTACK_LABELS.get(row.get('attack'), row.get('attack')) != self.filter_attack.get():
                continue
            iid = str(index)
            self.row_data[iid] = row
            self.table.insert('', 'end', iid=iid, values=self.row_values(row))
        if selected and selected[0] in self.row_data:
            self.table.selection_set(selected[0])
        count = len(self.row_data)
        self.chart_button.configure(state='normal' if count else 'disabled')
        self.row_count.configure(text=f'Đang xem {count} dòng.' if count else '0 dòng — không có dòng phù hợp.')
        self.selection_changed()

    def open_output(self):
        if self.result:
            os.startfile(self.result['output_dir'])
