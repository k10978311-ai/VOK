"""
Compile Qt translation files.

Usage:
    python scripts/compile_translations.py

Steps:
    1. Write translated .ts XML files for each language.
    2. Compile every .ts in resources/translations/ to a matching .qm file.

The .qm binary format is a minimal Qt QM implementation that covers the
single-plural, single-context case used by VOK (no numerus forms needed).
"""

from __future__ import annotations

import struct
import xml.etree.ElementTree as ET
from pathlib import Path

# ---------------------------------------------------------------------------
# Translation data  (source_text → translated_text) per locale
# ---------------------------------------------------------------------------

TRANSLATIONS: dict[str, dict[str, str]] = {
    "zh_CN": {
        # DashboardFeatureGrid
        "Included Tools & Features": "包含的工具和功能",
        "Multi-Source Support": "多平台支持",
        "1000+ sites: YouTube, TikTok, Pinterest & more.": (
            "支持 1000+ 个网站：YouTube、TikTok、Pinterest 等"
        ),
        "Quality Selector": "画质选择",
        "Pick 4K, 1080p, 720p or audio-only (MP3/M4A).": (
            "可选 4K、1080p、720p 或仅音频（MP3/M4A）"
        ),
        "Batch Download": "批量下载",
        "Paste multiple URLs or an entire playlist.": "粘贴多个链接或整个播放列表",
        "Smart File Naming": "智能文件命名",
        "Files saved by title/channel automatically.": "自动按标题/频道保存文件",
        # DashboardInstructionsCard
        "How to use": "使用方法",
        "1. Copy a video URL from your browser.": "1. 从浏览器复制视频链接。",
        "2. Go to the Download tab, paste the URL, and choose your format.": (
            "2. 转到下载标签，粘贴链接，选择格式。"
        ),
        "3. Click Download — track progress in the Logs tab.": (
            "3. 点击下载——在日志标签中查看进度。"
        ),
        # DashboardView
        "Dashboard": "仪表盘",
        # HomeBanner
        "VOK Downloader": "VOK 下载器",
        "View on GitHub": "在 GitHub 查看",
        "Watch tutorial on YouTube": "在 YouTube 观看教程",
        (
            "Download from YouTube, TikTok, Pinterest & 1000+ platforms"
            " \u2014 fast, offline, free."
        ): (
            "从 YouTube、TikTok、Pinterest 及 1000+ 个平台下载 — 快速、离线、免费。"
        ),
        "Download": "下载",
        "Paste a URL and start": "粘贴链接开始下载",
        "Logs": "日志",
        "View downloaded files": "查看已下载文件",
        "Open Folder": "打开文件夹",
        "Browse your downloads": "浏览下载内容",
        # SettingsView
        "Settings": "设置",
        "Downloads": "下载",
        "Download path": "下载路径",
        "Choose": "选择",
        "Default download format": "默认下载格式",
        "Video/audio quality and container used for new downloads": "新下载使用的视频/音频质量和容器",
        "Single video only (no playlists)": "仅单个视频（不含播放列表）",
        "Download only the current video; skip playlists when a single URL is used.": "仅下载当前视频；使用单个链接时跳过播放列表。",
        "Download mode": "下载模式",
        "Normal or enhanced download.": "普通或增强下载。",
        "Normal": "普通",
        "Enhance": "增强",
        "Sound alert on completed download": "下载完成音效提醒",
        "Play a sound when a download finishes successfully.": "成功完成下载时播放提示音。",
        "Sound alert on download error": "下载出错音效提醒",
        "Play a sound when a download fails or is skipped.": "下载失败或跳过时播放提示音。",
        "Performance": "性能",
        "Concurrent downloads": "并发下载数",
        "Number of parallel download jobs (1 \u2013 4)": "并行下载任务数（1 – 4）",
        "Concurrent fragments": "并发分段数",
        "Fragment threads per download job (1 \u2013 16)": "每个下载任务的分段线程数（1 – 16）",
        "Appearance": "外观",
        "Application theme": "应用主题",
        "Adjust the appearance of your application": "调整应用程序外观",
        "Light": "浅色",
        "Dark": "深色",
        "Follow system settings": "跟随系统设置",
        "Language": "语言",
        "Application display language (restart may be needed for full effect)": "应用显示语言（可能需要重启才能完全生效）",
        "Accent color": "主题色",
        "Hex color used as the application accent (e.g. #0078D4)": "用作应用主题色的十六进制颜色（如 #0078D4）",
        "Choose\u2026": "选择\u2026",
        "Advanced": "高级",
        "Cookies file": "Cookies 文件",
        "Netscape cookies.txt for sites that require login (ok.ru private, Instagram, etc.)": "需要登录网站的 Netscape cookies.txt（ok.ru 私有、Instagram 等）",
        "Path to cookies.txt (optional)": "cookies.txt 路径（可选）",
        "Browse\u2026": "浏览\u2026",
        "Reset settings": "重置设置",
        "Restore all settings to their factory defaults": "将所有设置恢复出厂默认值",
        "Reset to defaults": "重置为默认值",
        "Software update": "软件更新",
        "Check for updates when the application starts": "应用启动时检查更新",
        "The new version will be more stable and have more features": "新版本将更稳定并拥有更多功能",
        "About": "关于",
        "Help": "帮助",
        "Report bugs, request features, or read the documentation on GitHub": "在 GitHub 报告错误、请求功能或阅读文档",
        "Open help page": "打开帮助页面",
        "Provide feedback": "提供反馈",
        "Submit a bug report or feature request via GitHub Issues": "通过 GitHub Issues 提交错误报告或功能请求",
        "\u00a9 Copyright 2025, VOK Downloader \u2013 Version": "\u00a9 版权所有 2025，VOK 下载器 \u2013 版本",
        "Check update": "检查更新",
        "Reset": "重置",
        "Settings restored to defaults.": "设置已恢复为默认值。",
        "Language changed": "语言已更改",
        "Some text will update on next restart.": "部分文本将在下次重启后更新。",
        "Coming soon!": "即将推出！",
        "Download folder": "下载文件夹",
        "Select cookies file": "选择 Cookies 文件",
        "Text files (*.txt);;All files (*)": "文本文件 (*.txt);;所有文件 (*)",
        "No update": "无更新",
        "You are on the latest version.": "您已是最新版本。",
        "Update available": "有可用更新",
        "New version %1 is available.\n\nUpdate now? The app will close and the new version will be installed.": "新版本 %1 可用。\n\n立即更新？应用将关闭并安装新版本。",
        "Downloading update": "正在下载更新",
        "The installer is downloading. The app will close when ready.": "安装程序正在下载，准备好后应用将关闭。",
        "Update failed": "更新失败",
        "Could not download the update. Try again later.": "无法下载更新，请稍后重试。",
        # Exit Handler
        "Exit Application": "退出应用程序",
        "Are you sure you want to exit VOK completely?\n\nThis will close all downloads and background processes.": "确定要完全退出VOK吗？\n\n这将关闭所有下载和后台进程。",
        "Exit": "退出",
        "Cancel": "取消",
    },
    "ja_JP": {
        "Included Tools & Features": "ツールと機能",
        "Multi-Source Support": "マルチソース対応",
        "1000+ sites: YouTube, TikTok, Pinterest & more.": (
            "1000以上のサイト：YouTube、TikTok、Pinterestなど"
        ),
        "Quality Selector": "画質セレクター",
        "Pick 4K, 1080p, 720p or audio-only (MP3/M4A).": (
            "4K、1080p、720p、またはオーディオのみ（MP3/M4A）を選択"
        ),
        "Batch Download": "一括ダウンロード",
        "Paste multiple URLs or an entire playlist.": (
            "複数のURLまたはプレイリスト全体を貼り付け"
        ),
        "Smart File Naming": "スマートファイル命名",
        "Files saved by title/channel automatically.": "タイトル/チャンネル別に自動保存",
        "How to use": "使い方",
        "1. Copy a video URL from your browser.": "1. ブラウザから動画のURLをコピー。",
        "2. Go to the Download tab, paste the URL, and choose your format.": (
            "2. ダウンロードタブに移動し、URLを貼り付けてフォーマットを選択。"
        ),
        "3. Click Download — track progress in the Logs tab.": (
            "3. ダウンロードをクリック — ログタブで進捗を確認。"
        ),
        "Dashboard": "ダッシュボード",
        "VOK Downloader": "VOK ダウンローダー",
        "View on GitHub": "GitHubで見る",
        "Watch tutorial on YouTube": "YouTubeでチュートリアルを見る",
        (
            "Download from YouTube, TikTok, Pinterest & 1000+ platforms"
            " \u2014 fast, offline, free."
        ): (
            "YouTube、TikTok、Pinterestなど1000以上のプラットフォームから"
            "ダウンロード — 高速・オフライン・無料"
        ),
        "Download": "ダウンロード",
        "Paste a URL and start": "URLを貼り付けて開始",
        "Logs": "ログ",
        "View downloaded files": "ダウンロード済みファイルを表示",
        "Open Folder": "フォルダを開く",
        "Browse your downloads": "ダウンロードを参照",
        # SettingsView
        "Settings": "設定",
        "Downloads": "ダウンロード",
        "Download path": "ダウンロードパス",
        "Choose": "選択",
        "Default download format": "デフォルトのダウンロード形式",
        "Video/audio quality and container used for new downloads": "新規ダウンロードに使用するビデオ/音声品質とコンテナ",
        "Single video only (no playlists)": "単一動画のみ（プレイリストなし）",
        "Download only the current video; skip playlists when a single URL is used.": "現在の動画のみダウンロード；単一URLの場合プレイリストをスキップ。",
        "Download mode": "ダウンロードモード",
        "Normal or enhanced download.": "通常または高速ダウンロード。",
        "Normal": "通常",
        "Enhance": "高速",
        "Sound alert on completed download": "ダウンロード完了時の音声通知",
        "Play a sound when a download finishes successfully.": "ダウンロードが正常に完了したときに音を鳴らします。",
        "Sound alert on download error": "ダウンロードエラー時の音声通知",
        "Play a sound when a download fails or is skipped.": "ダウンロードが失敗またはスキップされたときに音を鳴らします。",
        "Performance": "パフォーマンス",
        "Concurrent downloads": "同時ダウンロード数",
        "Number of parallel download jobs (1 \u2013 4)": "並列ダウンロードジョブ数（1 ～ 4）",
        "Concurrent fragments": "同時フラグメント数",
        "Fragment threads per download job (1 \u2013 16)": "ダウンロードジョブごとのフラグメントスレッド数（1 ～ 16）",
        "Appearance": "外観",
        "Application theme": "アプリテーマ",
        "Adjust the appearance of your application": "アプリの外観を調整します",
        "Light": "ライト",
        "Dark": "ダーク",
        "Follow system settings": "システム設定に従う",
        "Language": "言語",
        "Application display language (restart may be needed for full effect)": "アプリの表示言語（完全に反映するには再起動が必要な場合があります）",
        "Accent color": "アクセントカラー",
        "Hex color used as the application accent (e.g. #0078D4)": "アプリのアクセントカラーとして使用する16進数カラー（例：#0078D4）",
        "Choose\u2026": "選択\u2026",
        "Advanced": "詳細設定",
        "Cookies file": "Cookieファイル",
        "Netscape cookies.txt for sites that require login (ok.ru private, Instagram, etc.)": "ログインが必要なサイト用のNetscape cookies.txt（ok.ruプライベート、Instagramなど）",
        "Path to cookies.txt (optional)": "cookies.txtのパス（任意）",
        "Browse\u2026": "参照\u2026",
        "Reset settings": "設定をリセット",
        "Restore all settings to their factory defaults": "すべての設定を初期値に戻します",
        "Reset to defaults": "デフォルトに戻す",
        "Software update": "ソフトウェアアップデート",
        "Check for updates when the application starts": "アプリ起動時にアップデートを確認",
        "The new version will be more stable and have more features": "新バージョンはより安定し、より多くの機能を持ちます",
        "About": "バージョン情報",
        "Help": "ヘルプ",
        "Report bugs, request features, or read the documentation on GitHub": "GitHubでバグ報告、機能リクエスト、またはドキュメントを読む",
        "Open help page": "ヘルプページを開く",
        "Provide feedback": "フィードバックを送信",
        "Submit a bug report or feature request via GitHub Issues": "GitHub Issuesでバグ報告または機能リクエストを送信",
        "\u00a9 Copyright 2025, VOK Downloader \u2013 Version": "\u00a9 Copyright 2025, VOK ダウンローダー \u2013 バージョン",
        "Check update": "アップデートを確認",
        "Reset": "リセット",
        "Settings restored to defaults.": "設定をデフォルトに戻しました。",
        "Language changed": "言語を変更しました",
        "Some text will update on next restart.": "一部のテキストは次回の再起動時に更新されます。",
        "Coming soon!": "近日公開！",
        "Download folder": "ダウンロードフォルダ",
        "Select cookies file": "Cookieファイルを選択",
        "Text files (*.txt);;All files (*)": "テキストファイル (*.txt);;すべてのファイル (*)",
        "No update": "アップデートなし",
        "You are on the latest version.": "最新バージョンをご利用中です。",
        "Update available": "アップデートが利用可能",
        "New version %1 is available.\n\nUpdate now? The app will close and the new version will be installed.": "新バージョン %1 が利用可能です。\n\n今すぐアップデートしますか？アプリが閉じて新バージョンがインストールされます。",
        "Downloading update": "アップデートをダウンロード中",
        "The installer is downloading. The app will close when ready.": "インストーラをダウンロード中です。準備ができるとアプリが閉じます。",
        "Update failed": "アップデート失敗",
        "Could not download the update. Try again later.": "アップデートをダウンロードできませんでした。後でもう一度お試しください。",
        # Exit Handler
        "Exit Application": "アプリケーションを終了",
        "Are you sure you want to exit VOK completely?\n\nThis will close all downloads and background processes.": "VOKを完全に終了してもよろしいですか？\n\nすべてのダウンロードとバックグラウンドプロセスが終了されます。",
        "Exit": "終了",
        "Cancel": "キャンセル",
    },
    "ko_KR": {
        "Included Tools & Features": "포함된 도구 및 기능",
        "Multi-Source Support": "멀티 소스 지원",
        "1000+ sites: YouTube, TikTok, Pinterest & more.": (
            "1000개 이상 사이트: YouTube, TikTok, Pinterest 등"
        ),
        "Quality Selector": "화질 선택",
        "Pick 4K, 1080p, 720p or audio-only (MP3/M4A).": (
            "4K, 1080p, 720p 또는 오디오만(MP3/M4A) 선택"
        ),
        "Batch Download": "일괄 다운로드",
        "Paste multiple URLs or an entire playlist.": (
            "여러 URL 또는 전체 재생목록 붙여넣기"
        ),
        "Smart File Naming": "스마트 파일 명명",
        "Files saved by title/channel automatically.": "제목/채널별로 자동 저장",
        "How to use": "사용 방법",
        "1. Copy a video URL from your browser.": (
            "1. 브라우저에서 동영상 URL을 복사하세요."
        ),
        "2. Go to the Download tab, paste the URL, and choose your format.": (
            "2. 다운로드 탭으로 이동하여 URL을 붙여넣고 형식을 선택하세요."
        ),
        "3. Click Download — track progress in the Logs tab.": (
            "3. 다운로드를 클릭하세요 — 로그 탭에서 진행 상황을 확인하세요."
        ),
        "Dashboard": "대시보드",
        "VOK Downloader": "VOK 다운로더",
        "View on GitHub": "GitHub에서 보기",
        "Watch tutorial on YouTube": "YouTube에서 튜토리얼 보기",
        (
            "Download from YouTube, TikTok, Pinterest & 1000+ platforms"
            " \u2014 fast, offline, free."
        ): (
            "YouTube, TikTok, Pinterest 및 1000개 이상의 플랫폼에서 다운로드"
            " — 빠르고, 오프라인, 무료"
        ),
        "Download": "다운로드",
        "Paste a URL and start": "URL을 붙여넣고 시작",
        "Logs": "로그",
        "View downloaded files": "다운로드된 파일 보기",
        "Open Folder": "폴더 열기",
        "Browse your downloads": "다운로드 탐색",
        # SettingsView
        "Settings": "설정",
        "Downloads": "다운로드",
        "Download path": "다운로드 경로",
        "Choose": "선택",
        "Default download format": "기본 다운로드 형식",
        "Video/audio quality and container used for new downloads": "새 다운로드에 사용할 비디오/오디오 품질 및 컨테이너",
        "Single video only (no playlists)": "단일 동영상만 (재생목록 제외)",
        "Download only the current video; skip playlists when a single URL is used.": "현재 동영상만 다운로드; 단일 URL 사용 시 재생목록을 건너뜁니다.",
        "Download mode": "다운로드 모드",
        "Normal or enhanced download.": "일반 또는 향상된 다운로드.",
        "Normal": "일반",
        "Enhance": "향상",
        "Sound alert on completed download": "다운로드 완료 시 소리 알림",
        "Play a sound when a download finishes successfully.": "다운로드가 성공적으로 완료되면 소리를 재생합니다.",
        "Sound alert on download error": "다운로드 오류 시 소리 알림",
        "Play a sound when a download fails or is skipped.": "다운로드가 실패하거나 건너뛰어지면 소리를 재생합니다.",
        "Performance": "성능",
        "Concurrent downloads": "동시 다운로드 수",
        "Number of parallel download jobs (1 \u2013 4)": "병렬 다운로드 작업 수 (1 – 4)",
        "Concurrent fragments": "동시 조각 수",
        "Fragment threads per download job (1 \u2013 16)": "다운로드 작업당 조각 스레드 수 (1 – 16)",
        "Appearance": "외관",
        "Application theme": "앱 테마",
        "Adjust the appearance of your application": "앱 외관을 조정합니다",
        "Light": "라이트",
        "Dark": "다크",
        "Follow system settings": "시스템 설정 따르기",
        "Language": "언어",
        "Application display language (restart may be needed for full effect)": "앱 표시 언어 (완전히 적용하려면 재시작이 필요할 수 있음)",
        "Accent color": "강조 색상",
        "Hex color used as the application accent (e.g. #0078D4)": "앱 강조 색상으로 사용할 16진수 색상 (예: #0078D4)",
        "Choose\u2026": "선택\u2026",
        "Advanced": "고급",
        "Cookies file": "쿠키 파일",
        "Netscape cookies.txt for sites that require login (ok.ru private, Instagram, etc.)": "로그인이 필요한 사이트용 Netscape cookies.txt (ok.ru 비공개, Instagram 등)",
        "Path to cookies.txt (optional)": "cookies.txt 경로 (선택)",
        "Browse\u2026": "찾아보기\u2026",
        "Reset settings": "설정 초기화",
        "Restore all settings to their factory defaults": "모든 설정을 초기값으로 복원합니다",
        "Reset to defaults": "기본값으로 초기화",
        "Software update": "소프트웨어 업데이트",
        "Check for updates when the application starts": "앱 시작 시 업데이트 확인",
        "The new version will be more stable and have more features": "새 버전은 더 안정적이고 더 많은 기능을 제공합니다",
        "About": "정보",
        "Help": "도움말",
        "Report bugs, request features, or read the documentation on GitHub": "GitHub에서 버그 신고, 기능 요청 또는 문서 읽기",
        "Open help page": "도움말 페이지 열기",
        "Provide feedback": "피드백 제공",
        "Submit a bug report or feature request via GitHub Issues": "GitHub Issues를 통해 버그 보고 또는 기능 요청 제출",
        "\u00a9 Copyright 2025, VOK Downloader \u2013 Version": "\u00a9 Copyright 2025, VOK 다운로더 \u2013 버전",
        "Check update": "업데이트 확인",
        "Reset": "초기화",
        "Settings restored to defaults.": "설정이 기본값으로 복원되었습니다.",
        "Language changed": "언어 변경됨",
        "Some text will update on next restart.": "일부 텍스트는 다음 재시작 시 업데이트됩니다.",
        "Coming soon!": "곧 출시 예정!",
        "Download folder": "다운로드 폴더",
        "Select cookies file": "쿠키 파일 선택",
        "Text files (*.txt);;All files (*)": "텍스트 파일 (*.txt);;모든 파일 (*)",
        "No update": "업데이트 없음",
        "You are on the latest version.": "최신 버전을 사용 중입니다.",
        "Update available": "업데이트 가능",
        "New version %1 is available.\n\nUpdate now? The app will close and the new version will be installed.": "새 버전 %1 이 출시되었습니다.\n\n지금 업데이트하시겠습니까? 앱이 닫히고 새 버전이 설치됩니다.",
        "Downloading update": "업데이트 다운로드 중",
        "The installer is downloading. The app will close when ready.": "설치 프로그램을 다운로드 중입니다. 준비되면 앱이 닫힙니다.",
        "Update failed": "업데이트 실패",
        "Could not download the update. Try again later.": "업데이트를 다운로드할 수 없습니다. 나중에 다시 시도하세요.",
        # Exit Handler
        "Exit Application": "응용 프로그램 종료",
        "Are you sure you want to exit VOK completely?\n\nThis will close all downloads and background processes.": "VOK를 완전히 종료하시겠습니까?\n\n모든 다운로드와 백그라운드 프로세스가 종료됩니다.",
        "Exit": "종료",
        "Cancel": "취소",
    },
    "ru_RU": {
        "Included Tools & Features": "Инструменты и функции",
        "Multi-Source Support": "Поддержка нескольких источников",
        "1000+ sites: YouTube, TikTok, Pinterest & more.": (
            "1000+ сайтов: YouTube, TikTok, Pinterest и другие"
        ),
        "Quality Selector": "Выбор качества",
        "Pick 4K, 1080p, 720p or audio-only (MP3/M4A).": (
            "Выберите 4K, 1080p, 720p или только аудио (MP3/M4A)"
        ),
        "Batch Download": "Пакетная загрузка",
        "Paste multiple URLs or an entire playlist.": (
            "Вставьте несколько ссылок или целый плейлист"
        ),
        "Smart File Naming": "Умное именование файлов",
        "Files saved by title/channel automatically.": (
            "Файлы сохраняются по названию/каналу автоматически"
        ),
        "How to use": "Как использовать",
        "1. Copy a video URL from your browser.": (
            "1. Скопируйте URL видео из браузера."
        ),
        "2. Go to the Download tab, paste the URL, and choose your format.": (
            "2. Перейдите на вкладку загрузки, вставьте URL и выберите формат."
        ),
        "3. Click Download — track progress in the Logs tab.": (
            "3. Нажмите Загрузить — отслеживайте прогресс во вкладке журнала."
        ),
        "Dashboard": "Главная",
        "VOK Downloader": "VOK Загрузчик",
        "View on GitHub": "Просмотр на GitHub",
        "Watch tutorial on YouTube": "Смотреть обучение на YouTube",
        (
            "Download from YouTube, TikTok, Pinterest & 1000+ platforms"
            " \u2014 fast, offline, free."
        ): (
            "Загружайте с YouTube, TikTok, Pinterest и 1000+ платформ"
            " — быстро, офлайн, бесплатно"
        ),
        "Download": "Скачать",
        "Paste a URL and start": "Вставьте ссылку и начните",
        "Logs": "Журнал",
        "View downloaded files": "Просмотр загруженных файлов",
        "Open Folder": "Открыть папку",
        "Browse your downloads": "Просмотр загрузок",
        # SettingsView
        "Settings": "Настройки",
        "Downloads": "Загрузки",
        "Download path": "Путь загрузки",
        "Choose": "Выбрать",
        "Default download format": "Формат загрузки по умолчанию",
        "Video/audio quality and container used for new downloads": "Качество видео/аудио и контейнер для новых загрузок",
        "Single video only (no playlists)": "Только одно видео (без плейлистов)",
        "Download only the current video; skip playlists when a single URL is used.": "Загружать только текущее видео; пропускать плейлисты при одиночном URL.",
        "Download mode": "Режим загрузки",
        "Normal or enhanced download.": "Обычная или улучшенная загрузка.",
        "Normal": "Обычный",
        "Enhance": "Улучшенный",
        "Sound alert on completed download": "Звуковое оповещение о завершении загрузки",
        "Play a sound when a download finishes successfully.": "Воспроизвести звук при успешном завершении загрузки.",
        "Sound alert on download error": "Звуковое оповещение об ошибке загрузки",
        "Play a sound when a download fails or is skipped.": "Воспроизвести звук при ошибке или пропуске загрузки.",
        "Performance": "Производительность",
        "Concurrent downloads": "Параллельные загрузки",
        "Number of parallel download jobs (1 \u2013 4)": "Количество параллельных задач загрузки (1 – 4)",
        "Concurrent fragments": "Параллельные фрагменты",
        "Fragment threads per download job (1 \u2013 16)": "Потоки фрагментов на задачу загрузки (1 – 16)",
        "Appearance": "Оформление",
        "Application theme": "Тема приложения",
        "Adjust the appearance of your application": "Настройте внешний вид приложения",
        "Light": "Светлая",
        "Dark": "Тёмная",
        "Follow system settings": "Следовать системным настройкам",
        "Language": "Язык",
        "Application display language (restart may be needed for full effect)": "Язык отображения приложения (для полного эффекта может потребоваться перезапуск)",
        "Accent color": "Цвет акцента",
        "Hex color used as the application accent (e.g. #0078D4)": "Шестнадцатеричный цвет акцента приложения (например #0078D4)",
        "Choose\u2026": "Выбрать\u2026",
        "Advanced": "Расширенные",
        "Cookies file": "Файл Cookies",
        "Netscape cookies.txt for sites that require login (ok.ru private, Instagram, etc.)": "Netscape cookies.txt для сайтов с авторизацией (ok.ru приватный, Instagram и др.)",
        "Path to cookies.txt (optional)": "Путь к cookies.txt (необязательно)",
        "Browse\u2026": "Обзор\u2026",
        "Reset settings": "Сбросить настройки",
        "Restore all settings to their factory defaults": "Восстановить все настройки до заводских значений",
        "Reset to defaults": "Сбросить по умолчанию",
        "Software update": "Обновление ПО",
        "Check for updates when the application starts": "Проверять обновления при запуске приложения",
        "The new version will be more stable and have more features": "Новая версия будет более стабильной и функциональной",
        "About": "О программе",
        "Help": "Справка",
        "Report bugs, request features, or read the documentation on GitHub": "Сообщить об ошибках, запросить функции или прочитать документацию на GitHub",
        "Open help page": "Открыть страницу справки",
        "Provide feedback": "Оставить отзыв",
        "Submit a bug report or feature request via GitHub Issues": "Отправить отчёт об ошибке или запрос на добавление функции через GitHub Issues",
        "\u00a9 Copyright 2025, VOK Downloader \u2013 Version": "\u00a9 Авторские права 2025, VOK Загрузчик \u2013 Версия",
        "Check update": "Проверить обновления",
        "Reset": "Сброс",
        "Settings restored to defaults.": "Настройки восстановлены по умолчанию.",
        "Language changed": "Язык изменён",
        "Some text will update on next restart.": "Некоторые тексты обновятся при следующем запуске.",
        "Coming soon!": "Скоро!",
        "Download folder": "Папка загрузки",
        "Select cookies file": "Выбрать файл Cookies",
        "Text files (*.txt);;All files (*)": "Текстовые файлы (*.txt);;Все файлы (*)",
        "No update": "Нет обновлений",
        "You are on the latest version.": "У вас установлена последняя версия.",
        "Update available": "Доступно обновление",
        "New version %1 is available.\n\nUpdate now? The app will close and the new version will be installed.": "Доступна новая версия %1.\n\nОбновить сейчас? Приложение закроется и новая версия будет установлена.",
        "Downloading update": "Загрузка обновления",
        "The installer is downloading. The app will close when ready.": "Установщик загружается. Приложение закроется, когда будет готово.",
        "Update failed": "Ошибка обновления",
        "Could not download the update. Try again later.": "Не удалось загрузить обновление. Попробуйте позже.",
        # Exit Handler
        "Exit Application": "Выйти из приложения",
        "Are you sure you want to exit VOK completely?\n\nThis will close all downloads and background processes.": "Вы уверены, что хотите полностью выйти из VOK?\n\nЭто закроет все загрузки и фоновые процессы.",
        "Exit": "Выйти",
        "Cancel": "Отмена",
    },
    "km_KH": {
        "Included Tools & Features": "ឧបករណ៍ និងមុខងារ",
        "Multi-Source Support": "គាំទ្រប្រភពច្រើន",
        "1000+ sites: YouTube, TikTok, Pinterest & more.": (
            "1000+ គេហទំព័រ: YouTube, TikTok, Pinterest និងច្រើនទៀត"
        ),
        "Quality Selector": "ជ្រើសរើសគុណភាព",
        "Pick 4K, 1080p, 720p or audio-only (MP3/M4A).": (
            "ជ្រើស 4K, 1080p, 720p ឬដែលមានតែសំឡេង (MP3/M4A)"
        ),
        "Batch Download": "ទាញយកជាបាច់",
        "Paste multiple URLs or an entire playlist.": (
            "បិទ URL ច្រើន ឬបញ្ជីចាក់ទាំងមូល"
        ),
        "Smart File Naming": "ដាក់ឈ្មោះឯកសារស្វ័យប្រវត្តិ",
        "Files saved by title/channel automatically.": (
            "ឯកសារត្រូវបានរក្សាទុកដោយចំណងជើង/ប៉ុស្តិ៍ដោយស្វ័យប្រវត្តិ"
        ),
        "How to use": "របៀបប្រើ",
        "1. Copy a video URL from your browser.": (
            "1. ចម្លង URL វីដេអូពីកម្មវិធីរុករករបស់អ្នក"
        ),
        "2. Go to the Download tab, paste the URL, and choose your format.": (
            "2. ចូលទៅផ្ទាំង ទាញយក បិទ URL ហើយជ្រើសទម្រង់"
        ),
        "3. Click Download — track progress in the Logs tab.": (
            "3. ចុច ទាញយក — តាមដានវឌ្ឍនភាពនៅផ្ទាំង កំណត់ហេតុ"
        ),
        "Dashboard": "ផ្ទាំងគ្រប់គ្រង",
        "VOK Downloader": "VOK Get",
        "View on GitHub": "មើលនៅ GitHub",
        "Watch tutorial on YouTube": "មើលការណែនាំនៅ YouTube",
        (
            "Download from YouTube, TikTok, Pinterest & 1000+ platforms"
            " \u2014 fast, offline, free."
        ): (
            "ទាញយកពី YouTube, TikTok, Pinterest និង 1000+ វេទិកា"
            " — លឿន, គ្មានអ៊ីនធឺណិត, ឥតគិតថ្លៃ"
        ),
        "Download": "ទាញយក",
        "Paste a URL and start": "បិទ URL ហើយចាប់ផ្តើម",
        "Logs": "កំណត់ហេតុ",
        "View downloaded files": "មើលឯកសារដែលបានទាញយក",
        "Open Folder": "បើកថត",
        "Browse your downloads": "រុករកការទាញយករបស់អ្នក",
        # SettingsView
        "Settings": "ការកំណត់",
        "Downloads": "ការទាញយក",
        "Download path": "ផ្លូវទាញយក",
        "Choose": "ជ្រើសរើស",
        "Default download format": "ទម្រង់ទាញយកលំនាំដើម",
        "Video/audio quality and container used for new downloads": "គុណភាពវីដេអូ/សំឡេង និងធុងប្រើប្រាស់សម្រាប់ការទាញយកថ្មី",
        "Single video only (no playlists)": "តែវីដេអូតែមួយ (គ្មានបញ្ជីចាក់)",
        "Download only the current video; skip playlists when a single URL is used.": "ទាញយកតែវីដេអូបច្ចុប្បន្ន; រំលងបញ្ជីចាក់នៅពេលប្រើ URL តែមួយ។",
        "Download mode": "របៀបទាញយក",
        "Normal or enhanced download.": "ការទាញយកធម្មតា ឬកម្រិតខ្ពស់។",
        "Normal": "ធម្មតា",
        "Enhance": "កម្រិតខ្ពស់",
        "Sound alert on completed download": "សំឡេងជូនដំណឹងនៅពេលទាញយករួច",
        "Play a sound when a download finishes successfully.": "លឺសំឡេងនៅពេលទាញយករួចជោគជ័យ។",
        "Sound alert on download error": "សំឡេងជូនដំណឹងនៅពេលការទាញយកបរាជ័យ",
        "Play a sound when a download fails or is skipped.": "លឺសំឡេងនៅពេលការទាញយកបរាជ័យ ឬត្រូវបានរំលង។",
        "Performance": "ប្រសិទ្ធភាព",
        "Concurrent downloads": "ការទាញយកដំណាលគ្នា",
        "Number of parallel download jobs (1 \u2013 4)": "ចំនួនការងារទាញយកដំណាលគ្នា (1 – 4)",
        "Concurrent fragments": "ចំណែកដំណាលគ្នា",
        "Fragment threads per download job (1 \u2013 16)": "ចំនួននូវវីតដំណាលគ្នាក្នុងការងារទាញយកនីមួយៗ (1 – 16)",
        "Appearance": "រូបរាង",
        "Application theme": "រូបរាងកម្មវិធី",
        "Adjust the appearance of your application": "កែតម្រូវរូបរាងកម្មវិធីរបស់អ្នក",
        "Light": "ភ្លឺ",
        "Dark": "ងងឹត",
        "Follow system settings": "តាមការកំណត់ប្រព័ន្ធ",
        "Language": "ភាសា",
        "Application display language (restart may be needed for full effect)": "ភាសាបង្ហាញកម្មវិធី (ប្រហែលត្រូវតែចាប់ផ្ដើមឡើងវិញ)",
        "Accent color": "ពណ៌ស្តង់ដារ",
        "Hex color used as the application accent (e.g. #0078D4)": "ពណ៌ hex ប្រើជាពណ៌ស្តង់ដារ (ឧ. #0078D4)",
        "Choose\u2026": "ជ្រើសរើស\u2026",
        "Advanced": "កម្រិតខ្ពស់",
        "Cookies file": "ឯកសារ Cookies",
        "Netscape cookies.txt for sites that require login (ok.ru private, Instagram, etc.)": "Netscape cookies.txt សម្រាប់គេហទំព័រដែលទាមទារការចូល (ok.ru ឯកជន, Instagram ។ល។)",
        "Path to cookies.txt (optional)": "ផ្លូវទៅ cookies.txt (ស្រេចចិត្ត)",
        "Browse\u2026": "រុករក\u2026",
        "Reset settings": "កំណត់ការកំណត់ឡើងវិញ",
        "Restore all settings to their factory defaults": "ស្ដារការកំណត់ទាំងអស់ទៅលំនាំដើម",
        "Reset to defaults": "កំណត់ជាលំនាំដើម",
        "Software update": "ការធ្វើបច្ចុប្បន្នភាពកម្មវិធី",
        "Check for updates when the application starts": "ពិនិត្យការធ្វើបច្ចុប្បន្នភាពនៅពេលដើរកម្មវិធី",
        "The new version will be more stable and have more features": "កំណែថ្មីនឹងមានស្ថិរភាពជាងមុន និងមុខងារច្រើនជាងមុន",
        "About": "អំពី",
        "Help": "ជំនួយ",
        "Report bugs, request features, or read the documentation on GitHub": "រាយការណ៍កំហុស សុំមុខងារ ឬអានឯកសារនៅ GitHub",
        "Open help page": "បើកទំព័រជំនួយ",
        "Provide feedback": "ផ្ដល់មតិ",
        "Submit a bug report or feature request via GitHub Issues": "ដាក់ស្នើរបាយការណ៍កំហុស ឬសំណើមុខងារតាម GitHub Issues",
        "\u00a9 Copyright 2025, VOK Downloader \u2013 Version": "\u00a9 រក្សាសិទ្ធិ 2025, VOK កម្មវិធីទាញយក \u2013 កំណែ",
        "Check update": "ពិនិត្យបច្ចុប្បន្នភាព",
        "Reset": "កំណត់ឡើងវិញ",
        "Settings restored to defaults.": "ការកំណត់ត្រូវបានស្ដារជាលំនាំដើម។",
        "Language changed": "ភាសាត្រូវបានផ្លាស់ប្ដូរ",
        "Some text will update on next restart.": "អក្សរមួយចំនួននឹងត្រូវបានធ្វើបច្ចុប្បន្នភាពនៅការចាប់ផ្ដើមបន្ទាប់។",
        "Coming soon!": "នឹងមកដល់ជាឆាប់!",
        "Download folder": "ថតទាញយក",
        "Select cookies file": "ជ្រើសរើសឯកសារ Cookies",
        "Text files (*.txt);;All files (*)": "ឯកសារអក្សរ (*.txt);;ឯកសារទាំងអស់ (*)",
        "No update": "គ្មានបច្ចុប្បន្នភាព",
        "You are on the latest version.": "អ្នកកំពុងប្រើកំណែចុងក្រោយ។",
        "Update available": "មានបច្ចុប្បន្នភាព",
        "New version %1 is available.\n\nUpdate now? The app will close and the new version will be installed.": "កំណែថ្មី %1 អាចប្រើបាន។\n\nធ្វើបច្ចុប្បន្នភាពឥឡូវ? កម្មវិធីនឹងបិទ ហើយកំណែថ្មីនឹងត្រូវបានដំឡើង។",
        "Downloading update": "កំពុងទាញយកបច្ចុប្បន្នភាព",
        "The installer is downloading. The app will close when ready.": "កំពុងទាញយកកម្មវិធីដំឡើង។ កម្មវិធីនឹងបិទនៅពេលរួចរាល់។",
        "Update failed": "ការធ្វើបច្ចុប្បន្នភាពបរាជ័យ",
        "Could not download the update. Try again later.": "មិនអាចទាញយកបច្ចុប្បន្នភាពបានទេ។ ព្យាយាមម្ដងទៀតនៅពេលក្រោយ។",
        # Exit Handler
        "Exit Application": "ចុះចេញពីកម្មវិធី",
        "Are you sure you want to exit VOK completely?\n\nThis will close all downloads and background processes.": "តើអ្នកប្រាកដថាចង់ចេញពី VOK ទាំងស្រុងឬទេ?\n\nនេះនឹងបិទការទាញយកទាំងអស់ និងដំណើរការផ្ទៃខាងក្រោយ។",
        "Exit": "ចេញ",
        "Cancel": "បោះបង់",
    },
}

