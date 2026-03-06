# coding: utf-8
"""Application-wide signal bus — thin singleton for cross-component communication."""

from PyQt5.QtCore import QObject, pyqtSignal


class _SignalBus(QObject):
    # Download lifecycle
    # (job_id, url, output_dir)
    download_started = pyqtSignal(str, str, str)
    # (job_id, progress 0.0–1.0)
    download_progress = pyqtSignal(str, float)
    # (job_id, success, url_or_msg, filepath, size_bytes)
    download_finished = pyqtSignal(str, bool, str, str, int)

    # Enhance lifecycle
    # (job_id, source_filename)
    enhance_started = pyqtSignal(str, str)
    # (job_id, success, source_filename, output_path, size_bytes)
    enhance_finished = pyqtSignal(str, bool, str, str, int)


signal_bus = _SignalBus()
