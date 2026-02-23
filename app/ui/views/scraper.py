"""Scraper view: Post Analytics, Comments, Search/Hashtag, and Translation."""

from datetime import datetime

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QHeaderView,
    QTableWidgetItem,
    QVBoxLayout,
)
from qfluentwidgets import (
    BodyLabel,
    CardWidget,
    ComboBox,
    FluentIcon,
    IndeterminateProgressBar,
    LineEdit,
    PlainTextEdit,
    PrimaryPushButton,
    PushButton,
    SpinBox,
    StrongBodyLabel,
    SwitchButton,
    TableWidget,
    TransparentPushButton,
)

from app.common.state import add_log_entry
from app.config import load_settings
from app.core.scraper import (
    CommentsWorker,
    MetaFetchWorker,
    SearchWorker,
    TranslateWorker,
    _SEARCH_PREFIXES,
    fmt_date,
    fmt_duration,
    fmt_num,
)
from app.ui.components import CardHeader

from .base import BaseView

# ── Stat rows displayed in the Post Analytics table ──────────────────────────
_STAT_FIELDS: list[tuple[str, str]] = [
    ("title",                  "Title"),
    ("uploader",               "Creator / Channel"),
    ("channel_follower_count", "Followers / Subscribers"),
    ("upload_date",            "Upload Date"),
    ("view_count",             "Views"),
    ("like_count",             "Likes"),
    ("dislike_count",          "Dislikes"),
    ("comment_count",          "Comments"),
    ("duration",               "Duration"),
    ("categories",             "Categories"),
    ("tags",                   "Tags"),
    ("webpage_url",            "URL"),
    ("description",            "Description"),
]

_SORT_OPTIONS = ["Default", "Views (high→low)", "Likes (high→low)", "Date (newest)", "Date (oldest)"]


