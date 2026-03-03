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
    },
    "th_TH": {
        "Included Tools & Features": "เครื่องมือและคุณสมบัติ",
        "Multi-Source Support": "รองรับหลายแหล่ง",
        "1000+ sites: YouTube, TikTok, Pinterest & more.": (
            "1000+ เว็บไซต์: YouTube, TikTok, Pinterest และอื่นๆ"
        ),
        "Quality Selector": "เลือกคุณภาพ",
        "Pick 4K, 1080p, 720p or audio-only (MP3/M4A).": (
            "เลือก 4K, 1080p, 720p หรือเฉพาะเสียง (MP3/M4A)"
        ),
        "Batch Download": "ดาวน์โหลดหลายรายการ",
        "Paste multiple URLs or an entire playlist.": (
            "วางหลาย URL หรือเพลย์ลิสต์ทั้งหมด"
        ),
        "Smart File Naming": "ตั้งชื่อไฟล์อัตโนมัติ",
        "Files saved by title/channel automatically.": (
            "บันทึกไฟล์ตามชื่อ/ช่องอัตโนมัติ"
        ),
        "How to use": "วิธีใช้",
        "1. Copy a video URL from your browser.": (
            "1. คัดลอก URL วิดีโอจากเบราว์เซอร์ของคุณ"
        ),
        "2. Go to the Download tab, paste the URL, and choose your format.": (
            "2. ไปที่แท็บดาวน์โหลด วาง URL และเลือกรูปแบบ"
        ),
        "3. Click Download — track progress in the Logs tab.": (
            "3. คลิกดาวน์โหลด — ติดตามความคืบหน้าในแท็บบันทึก"
        ),
        "Dashboard": "แดชบอร์ด",
        "VOK Downloader": "VOK ดาวน์โหลดเดอร์",
        "View on GitHub": "ดูบน GitHub",
        "Watch tutorial on YouTube": "ดูบทช่วยสอนบน YouTube",
        (
            "Download from YouTube, TikTok, Pinterest & 1000+ platforms"
            " \u2014 fast, offline, free."
        ): (
            "ดาวน์โหลดจาก YouTube, TikTok, Pinterest และ 1000+ แพลตฟอร์ม"
            " — รวดเร็ว, ออฟไลน์, ฟรี"
        ),
        "Download": "ดาวน์โหลด",
        "Paste a URL and start": "วาง URL และเริ่มต้น",
        "Logs": "บันทึก",
        "View downloaded files": "ดูไฟล์ที่ดาวน์โหลด",
        "Open Folder": "เปิดโฟลเดอร์",
        "Browse your downloads": "เรียกดูการดาวน์โหลด",
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
    "th_TH": "th_TH",
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
