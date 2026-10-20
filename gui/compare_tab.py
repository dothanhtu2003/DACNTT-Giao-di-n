import tkinter as tk
import json
from tkinter import ttk
from copy import deepcopy

from gui.common import BaseTab, Preview, message_editor, format_value
from gui.compare_chart import CompareChart
from services.robustness import (ATTACK_LABELS, DEFAULT_PARAMETERS, PARAMETER_HELP,
                                 NOISE, SEED, validate_configuration)

ROWS = [('Capacity bits', 'capacity_bits'), ('Payload bytes', 'payload_bytes'),
        ('Packet bits', 'packet_bits'), ('Usage %', 'usage_percent'), ('bpp', 'bpp'),
        ('PSNR (dB)', 'psnr'), ('SSIM', 'ssim'),
        ('BER nhúng', 'ber'), ('Khôi phục packet', 'extract_status')]

ROBUSTNESS_ROWS = [
    ('Tác động và tham số', 'attack'), ('Seed', 'seed'),
    ('Kích thước ảnh sau tác động', 'dimensions'), ('BER sau tác động', 'ber'),
    ('Khôi phục toàn bộ packet', 'recovery'), ('Nguyên nhân / ghi chú', 'notes'),
]
PARAMETER_LABELS = {
    'quality': 'Chất lượng JPEG', 'sigma': 'Độ lệch chuẩn nhiễu',
    'amount': 'Tỷ lệ pixel nhiễu', 'kernel_size': 'Cạnh bộ lọc',
    'delta': 'Mức tăng độ sáng', 'alpha': 'Hệ số tương phản',
    'scale': 'Tỷ lệ mỗi chiều', 'fraction': 'Phần giữ lại mỗi chiều',
}
RESULT_COLORS = {'neutral': '#1d2939', 'muted': '#596579',
                 'success': '#166534', 'failure': '#b42318'}


