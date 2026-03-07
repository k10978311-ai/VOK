from collections import deque

from PyQt5.QtCore import QObject, QThread, pyqtSignal
from PyQt5.QtSql import QSqlDatabase

from .db_initializer import DBInitializer
from .service import *


class SqlRequest:
    """SQL request for async DB call."""

    def __init__(self, service: str, method: str, slot=None, params: dict = None):
        self.service = service
        self.method = method
        self.slot = slot
        self.params = params or {}


class SqlResponse:
    """SQL response with result and callback slot."""

    def __init__(self, data, slot):
        self.slot = slot
        self.data = data


class SqlSignalBus(QObject):
    """Signal bus for database thread."""

    fetchDataSig = pyqtSignal(object)  # SqlRequest
    dataFetched = pyqtSignal(object)  # SqlResponse


sqlSignalBus = SqlSignalBus()


def sqlRequest(service: str, method: str, slot=None, **params):
    """ query sql from database """
    request = SqlRequest(service, method, slot, params)
    sqlSignalBus.fetchDataSig.emit(request)



class Database(QObject):
    """ Database """

    def __init__(self, db: QSqlDatabase = None, parent=None):
        """
        Parameters
        ----------
        directories: List[str]
            audio directories

        db: QDataBase
            database to be used

        watch: bool
            whether to monitor audio directories

        parent:
            parent instance
        """
        super().__init__(parent=parent)
        self.taskService = TaskService(db)

    def setDatabase(self, db: QSqlDatabase):
        """ set the database to be used """
        self.taskService.taskDao.setDatabase(db)



class DatabaseThread(QThread):
    """ Database thread """

    def __init__(self, db: QSqlDatabase = None, parent=None):
        """
        Parameters
        ----------
        directories: List[str]
            audio directories

        db: QDataBase
            database to be used

        watch: bool
            whether to monitor audio directories

        parent:
            parent instance
        """
        super().__init__(parent=parent)
        self.database = Database(db, self)
        self.tasks = deque()
        self._stop_requested = False

        sqlSignalBus.fetchDataSig.connect(self.onFetchData)

    def run(self):
        while self.tasks and not self._stop_requested:
            task, request = self.tasks.popleft()
            try:
                result = task(**request.params)
                if not self._stop_requested:
                    sqlSignalBus.dataFetched.emit(SqlResponse(result, request.slot))
            except Exception as e:
                # Log error but continue processing
                print(f"Database task error: {e}")
                if hasattr(request, 'slot') and request.slot:
                    sqlSignalBus.dataFetched.emit(SqlResponse(None, request.slot))

    def onFetchData(self, request: SqlRequest):
        if self._stop_requested:
            return
        service = getattr(self.database, request.service)
        task = getattr(service, request.method)
        self.tasks.append((task, request))

        if not self.isRunning() and not self._stop_requested:
            self.start()
    
    def stop_gracefully(self):
        """Request the thread to stop gracefully."""
        self._stop_requested = True
        self.tasks.clear()  # Clear remaining tasks