# ---------------------------------------------------------------------------
# .ts file writer
# ---------------------------------------------------------------------------

_TS_HEADER = """\
<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE TS>
<TS version="2.1" language="{language}">
"""

_TS_CONTEXT_OPEN = "    <context>\n        <name>{name}</name>\n"
_TS_CONTEXT_CLOSE = "    </context>\n"
_TS_MESSAGE = (
    "        <message>\n"
    "            <source>{source}</source>\n"
    "            <translation>{translation}</translation>\n"
    "        </message>\n"
)


def _xml_escape(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def write_ts(ts_path: Path, language: str, lookup: dict[str, str]) -> None:
    """Regenerate a .ts file with filled-in translations."""
    # Parse existing .ts to preserve context/message structure.
    tree = ET.parse(ts_path)
    root = tree.getroot()

    lines = [_TS_HEADER.format(language=language)]
    for ctx in root.findall("context"):
        name_el = ctx.find("name")
        ctx_name = name_el.text if name_el is not None else ""
        lines.append(_TS_CONTEXT_OPEN.format(name=_xml_escape(ctx_name)))
        for msg in ctx.findall("message"):
            src_el = msg.find("source")
            source = src_el.text if src_el is not None else ""
            translation = lookup.get(source, "")
            lines.append(
                _TS_MESSAGE.format(
                    source=_xml_escape(source),
                    translation=_xml_escape(translation) if translation else "",
                )
            )
        lines.append(_TS_CONTEXT_CLOSE)
    lines.append("</TS>\n")

    ts_path.write_text("".join(lines), encoding="utf-8")
    filled = sum(1 for v in lookup.values() if v)
    print(f"  Wrote {ts_path.name}  ({filled} translations)")


# ---------------------------------------------------------------------------
# .qm binary compiler
# ---------------------------------------------------------------------------

# Real Qt .qm magic (16 bytes)
_QM_MAGIC = bytes([
    0x3C, 0xB8, 0x64, 0x18,
    0xCA, 0xEF, 0x9C, 0x95,
    0xCD, 0x21, 0x1C, 0xBF,
    0x60, 0xA1, 0xBD, 0xDD,
])

_TAG_END = 0x01
_TAG_TRANSLATION = 0x03
_TAG_COMMENT = 0x08
_TAG_SOURCETEXT = 0x06
_TAG_CONTEXT = 0x07

_SEC_LANGUAGE = 0xA7
_SEC_HASHES = 0x42
_SEC_MESSAGES = 0x69
_SEC_NUMERUSRULES = 0x88


def _elf_hash(text: str) -> int:
    """ELF hash used by Qt's QMTranslator for source-text lookup."""
    h = 0
    for byte in text.encode("utf-8"):
        h = ((h << 4) + byte) & 0xFFFFFFFF
        g = h & 0xF0000000
        if g:
            h ^= g >> 24
        h &= (~g) & 0xFFFFFFFF
    return h if h else 1


def _sec(tag: int, data: bytes) -> bytes:
    return struct.pack("B", tag) + struct.pack(">I", len(data)) + data


def _field(tag: int, data: bytes) -> bytes:
    return struct.pack("B", tag) + struct.pack(">I", len(data)) + data


def compile_ts(ts_path: Path, qm_path: Path) -> int:
    """Compile a .ts XML file into a binary .qm file.  Returns message count."""
    tree = ET.parse(ts_path)
    root = tree.getroot()

    language: str = root.get("language", "")
    messages_data = b""
    # Each entry: (lookup_hash, msg_offset)
    # Qt lookup hash = elfHash(source) ^ elfHash(context)
    # (comment/disambiguation is empty so contributes 0)
    hash_entries: list[tuple[int, int]] = []

    for ctx in root.findall("context"):
        name_el = ctx.find("name")
        ctx_name = (name_el.text or "") if name_el is not None else ""

        for msg in ctx.findall("message"):
            src_el = msg.find("source")
            trans_el = msg.find("translation")
            if src_el is None:
                continue

            source: str = src_el.text or ""
            translation: str = ""
            if trans_el is not None:
                t = trans_el.text or ""
                # Skip messages explicitly marked unfinished with no text.
                if trans_el.get("type") == "unfinished" and not t:
                    continue
                translation = t or source
            else:
                translation = source

            offset = len(messages_data)
            # Qt hash table uses elfHash(sourceText) only for index;
            # context discrimination happens inside the message via tag comparison.
            lookup_hash = _elf_hash(source)
            hash_entries.append((lookup_hash, offset))

            # Build message record — Qt message field order matters:
            # 0x03 translation, 0x08 empty comment, 0x06 source, 0x07 context, 0x01 end
            rec = _field(_TAG_TRANSLATION, translation.encode("utf-16-be"))
            rec += _field(_TAG_COMMENT, b"")
            rec += _field(_TAG_SOURCETEXT, source.encode("utf-8"))
            if ctx_name:
                rec += _field(_TAG_CONTEXT, ctx_name.encode("utf-8"))
            rec += struct.pack("B", _TAG_END)
            messages_data += rec

    # Qt requires the hash table sorted by hash value for binary search
    hash_entries.sort(key=lambda e: e[0])
    hashes_data = b"".join(struct.pack(">II", h, off) for h, off in hash_entries)

    output = _QM_MAGIC
    if language:
        output += _sec(_SEC_LANGUAGE, language.encode("utf-8"))
    output += _sec(_SEC_HASHES, hashes_data)
    output += _sec(_SEC_MESSAGES, messages_data)

    qm_path.write_bytes(output)
    return len(hash_entries)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

_TRANSLATIONS_DIR = Path(__file__).parent.parent / "resources" / "translations"

# Map locale suffix → TRANSLATIONS key
_LOCALE_MAP = {
    "zh_CN": "zh_CN",
    "ja_JP": "ja_JP",
    "ko_KR": "ko_KR",
    "ru_RU": "ru_RU",
    "km_KH": "km_KH",
}


def main() -> None:
    print("=== VOK translation compiler ===\n")

    # 1. Write translated .ts files
    print("Step 1 — Writing .ts files …")
    for ts_file in sorted(_TRANSLATIONS_DIR.glob("vok_*.ts")):
        # Extract locale from filename, e.g. vok_zh_CN.ts -> zh_CN
        parts = ts_file.stem.split("_", 1)
        if len(parts) < 2:
            continue
        locale = parts[1]
        lookup = TRANSLATIONS.get(locale, {})
        write_ts(ts_file, locale, lookup)

    # 2. Compile .ts → .qm
    print("\nStep 2 — Compiling .ts → .qm …")
    total = 0
    for ts_file in sorted(_TRANSLATIONS_DIR.glob("vok_*.ts")):
        qm_file = ts_file.with_suffix(".qm")
        count = compile_ts(ts_file, qm_file)
        total += count
        print(f"  {ts_file.name} → {qm_file.name}  ({count} messages)")

    print(f"\nDone — {total} messages compiled across {len(list(_TRANSLATIONS_DIR.glob('*.qm')))} files.")


if __name__ == "__main__":
    main()
