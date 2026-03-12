"""Reusable UI components. Path: app.ui.components."""

__version__ = "0.1.0"

from .active_badge import ActiveBadge
from .batch_enhance_table import BatchEnhanceTable
from .card_header import CardHeader
from .dashboard_feature_card import DashboardFeatureCard
from .dashboard_feature_grid import DashboardFeatureGrid
from .dashboard_instructions_card import DashboardInstructionsCard
from .download_enhance_feature import DownloadEnhanceFeature, EnhanceOptions
from .download_path_panel import DownloadPathPanel
from .download_table_card import DownloadTableCard
from .DownloadPowerSettingCard import DownloadConfigCard
from .download_task_model import (
    DownloadTaskModel,
    COL_TITLE, COL_HOST, COL_STATUS, COL_SIZE, COL_PROGRESS,
    _STATUS_PENDING, _STATUS_RUNNING, _STATUS_DONE, _STATUS_ERROR, _STATUS_CANCELED,
)
from .status_table import StatusTable
from .task_command_bar import TaskCommandBar
from .task_card_view import (
    DownloadingTaskView,
    EnhancingTaskView,
    FailedTaskView,
    SuccessTaskView,
    TaskCardView,
)
from .task_stacked_widget import TaskStackedWidget

__all__ = [
    "ActiveBadge",
    "BatchEnhanceTable",
    "CardHeader",
    "DashboardFeatureCard",
    "DashboardFeatureGrid",
    "DashboardInstructionsCard",
    "DownloadConfigCard",
    "DownloadTaskModel",
    "DownloadEnhanceFeature",
    "DownloadingTaskView",
    "DownloadPathPanel",
    "DownloadTableCard",
    "EnhancingTaskView",
    "EnhanceOptions",
    "FailedTaskView",
    "StatusTable",
    "SuccessTaskView",
    "TaskCommandBar",
    "TaskCardView",
    "TaskStackedWidget",
]
