from PyQt5.QtWidgets import QMainWindow
from app.ui.views.base import BaseView
from app.ui.components.home_banner import HomeBanner

class HomeInterface(BaseView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Home")