import tkinter as tk
from tkinter import ttk

from gui.common import BaseTab, Preview, message_editor, format_value, format_status
from gui.compare_chart import CompareChart

ROWS = [('Dung lượng (bit)', 'capacity_bits'), ('Văn bản (byte)', 'payload_bytes'),
        ('Packet (bit)', 'packet_bits'), ('Sử dụng (%)', 'usage_percent'), ('bpp', 'bpp'),
        ('PSNR (dB)', 'psnr'), ('SSIM', 'ssim'),
        ('BER nhúng', 'ber'), ('Khôi phục packet', 'extract_status')]


class CompareTab(BaseTab):
    def __init__(self, parent, app):
        super().__init__(parent, app)
        self.results = {}
        self.version = 0
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
        ttk.Label(left, text='Văn bản bí mật').pack(anchor='w')
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
        ttk.Label(table_frame, text='Chất lượng nhúng').pack(anchor='w')
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
            self.previews[method] = Preview(column, method + ' sau nhúng', (230, 50))
            self.previews[method].configure(padding=2)
            self.previews[method].caption.pack_forget()
            self.previews[method].pack(fill='both', expand=True)
            button = ttk.Button(save_row, text=f'Lưu Stego {method}', state='disabled',
                                command=lambda m=method: self.save_result(self.results.get(m)))
            button.pack(side='left', expand=True, pady=4)
            self.save_buttons[method] = button
        self.status_label = ttk.Label(right, text='',
                                      wraplength=550, font=('Segoe UI', 9))
        right.bind('<Configure>', lambda event: self.status_label.configure(wraplength=max(100, event.width)))
        self.status_label.grid(row=3, column=0, sticky='ew')

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

    def update_busy(self):
        if self.batch_panel is not None:
            self.batch_panel.update_busy()

    def choose(self):
        self.choose_image(self.preview, self.clear)

    def clear(self):
        self.version += 1
        self.results = {}
        self.update_busy()
        self.chart.clear()
        self.table.delete(*self.table.get_children())
        for method in ('PVD', 'DWT'):
            self.previews[method].clear()
            self.save_buttons[method].configure(state='disabled')
        self.status_label.configure(text='')

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
        self.update_busy()
        self.chart.show(self.results)
        self.table.delete(*self.table.get_children())
        for label, key in ROWS:
            formatter = format_status if key == 'extract_status' else format_value
            self.table.insert('', 'end', values=(label, *(formatter(self.results[m].get(key)) for m in ('PVD', 'DWT'))))
        errors = []
        for method, result in self.results.items():
            self.save_buttons[method].configure(state='normal' if result['success'] else 'disabled')
            if result['output_image'] is not None:
                self.previews[method].show(result['output_image'])
            else:
                self.previews[method].clear()
            if result['error']:
                errors.append(method + ': ' + result['error'])
        text = {'success': 'PVD và DWT khôi phục khớp 100%.',
                'partial': 'Chỉ một phương pháp nhúng thành công.',
                'failed': 'Cả hai phương pháp nhúng thất bại.'}[comparison['status']]
        self.status_label.configure(text=text + ('\n' + '\n'.join(errors) if errors else ''))
        self.app.set_status('Đã so sánh PVD/DWT.')
