# coding: utf-8
import os
from pathlib import Path
from typing import Dict

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QHBoxLayout

from qfluentwidgets import SegmentedWidget

from app.common.database import sqlRequest
from app.common.database.entity import Task, TaskStatus
from app.common.signal_bus import signal_bus
from app.config import load_settings
from app.common.format import format_size
from app.common.speed_badge import SpeedBadge
from ..components.active_badge import ActiveBadge
from ..components.interface import Interface
from ..components.task_card import (
    EnhanceJobCard,
    FailedTaskCard,
    LiveDownloadingTaskCard,
    SuccessTaskCard,
    VODDownloadProgressInfo,
    VODDownloadingTaskCard,
)
from ..components.task_card_view import (
    DownloadingTaskView,
    EnhancingTaskView,
    FailedTaskView,
    SuccessTaskView,
)
from ..components.task_stacked_widget import TaskStackedWidget


# ── Card list view ─────────────────────────────────────────────────────────────


# ── Main interface ─────────────────────────────────────────────────────────────
class TaskInterface(Interface):
    """Unified job tracker: Downloading / Enhancing / Finished / Failed tabs."""

    _TAB_DL       = "downloading"
    _TAB_ENHANCE  = "enhancing"
    _TAB_FINISHED = "finished"
    _TAB_FAILED   = "failed"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle(self.tr("Tasks"))

        # Maps signal-bus job_id strings to the in-progress Task entity so the
        # correct Task object is available when a download completes.
        self._task_map: Dict[str, Task] = {}

        self._speed_badge = SpeedBadge(self)
        self._build_ui()
        self._connect_signals()

    # ── UI construction ────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        # Replace the default single title widget with a title + badge row.
        self.vBoxLayout.removeWidget(self.titleLabel)
        title_row = QHBoxLayout()
        title_row.setContentsMargins(0, 0, 0, 0)
        title_row.setSpacing(8)

        self._active_badge = ActiveBadge(self.view)
        title_row.addWidget(self.titleLabel, 0, Qt.AlignVCenter)
        title_row.addWidget(self._active_badge, 0, Qt.AlignVCenter)
        title_row.addStretch(1)
        self.vBoxLayout.insertLayout(0, title_row)

        # Views are built before the pivot so the pivot lambdas can close over them.
        self._dl_view       = DownloadingTaskView(self)
        self._enhance_view  = EnhancingTaskView(self)
        self._finished_view = SuccessTaskView(self)
        self._failed_view   = FailedTaskView(self)

        self.stackedWidget = TaskStackedWidget()
        self.stackedWidget.addWidget(self._dl_view)
        self.stackedWidget.addWidget(self._enhance_view)
        self.stackedWidget.addWidget(self._finished_view)
        self.stackedWidget.addWidget(self._failed_view)

        # Pivot uses setCurrentWidget (widget reference) so reordering tabs never
        # silently breaks navigation the way hardcoded indices would.
        self.pivot = SegmentedWidget()
        self.pivot.addItem(self._TAB_DL,       self.tr("Downloading"), lambda: self.stackedWidget.setCurrentWidget(self._dl_view))
        self.pivot.addItem(self._TAB_ENHANCE,  self.tr("Enhancing"),   lambda: self.stackedWidget.setCurrentWidget(self._enhance_view))
        self.pivot.addItem(self._TAB_FINISHED, self.tr("Finished"),    lambda: self.stackedWidget.setCurrentWidget(self._finished_view))
        self.pivot.addItem(self._TAB_FAILED,   self.tr("Failed"),      lambda: self.stackedWidget.setCurrentWidget(self._failed_view))
        self.pivot.setCurrentItem(self._TAB_DL)

        self.setViewportMargins(0, 140, 0, 10)
        self.vBoxLayout.addWidget(self.pivot, 0, Qt.AlignLeft)
        self.viewLayout.addWidget(self.stackedWidget)

    # ── Signal wiring ──────────────────────────────────────────────────────

    def _connect_signals(self) -> None:
        signal_bus.download_started.connect(self._on_download_started)
        signal_bus.download_progress.connect(self._on_download_progress)
        signal_bus.download_progress_detail.connect(self._on_download_progress_detail)
        signal_bus.download_finished.connect(self._on_download_finished)
        signal_bus.enhance_started.connect(self._on_enhance_started)
        signal_bus.enhance_finished.connect(self._on_enhance_finished)
        signal_bus.redownload_task.connect(self._on_redownload_task)

        # Badge is driven by signals so no manual refresh calls are needed anywhere.
        for view in (self._dl_view, self._enhance_view):
            view.cardCountChanged.connect(self._on_active_count_changed)

    # ── Download handlers ──────────────────────────────────────────────────

    def _on_download_started(self, job_id: str, url: str, output_dir: str) -> None:
        task = Task(
            id=job_id,
            url=url,
            fileName=os.path.basename(url.rstrip("/")) or job_id,
            saveFolder=output_dir,
            status=TaskStatus.RUNNING,
        )
        self._task_map[job_id] = task
        card = (LiveDownloadingTaskCard(task)
                if getattr(task, "isLive", False)
                else VODDownloadingTaskCard(task))
        card.deleted.connect(lambda t: self._dl_view.remove_card_by_id(t.id))
        self._dl_view.add_card(card, job_id)

    def _on_download_progress(self, job_id: str, progress: float) -> None:
        # Kept for bare-progress updates (e.g. indeterminate phase before detail arrives).
        card = self._dl_view.find_card(job_id)
        if isinstance(card, VODDownloadingTaskCard):
            pct = int(max(0.0, min(1.0, progress)) * 100)
            card.progressBar.setRange(0, 100)
            card.progressBar.setValue(pct)

    def _on_download_progress_detail(
        self,
        job_id: str,
        pct: float,
        speed: str,
        eta: str,
        cur_size: str,
        tot_size: str,
    ) -> None:
        card = self._dl_view.find_card(job_id)
        if isinstance(card, VODDownloadingTaskCard):
            card.setInfo(VODDownloadProgressInfo(
                speed=speed,
                remainTime=eta,
                currentSize=cur_size,
                totalSize=tot_size,
                currentChunk=int(max(0.0, min(1.0, pct)) * 100),
                totalChunks=100,
            ))

    def _on_download_finished(
        self, job_id: str, success: bool, _url: str, filepath: str, size_bytes: int
    ) -> None:
        task = self._task_map.pop(job_id, None)
        self._dl_view.remove_card_by_id(job_id)
        if task is None:
            return

        if filepath:
            task.fileName = os.path.basename(filepath)

        if success:
            task.success()
            card = SuccessTaskCard(task, self._finished_view)
            card.deleted.connect(lambda t: self._finished_view.remove_card_by_id(t.id))
            self._finished_view.add_card(card, task.id)
        else:
            task.error()
            card = FailedTaskCard(task, self._failed_view)
            card.deleted.connect(lambda t: self._failed_view.remove_card_by_id(t.id))
            self._failed_view.add_card(card, task.id)

    # ── Enhance handlers ───────────────────────────────────────────────────

    def _on_enhance_started(self, job_id: str, filename: str) -> None:
        # Card type changes from DownloadJobCard → EnhanceJobCard; destroy the old one.
        self._dl_view.remove_card_by_id(job_id)
        card = EnhanceJobCard(
            job_id, filename,
            status="Enhancing",
            parent=self._enhance_view,
        )
        self._enhance_view.add_card(card, job_id)

    def _on_enhance_finished(
        self, job_id: str, success: bool, filename: str, output_path: str, size_bytes: int
    ) -> None:
        # Reuse the existing card: take it out, update in-place, move to target list.
        card = self._enhance_view.take_card(job_id)
        if card is None:
            return
        card.mark_finished(success, output_path or filename, size_bytes)
        target = self._finished_view if success else self._failed_view
        target.add_card(card, job_id)

        if load_settings().get("enhance_task_store_history", True):
            self._save_enhance_task(job_id, success, filename, output_path, size_bytes)

    def _save_enhance_task(
        self, job_id: str, success: bool, filename: str, output_path: str, size_bytes: int
    ) -> None:
        """Persist a finished enhance job to the local SQLite database."""
        resolved_path = output_path or filename
        save_folder = str(Path(resolved_path).parent) if resolved_path else ""
        file_name   = os.path.basename(resolved_path) if resolved_path else filename
        task = Task(
            id=job_id,
            url="",
            fileName=file_name,
            saveFolder=save_folder,
            size=format_size(size_bytes) if size_bytes >= 0 else "0 B",
            status=TaskStatus.SUCCESS if success else TaskStatus.FAILED,
        )
        sqlRequest("taskService", "add", None, task=task)

    def _on_redownload_task(self, task: Task) -> None:
        signal_bus.download_started.emit(
            task.id, task.url or "", task.saveFolder or ""
        )

    # ── Badge ──────────────────────────────────────────────────────────────

    def _on_active_count_changed(self, _: int) -> None:
        self._active_badge.set_count(
            self._dl_view.count() + self._enhance_view.count()
        )

    # ── Public navigation helpers ──────────────────────────────────────────

    def _switch_to(self, tab_key: str) -> None:
        tab_map = {
            self._TAB_DL:       self._dl_view,
            self._TAB_ENHANCE:  self._enhance_view,
            self._TAB_FINISHED: self._finished_view,
            self._TAB_FAILED:   self._failed_view,
        }
        self.pivot.setCurrentItem(tab_key)
        self.stackedWidget.setCurrentWidget(tab_map[tab_key])

    def switch_to_downloading(self) -> None:
        self._switch_to(self._TAB_DL)

    def switch_to_enhancing(self) -> None:
        self._switch_to(self._TAB_ENHANCE)

    def switch_to_finished(self) -> None:
        self._switch_to(self._TAB_FINISHED)

    def switch_to_failed(self) -> None:
        self._switch_to(self._TAB_FAILED)

    switch_to_active = switch_to_downloading  # legacy alias
