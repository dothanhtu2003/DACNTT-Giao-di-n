"""Điểm khởi chạy ứng dụng desktop PVD & DWT."""

from gui.main_window import MainWindow


def main() -> None:
    """Khởi chạy giao diện bốn tab."""
    MainWindow().mainloop()


if __name__ == "__main__":
    main()
