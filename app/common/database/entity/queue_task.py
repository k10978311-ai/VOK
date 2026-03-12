# coding: utf-8
"""QueueTask entity — persists one yt-dlp download job across app restarts."""

from dataclasses import dataclass, field

from .entity import Entity
from ..utils.uuid_utils import UUIDUtils


# Mirror of the status strings used by the UI / DownloadTaskModel
QUEUE_STATUS_PENDING    = "Pending"
QUEUE_STATUS_RUNNING    = "Downloading"
QUEUE_STATUS_ENHANCING  = "Enhancing"
QUEUE_STATUS_DONE       = "Done"
QUEUE_STATUS_ERROR      = "Error"
QUEUE_STATUS_CANCELED   = "Canceled"

# Statuses that should be restored as Pending on next launch
_RECOVERABLE = {QUEUE_STATUS_PENDING, QUEUE_STATUS_RUNNING}


@dataclass
class QueueTask(Entity):
    """One row in tbl_download_queue."""

    id:           str = field(default_factory=UUIDUtils.getUUID)
    job_id:       str = ""          # DownloadManager job_id (blank until enqueued)
    url:          str = ""          # video / playlist URL
    title:        str = ""          # display title
    host:         str = ""          # platform / domain label
    format_key:   str = "Best (video+audio)"
    output_dir:   str = ""          # resolved save directory
    cookies_file: str = ""
    status:       str = QUEUE_STATUS_PENDING
    create_time:  str = ""          # ISO string set at insert time
