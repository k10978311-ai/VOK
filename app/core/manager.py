"""Multi-thread download manager: queue and worker pool for parallel downloads."""

import uuid
from queue import Empty, Queue

from PyQt5.QtCore import QObject, pyqtSignal

from app.config import load_settings
from app.core.download import DownloadWorker


class DownloadJob:
    """One download request."""

    __slots__ = ("url", "output_dir", "format_key", "single_video", "cookies_file", "job_id")

    def __init__(
        self,
        url: str,
        output_dir: str = "",
        format_key: str = "Best (video+audio)",
        single_video: bool = True,
        cookies_file: str = "",
        job_id: str | None = None,
    ):
        self.url = url.strip()
        self.output_dir = output_dir
        self.format_key = format_key
        self.single_video = single_video
        self.cookies_file = cookies_file or ""
        self.job_id = job_id or f"{self.url[:64]}_{uuid.uuid4().hex[:8]}"


class DownloadManager(QObject):
    """Runs up to N DownloadWorkers in parallel; queues extra jobs.

    Signals
    -------
    log_line      (job_id, message)
    progress      (job_id, 0.0..1.0)
    job_finished  (job_id, success, message, filepath, size_bytes)
    """

    log_line = pyqtSignal(str, str)
    progress = pyqtSignal(str, float)
    job_finished = pyqtSignal(str, bool, str, str, int)

    def __init__(self, max_workers: int | None = None, parent=None):
        super().__init__(parent)
        s = load_settings()
        self._max_workers = max_workers or max(1, min(4, int(s.get("concurrent_downloads", 2))))
        self._concurrent_fragments = max(1, min(16, int(s.get("concurrent_fragments", 4))))
        self._queue: Queue[DownloadJob] = Queue()
        self._running: dict[str, DownloadWorker] = {}
        self._stop = False

    def enqueue(self, job: DownloadJob) -> None:
        """Add a job; start immediately if a worker slot is free."""
        if len(self._running) < self._max_workers:
            self._start_job(job)
        else:
            self._queue.put(job)

    def _start_job(self, job: DownloadJob) -> None:
        worker = DownloadWorker(
            job.url,
            job.output_dir,
            job.format_key,
            single_video=job.single_video,
            concurrent_fragments=self._concurrent_fragments,
            cookies_file=job.cookies_file,
            job_id=job.job_id,
        )

        def on_log(msg: str):
            self.log_line.emit(job.job_id, msg)

        def on_progress(v: float):
            self.progress.emit(job.job_id, v)

        def on_finished(success: bool, message: str, filepath: str, size_bytes: int):
            self.job_finished.emit(job.job_id, success, message, filepath, size_bytes)
            self._running.pop(job.job_id, None)
            self._start_next()

        worker.log_line.connect(on_log)
        worker.progress.connect(on_progress)
        worker.finished_signal.connect(on_finished)
        self._running[job.job_id] = worker
        worker.start()

    def _start_next(self) -> None:
        if self._stop or len(self._running) >= self._max_workers:
            return
        try:
            job = self._queue.get_nowait()
            self._start_job(job)
        except Empty:
            pass

    def cancel_job(self, job_id: str) -> None:
        w = self._running.get(job_id)
        if w:
            w.cancel()

    def cancel_all(self) -> None:
        """Cancel all running jobs and clear the queue so no further jobs start."""
        self._stop = True
        # Drain queue so no new jobs start after we cancel running ones
        while True:
            try:
                self._queue.get_nowait()
            except Empty:
                break
        for w in list(self._running.values()):
            w.cancel()
        self._stop = False