class ScraperView(BaseView):
    """Four-section social-media analytics view."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Social Analytics")

        self._meta_worker: MetaFetchWorker | None = None
        self._comments_worker: CommentsWorker | None = None
        self._search_worker: SearchWorker | None = None
        self._translate_worker: TranslateWorker | None = None

        self._build_stats_card()
        self._build_comments_card()
        self._build_search_card()
        self._build_translate_card()
        self._layout.addStretch(1)

    # ── Post Analytics ────────────────────────────────────────────────────

    def _build_stats_card(self):
        card = CardWidget(self)
        lay = QVBoxLayout(card)
        lay.setSpacing(10)
        lay.addWidget(CardHeader(FluentIcon.FEEDBACK, "Post Analytics & Engagement", card))

        input_row = QHBoxLayout()
        input_row.addWidget(BodyLabel("URL", card))
        self._stats_url = LineEdit(card)
        self._stats_url.setPlaceholderText(
            "Paste a video / post URL — YouTube, TikTok, Instagram, Facebook, Pinterest, X …"
        )
        self._stats_url.setClearButtonEnabled(True)
        input_row.addWidget(self._stats_url, 1)
        self._stats_btn = PrimaryPushButton("Fetch Stats", card)
        self._stats_btn.setIcon(FluentIcon.SEARCH)
        self._stats_btn.clicked.connect(self._fetch_stats)
        input_row.addWidget(self._stats_btn)
        lay.addLayout(input_row)

        self._stats_progress = IndeterminateProgressBar(card)
        self._stats_progress.setVisible(False)
        lay.addWidget(self._stats_progress)

        self._stats_status = BodyLabel("", card)
        lay.addWidget(self._stats_status)

        # Stats result table: Metric | Value
        self._stats_table = TableWidget(card)
        self._stats_table.setColumnCount(2)
        self._stats_table.setHorizontalHeaderLabels(["Metric", "Value"])
        h = self._stats_table.horizontalHeader()
        h.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        h.setSectionResizeMode(1, QHeaderView.Stretch)
        self._stats_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._stats_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._stats_table.setAlternatingRowColors(True)
        self._stats_table.verticalHeader().setVisible(False)
        self._stats_table.setMinimumHeight(260)
        lay.addWidget(self._stats_table)

        self._layout.addWidget(card)

    # ── Comments Scraper ──────────────────────────────────────────────────

    def _build_comments_card(self):
        card = CardWidget(self)
        lay = QVBoxLayout(card)
        lay.setSpacing(10)
        lay.addWidget(CardHeader(FluentIcon.CHAT, "Comments Scraper", card))

        input_row = QHBoxLayout()
        input_row.addWidget(BodyLabel("URL", card))
        self._comments_url = LineEdit(card)
        self._comments_url.setPlaceholderText("Paste a post URL to scrape comments…")
        self._comments_url.setClearButtonEnabled(True)
        input_row.addWidget(self._comments_url, 1)
        input_row.addWidget(BodyLabel("Max", card))
        self._comments_max = SpinBox(card)
        self._comments_max.setRange(10, 1000)
        self._comments_max.setValue(100)
        self._comments_max.setFixedWidth(90)
        input_row.addWidget(self._comments_max)
        self._comments_btn = PrimaryPushButton("Fetch Comments", card)
        self._comments_btn.setIcon(FluentIcon.SEARCH)
        self._comments_btn.clicked.connect(self._fetch_comments)
        input_row.addWidget(self._comments_btn)
        lay.addLayout(input_row)

        self._comments_progress = IndeterminateProgressBar(card)
        self._comments_progress.setVisible(False)
        lay.addWidget(self._comments_progress)

        self._comments_status = BodyLabel("", card)
        lay.addWidget(self._comments_status)

        acts = QHBoxLayout()
        self._export_comments_btn = PushButton("Export CSV", card)
        self._export_comments_btn.setIcon(FluentIcon.SAVE)
        self._export_comments_btn.setEnabled(False)
        self._export_comments_btn.clicked.connect(self._export_comments)
        acts.addStretch(1)
        acts.addWidget(self._export_comments_btn)
        lay.addLayout(acts)

        self._comments_table = TableWidget(card)
        self._comments_table.setColumnCount(4)
        self._comments_table.setHorizontalHeaderLabels(["Author", "Comment", "Likes", "Date"])
        ch = self._comments_table.horizontalHeader()
        ch.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        ch.setSectionResizeMode(1, QHeaderView.Stretch)
        ch.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        ch.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self._comments_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._comments_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._comments_table.setAlternatingRowColors(True)
        self._comments_table.verticalHeader().setVisible(False)
        self._comments_table.setMinimumHeight(220)
        lay.addWidget(self._comments_table)

        self._layout.addWidget(card)

    # ── Content Search ────────────────────────────────────────────────────

    def _build_search_card(self):
        card = CardWidget(self)
        lay = QVBoxLayout(card)
        lay.setSpacing(10)
        lay.addWidget(CardHeader(FluentIcon.SEARCH, "Content Search & Hashtag Scraping", card))

        input_row = QHBoxLayout()
        input_row.addWidget(BodyLabel("Keyword", card))
        self._search_kw = LineEdit(card)
        self._search_kw.setPlaceholderText("Enter keyword or hashtag…")
        self._search_kw.setClearButtonEnabled(True)
        input_row.addWidget(self._search_kw, 1)

        input_row.addWidget(BodyLabel("Platform", card))
        self._search_platform = ComboBox(card)
        self._search_platform.addItems(list(_SEARCH_PREFIXES.keys()))
        input_row.addWidget(self._search_platform)

        self._hashtag_switch = SwitchButton(card)
        self._hashtag_switch.setChecked(False)
        input_row.addWidget(BodyLabel("Hashtag", card))
        input_row.addWidget(self._hashtag_switch)

        self._search_btn = PrimaryPushButton("Search", card)
        self._search_btn.setIcon(FluentIcon.SEARCH)
        self._search_btn.clicked.connect(self._do_search)
        input_row.addWidget(self._search_btn)
        lay.addLayout(input_row)

        sort_row = QHBoxLayout()
        sort_row.addWidget(BodyLabel("Sort by:", card))
        self._search_sort = ComboBox(card)
        self._search_sort.addItems(_SORT_OPTIONS)
        self._search_sort.currentIndexChanged.connect(self._sort_results)
        sort_row.addWidget(self._search_sort)
        sort_row.addStretch(1)
        self._search_status = BodyLabel("", card)
        sort_row.addWidget(self._search_status)
        lay.addLayout(sort_row)

        self._search_progress = IndeterminateProgressBar(card)
        self._search_progress.setVisible(False)
        lay.addWidget(self._search_progress)

        self._search_table = TableWidget(card)
        self._search_table.setColumnCount(6)
        self._search_table.setHorizontalHeaderLabels(
            ["Title", "Creator", "Views", "Likes", "Duration", "Date"]
        )
        sh = self._search_table.horizontalHeader()
        sh.setSectionResizeMode(0, QHeaderView.Stretch)
        sh.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        sh.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        sh.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        sh.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        sh.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self._search_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._search_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._search_table.setAlternatingRowColors(True)
        self._search_table.verticalHeader().setVisible(False)
        self._search_table.setMinimumHeight(240)
        self._search_table.doubleClicked.connect(self._on_result_double_clicked)
        lay.addWidget(self._search_table)

        hint = BodyLabel("Double-click a row to copy its URL to the Download tab.", card)
        hint.setTextColor(QColor("#888888"), QColor("#aaaaaa"))
        lay.addWidget(hint)

        self._search_results: list[dict] = []
        self._layout.addWidget(card)

    # ── Content Translation ───────────────────────────────────────────────

    def _build_translate_card(self):
        card = CardWidget(self)
        lay = QVBoxLayout(card)
        lay.setSpacing(10)
        lay.addWidget(CardHeader(FluentIcon.LANGUAGE, "Content Translation", card))

        ctrl_row = QHBoxLayout()
        ctrl_row.addWidget(BodyLabel("Target language:", card))
        self._lang_combo = ComboBox(card)
        self._lang_combo.addItems(list(TranslateWorker.LANGUAGES.keys()))
        ctrl_row.addWidget(self._lang_combo)
        ctrl_row.addStretch(1)
        self._translate_btn = PrimaryPushButton("Translate", card)
        self._translate_btn.setIcon(FluentIcon.LANGUAGE)
        self._translate_btn.clicked.connect(self._do_translate)
        ctrl_row.addWidget(self._translate_btn)
        lay.addLayout(ctrl_row)

        self._translate_progress = IndeterminateProgressBar(card)
        self._translate_progress.setVisible(False)
        lay.addWidget(self._translate_progress)

        self._translate_status = BodyLabel("", card)
        lay.addWidget(self._translate_status)

        cols_row = QHBoxLayout()
        src_col = QVBoxLayout()
        src_col.addWidget(StrongBodyLabel("Source text", card))
        self._translate_input = PlainTextEdit(card)
        self._translate_input.setPlaceholderText("Paste any text to translate (title, description, comment …)")
        self._translate_input.setMinimumHeight(100)
        src_col.addWidget(self._translate_input)

        dst_col = QVBoxLayout()
        dst_col.addWidget(StrongBodyLabel("Translation", card))
        self._translate_output = PlainTextEdit(card)
        self._translate_output.setReadOnly(True)
        self._translate_output.setMinimumHeight(100)
        dst_col.addWidget(self._translate_output)

        cols_row.addLayout(src_col, 1)
        cols_row.addLayout(dst_col, 1)
        lay.addLayout(cols_row)

        self._layout.addWidget(card)

    # ── Stats logic ───────────────────────────────────────────────────────

    def _fetch_stats(self):
        url = self._stats_url.text().strip()
        if not url:
            self._stats_status.setText("Enter a URL first.")
            return
        if self._meta_worker and self._meta_worker.isRunning():
            return

        s = load_settings()
        self._meta_worker = MetaFetchWorker(url, cookies_file=s.get("cookies_file", ""), parent=self)
        self._meta_worker.log_line.connect(lambda m: add_log_entry("info", m))
        self._meta_worker.data_ready.connect(self._on_stats_ready)
        self._meta_worker.finished_signal.connect(self._on_stats_done)
        self._stats_progress.setVisible(True)
        self._stats_btn.setEnabled(False)
        self._stats_status.setText("Fetching…")
        self._meta_worker.start()

    def _on_stats_ready(self, info: dict):
        self._stats_table.setRowCount(0)

        def _add(metric: str, value: str):
            row = self._stats_table.rowCount()
            self._stats_table.insertRow(row)
            self._stats_table.setItem(row, 0, QTableWidgetItem(metric))
            self._stats_table.setItem(row, 1, QTableWidgetItem(value))

        for field, label in _STAT_FIELDS:
            raw = info.get(field)
            if raw is None:
                continue
            if field == "upload_date":
                val = fmt_date(str(raw))
            elif field == "duration":
                val = fmt_duration(raw)
            elif field in ("view_count", "like_count", "dislike_count",
                           "comment_count", "channel_follower_count"):
                val = fmt_num(raw)
            elif field == "tags":
                tags = list(raw) if raw else []
                val = ", ".join(tags[:20]) + ("…" if len(tags) > 20 else "")
            elif field == "categories":
                val = ", ".join(list(raw)) if raw else "—"
            elif field == "description":
                desc = str(raw).strip()
                val = (desc[:200] + "…") if len(desc) > 200 else desc
            else:
                val = str(raw)
            _add(label, val or "—")

        # Populate translation input with description if empty
        if not self._translate_input.toPlainText().strip():
            desc = info.get("description", "")
            if desc:
                self._translate_input.setPlainText(str(desc)[:500])

    def _on_stats_done(self, success: bool, msg: str):
        self._stats_progress.setVisible(False)
        self._stats_btn.setEnabled(True)
        self._stats_status.setText(msg)

    # ── Comments logic ────────────────────────────────────────────────────

    def _fetch_comments(self):
        url = self._comments_url.text().strip()
        if not url:
            self._comments_status.setText("Enter a URL first.")
            return
        if self._comments_worker and self._comments_worker.isRunning():
            return

        s = load_settings()
        self._comments_worker = CommentsWorker(
            url,
            max_comments=self._comments_max.value(),
            cookies_file=s.get("cookies_file", ""),
            parent=self,
        )
        self._comments_worker.log_line.connect(lambda m: add_log_entry("info", m))
        self._comments_worker.comments_ready.connect(self._on_comments_ready)
        self._comments_worker.finished_signal.connect(self._on_comments_done)
        self._comments_progress.setVisible(True)
        self._comments_btn.setEnabled(False)
        self._comments_status.setText("Fetching comments…")
        self._comments_worker.start()

    def _on_comments_ready(self, comments: list):
        self._comments_table.setRowCount(0)
        self._stored_comments = comments
        for c in comments:
            row = self._comments_table.rowCount()
            self._comments_table.insertRow(row)
            self._comments_table.setItem(row, 0, QTableWidgetItem(c.get("author") or ""))
            text = (c.get("text") or "").replace("\n", " ")
            self._comments_table.setItem(row, 1, QTableWidgetItem(text[:200]))
            self._comments_table.setItem(row, 2, QTableWidgetItem(fmt_num(c.get("like_count"))))
            ts = c.get("timestamp") or c.get("modified_timestamp") or 0
            date_str = ""
            if ts:
                try:
                    from datetime import datetime
                    date_str = datetime.utcfromtimestamp(int(ts)).strftime("%Y-%m-%d")
                except Exception:
                    pass
            self._comments_table.setItem(row, 3, QTableWidgetItem(date_str))
        self._export_comments_btn.setEnabled(bool(comments))

    def _on_comments_done(self, success: bool, msg: str):
        self._comments_progress.setVisible(False)
        self._comments_btn.setEnabled(True)
        self._comments_status.setText(msg)

    def _export_comments(self):
        from PyQt5.QtWidgets import QFileDialog
        comments = getattr(self, "_stored_comments", [])
        if not comments:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Export Comments", "comments.csv", "CSV files (*.csv)")
        if not path:
            return
        try:
            import csv
            with open(path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                writer.writerow(["Author", "Comment", "Likes", "Date"])
                for c in comments:
                    ts = c.get("timestamp") or 0
                    date_str = ""
                    if ts:
                        try:
                            from datetime import datetime
                            date_str = datetime.utcfromtimestamp(int(ts)).strftime("%Y-%m-%d")
                        except Exception:
                            pass
                    writer.writerow([
                        c.get("author") or "",
                        (c.get("text") or "").replace("\n", " "),
                        c.get("like_count") or 0,
                        date_str,
                    ])
            self._comments_status.setText(f"Exported {len(comments)} comments → {path}")
        except Exception as exc:
            self._comments_status.setText(f"Export failed: {exc}")

    # ── Search logic ──────────────────────────────────────────────────────

    def _do_search(self):
        kw = self._search_kw.text().strip()
        if not kw:
            self._search_status.setText("Enter a keyword first.")
            return
        if self._search_worker and self._search_worker.isRunning():
            return

        s = load_settings()
        self._search_worker = SearchWorker(
            kw,
            platform=self._search_platform.currentText(),
            is_hashtag=self._hashtag_switch.isChecked(),
            cookies_file=s.get("cookies_file", ""),
            parent=self,
        )
        self._search_worker.log_line.connect(lambda m: add_log_entry("info", m))
        self._search_worker.results_ready.connect(self._on_results_ready)
        self._search_worker.finished_signal.connect(self._on_search_done)
        self._search_progress.setVisible(True)
        self._search_btn.setEnabled(False)
        self._search_status.setText("Searching…")
        self._search_worker.start()

    def _on_results_ready(self, results: list):
        self._search_results = results
        self._populate_search_table(results)

    def _populate_search_table(self, results: list):
        self._search_table.setRowCount(0)
        for r in results:
            row = self._search_table.rowCount()
            self._search_table.insertRow(row)
            self._search_table.setItem(row, 0, QTableWidgetItem(r.get("title") or ""))
            self._search_table.setItem(row, 1, QTableWidgetItem(r.get("uploader") or ""))
            views_item = QTableWidgetItem(fmt_num(r.get("view_count")))
            views_item.setData(Qt.UserRole, r.get("view_count") or 0)
            self._search_table.setItem(row, 2, views_item)
            likes_item = QTableWidgetItem(fmt_num(r.get("like_count")))
            likes_item.setData(Qt.UserRole, r.get("like_count") or 0)
            self._search_table.setItem(row, 3, likes_item)
            self._search_table.setItem(row, 4, QTableWidgetItem(fmt_duration(r.get("duration"))))
            self._search_table.setItem(row, 5, QTableWidgetItem(fmt_date(r.get("upload_date") or "")))

    def _sort_results(self):
        option = self._search_sort.currentText()
        results = list(self._search_results)
        if option == "Views (high→low)":
            results.sort(key=lambda r: r.get("view_count") or 0, reverse=True)
        elif option == "Likes (high→low)":
            results.sort(key=lambda r: r.get("like_count") or 0, reverse=True)
        elif option == "Date (newest)":
            results.sort(key=lambda r: r.get("upload_date") or "", reverse=True)
        elif option == "Date (oldest)":
            results.sort(key=lambda r: r.get("upload_date") or "")
        self._populate_search_table(results)

    def _on_search_done(self, success: bool, msg: str):
        self._search_progress.setVisible(False)
        self._search_btn.setEnabled(True)
        self._search_status.setText(msg)

    def _on_result_double_clicked(self, index):
        row = index.row()
        if row < len(self._search_results):
            url = self._search_results[row].get("url", "")
            if url:
                # Copy URL to clipboard
                from PyQt5.QtWidgets import QApplication
                QApplication.clipboard().setText(url)
                self._search_status.setText(f"URL copied: {url[:60]}…" if len(url) > 60 else f"URL copied: {url}")

    # ── Translation logic ─────────────────────────────────────────────────

    def _do_translate(self):
        text = self._translate_input.toPlainText().strip()
        if not text:
            self._translate_status.setText("Enter text to translate.")
            return
        if self._translate_worker and self._translate_worker.isRunning():
            return

        lang_name = self._lang_combo.currentText()
        lang_code = TranslateWorker.LANGUAGES.get(lang_name, "en")
        self._translate_worker = TranslateWorker(text, target_lang=lang_code, parent=self)
        self._translate_worker.log_line.connect(lambda m: add_log_entry("info", m))
        self._translate_worker.translation_ready.connect(self._translate_output.setPlainText)
        self._translate_worker.finished_signal.connect(self._on_translate_done)
        self._translate_progress.setVisible(True)
        self._translate_btn.setEnabled(False)
        self._translate_status.setText("Translating…")
        self._translate_worker.start()

    def _on_translate_done(self, success: bool, msg: str):
        self._translate_progress.setVisible(False)
        self._translate_btn.setEnabled(True)
        self._translate_status.setText(msg)