class CompareTab(BaseTab):
    def __init__(self, parent, app):
        super().__init__(parent, app)
        self.results = {}
        self.version = 0
        self.robustness_results = {}
        self.mode = tk.StringVar(value='Một ảnh')
        self.batch_panel = None
        modes = ttk.Frame(self)
        modes.grid(row=0, column=0, sticky='ew', pady=(0, 6))
        for name in ('Một ảnh', 'Bộ ảnh'):
            ttk.Radiobutton(modes, text=name, variable=self.mode, value=name,
                            command=self.mode_changed).pack(side='left', padx=8)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        self.canvas = tk.Canvas(self, highlightthickness=0, background='#f4f6f8')
        self.canvas.grid(row=1, column=0, sticky='nsew')
        scroll = ttk.Scrollbar(self, orient='vertical', command=self.canvas.yview)
        self.page_scroll = scroll
        scroll.grid(row=1, column=1, sticky='ns')
        self.canvas.configure(yscrollcommand=scroll.set)
        self.viewport = ttk.Frame(self.canvas)
        self.content = ttk.Frame(self.viewport)
        self.content.pack(fill='x')
        window = self.canvas.create_window((0, 0), window=self.viewport, anchor='nw')
        self.viewport.bind('<Configure>', lambda e: self.canvas.configure(scrollregion=self.canvas.bbox('all')))
        self.canvas.bind('<Configure>', lambda e: self.canvas.itemconfigure(window, width=e.width))
        self.app.bind_all('<MouseWheel>', self.scroll_wheel, add='+')
        top = ttk.Frame(self.content, height=580)
        top.pack(fill='x')
        top.pack_propagate(False)
        top.grid_propagate(False)
        top.columnconfigure(0, weight=2)
        top.columnconfigure(1, weight=3)
        top.rowconfigure(0, weight=1)
        left = ttk.Frame(top)
        left.grid(row=0, column=0, sticky='nsew', padx=(0, 18))
        self.preview = Preview(left, 'Cùng ảnh nguồn', (320, 100))
        self.preview.pack(fill='both', expand=True)
        ttk.Button(left, text='Chọn ảnh PNG/BMP', command=self.choose).pack(anchor='w', pady=8)
        ttk.Label(left, text='Cùng văn bản UTF-8').pack(anchor='w')
        frame, self.message = message_editor(left, height=2)
        frame.pack(fill='both', expand=True, pady=8)
        self.message.bind('<<Modified>>', self.message_changed)
        ttk.Button(left, text='Chạy so sánh', style='Accent.TButton', command=self.compare).pack(anchor='w')
        right = ttk.Frame(top)
        right.grid(row=0, column=1, sticky='nsew')
        right.columnconfigure(0, weight=1)
        right.rowconfigure(1, weight=1, minsize=150)
        ttk.Style(self).configure('Compare.Treeview', rowheight=22)
        table_frame = ttk.Frame(right)
        table_frame.grid(row=0, column=0, sticky='ew')
        ttk.Label(table_frame, text='Trước tác động · PSNR/SSIM: ảnh gốc so với Stego').pack(anchor='w')
        self.table = ttk.Treeview(table_frame, columns=('metric', 'PVD', 'DWT'), show='headings', height=9, style='Compare.Treeview')
        for key, width in [('metric', 135), ('PVD', 165), ('DWT', 165)]:
            self.table.heading(key, text='Tiêu chí' if key == 'metric' else key)
            self.table.column(key, width=width, minwidth=90, anchor='w')
        self.table.pack(fill='x')
        self.chart = CompareChart(right)
        self.chart.grid(row=1, column=0, sticky='nsew', pady=(6, 0))
        preview_row = ttk.Frame(left)
        preview_row.pack(side='bottom', fill='x', before=self.preview, pady=(6, 0))
        save_row = ttk.Frame(right)
        save_row.grid(row=2, column=0, sticky='ew')
        self.previews, self.save_buttons = {}, {}
        for method in ('PVD', 'DWT'):
            column = ttk.Frame(preview_row)
            column.pack(side='left', fill='both', expand=True, padx=3)
            self.previews[method] = Preview(column, method + ' trước tác động', (230, 50))
            self.previews[method].configure(padding=2)
            self.previews[method].caption.pack_forget()
            self.previews[method].pack(fill='both', expand=True)
            button = ttk.Button(save_row, text=f'Lưu {method} trước tác động', state='disabled',
                                command=lambda m=method: self.save_result(self.results.get(m)))
            button.pack(side='left', expand=True, pady=4)
            self.save_buttons[method] = button
        self.status_label = ttk.Label(right, text='Hai phương pháp chạy độc lập.',
                                      wraplength=550, font=('Segoe UI', 9))
        right.bind('<Configure>', lambda event: self.status_label.configure(wraplength=max(100, event.width)))
        self.status_label.grid(row=3, column=0, sticky='ew')
        self.build_robustness()

    def mode_changed(self):
        self.version += 1
        self.content.pack_forget()
        if self.batch_panel is not None:
            self.batch_panel.grid_remove()
            self.batch_panel.changed()
        if self.mode.get() == 'Bộ ảnh':
            if self.batch_panel is None:
                from gui.batch_panel import BatchPanel
                self.batch_panel = BatchPanel(self, self)
            self.canvas.grid_remove()
            self.page_scroll.grid_remove()
            self.batch_panel.grid(row=1, column=0, columnspan=2, sticky='nsew')
        else:
            self.canvas.grid()
            self.page_scroll.grid()
            self.content.pack(fill='x')
        self.canvas.yview_moveto(0)
        self.update_busy()

    def scroll_wheel(self, event):
        if self.app.notebook.select() == str(self) and self.mode.get() == 'Một ảnh':
            self.canvas.yview_scroll(-int(event.delta / 120), 'units')
            return 'break'

    def build_robustness(self):
        panel = ttk.LabelFrame(self.content, text='Thử nghiệm độ bền', padding=10)
        panel.pack(fill='x', pady=(12, 0))
        controls = ttk.Frame(panel)
        controls.pack(fill='x')
        self.attack = tk.StringVar(value=ATTACK_LABELS['none'])
        self.parameter = tk.StringVar()
        self.seed = tk.StringVar(value=str(SEED))
        ttk.Label(controls, text='Tác động:').pack(side='left')
        ttk.Combobox(controls, textvariable=self.attack, values=list(ATTACK_LABELS.values()),
                     state='readonly', width=25).pack(side='left', padx=8)
        self.try_button = ttk.Button(controls, text='Thử độ bền', command=self.try_robustness,
                                     state='disabled')
        self.try_button.pack(side='left')
        self.parameter_frame = ttk.Frame(panel)
        self.parameter_label = ttk.Label(self.parameter_frame)
        self.parameter_label.pack(side='left')
        ttk.Entry(self.parameter_frame, textvariable=self.parameter, width=16).pack(side='left', padx=8)
        self.seed_frame = ttk.Frame(panel)
        ttk.Label(self.seed_frame, text='Seed: số nguyên không âm (NumPy, không giới hạn 32 bit)').pack(side='left')
        ttk.Entry(self.seed_frame, textvariable=self.seed, width=28).pack(side='left', padx=8)
        self.attack_note = ttk.Label(panel, wraplength=850)
        self.attack_note.pack(fill='x', pady=4)
        self.robustness_grid = ttk.Frame(panel)
        self.robustness_grid.pack(fill='x')
        self.attacked_previews, self.robustness_cells = {}, {}
        self.robustness_headers, self.robustness_row_labels = {}, {}
        for column, title in enumerate(('Chỉ số', 'PVD', 'DWT')):
            header = ttk.Label(self.robustness_grid, text=title, font=('Segoe UI', 10, 'bold'))
            header.grid(row=0, column=column, sticky='ew', padx=6, pady=(2, 4))
            self.robustness_headers[title] = header
        for column, method in enumerate(('PVD', 'DWT'), start=1):
            preview = Preview(self.robustness_grid, method + ' sau tác động', (150, 150))
            preview.configure(padding=2)
            preview.caption.pack_forget()
            preview.grid(row=1, column=column, sticky='n', padx=6, pady=(0, 4))
            self.attacked_previews[method] = preview
            self.robustness_cells[method] = {}
        for row, (title, key) in enumerate(ROBUSTNESS_ROWS, start=2):
            label = ttk.Label(self.robustness_grid, text=title, width=1,
                              anchor='nw', justify='left', padding=6)
            label.grid(row=row, column=0, sticky='nsew')
            self.robustness_row_labels[key] = label
            for column, method in enumerate(('PVD', 'DWT'), start=1):
                cell = ttk.Label(self.robustness_grid, width=1, anchor='nw',
                                 justify='left', padding=6)
                cell.grid(row=row, column=column, sticky='nsew')
                self.robustness_cells[method][key] = cell
        self.robustness_grid.bind('<Configure>', self.resize_robustness_columns)
        self.parameter.trace_add('write', self.robustness_changed)
        self.seed.trace_add('write', self.robustness_changed)
        self.attack.trace_add('write', self.attack_changed)
        self.attack_changed()

    def attack_name(self):
        return next(name for name, label in ATTACK_LABELS.items() if label == self.attack.get())

    def attack_changed(self, *args):
        name = self.attack_name()
        self.parameter_frame.pack_forget()
        self.seed_frame.pack_forget()
        params = DEFAULT_PARAMETERS[name]
        if params:
            key, value = next(iter(params.items()))
            self.parameter_label.configure(text=PARAMETER_HELP[key])
            self.parameter.set(str(value))
            self.parameter_frame.pack(fill='x', before=self.attack_note, pady=4)
        if name in NOISE:
            self.seed_frame.pack(fill='x', before=self.attack_note, pady=4)
        self.attack_note.configure(text=(
            'Giữ kích thước sau resize/crop, không căn chỉnh. Có thể mất đồng bộ và không khôi phục được.'
            if name in ('resize', 'crop') else
            'Mỗi lần thử bắt đầu từ Stego trước tác động. JPEG encode/decode trong bộ nhớ; tác động quang học giữ alpha.'))
        self.robustness_changed()

    def clear_robustness(self):
        self.robustness_results = {}
        for method in ('PVD', 'DWT'):
            self.attacked_previews[method].clear('Chưa thử')
            for key in self.robustness_cells[method]:
                self.set_robustness_cell(method, key, 'Chưa thử')

    def resize_robustness_columns(self, event):
        # Allocate from the viewport, never from the requested width of long text.
        metric_width = min(210, event.width // 4)
        method_width = (event.width - metric_width) // 2
        for column, width in enumerate((metric_width, method_width, method_width)):
            self.robustness_grid.columnconfigure(column, minsize=width, weight=0)
            labels = (self.robustness_row_labels.values() if column == 0 else
                      self.robustness_cells[('PVD', 'DWT')[column - 1]].values())
            for label in labels:
                label.configure(wraplength=max(1, width - 12))

    def set_robustness_cell(self, method, key, text, state='neutral'):
        self.robustness_cells[method][key].configure(
            text=text, foreground=RESULT_COLORS[state],
            font=('Segoe UI', 10, 'bold' if state in ('success', 'failure') else 'normal'))

    def show_robustness_result(self, method, result):
        parameters = result.get('attack_parameters') or {}
        if isinstance(parameters, str):
            parameters = json.loads(parameters)
        attack = ATTACK_LABELS.get(result.get('attack'), '—')
        details = [f'{PARAMETER_LABELS.get(key, key)}: {value:g}'
                   if isinstance(value, (int, float)) else
                   f'{PARAMETER_LABELS.get(key, key)}: {value}'
                   for key, value in parameters.items()]
        self.set_robustness_cell(method, 'attack', '\n'.join([attack, *details]))
        not_tested = result['status'] == 'not_tested'
        self.set_robustness_cell(method, 'seed', '—' if not_tested else
                                 ('Không dùng' if result['seed'] is None else str(result['seed'])))
        width, height = result.get('width'), result.get('height')
        self.set_robustness_cell(method, 'dimensions',
                                 f'{width} × {height}' if not not_tested and
                                 width is not None and height is not None else '—')
        ber = result.get('ber')
        self.set_robustness_cell(method, 'ber', '—' if not_tested else
                                 ('Không xác định' if ber is None else format_value(ber)),
                                 'muted' if not not_tested and ber is None else 'neutral')
        state = 'muted' if not_tested else ('success' if result['success'] else 'failure')
        self.set_robustness_cell(method, 'recovery', 'Không thử được' if not_tested else
                                 ('Khôi phục đúng' if result['success'] else 'Thất bại'), state)
        notes = ['Nhúng thất bại'] if not_tested else []
        for key in ('error', 'notes', 'history_warning'):
            note = result.get(key)
            if note and note not in notes and not (not_tested and key == 'error' and
                                                   note == 'Không thử được — nhúng thất bại'):
                notes.append(note)
        self.set_robustness_cell(method, 'notes', '\n'.join(notes) or '—')
        preview = self.attacked_previews[method]
        if result.get('output_image') is not None and not not_tested:
            preview.show(result['output_image'])
        else:
            preview.clear('Không thử được' if not_tested else 'Chưa có ảnh kết quả')

    def robustness_changed(self, *args):
        self.version += 1
        self.clear_robustness()
        self.update_busy()

    def update_busy(self):
        if self.batch_panel is not None:
            self.batch_panel.update_busy()
        available = any(r.get('success') and r.get('expected_packet') is not None
                        and r.get('output_image') is not None for r in self.results.values())
        self.try_button.configure(state='normal' if available and not self.app.busy else 'disabled')

    def try_robustness(self):
        if self.app.busy:
            return
        self.message_changed()
        if not any(r.get('success') for r in self.results.values()):
            return
        name = self.attack_name()
        parameters = {key: self.parameter.get() for key in DEFAULT_PARAMETERS[name]}
        try:
            parameters, seed = validate_configuration(name, parameters, self.seed.get())
        except ValueError as exc:
            self.show_error(str(exc))
            return
        self.clear_robustness()
        token = self.version
        embedded = deepcopy(self.results)
        service = self.app.service
        def completed(results):
            warnings = [r['history_warning'] for r in results.values() if r.get('history_warning')]
            if token != self.version:
                self.app.set_status('Tác vụ cấu hình cũ đã hoàn tất; kết quả hiển thị đã bị bỏ.' +
                                    (' ' + ' '.join(warnings) if warnings else ''))
                return
            self.robustness_results = results
            for method, result in results.items():
                self.show_robustness_result(method, result)
            self.app.set_status('Đã hoàn tất thử độ bền.' + (' ' + ' '.join(warnings) if warnings else ''))
        self.app.run_job(lambda: service.try_robustness(embedded, name, parameters, seed), completed)

    def choose(self):
        self.choose_image(self.preview, self.clear)

    def clear(self):
        self.version += 1
        self.results = {}
        self.clear_robustness()
        self.update_busy()
        self.chart.clear()
        self.table.delete(*self.table.get_children())
        for method in ('PVD', 'DWT'):
            self.previews[method].clear()
            self.save_buttons[method].configure(state='disabled')
        self.status_label.configure(text='Hai phương pháp chạy độc lập.')

    def message_changed(self, event=None):
        if self.message.edit_modified():
            self.message.edit_modified(False)
            self.clear()

    def compare(self):
        if self.app.busy:
            return
        if not self.require_image():
            return
        self.message_changed()
        path, message = self.path, self.message.get('1.0', 'end-1c')
        service = self.app.service
        if not self.app.busy:
            self.clear()
        token = self.version
        def completed(result):
            if token != self.version:
                self.app.set_status('Tác vụ đã hoàn tất cho dữ liệu trước đó. Hãy chạy lại so sánh.')
                return
            self.show_result(result)
        self.app.run_job(lambda: service.compare(path, message), completed)

    def show_result(self, comparison):
        self.results = comparison['results']
        self.clear_robustness()
        self.update_busy()
        self.chart.show(self.results)
        self.table.delete(*self.table.get_children())
        for label, key in ROWS:
            self.table.insert('', 'end', values=(label, *(format_value(self.results[m].get(key)) for m in ('PVD', 'DWT'))))
        errors = []
        for method, result in self.results.items():
            self.save_buttons[method].configure(state='normal' if result['success'] else 'disabled')
            if result['output_image'] is not None:
                self.previews[method].show(result['output_image'])
            else:
                self.previews[method].clear()
            if result['error']:
                errors.append(method + ': ' + result['error'])
        text = {'success': 'Cả hai phương pháp trích xuất khớp dữ liệu gốc.',
                'partial': 'Partial · Chỉ một phương pháp thành công.',
                'failed': 'Cả hai phương pháp chưa thành công.'}[comparison['status']]
        self.status_label.configure(text=text + ('\n' + '\n'.join(errors) if errors else ''))
        self.app.set_status(text)
