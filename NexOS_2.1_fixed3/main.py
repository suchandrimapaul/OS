import sys, os, json, math, shutil, zipfile, random
from pathlib import Path
from datetime import datetime

from PySide6.QtCore import Qt, QTimer, QTime, QDate, QSize, QUrl, Signal, QPoint, QMimeData
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QPen, QImage, QTransform, QFont, QDrag, QAction
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QFrame, QLabel, QPushButton, QToolButton,
    QVBoxLayout, QHBoxLayout, QGridLayout, QListWidget, QListWidgetItem, QTreeWidget,
    QTreeWidgetItem, QFileDialog, QMessageBox, QLineEdit, QTextEdit, QPlainTextEdit,
    QComboBox, QSpinBox, QCheckBox, QSlider, QTabWidget, QCalendarWidget, QTimeEdit,
    QProgressBar, QSplitter, QInputDialog, QColorDialog, QDialog, QDialogButtonBox,
    QFormLayout, QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QMenu, QScrollArea, QSizePolicy
)

BASE = Path(__file__).resolve().parent
STORAGE = BASE / "Storage"
USERDATA = BASE / "userdata.json"
SETTINGS = BASE / "settings.json"
BACKUPS = BASE / "backups"
ASSETS = BASE / "assets"
for d in (STORAGE, BACKUPS, ASSETS):
    d.mkdir(exist_ok=True)
LIMIT = 20 * 1024 * 1024
APP_VERSION = "NexOS 2.1"

DEFAULT_SETTINGS = {
    "username": "NexUser",
    "theme": "Midnight",
    "accent": "#6ea8ff",
    "background": "",          # empty = use theme bg
    "bg_animation": "Aurora",
    "bg_image": "",            # relative path inside Storage
    "language": "English",
    "airplane": False,
    "volume": 75,
    "notifications": True,
    "animations": True,
}

# Migrate old keys if present
def load_json(path, default):
    try:
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            out = dict(default)
            out.update(data)
            # migrate wallpaper_mode → bg_animation
            if "wallpaper_mode" in data and "bg_animation" not in data:
                out["bg_animation"] = data["wallpaper_mode"]
            return out
    except Exception:
        pass
    return dict(default) if isinstance(default, dict) else default

def save_json(path, data):
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

settings = load_json(SETTINGS, DEFAULT_SETTINGS)
messages = load_json(USERDATA, {"conversations": {}, "calendar": {}})
messages.setdefault("conversations", {})
messages.setdefault("calendar", {})

def save_data():
    save_json(USERDATA, messages)

def storage_size():
    total = 0
    for p in STORAGE.rglob("*"):
        if p.is_file():
            try:
                total += p.stat().st_size
            except OSError:
                pass
    return total

def fmt_size(n):
    if n < 1024:
        return f"{n} B"
    if n < 1024 ** 2:
        return f"{n / 1024:.1f} KB"
    return f"{n / 1024 ** 2:.1f} MB"

def inside_storage(p):
    try:
        Path(p).resolve().relative_to(STORAGE.resolve())
        return True
    except ValueError:
        return False

def unique_name(parent, name):
    name = Path(name).name
    p = parent / name
    if not p.exists():
        return p
    stem, suf = p.stem, p.suffix
    for i in range(2, 10000):
        q = parent / f"{stem} ({i}){suf}"
        if not q.exists():
            return q
    raise RuntimeError("Could not create a unique name")

def safe_storage(rel=""):
    p = (STORAGE / rel).resolve()
    if not inside_storage(p) and p != STORAGE.resolve():
        raise ValueError("Invalid Storage location")
    return p

THEMES = {
    "Nex Dark": ("#0a101a", "#101a29", "#eaf2ff", "#4aa3ff"),
    "Midnight": ("#07101d", "#0d192a", "#edf5ff", "#77aaff"),
    "Ocean": ("#06131a", "#0c222d", "#e8fbff", "#55d6ff"),
    "Forest": ("#07150f", "#10271c", "#edfff4", "#61e6a2"),
    "Violet": ("#10091a", "#20102f", "#f7edff", "#c596ff"),
    "Sunset": ("#1b0e09", "#302019", "#fff3eb", "#ff9a68"),
    "Ruby": ("#18090e", "#30111c", "#ffeef2", "#ff6f91"),
    "Slate": ("#101216", "#1d222a", "#f2f5f8", "#aab6c5"),
    "Paper": ("#e9edf3", "#ffffff", "#17202b", "#3367d6"),
    "Solar": ("#171307", "#2a210b", "#fffbe8", "#ffd65a"),
    "Mono": ("#090909", "#171717", "#f3f3f3", "#bdbdbd"),
}

ANIMS = [
    "None", "Aurora", "Stars", "Bubbles", "Matrix", "Grid", "Rain",
    "Orbit", "Particles", "Waves", "Pulse", "Snow", "Fireflies",
    "Spectrum", "Comets"
]

EXT_ICONS = {
    ".txt": "txt.svg", ".md": "txt.svg", ".log": "txt.svg",
    ".py": "code.svg", ".js": "code.svg", ".html": "code.svg", ".css": "code.svg",
    ".json": "code.svg", ".xml": "code.svg", ".cpp": "code.svg", ".c": "code.svg",
    ".java": "code.svg", ".ts": "code.svg",
    ".png": "image.svg", ".jpg": "image.svg", ".jpeg": "image.svg", ".webp": "image.svg",
    ".bmp": "image.svg", ".gif": "image.svg",
    ".mp3": "audio.svg", ".wav": "audio.svg", ".m4a": "audio.svg", ".ogg": "audio.svg",
    ".flac": "audio.svg",
    ".mp4": "video.svg", ".mkv": "video.svg", ".webm": "video.svg", ".avi": "video.svg",
    ".mov": "video.svg", ".wmv": "video.svg",
    ".pdf": "file.svg", ".zip": "file.svg",
}

APP_ICONS = {
    "Terminal": "terminal.svg",
    "File Explorer": "explorer.svg",
    "Calculator": "calc.svg",
    "Calendar": "calendar.svg",
    "Messages": "messages.svg",
    "Clock": "clock.svg",
    "Notepad": "notepad.svg",
    "Code Editor": "code.svg",
    "Paint": "paint.svg",
    "Photos": "photos.svg",
    "Camera": "camera.svg",
    "Voice Recorder": "voice.svg",
    "Settings": "settings.svg",
    "Get Help": "help.svg",
    "Media Player": "media.svg",
    "Browser": "browser.svg",
    "YouTube": "youtube.svg",
    "Mail": "mail.svg",
    "Poki Games": "poki.svg",
    "Store": "store.svg",
    "Tetris": "tetris.svg",
    "Tic Tac Toe": "tictactoe.svg",
    "Pong": "pong.svg",
}

MEDIA_DIR = STORAGE / "Media"
MEDIA_DIR.mkdir(exist_ok=True)

def icon_for(path):
    p = Path(path)
    if p.is_dir():
        name = "folder.svg"
    else:
        name = EXT_ICONS.get(p.suffix.lower(), "file.svg")
    return QIcon(str(ASSETS / name))

def app_icon(name, size=34):
    fname = APP_ICONS.get(name, "nexos.svg")
    path = ASSETS / fname
    if not path.exists():
        path = ASSETS / "nexos.svg"
    return QIcon(str(path)).pixmap(size, size)

# ───────────────────────── Storage Picker (File Explorer style) ─────────────────────────
class StoragePicker(QDialog):
    """
    Storage-only file/folder picker used everywhere instead of system QFileDialog.
    mode: 'file' | 'folder' | 'save'
    filters: list of extensions e.g. ['.py', '.txt'] or None for all
    """
    def __init__(self, parent=None, title="Choose from Storage", mode="file",
                 filters=None, start_name="", start_dir=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(720, 480)
        self.mode = mode
        self.filters = [f.lower() if f.startswith(".") else f".{f.lower()}" for f in (filters or [])]
        self.selected = None
        self.current = Path(start_dir) if start_dir and inside_storage(start_dir) else STORAGE

        v = QVBoxLayout(self)
        # toolbar
        top = QHBoxLayout()
        for txt, tip, fn in [
            ("↑", "Up", self.go_up),
            ("↻", "Refresh", self.refresh),
        ]:
            b = QToolButton()
            b.setText(txt)
            b.setToolTip(tip)
            b.setFixedSize(40, 32)
            b.clicked.connect(fn)
            top.addWidget(b)
        self.loc = QLabel("Storage")
        top.addWidget(self.loc, 1)
        v.addLayout(top)

        split = QSplitter()
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Folders"])
        self.tree.setMinimumWidth(160)
        self.tree.itemClicked.connect(lambda it, c: self.navigate(Path(it.data(0, Qt.UserRole))))
        self.list = QListWidget()
        self.list.setViewMode(QListWidget.IconMode)
        self.list.setIconSize(QSize(48, 48))
        self.list.setResizeMode(QListWidget.Adjust)
        self.list.setSpacing(10)
        self.list.setGridSize(QSize(90, 90))
        self.list.itemDoubleClicked.connect(self.on_double)
        self.list.itemClicked.connect(self.on_click)
        split.addWidget(self.tree)
        split.addWidget(self.list)
        split.setSizes([180, 520])
        v.addWidget(split, 1)

        # name row for save mode
        self.name_row = QHBoxLayout()
        self.name_edit = QLineEdit(start_name or "")
        self.name_edit.setPlaceholderText("File name…")
        if mode == "save":
            self.name_row.addWidget(QLabel("Name:"))
            self.name_row.addWidget(self.name_edit, 1)
            v.addLayout(self.name_row)
        else:
            self.name_edit.hide()

        # filter hint
        if self.filters:
            hint = QLabel("Showing: " + ", ".join(self.filters))
            hint.setStyleSheet("color:#94a7bd;font-size:12px;")
            v.addWidget(hint)

        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(self.accept_pick)
        bb.rejected.connect(self.reject)
        v.addWidget(bb)
        self.refresh()

    def rel(self, p):
        r = p.relative_to(STORAGE)
        return "" if str(r) == "." else r.as_posix()

    def refresh(self):
        self.loc.setText("Storage" + (" / " + self.rel(self.current) if self.current != STORAGE else ""))
        self.list.clear()
        self.tree.clear()
        root = QTreeWidgetItem(["Storage"])
        root.setData(0, Qt.UserRole, str(STORAGE))
        root.setIcon(0, QIcon(str(ASSETS / "folder.svg")))
        self.tree.addTopLevelItem(root)
        self.fill_tree(root, STORAGE)
        root.setExpanded(True)
        for p in sorted(self.current.iterdir(), key=lambda x: (x.is_file(), x.name.lower())):
            if p.is_file() and self.filters and p.suffix.lower() not in self.filters:
                continue
            if self.mode == "folder" and p.is_file():
                continue
            it = QListWidgetItem(icon_for(p), p.name)
            it.setData(Qt.UserRole, str(p))
            it.setSizeHint(QSize(84, 84))
            self.list.addItem(it)

    def fill_tree(self, item, p):
        for x in sorted(p.iterdir(), key=lambda z: z.name.lower()):
            if x.is_dir():
                i = QTreeWidgetItem([x.name])
                i.setData(0, Qt.UserRole, str(x))
                i.setIcon(0, QIcon(str(ASSETS / "folder.svg")))
                item.addChild(i)
                self.fill_tree(i, x)

    def navigate(self, p):
        p = p.resolve()
        if inside_storage(p) and p.is_dir():
            self.current = p
            self.refresh()

    def go_up(self):
        if self.current != STORAGE:
            self.navigate(self.current.parent)

    def on_click(self, it):
        p = Path(it.data(Qt.UserRole))
        if self.mode == "save" and p.is_file():
            self.name_edit.setText(p.name)
        self.selected = p

    def on_double(self, it):
        p = Path(it.data(Qt.UserRole))
        if p.is_dir():
            self.navigate(p)
        else:
            self.selected = p
            if self.mode != "folder":
                self.accept()

    def accept_pick(self):
        if self.mode == "save":
            name = self.name_edit.text().strip()
            if not name:
                QMessageBox.warning(self, "Name required", "Enter a file name.")
                return
            self.selected = self.current / Path(name).name
            self.accept()
            return
        if self.mode == "folder":
            # current folder or selected folder item
            if self.selected and Path(self.selected).is_dir():
                self.accept()
            else:
                self.selected = self.current
                self.accept()
            return
        # file mode
        if self.selected and Path(self.selected).is_file():
            self.accept()
        else:
            QMessageBox.information(self, "Select a file", "Double-click or select a file, then OK.")

    @staticmethod
    def pick_file(parent, title="Open from Storage", filters=None):
        dlg = StoragePicker(parent, title=title, mode="file", filters=filters)
        if dlg.exec() == QDialog.Accepted and dlg.selected:
            return Path(dlg.selected)
        return None

    @staticmethod
    def pick_folder(parent, title="Choose folder in Storage"):
        dlg = StoragePicker(parent, title=title, mode="folder")
        if dlg.exec() == QDialog.Accepted and dlg.selected:
            return Path(dlg.selected)
        return None

    @staticmethod
    def pick_save(parent, title="Save in Storage", start_name="", filters=None):
        dlg = StoragePicker(parent, title=title, mode="save", filters=filters, start_name=start_name)
        if dlg.exec() == QDialog.Accepted and dlg.selected:
            return Path(dlg.selected)
        return None

class Logo(QLabel):
    def __init__(self, size=34, app_name=None):
        super().__init__()
        self.setFixedSize(size, size)
        if app_name:
            self.setPixmap(app_icon(app_name, size))
        else:
            self.setPixmap(QIcon(str(ASSETS / "nexos.svg")).pixmap(size, size))

class Background(QWidget):
    def __init__(self):
        super().__init__()
        self.t = 0
        self.pts = [(random.random(), random.random(), random.uniform(.2, 1.2)) for _ in range(100)]
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(45)

    def tick(self):
        self.t += 1
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        theme = THEMES.get(settings.get("theme"), THEMES["Midnight"])
        bg_color = settings.get("background") or theme[0]
        p.fillRect(self.rect(), QColor(bg_color))
        w, h = self.width(), self.height()
        accent = settings.get("accent", theme[3])

        # optional wallpaper image from Storage
        img_rel = settings.get("bg_image", "")
        if img_rel:
            try:
                f = safe_storage(img_rel)
                if f.exists() and f.is_file():
                    p.setOpacity(0.22)
                    pix = QPixmap(str(f)).scaled(self.size(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
                    p.drawPixmap(self.rect(), pix)
                    p.setOpacity(1.0)
            except Exception:
                pass

        if not settings.get("animations", True):
            return
        a = settings.get("bg_animation", "Aurora")
        if a == "None":
            return

        if a == "Aurora":
            for i, c in enumerate(["#0d4c68", "#37206b", "#135e46"]):
                x = int((math.sin(self.t / 80 + i) * .35 + .5) * w)
                y = int((math.cos(self.t / 100 + i) * .35 + .5) * h)
                col = QColor(c)
                col.setAlpha(40)
                p.setBrush(col)
                p.setPen(Qt.NoPen)
                p.drawEllipse(x - 260, y - 260, 520, 520)
        elif a in ("Stars", "Snow", "Fireflies"):
            color = QColor("#b8ff77" if a == "Fireflies" else "#ffffff")
            p.setPen(QPen(color, 2))
            for x, y, s in self.pts:
                yy = (y * h + self.t * s) if a == "Snow" else y * h
                glow = abs(math.sin(self.t / 18 * s)) if a == "Fireflies" else 1
                color.setAlpha(int(40 + 110 * glow))
                p.setPen(QPen(color, 2))
                p.drawPoint(int(x * w), int(yy % h))
        elif a == "Bubbles":
            p.setPen(Qt.NoPen)
            for i, (x, y, s) in enumerate(self.pts[:40]):
                r = int(8 + 18 * s)
                xx = int((x * w + math.sin(self.t / 40 + i) * 20) % w)
                yy = int((h - (y * h + self.t * s * 1.5) % (h + 40)))
                col = QColor(accent)
                col.setAlpha(50)
                p.setBrush(col)
                p.drawEllipse(xx, yy, r, r)
        elif a in ("Grid", "Rain", "Matrix"):
            col = QColor("#42ff8a" if a == "Matrix" else accent)
            col.setAlpha(90)
            p.setPen(QPen(col, 1))
            off = (self.t // 2) % 40
            if a == "Grid":
                for x in range(-40 + off, w, 40):
                    p.drawLine(x, 0, x, h)
                for y in range(-40 + off, h, 40):
                    p.drawLine(0, y, w, y)
            else:
                for x, y, s in self.pts:
                    yy = (y * h + self.t * s * 4) % h
                    p.drawLine(int(x * w), int(yy), int(x * w), int(yy + 20 * s))
        elif a == "Orbit":
            cx, cy = w / 2, h / 2
            col = QColor(accent)
            col.setAlpha(120)
            p.setPen(QPen(col, 1))
            p.setBrush(QColor(accent))
            for r in (100, 180, 260):
                p.setBrush(Qt.NoBrush)
                p.drawEllipse(int(cx - r), int(cy - r), 2 * r, 2 * r)
                q = self.t / 30 + r
                x = cx + math.cos(q) * r
                y = cy + math.sin(q) * r
                p.setBrush(QColor(accent))
                p.drawEllipse(int(x - 5), int(y - 5), 10, 10)
        elif a == "Pulse":
            r = 80 + int(abs(math.sin(self.t / 25)) * 220)
            col = QColor(accent)
            col.setAlpha(90)
            p.setPen(QPen(col, 2))
            p.setBrush(Qt.NoBrush)
            p.drawEllipse(w // 2 - r, h // 2 - r, 2 * r, 2 * r)
        elif a == "Waves":
            col = QColor(accent)
            col.setAlpha(70)
            p.setPen(QPen(col, 2))
            for k in range(4):
                last = None
                for x in range(0, w, 12):
                    y = h * .45 + k * 35 + math.sin(x / 70 + self.t / 35 + k) * 25
                    if last:
                        p.drawLine(last[0], last[1], x, int(y))
                    last = (x, int(y))
        elif a == "Spectrum":
            col = QColor(accent)
            col.setAlpha(40)
            p.setBrush(col)
            p.setPen(Qt.NoPen)
            for x in range(0, w, 10):
                p.drawRect(x, int(h - (20 + abs(math.sin(x / 55 + self.t / 15)) * 100)), 8, 120)
        elif a == "Comets":
            col = QColor(accent)
            col.setAlpha(140)
            p.setPen(QPen(col, 2))
            for x, y, s in self.pts[:30]:
                xx = (x * w + self.t * s * 3) % w
                yy = (y * h + self.t * s) % h
                p.drawLine(int(xx), int(yy), int(xx - 25 * s), int(yy - 10 * s))
        elif a == "Particles":
            col = QColor(accent)
            col.setAlpha(160)
            p.setPen(QPen(col, 2))
            q = []
            for i, (x, y, s) in enumerate(self.pts):
                xx = (x * w + math.sin(self.t / 50 + i) * 30) % w
                yy = (y * h + math.cos(self.t / 60 + i) * 30) % h
                q.append((xx, yy))
                p.drawPoint(int(xx), int(yy))
            col.setAlpha(30)
            p.setPen(QPen(col, 1))
            for i in range(0, len(q), 5):
                for j in range(i + 1, min(i + 4, len(q))):
                    p.drawLine(int(q[i][0]), int(q[i][1]), int(q[j][0]), int(q[j][1]))

class AppWindow(QFrame):
    def __init__(self, shell, title):
        super().__init__()
        self.shell = shell
        self.title = title
        self.setObjectName("AppWindow")
        self.v = QVBoxLayout(self)
        self.v.setContentsMargins(0, 0, 0, 0)
        self.v.setSpacing(0)
        bar = QFrame()
        bar.setObjectName("AppBar")
        hb = QHBoxLayout(bar)
        hb.setContentsMargins(14, 9, 10, 9)
        hb.addWidget(Logo(28, title))
        t = QLabel(title)
        t.setObjectName("AppTitle")
        hb.addWidget(t)
        hb.addStretch()
        mini = QToolButton()
        mini.setText("—")
        mini.setToolTip("Minimize")
        mini.clicked.connect(self.hide)
        close = QToolButton()
        close.setText("×")
        close.setToolTip("Close")
        close.clicked.connect(self.close)
        hb.addWidget(mini)
        hb.addWidget(close)
        self.v.addWidget(bar)
        self.content = QWidget()
        self.cv = QVBoxLayout(self.content)
        self.cv.setContentsMargins(16, 14, 16, 14)
        self.cv.setSpacing(12)
        self.v.addWidget(self.content, 1)

    def add(self, w):
        self.cv.addWidget(w)

    def add_layout(self, l):
        w = QWidget()
        w.setLayout(l)
        self.cv.addWidget(w)

    def closeEvent(self, e):
        name = self.title
        if name in self.shell.apps:
            del self.shell.apps[name]
        e.accept()

# ───────────────────────── Terminal ─────────────────────────
class Terminal(AppWindow):
    def __init__(self, shell):
        super().__init__(shell, "Terminal")
        self.cwd = STORAGE
        self.output = QPlainTextEdit()
        self.output.setReadOnly(True)
        self.output.setObjectName("terminalOut")
        self.input = QLineEdit()
        self.input.setPlaceholderText("Type a command…  (help for commands)")
        self.input.returnPressed.connect(self.run)
        self.add(self.output)
        self.add(self.input)
        self.print("NexOS Terminal\nStorage-only shell • type help")

    def prompt(self):
        rel = self.cwd.relative_to(STORAGE)
        return "NexOS:" + ("/" if not str(rel) else "/" + rel.as_posix() + "/") + "> "

    def print(self, x):
        self.output.appendPlainText(x)

    def run(self):
        raw = self.input.text().strip()
        self.input.clear()
        if not raw:
            return
        self.print(self.prompt() + raw)
        parts = raw.split()
        cmd = parts[0].lower()
        args = parts[1:]
        try:
            cur = self.cwd
            if cmd == "help":
                out = "help ls cd pwd mkdir touch write cat rename rm copy move tree find storage date apps clear whoami"
            elif cmd == "ls":
                out = "\n".join(("[DIR] " if p.is_dir() else "      ") + p.name for p in sorted(cur.iterdir(), key=lambda x: (x.is_file(), x.name.lower()))) or "(empty)"
            elif cmd == "pwd":
                out = "Storage/" + str(cur.relative_to(STORAGE)).replace(".", "")
            elif cmd == "cd":
                target = (cur / (args[0] if args else ".")).resolve()
                target.relative_to(STORAGE)
                self.cwd = target
                out = ""
            elif cmd == "mkdir":
                (cur / Path(args[0]).name).mkdir()
                out = "Created folder."
            elif cmd == "touch":
                (cur / Path(args[0]).name).touch()
                out = "Created file."
            elif cmd == "write":
                if len(args) < 2:
                    out = "Usage: write filename text"
                else:
                    (cur / Path(args[0]).name).write_text(" ".join(args[1:]), encoding="utf-8")
                    out = "Saved."
            elif cmd == "cat":
                out = (cur / Path(args[0]).name).read_text(encoding="utf-8", errors="replace")
            elif cmd == "rename":
                (cur / Path(args[0]).name).rename(unique_name(cur, args[1]))
                out = "Renamed."
            elif cmd == "rm":
                p = cur / Path(args[0]).name
                shutil.rmtree(p) if p.is_dir() else p.unlink()
                out = "Deleted."
            elif cmd in ("copy", "cp"):
                src = cur / Path(args[0]).name
                dst = cur / Path(args[1]).name
                shutil.copytree(src, dst) if src.is_dir() else shutil.copy2(src, dst)
                out = "Copied."
            elif cmd in ("move", "mv"):
                shutil.move(str(cur / Path(args[0]).name), str(cur / Path(args[1]).name))
                out = "Moved."
            elif cmd == "tree":
                out = self.tree(cur)
            elif cmd == "find":
                out = "\n".join(str(p.relative_to(STORAGE)) for p in STORAGE.rglob("*") if args and args[0].lower() in p.name.lower()) or "No matches."
            elif cmd == "storage":
                out = f"{fmt_size(storage_size())} / 20 MB"
            elif cmd == "date":
                out = datetime.now().strftime("%A, %d %B %Y  %I:%M:%S %p")
            elif cmd == "whoami":
                out = settings.get("username", "NexUser")
            elif cmd == "apps":
                out = "Terminal, File Explorer, Calculator, Calendar, Messages, Clock, Notepad, Code Editor, Paint, Photos, Voice Recorder, Settings, Get Help, Media Player, Browser, Store, Tetris, Tic Tac Toe, Pong"
            elif cmd == "clear":
                self.output.clear()
                return
            else:
                out = f"Unknown command: {cmd}"
            if out:
                self.print(out)
        except Exception as e:
            self.print(f"Error: {e}")

    def tree(self, root, prefix=""):
        lines = []
        items = sorted(root.iterdir(), key=lambda x: (x.is_file(), x.name.lower()))
        for i, p in enumerate(items):
            last = i == len(items) - 1
            lines.append(prefix + ("└── " if last else "├── ") + p.name)
            if p.is_dir():
                lines.append(self.tree(p, prefix + ("    " if last else "│   ")))
        return "\n".join(lines)

# ───────────────────────── File Explorer ─────────────────────────
class FileListWidget(QListWidget):
    def __init__(self, explorer):
        super().__init__()
        self.explorer = explorer
        self.setViewMode(QListWidget.IconMode)
        self.setIconSize(QSize(56, 56))
        self.setResizeMode(QListWidget.Adjust)
        self.setMovement(QListWidget.Snap)
        self.setSpacing(14)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDefaultDropAction(Qt.MoveAction)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setGridSize(QSize(100, 100))
        self.setWordWrap(True)
        self.setUniformItemSizes(True)

    def startDrag(self, supportedActions):
        item = self.currentItem()
        if not item:
            return
        mime = QMimeData()
        mime.setText(item.data(Qt.UserRole))
        drag = QDrag(self)
        drag.setMimeData(mime)
        drag.setPixmap(item.icon().pixmap(48, 48))
        drag.exec(Qt.MoveAction)

    def dragEnterEvent(self, event):
        if event.mimeData().hasText():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if event.mimeData().hasText():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        src_path = Path(event.mimeData().text())
        if not src_path.exists() or not inside_storage(src_path):
            event.ignore()
            return
        item = self.itemAt(event.position().toPoint())
        if item:
            dest = Path(item.data(Qt.UserRole))
            if dest.is_dir() and dest != src_path and dest != src_path.parent:
                target = unique_name(dest, src_path.name)
                try:
                    shutil.move(str(src_path), str(target))
                    self.explorer.refresh()
                    event.acceptProposedAction()
                    return
                except Exception as e:
                    QMessageBox.warning(self, "Move failed", str(e))
        if src_path.parent != self.explorer.current:
            target = unique_name(self.explorer.current, src_path.name)
            try:
                shutil.move(str(src_path), str(target))
                self.explorer.refresh()
                event.acceptProposedAction()
                return
            except Exception as e:
                QMessageBox.warning(self, "Move failed", str(e))
        event.ignore()

class FileExplorer(AppWindow):
    pathChanged = Signal(object)

    def __init__(self, shell):
        super().__init__(shell, "File Explorer")
        self.current = STORAGE
        self.back = []
        self.forward = []
        top = QHBoxLayout()
        for txt, tip, fn in [
            ("←", "Back", self.go_back),
            ("→", "Forward", self.go_forward),
            ("↑", "Up", self.go_up),
            ("↻", "Refresh", self.refresh)
        ]:
            b = QToolButton()
            b.setText(txt)
            b.setToolTip(tip)
            b.setFixedSize(42, 36)
            b.clicked.connect(fn)
            top.addWidget(b)
        self.location = QLabel("Storage")
        self.location.setObjectName("location")
        top.addWidget(self.location, 1)
        new = QPushButton("New")
        new.clicked.connect(self.new_menu)
        top.addWidget(new)
        self.add_layout(top)
        split = QSplitter()
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Folders"])
        self.tree.setMinimumWidth(180)
        self.tree.itemClicked.connect(lambda it, c: self.navigate(Path(it.data(0, Qt.UserRole))))
        self.list = FileListWidget(self)
        self.list.itemDoubleClicked.connect(self.open_item)
        self.list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list.customContextMenuRequested.connect(self.context)
        split.addWidget(self.tree)
        split.addWidget(self.list)
        split.setSizes([220, 700])
        self.add(split)
        self.refresh()

    def rel(self, p):
        r = p.relative_to(STORAGE)
        return "" if str(r) == "." else r.as_posix()

    def refresh(self):
        self.location.setText("Storage" + (" / " + self.rel(self.current) if self.current != STORAGE else ""))
        self.list.clear()
        self.tree.clear()
        root = QTreeWidgetItem(["Storage"])
        root.setData(0, Qt.UserRole, str(STORAGE))
        root.setIcon(0, QIcon(str(ASSETS / "folder.svg")))
        self.tree.addTopLevelItem(root)
        self.fill_tree(root, STORAGE)
        root.setExpanded(True)
        for p in sorted(self.current.iterdir(), key=lambda x: (x.is_file(), x.name.lower())):
            it = QListWidgetItem(icon_for(p), p.name)
            it.setData(Qt.UserRole, str(p))
            it.setToolTip(p.name)
            it.setSizeHint(QSize(90, 90))
            self.list.addItem(it)
        self.pathChanged.emit(self.current)

    def fill_tree(self, item, p):
        for x in sorted(p.iterdir(), key=lambda z: z.name.lower()):
            if x.is_dir():
                i = QTreeWidgetItem([x.name])
                i.setData(0, Qt.UserRole, str(x))
                i.setIcon(0, QIcon(str(ASSETS / "folder.svg")))
                item.addChild(i)
                self.fill_tree(i, x)

    def navigate(self, p, record=True):
        p = p.resolve()
        if not inside_storage(p) or not p.is_dir():
            return
        if record and p != self.current:
            self.back.append(self.current)
            self.forward.clear()
        self.current = p
        self.refresh()

    def open_item(self, it):
        p = Path(it.data(Qt.UserRole))
        if p.is_dir():
            self.navigate(p)
        else:
            self.shell.open_file(p)

    def go_back(self):
        if self.back:
            self.forward.append(self.current)
            self.current = self.back.pop()
            self.refresh()

    def go_forward(self):
        if self.forward:
            self.back.append(self.current)
            self.current = self.forward.pop()
            self.refresh()

    def go_up(self):
        if self.current != STORAGE:
            self.navigate(self.current.parent)

    def new_menu(self):
        m = QMenu(self)
        a = m.addAction("New folder")
        b = m.addAction("New text file")
        c = m.addAction("New code file")
        x = m.exec(self.mapToGlobal(self.rect().center()))
        if x == a:
            self.make_folder()
        elif x == b:
            self.make_file("New Text.txt")
        elif x == c:
            self.make_file("main.py")

    def make_folder(self):
        n = QInputDialog.getText(self, "New folder", "Folder name:")[0].strip()
        if n:
            try:
                (self.current / Path(n).name).mkdir()
                self.refresh()
            except Exception as e:
                QMessageBox.warning(self, "Cannot create", str(e))

    def make_file(self, default):
        n = QInputDialog.getText(self, "New file", "File name:", text=default)[0].strip()
        if n:
            try:
                unique_name(self.current, n).write_text("", encoding="utf-8")
                self.refresh()
            except Exception as e:
                QMessageBox.warning(self, "Cannot create", str(e))

    def context(self, pos):
        it = self.list.itemAt(pos)
        if not it:
            return
        p = Path(it.data(Qt.UserRole))
        m = QMenu(self)
        o = m.addAction("Open")
        r = m.addAction("Rename")
        mv = m.addAction("Move to…")
        cp = m.addAction("Copy")
        d = m.addAction("Delete")
        x = m.exec(self.list.mapToGlobal(pos))
        try:
            if x == o:
                self.open_item(it)
            elif x == r:
                n = QInputDialog.getText(self, "Rename", "New name:", text=p.name)[0].strip()
                if n and n != p.name:
                    p.rename(unique_name(p.parent, n))
                    self.refresh()
            elif x == mv:
                self.move_item(p)
            elif x == cp:
                target = unique_name(p.parent, p.stem + " Copy" + p.suffix)
                shutil.copytree(p, target) if p.is_dir() else shutil.copy2(p, target)
                self.refresh()
            elif x == d and QMessageBox.question(self, "Delete", f"Delete {p.name}?") == QMessageBox.Yes:
                shutil.rmtree(p) if p.is_dir() else p.unlink()
                self.refresh()
        except Exception as e:
            QMessageBox.warning(self, "File operation", str(e))

    def move_item(self, p):
        dest = StoragePicker.pick_folder(self, "Move to folder")
        if not dest:
            return
        if dest == p.parent:
            return
        if dest == p or (p.is_dir() and str(dest).startswith(str(p) + os.sep)):
            QMessageBox.warning(self, "Move", "Cannot move a folder into itself.")
            return
        target = dest / p.name
        if target.exists():
            target = unique_name(dest, p.name)
        try:
            shutil.move(str(p), str(target))
            self.refresh()
        except Exception as e:
            QMessageBox.warning(self, "Move failed", str(e))

# ───────────────────────── Calculator ─────────────────────────
class Calculator(AppWindow):
    def __init__(self, shell):
        super().__init__(shell, "Calculator")
        tabs = QTabWidget()
        tabs.addTab(self.basic(), "Basic")
        tabs.addTab(self.scientific(), "Scientific")
        tabs.addTab(self.programmer(), "Programmer")
        self.add(tabs)

    def basic(self):
        w = QWidget()
        v = QVBoxLayout(w)
        self.display = QLineEdit()
        self.display.setAlignment(Qt.AlignRight)
        self.display.setObjectName("calcDisplay")
        v.addWidget(self.display)
        g = QGridLayout()
        keys = ["7", "8", "9", "÷", "4", "5", "6", "×", "1", "2", "3", "−", "0", ".", "+", "=", "C", "(", ")", "⌫"]
        for i, k in enumerate(keys):
            b = QPushButton(k)
            b.setMinimumHeight(52)
            b.clicked.connect(lambda _, x=k: self.calc_key(x))
            g.addWidget(b, i // 4, i % 4)
        v.addLayout(g)
        return w

    def calc_key(self, k):
        if k == "C":
            self.display.clear()
        elif k == "⌫":
            self.display.backspace()
        elif k == "=":
            try:
                expr = self.display.text().replace("÷", "/").replace("×", "*").replace("−", "-")
                self.display.setText(str(eval(expr, {"__builtins__": {}}, {
                    "sqrt": math.sqrt, "sin": math.sin, "cos": math.cos,
                    "tan": math.tan, "log": math.log, "pi": math.pi, "e": math.e
                })))
            except Exception:
                self.display.setText("Error")
        else:
            self.display.insert(k)

    def scientific(self):
        w = QWidget()
        v = QVBoxLayout(w)
        d = QLineEdit()
        d.setObjectName("calcDisplay")
        v.addWidget(d)
        g = QGridLayout()
        for i, k in enumerate(["sin", "cos", "tan", "sqrt", "log", "pi", "e", "x²", "%", "="]):
            b = QPushButton(k)
            b.setMinimumHeight(48)
            b.clicked.connect(lambda _, x=k: self.sci(d, x))
            g.addWidget(b, i // 4, i % 4)
        v.addLayout(g)
        return w

    def sci(self, d, k):
        try:
            if k == "=":
                d.setText(str(eval(d.text(), {"__builtins__": {}}, {
                    "sin": math.sin, "cos": math.cos, "tan": math.tan,
                    "sqrt": math.sqrt, "log": math.log, "pi": math.pi, "e": math.e
                })))
            elif k == "x²":
                d.setText(str(float(d.text()) ** 2))
            elif k == "%":
                d.setText(str(float(d.text()) / 100))
            elif k in ("pi", "e"):
                d.insert(str(getattr(math, k)))
            else:
                d.setText(f"{k}({d.text()})")
        except Exception:
            d.setText("Error")

    def programmer(self):
        w = QWidget()
        f = QFormLayout(w)
        d = QLineEdit()
        base = QComboBox()
        base.addItems(["2", "8", "10", "16"])
        out = QLineEdit()
        out.setReadOnly(True)
        b = QPushButton("Convert")

        def conv():
            try:
                out.setText(format(int(d.text(), 10), int(base.currentText())))
            except Exception:
                out.setText("Invalid number")
        b.clicked.connect(conv)
        f.addRow("Decimal", d)
        f.addRow("Output base", base)
        f.addRow(b)
        f.addRow("Result", out)
        return w

# ───────────────────────── Calendar ─────────────────────────
class CalendarApp(AppWindow):
    def __init__(self, shell):
        super().__init__(shell, "Calendar")
        split = QSplitter()
        left = QCalendarWidget()
        left.setMinimumWidth(320)
        right = QWidget()
        rv = QVBoxLayout(right)
        rv.setContentsMargins(8, 4, 4, 4)
        self.heading = QLabel()
        self.heading.setObjectName("sectionTitle")
        self.notes = QTextEdit()
        self.notes.setPlaceholderText("Notes for this date…")
        self.notes.setMinimumHeight(200)
        rv.addWidget(self.heading)
        rv.addWidget(self.notes, 1)
        split.addWidget(left)
        split.addWidget(right)
        split.setSizes([380, 480])
        self.add(split)
        self.cal = left
        self.cal.selectionChanged.connect(self.load)
        self.notes.textChanged.connect(self.save)
        self.load()

    def key(self):
        return self.cal.selectedDate().toString("yyyy-MM-dd")

    def load(self):
        self.heading.setText(self.cal.selectedDate().toString("dddd, dd MMMM yyyy"))
        self.notes.blockSignals(True)
        self.notes.setPlainText(messages["calendar"].get(self.key(), ""))
        self.notes.blockSignals(False)

    def save(self):
        messages["calendar"][self.key()] = self.notes.toPlainText()
        save_data()

# ───────────────────────── Messages ─────────────────────────
class MessagesApp(AppWindow):
    def __init__(self, shell):
        super().__init__(shell, "Messages")
        self.current = None
        split = QSplitter()
        left = QWidget()
        lv = QVBoxLayout(left)
        lv.setContentsMargins(0, 0, 0, 0)
        top = QHBoxLayout()
        title = QLabel("Conversations")
        title.setObjectName("sectionTitle")
        new = QPushButton("New")
        new.setFixedWidth(70)
        new.clicked.connect(self.new_person)
        top.addWidget(title)
        top.addStretch()
        top.addWidget(new)
        lv.addLayout(top)
        self.people = QListWidget()
        self.people.setMinimumWidth(180)
        lv.addWidget(self.people)
        right = QWidget()
        rv = QVBoxLayout(right)
        rv.setContentsMargins(8, 0, 0, 0)
        self.chat = QListWidget()
        self.chat.setMinimumHeight(280)
        rv.addWidget(self.chat, 1)
        row = QHBoxLayout()
        self.input = QLineEdit()
        self.input.setPlaceholderText("Write a message…")
        send = QPushButton("Send")
        send.setFixedWidth(80)
        send.clicked.connect(self.send)
        self.input.returnPressed.connect(self.send)
        row.addWidget(self.input, 1)
        row.addWidget(send)
        rv.addLayout(row)
        split.addWidget(left)
        split.addWidget(right)
        split.setSizes([220, 680])
        self.add(split)
        self.people.itemClicked.connect(self.load)
        self.people.addItems(sorted(messages["conversations"].keys()))
        if self.people.count():
            self.people.setCurrentRow(0)
            self.load(self.people.currentItem())
        else:
            self.chat.addItem("Create a conversation to start messaging.")

    def new_person(self):
        n = QInputDialog.getText(self, "New conversation", "Name:")[0].strip()
        if n and n not in messages["conversations"]:
            messages["conversations"][n] = []
            save_data()
            self.people.addItem(n)
            self.people.setCurrentRow(self.people.count() - 1)
            self.load(self.people.currentItem())

    def load(self, it):
        if not it:
            return
        self.current = it.text()
        self.chat.clear()
        for m in messages["conversations"].get(self.current, []):
            self.chat.addItem(("You  ·  " if m["from"] == "me" else self.current + "  ·  ") + m["text"])

    def send(self):
        text = self.input.text().strip()
        if not self.current or not text:
            return
        messages["conversations"].setdefault(self.current, []).append({"from": "me", "text": text})
        save_data()
        self.input.clear()
        self.load(self.people.currentItem())

# ───────────────────────── Clock ─────────────────────────
class ClockApp(AppWindow):
    def __init__(self, shell):
        super().__init__(shell, "Clock")
        tabs = QTabWidget()
        clock = QWidget()
        v = QVBoxLayout(clock)
        self.big = QLabel()
        self.big.setObjectName("bigClock")
        self.big.setAlignment(Qt.AlignCenter)
        self.date = QLabel()
        self.date.setAlignment(Qt.AlignCenter)
        v.addStretch()
        v.addWidget(self.big)
        v.addWidget(self.date)
        v.addStretch()
        tabs.addTab(clock, "Clock")
        sw = QWidget()
        sv = QVBoxLayout(sw)
        self.sw = QLabel("00:00.00")
        self.sw.setObjectName("bigClock")
        self.sw.setAlignment(Qt.AlignCenter)
        r = QHBoxLayout()
        start = QPushButton("Start")
        pause = QPushButton("Pause")
        reset = QPushButton("Reset")
        r.addWidget(start)
        r.addWidget(pause)
        r.addWidget(reset)
        sv.addStretch()
        sv.addWidget(self.sw)
        sv.addLayout(r)
        sv.addStretch()
        tabs.addTab(sw, "Stopwatch")
        alarm = QWidget()
        av = QFormLayout(alarm)
        self.alarm = QTimeEdit(QTime.currentTime())
        self.alarm.setDisplayFormat("hh:mm AP")
        self.alarm_on = QCheckBox("Enable alarm")
        self.alarm_status = QLabel("Alarm is off")
        av.addRow("Alarm time", self.alarm)
        av.addRow(self.alarm_on)
        av.addRow(self.alarm_status)
        tabs.addTab(alarm, "Alarm")
        self.add(tabs)
        self.running = False
        self.ms = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(50)
        start.clicked.connect(lambda: setattr(self, "running", True))
        pause.clicked.connect(lambda: setattr(self, "running", False))
        reset.clicked.connect(self.reset)

    def tick(self):
        now = datetime.now()
        self.big.setText(now.strftime("%I:%M:%S %p"))
        self.date.setText(now.strftime("%A, %d %B %Y"))
        if self.running:
            self.ms += 50
            self.sw.setText(f"{self.ms // 60000:02d}:{(self.ms // 1000) % 60:02d}.{(self.ms % 1000) // 10:02d}")
        if self.alarm_on.isChecked() and now.strftime("%H:%M") == self.alarm.time().toString("HH:mm"):
            self.alarm_status.setText("Alarm time reached!")

    def reset(self):
        self.running = False
        self.ms = 0
        self.sw.setText("00:00.00")

# ───────────────────────── Notepad ─────────────────────────
class Notepad(AppWindow):
    def __init__(self, shell, title="Notepad"):
        super().__init__(shell, title)
        self.current_path = None
        row = QHBoxLayout()
        new = QPushButton("New")
        openb = QPushButton("Open")
        save = QPushButton("Save")
        saveas = QPushButton("Save as…")
        self.name = QLineEdit("Untitled.txt")
        row.addWidget(new)
        row.addWidget(openb)
        row.addWidget(save)
        row.addWidget(saveas)
        row.addWidget(self.name, 1)
        self.add_layout(row)
        self.editor = QPlainTextEdit()
        self.editor.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.editor.setMinimumHeight(360)
        self.add(self.editor)
        new.clicked.connect(self.new_file)
        openb.clicked.connect(self.open)
        save.clicked.connect(self.save)
        saveas.clicked.connect(self.save_as)

    def new_file(self):
        self.current_path = None
        self.name.setText("Untitled.txt")
        self.editor.clear()

    def open(self):
        p = StoragePicker.pick_file(self, "Open text file", filters=[".txt", ".md", ".log", ".py", ".js", ".html", ".css", ".json", ".xml", ".ts", ".cpp", ".c", ".java"])
        if p:
            self.load_path(p)

    def load_path(self, p):
        try:
            self.editor.setPlainText(p.read_text(encoding="utf-8", errors="replace"))
            self.name.setText(p.name)
            self.current_path = p
        except Exception as e:
            QMessageBox.warning(self, "Open failed", str(e))

    def save(self):
        if self.current_path and inside_storage(self.current_path):
            p = self.current_path
        else:
            p = unique_name(STORAGE, self.name.text().strip() or "Untitled.txt")
        try:
            p.write_text(self.editor.toPlainText(), encoding="utf-8")
            self.current_path = p
            self.name.setText(p.name)
            self.shell.refresh_explorer()
            self.status_message("Saved to Storage")
        except Exception as e:
            QMessageBox.warning(self, "Save failed", str(e))

    def save_as(self):
        p = StoragePicker.pick_save(self, "Save as in Storage", start_name=self.name.text() or "Untitled.txt")
        if p:
            if not inside_storage(p):
                QMessageBox.warning(self, "Storage only", "NexOS saves user files inside Storage.")
                return
            p.write_text(self.editor.toPlainText(), encoding="utf-8")
            self.current_path = p
            self.name.setText(p.name)
            self.shell.refresh_explorer()

    def status_message(self, msg):
        self.setWindowTitle(f"{self.title} — {msg}")
        QTimer.singleShot(1800, lambda: self.setWindowTitle(self.title))

# ───────────────────────── Code Editor ─────────────────────────
class CodeEditor(AppWindow):
    def __init__(self, shell):
        super().__init__(shell, "Code Editor")
        self.current_path = None
        bar = QHBoxLayout()
        new = QPushButton("New")
        openb = QPushButton("Open")
        save = QPushButton("Save")
        run = QPushButton("▶ Run")
        run.setObjectName("runBtn")
        self.name = QLineEdit("Untitled.py")
        self.name.setMinimumWidth(160)
        bar.addWidget(new)
        bar.addWidget(openb)
        bar.addWidget(save)
        bar.addWidget(run)
        bar.addStretch()
        bar.addWidget(QLabel("File:"))
        bar.addWidget(self.name)
        self.add_layout(bar)
        self.editor = QPlainTextEdit()
        self.editor.setFont(QFont("Consolas", 12))
        self.editor.setTabStopDistance(32)
        self.editor.setPlaceholderText("# Write Python or any code here…\n# Save as .py then press Run")
        self.editor.setObjectName("codeEditor")
        self.editor.setMinimumHeight(320)
        self.editor.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.add(self.editor)
        out_label = QLabel("Output")
        out_label.setObjectName("sectionTitle")
        self.output = QPlainTextEdit()
        self.output.setReadOnly(True)
        self.output.setObjectName("terminalOut")
        self.output.setMaximumHeight(160)
        self.output.setPlaceholderText("Run output appears here…")
        self.add(out_label)
        self.add(self.output)
        new.clicked.connect(self.new_file)
        openb.clicked.connect(self.open)
        save.clicked.connect(self.save)
        run.clicked.connect(self.run_code)

    def new_file(self):
        self.current_path = None
        self.name.setText("Untitled.py")
        self.editor.clear()
        self.output.clear()

    def open(self):
        p = StoragePicker.pick_file(
            self, "Open code file",
            filters=[".py", ".js", ".html", ".css", ".json", ".xml", ".ts", ".cpp", ".c", ".java", ".md", ".txt"]
        )
        if p:
            self.load_path(p)

    def load_path(self, p):
        try:
            self.editor.setPlainText(p.read_text(encoding="utf-8", errors="replace"))
            self.name.setText(p.name)
            self.current_path = p
            self.output.clear()
        except Exception as e:
            QMessageBox.warning(self, "Open failed", str(e))

    def save(self):
        if self.current_path and inside_storage(self.current_path):
            p = self.current_path
        else:
            p = StoragePicker.pick_save(self, "Save code in Storage", start_name=self.name.text() or "Untitled.py",
                                        filters=[".py", ".js", ".html", ".css", ".json", ".txt"])
            if not p:
                return
        try:
            p.write_text(self.editor.toPlainText(), encoding="utf-8")
            self.current_path = p
            self.name.setText(p.name)
            self.shell.refresh_explorer()
            self.output.appendPlainText(f"✓ Saved → {p.name}")
        except Exception as e:
            QMessageBox.warning(self, "Save failed", str(e))

    def run_code(self):
        if not self.current_path:
            self.save()
        if not self.current_path:
            return
        p = self.current_path
        if p.suffix.lower() != ".py":
            self.output.appendPlainText("Run is only available for Python (.py) files.")
            return
        try:
            p.write_text(self.editor.toPlainText(), encoding="utf-8")
        except Exception as e:
            self.output.appendPlainText(f"Save before run failed: {e}")
            return
        import subprocess
        self.output.appendPlainText(f"── Running {p.name} ──")
        try:
            proc = subprocess.run(
                [sys.executable, str(p)],
                capture_output=True, text=True, timeout=10, cwd=str(p.parent)
            )
            out = (proc.stdout + proc.stderr).strip() or "(no output)"
            self.output.appendPlainText(out)
            self.output.appendPlainText(f"── exit {proc.returncode} ──")
        except subprocess.TimeoutExpired:
            self.output.appendPlainText("Timed out (10s limit).")
        except Exception as e:
            self.output.appendPlainText(f"Error: {e}")

# ───────────────────────── Paint ─────────────────────────
class Paint(AppWindow):
    def __init__(self, shell):
        super().__init__(shell, "Paint")
        self.color = QColor(settings.get("accent", "#6ea8ff"))
        self.size = 6
        row = QHBoxLayout()
        col = QPushButton("Color")
        sz = QSpinBox()
        sz.setRange(1, 50)
        sz.setValue(6)
        clear = QPushButton("Clear")
        save = QPushButton("Save")
        row.addWidget(col)
        row.addWidget(QLabel("Brush"))
        row.addWidget(sz)
        row.addWidget(clear)
        row.addWidget(save)
        row.addStretch()
        self.add_layout(row)
        self.canvas = QLabel()
        self.canvas.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.canvas.setMinimumSize(700, 420)
        self.img = QImage(1000, 600, QImage.Format_ARGB32)
        self.img.fill(Qt.white)
        self.update_canvas()
        self.add(self.canvas)
        sz.valueChanged.connect(lambda x: setattr(self, "size", x))
        col.clicked.connect(lambda: self.pick())
        clear.clicked.connect(self.clear)
        save.clicked.connect(self.save)
        self.canvas.mousePressEvent = self.draw
        self.canvas.mouseMoveEvent = self.draw

    def update_canvas(self):
        self.canvas.setPixmap(QPixmap.fromImage(self.img))

    def pick(self):
        c = QColorDialog.getColor(self.color, self)
        if c.isValid():
            self.color = c

    def draw(self, e):
        if e.buttons() & Qt.LeftButton or e.type() == 2:
            p = QPainter(self.img)
            p.setPen(QPen(self.color, self.size, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            p.drawPoint(e.position().toPoint())
            p.end()
            self.update_canvas()

    def clear(self):
        self.img.fill(Qt.white)
        self.update_canvas()

    def save(self):
        p = StoragePicker.pick_save(self, "Save painting", start_name="painting.png", filters=[".png", ".jpg"])
        if p:
            if not p.suffix:
                p = p.with_suffix(".png")
            self.img.save(str(p))
            self.shell.refresh_explorer()

# ───────────────────────── Photos ─────────────────────────
class Photos(AppWindow):
    def __init__(self, shell):
        super().__init__(shell, "Photos")
        self.current = None
        self.current_path = None
        row = QHBoxLayout()
        gallery = QPushButton("Refresh gallery")
        openb = QPushButton("Open")
        camera = QPushButton("📷 Camera")
        rotate = QPushButton("Rotate")
        gray = QPushButton("Grayscale")
        save = QPushButton("Save copy")
        for b in (gallery, openb, camera, rotate, gray, save):
            row.addWidget(b)
        row.addStretch()
        self.add_layout(row)
        split = QSplitter()
        self.files = QListWidget()
        self.files.setIconSize(QSize(72, 72))
        self.files.setMinimumWidth(180)
        self.files.itemClicked.connect(self.load_item)
        self.view = QLabel("No photo selected\n\nPhotos in Storage appear on the left.")
        self.view.setAlignment(Qt.AlignCenter)
        self.view.setMinimumSize(480, 360)
        self.view.setObjectName("photoView")
        split.addWidget(self.files)
        split.addWidget(self.view)
        split.setSizes([220, 680])
        self.add(split)
        gallery.clicked.connect(self.refresh_gallery)
        openb.clicked.connect(self.open)
        camera.clicked.connect(self.open_camera)
        rotate.clicked.connect(self.rotate)
        gray.clicked.connect(self.gray)
        save.clicked.connect(self.save_copy)
        self.refresh_gallery()

    def refresh_gallery(self):
        self.files.clear()
        ext = {".png", ".jpg", ".jpeg", ".bmp", ".webp", ".gif"}
        for p in sorted(STORAGE.rglob("*")):
            if p.is_file() and p.suffix.lower() in ext:
                it = QListWidgetItem(icon_for(p), p.name)
                it.setData(Qt.UserRole, str(p))
                self.files.addItem(it)
        if self.files.count() == 0:
            self.view.setText("No photos in Storage yet.\nUse Camera or save an image from Paint.")

    def load_item(self, it):
        self.load_path(Path(it.data(Qt.UserRole)))

    def open(self):
        p = StoragePicker.pick_file(self, "Open image", filters=[".png", ".jpg", ".jpeg", ".bmp", ".webp", ".gif"])
        if p:
            self.load_path(p)

    def load_path(self, p):
        if not inside_storage(p):
            QMessageBox.warning(self, "Storage only", "Photos app only opens images from Storage.")
            return
        img = QImage(str(p))
        if img.isNull():
            QMessageBox.warning(self, "Photos", "This image could not be opened.")
            return
        self.current = img
        self.current_path = p
        self.update_preview()

    def update_preview(self):
        if self.current:
            self.view.setPixmap(
                QPixmap.fromImage(self.current).scaled(
                    self.view.size() - QSize(16, 16), Qt.KeepAspectRatio, Qt.SmoothTransformation
                )
            )

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self.update_preview()

    def rotate(self):
        if self.current:
            self.current = self.current.transformed(QTransform().rotate(90))
            self.update_preview()

    def gray(self):
        if self.current:
            self.current = self.current.convertToFormat(QImage.Format_Grayscale8)
            self.update_preview()

    def save_copy(self):
        if self.current:
            p = StoragePicker.pick_save(self, "Save edited image", start_name="edited.png", filters=[".png", ".jpg"])
            if p:
                if not p.suffix:
                    p = p.with_suffix(".png")
                self.current.save(str(p))
                self.refresh_gallery()
                self.shell.refresh_explorer()

    def open_camera(self):
        CameraDialog(self).exec()

class CameraDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("NexOS Camera")
        self.resize(820, 620)
        self.image = None
        v = QVBoxLayout(self)
        self.preview = QLabel("Starting camera…")
        self.preview.setAlignment(Qt.AlignCenter)
        v.addWidget(self.preview, 1)
        row = QHBoxLayout()
        snap = QPushButton("Take photo")
        close = QPushButton("Close")
        row.addWidget(snap)
        row.addWidget(close)
        v.addLayout(row)
        close.clicked.connect(self.close)
        snap.clicked.connect(self.capture)
        self.available = False
        try:
            from PySide6.QtMultimedia import QCamera, QMediaCaptureSession, QImageCapture
            from PySide6.QtMultimediaWidgets import QVideoWidget
            self.camera = QCamera()
            self.session = QMediaCaptureSession()
            self.capture_obj = QImageCapture()
            self.session.setCamera(self.camera)
            self.session.setImageCapture(self.capture_obj)
            self.video = QVideoWidget()
            self.session.setVideoOutput(self.video)
            v.insertWidget(0, self.video, 1)
            self.preview.hide()
            self.capture_obj.imageCaptured.connect(self.got_image)
            self.camera.start()
            self.available = True
        except Exception:
            self.preview.setText("Camera is not available on this PC.\nConnect a camera and restart NexOS.")

    def capture(self):
        if self.available:
            self.capture_obj.capture()

    def got_image(self, id, image):
        MEDIA_DIR.mkdir(exist_ok=True)
        path = unique_name(MEDIA_DIR, f"photo_{datetime.now():%Y%m%d_%H%M%S}.jpg")
        image.save(str(path))
        self.parent().load_path(path)
        self.parent().refresh_gallery()
        self.parent().shell.refresh_explorer()
        self.close()

    def closeEvent(self, e):
        try:
            self.camera.stop()
        except Exception:
            pass
        e.accept()

# ───────────────────────── Voice Recorder ─────────────────────────
class VoiceRecorder(AppWindow):
    def __init__(self, shell):
        super().__init__(shell, "Voice Recorder")
        self.available = False
        self.recording = False
        card = QFrame()
        card.setObjectName("Hero")
        cv = QVBoxLayout(card)
        cv.setContentsMargins(24, 28, 24, 28)
        title = QLabel("Voice Recorder")
        title.setObjectName("sectionTitle")
        title.setAlignment(Qt.AlignCenter)
        self.status = QLabel("Ready to record")
        self.status.setAlignment(Qt.AlignCenter)
        self.status.setStyleSheet("font-size:16px;padding:8px;")
        self.meter = QProgressBar()
        self.meter.setRange(0, 100)
        self.meter.setValue(0)
        self.meter.setMinimumHeight(18)
        row = QHBoxLayout()
        self.startb = QPushButton("●  Start recording")
        self.startb.setMinimumHeight(48)
        self.stopb = QPushButton("■  Stop")
        self.stopb.setMinimumHeight(48)
        self.stopb.setEnabled(False)
        row.addWidget(self.startb)
        row.addWidget(self.stopb)
        cv.addWidget(title)
        cv.addSpacing(12)
        cv.addWidget(self.status)
        cv.addSpacing(8)
        cv.addWidget(self.meter)
        cv.addSpacing(16)
        cv.addLayout(row)
        self.add(card)
        tip = QLabel("Recordings are saved as .m4a in Storage.")
        tip.setAlignment(Qt.AlignCenter)
        tip.setStyleSheet("color:#94a7bd;font-size:12px;")
        self.add(tip)
        self.startb.clicked.connect(self.start)
        self.stopb.clicked.connect(self.stop)
        try:
            from PySide6.QtMultimedia import QMediaRecorder, QMediaCaptureSession, QAudioInput
            self.rec = QMediaRecorder()
            self.cap = QMediaCaptureSession()
            self.audio = QAudioInput()
            self.cap.setAudioInput(self.audio)
            self.cap.setRecorder(self.rec)
            self.available = True
        except Exception:
            self.status.setText("Audio recording is not available on this system.")
            self.startb.setEnabled(False)
        self.ui_timer = QTimer(self)
        self.ui_timer.timeout.connect(lambda: self.meter.setValue((self.meter.value() + 3) % 101))

    def start(self):
        if not self.available:
            return
        p = unique_name(STORAGE, "recording.m4a")
        self.rec.setOutputLocation(QUrl.fromLocalFile(str(p)))
        self.rec.record()
        self.recording = True
        self.startb.setEnabled(False)
        self.stopb.setEnabled(True)
        self.status.setText("● Recording…")
        self.ui_timer.start(80)

    def stop(self):
        if not self.available or not self.recording:
            return
        self.rec.stop()
        self.recording = False
        self.startb.setEnabled(True)
        self.stopb.setEnabled(False)
        self.ui_timer.stop()
        self.meter.setValue(0)
        self.status.setText("Recording saved in Storage")
        self.shell.refresh_explorer()

# ───────────────────────── Settings (v1 features) ─────────────────────────
class SettingsApp(AppWindow):
    def __init__(self, shell):
        super().__init__(shell, "Settings")
        tabs = QTabWidget()

        # Appearance
        ui = QWidget()
        f = QFormLayout(ui)
        self.username = QLineEdit(settings.get("username", "NexUser"))
        self.theme = QComboBox()
        self.theme.addItems(list(THEMES.keys()))
        self.theme.setCurrentText(settings.get("theme", "Midnight"))
        self.anim = QComboBox()
        self.anim.addItems(ANIMS)
        self.anim.setCurrentText(settings.get("bg_animation", "Aurora"))
        self.anim_on = QCheckBox("Enable desktop animations")
        self.anim_on.setChecked(settings.get("animations", True))
        self.accent = QLineEdit(settings.get("accent", "#6ea8ff"))
        self.bg_color = QLineEdit(settings.get("background", ""))
        self.bg_color.setPlaceholderText("Leave empty to use theme background")
        self.bg_image = QLineEdit(settings.get("bg_image", ""))
        self.bg_image.setPlaceholderText("Relative path in Storage, e.g. wallpapers/bg.png")
        pick_img = QPushButton("Browse…")
        pick_img.clicked.connect(self.pick_bg_image)
        img_row = QHBoxLayout()
        img_row.addWidget(self.bg_image, 1)
        img_row.addWidget(pick_img)
        img_w = QWidget()
        img_w.setLayout(img_row)
        self.lang = QComboBox()
        self.lang.addItems(["English", "বাংলা", "हिन्दी", "Español", "Deutsch", "Hindi", "Bengali", "French"])
        self.lang.setCurrentText(settings.get("language", "English"))
        self.volume = QSlider(Qt.Horizontal)
        self.volume.setRange(0, 100)
        self.volume.setValue(settings.get("volume", 75))
        self.air = QCheckBox("Airplane mode")
        self.air.setChecked(settings.get("airplane", False))
        self.notif = QCheckBox("Notifications")
        self.notif.setChecked(settings.get("notifications", True))
        applyb = QPushButton("Apply")
        reset = QPushButton("Reset Defaults")
        f.addRow("Username", self.username)
        f.addRow("Theme", self.theme)
        f.addRow("Background animation", self.anim)
        f.addRow(self.anim_on)
        f.addRow("Accent color", self.accent)
        f.addRow("Custom background", self.bg_color)
        f.addRow("Wallpaper (Storage)", img_w)
        f.addRow("Language", self.lang)
        f.addRow("Volume", self.volume)
        f.addRow(self.air)
        f.addRow(self.notif)
        f.addRow(applyb, reset)
        tabs.addTab(ui, "Appearance")

        # Backup
        data = QWidget()
        dv = QVBoxLayout(data)
        dv.addWidget(QLabel("Backup includes settings, messages, calendar data and all Storage files.\nStorage quota is 20 MB."))
        backup = QPushButton("Export backup ZIP")
        imp = QPushButton("Import backup ZIP")
        dv.addWidget(backup)
        dv.addWidget(imp)
        tabs.addTab(data, "Backup")

        self.add(tabs)
        applyb.clicked.connect(self.apply)
        reset.clicked.connect(self.reset)
        backup.clicked.connect(self.export_backup)
        imp.clicked.connect(self.import_backup)

    def pick_bg_image(self):
        p = StoragePicker.pick_file(self, "Choose wallpaper from Storage",
                                    filters=[".png", ".jpg", ".jpeg", ".bmp", ".webp"])
        if p:
            try:
                rel = p.relative_to(STORAGE).as_posix()
                self.bg_image.setText(rel)
            except Exception:
                self.bg_image.setText(p.name)

    def apply(self):
        settings.update(
            username=self.username.text().strip() or "NexUser",
            theme=self.theme.currentText(),
            bg_animation=self.anim.currentText(),
            animations=self.anim_on.isChecked(),
            accent=self.accent.text().strip() or "#6ea8ff",
            background=self.bg_color.text().strip(),
            bg_image=self.bg_image.text().strip(),
            language=self.lang.currentText(),
            volume=self.volume.value(),
            airplane=self.air.isChecked(),
            notifications=self.notif.isChecked(),
        )
        save_json(SETTINGS, settings)
        self.shell.apply_theme()
        if settings.get("notifications", True):
            QMessageBox.information(self, "Settings", "Settings applied.")

    def reset(self):
        settings.clear()
        settings.update(DEFAULT_SETTINGS)
        save_json(SETTINGS, settings)
        self.shell.apply_theme()
        self.close()
        self.shell.apps.pop("Settings", None)
        self.shell.open_app("Settings")

    def export_backup(self):
        # allow save outside for backup convenience, but default to backups folder
        p = QFileDialog.getSaveFileName(
            self, "Export backup",
            str(BACKUPS / f"NexOS-{datetime.now():%Y%m%d-%H%M%S}.zip"),
            "ZIP (*.zip)"
        )[0]
        if not p:
            return
        with zipfile.ZipFile(p, "w", zipfile.ZIP_DEFLATED) as z:
            if SETTINGS.exists():
                z.write(SETTINGS, "settings.json")
            if USERDATA.exists():
                z.write(USERDATA, "userdata.json")
            for f in STORAGE.rglob("*"):
                if f.is_file():
                    z.write(f, "Storage/" + str(f.relative_to(STORAGE)))
        QMessageBox.information(self, "Backup", "Backup created.")

    def import_backup(self):
        p = QFileDialog.getOpenFileName(self, "Import backup", str(BACKUPS), "ZIP (*.zip)")[0]
        if not p:
            return
        try:
            with zipfile.ZipFile(p) as z:
                names = z.namelist()
                if any(Path(n).is_absolute() or ".." in Path(n).parts for n in names):
                    raise ValueError("Unsafe backup")
                incoming = sum(i.file_size for i in z.infolist() if i.filename.startswith("Storage/") and not i.is_dir())
                if incoming > LIMIT:
                    raise ValueError("Backup Storage exceeds 20 MB")
                if "settings.json" in names:
                    settings.update(json.loads(z.read("settings.json")))
                if "userdata.json" in names:
                    global messages
                    messages = json.loads(z.read("userdata.json"))
                for n in names:
                    if n.startswith("Storage/") and n != "Storage/":
                        out = safe_storage(n[8:])
                        out.parent.mkdir(parents=True, exist_ok=True)
                        out.write_bytes(z.read(n))
            save_json(SETTINGS, settings)
            save_data()
            self.shell.apply_theme()
            self.shell.refresh_explorer()
            QMessageBox.information(self, "Backup", "Imported successfully.")
        except Exception as e:
            QMessageBox.warning(self, "Import failed", str(e))

# ───────────────────────── Help ─────────────────────────
class Help(AppWindow):
    def __init__(self, shell):
        super().__init__(shell, "Get Help")
        tabs = QTabWidget()
        intro = QTextEdit()
        intro.setReadOnly(True)
        intro.setHtml(
            "<h1>NexOS Help</h1>"
            "<p>NexOS is a Python desktop environment. Your personal files live in <b>Storage</b>.</p>"
            "<h3>File Explorer</h3>"
            "<p>Use Back, Forward, Up, New, Rename, Move to…, Copy and Delete. "
            "Drag files onto folders to move them. Every file type has its own icon.</p>"
            "<h3>Storage Picker</h3>"
            "<p>Code Editor, Notepad, Photos, Media Player and Paint all use the same "
            "Storage browser to open and save files — never outside Storage.</p>"
            "<h3>Code Editor</h3>"
            "<p>Open source files from Storage, edit, save, and run Python (.py) files. Output appears below the editor.</p>"
            "<h3>Settings (v1 features)</h3>"
            "<p>Username, themes, 15 background animations, accent color, custom background, "
            "wallpaper from Storage, language, volume, airplane mode, notifications, backup/import.</p>"
            "<h3>Photos & Media</h3>"
            "<p>Gallery and player only use Storage. Camera captures into Storage.</p>"
        )
        tabs.addTab(intro, "NexOS")
        self.add(tabs)

# ───────────────────────── Media Player ─────────────────────────
class MediaPlayer(AppWindow):
    def __init__(self, shell):
        super().__init__(shell, "Media Player")
        self.available = False
        try:
            from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
            from PySide6.QtMultimediaWidgets import QVideoWidget
            self.player = QMediaPlayer()
            self.audio = QAudioOutput()
            self.audio.setVolume(settings.get("volume", 75) / 100)
            self.player.setAudioOutput(self.audio)
            self.video = QVideoWidget()
            self.video.setMinimumHeight(280)
            self.player.setVideoOutput(self.video)
            self.available = True
        except Exception:
            pass
        self.titlelabel = QLabel("No media selected")
        self.titlelabel.setObjectName("sectionTitle")
        self.add(self.titlelabel)
        if self.available:
            self.add(self.video)
        else:
            self.add(QLabel("Qt Multimedia is unavailable. Install the requirements and restart NexOS."))
        row = QHBoxLayout()
        openb = QPushButton("Open from Storage")
        play = QPushButton("Play / Pause")
        stop = QPushButton("Stop")
        row.addWidget(openb)
        row.addWidget(play)
        row.addWidget(stop)
        row.addStretch()
        self.add_layout(row)
        tip = QLabel("Media Player only opens files from Storage (mp3, wav, m4a, mp4, mkv, …).")
        tip.setStyleSheet("color:#94a7bd;font-size:12px;")
        self.add(tip)
        openb.clicked.connect(self.open)
        play.clicked.connect(self.toggle)
        stop.clicked.connect(lambda: self.player.stop() if self.available else None)

    def open(self):
        if not self.available:
            return
        p = StoragePicker.pick_file(
            self, "Open media from Storage",
            filters=[".mp3", ".wav", ".m4a", ".ogg", ".flac", ".mp4", ".mkv", ".webm", ".avi", ".mov", ".wmv"]
        )
        if p:
            self.load_media(p)

    def load_media(self, p):
        if not self.available:
            return
        if not inside_storage(p):
            QMessageBox.warning(self, "Storage only", "Media Player only opens files from Storage.")
            return
        self.player.setSource(QUrl.fromLocalFile(str(p)))
        self.titlelabel.setText(p.name)
        self.audio.setVolume(settings.get("volume", 75) / 100)
        self.player.play()

    def toggle(self):
        if not self.available:
            return
        if self.player.playbackState() == self.player.PlayingState:
            self.player.pause()
        else:
            self.player.play()

# ───────────────────────── Camera App ─────────────────────────
class CameraApp(AppWindow):
    """Capture photos and videos, save into Storage/Media."""
    def __init__(self, shell):
        super().__init__(shell, "Camera")
        MEDIA_DIR.mkdir(exist_ok=True)
        self.available = False
        self.recording = False
        self.mode = "photo"  # photo | video

        # Mode switch
        mode_row = QHBoxLayout()
        self.photo_btn = QPushButton("📷  Photo")
        self.video_btn = QPushButton("🎬  Video")
        self.photo_btn.setCheckable(True)
        self.video_btn.setCheckable(True)
        self.photo_btn.setChecked(True)
        self.photo_btn.clicked.connect(lambda: self.set_mode("photo"))
        self.video_btn.clicked.connect(lambda: self.set_mode("video"))
        mode_row.addWidget(self.photo_btn)
        mode_row.addWidget(self.video_btn)
        mode_row.addStretch()
        self.add_layout(mode_row)

        self.preview = QLabel("Starting camera…")
        self.preview.setAlignment(Qt.AlignCenter)
        self.preview.setMinimumHeight(320)
        self.preview.setObjectName("photoView")
        self.add(self.preview)

        self.status = QLabel("Ready")
        self.status.setAlignment(Qt.AlignCenter)
        self.add(self.status)

        btn_row = QHBoxLayout()
        self.capture_btn = QPushButton("Take photo")
        self.capture_btn.setMinimumHeight(48)
        self.capture_btn.clicked.connect(self.capture)
        open_media = QPushButton("Open Media folder")
        open_media.clicked.connect(self.open_media_folder)
        btn_row.addWidget(self.capture_btn)
        btn_row.addWidget(open_media)
        self.add_layout(btn_row)

        tip = QLabel("Captures are saved in Storage → Media")
        tip.setAlignment(Qt.AlignCenter)
        tip.setStyleSheet("color:#94a7bd;font-size:12px;")
        self.add(tip)

        try:
            from PySide6.QtMultimedia import (
                QCamera, QMediaCaptureSession, QImageCapture, QMediaRecorder, QAudioInput
            )
            from PySide6.QtMultimediaWidgets import QVideoWidget
            self.camera = QCamera()
            self.session = QMediaCaptureSession()
            self.image_capture = QImageCapture()
            self.recorder = QMediaRecorder()
            self.audio_in = QAudioInput()
            self.session.setCamera(self.camera)
            self.session.setImageCapture(self.image_capture)
            self.session.setRecorder(self.recorder)
            self.session.setAudioInput(self.audio_in)
            self.video_widget = QVideoWidget()
            self.video_widget.setMinimumHeight(320)
            self.session.setVideoOutput(self.video_widget)
            self.preview.hide()
            # insert live preview above status
            idx = self.cv.indexOf(self.status)
            self.cv.insertWidget(max(0, idx - 1), self.video_widget, 1)
            self.image_capture.imageCaptured.connect(self.on_photo)
            self.recorder.recorderStateChanged.connect(self.on_rec_state)
            self.camera.start()
            self.available = True
            self.status.setText("Camera ready — Photo mode")
        except Exception as e:
            self.preview.setText(
                "Camera is not available on this PC.\n"
                "Connect a camera and restart NexOS.\n\n" + str(e)
            )
            self.capture_btn.setEnabled(False)

    def set_mode(self, mode):
        self.mode = mode
        self.photo_btn.setChecked(mode == "photo")
        self.video_btn.setChecked(mode == "video")
        if mode == "photo":
            self.capture_btn.setText("Take photo")
            if self.recording:
                self.stop_video()
            self.status.setText("Camera ready — Photo mode")
        else:
            self.capture_btn.setText("●  Start recording")
            self.status.setText("Camera ready — Video mode")

    def capture(self):
        if not self.available:
            return
        if self.mode == "photo":
            self.image_capture.capture()
            self.status.setText("Capturing…")
        else:
            if self.recording:
                self.stop_video()
            else:
                self.start_video()

    def on_photo(self, id, image):
        MEDIA_DIR.mkdir(exist_ok=True)
        path = unique_name(MEDIA_DIR, f"photo_{datetime.now():%Y%m%d_%H%M%S}.jpg")
        image.save(str(path))
        self.status.setText(f"Saved → Media/{path.name}")
        self.shell.refresh_explorer()

    def start_video(self):
        MEDIA_DIR.mkdir(exist_ok=True)
        path = unique_name(MEDIA_DIR, f"video_{datetime.now():%Y%m%d_%H%M%S}.mp4")
        self._video_path = path
        self.recorder.setOutputLocation(QUrl.fromLocalFile(str(path)))
        self.recorder.record()
        self.recording = True
        self.capture_btn.setText("■  Stop recording")
        self.status.setText("● Recording video…")

    def stop_video(self):
        self.recorder.stop()
        self.recording = False
        self.capture_btn.setText("●  Start recording")
        name = getattr(self, "_video_path", None)
        self.status.setText(f"Saved → Media/{name.name}" if name else "Video saved")
        self.shell.refresh_explorer()

    def on_rec_state(self, state):
        pass

    def open_media_folder(self):
        self.shell.open_app("File Explorer")
        fe = self.shell.apps.get("File Explorer")
        if fe:
            fe.navigate(MEDIA_DIR)

    def closeEvent(self, e):
        try:
            if self.recording:
                self.recorder.stop()
            self.camera.stop()
        except Exception:
            pass
        super().closeEvent(e)


# ───────────────────────── Web App (YouTube / Mail / Poki) ─────────────────────────
class WebApp(AppWindow):
    """
    App-style embedded site — no URL bar, no Go button.
    Feels like a native app, not a browser.
    """
    def __init__(self, shell, title, url):
        super().__init__(shell, title)
        self.start_url = url
        self.available = False
        # minimal toolbar: back / forward / refresh only (no address bar)
        row = QHBoxLayout()
        back = QToolButton()
        back.setText("←")
        back.setToolTip("Back")
        forward = QToolButton()
        forward.setText("→")
        forward.setToolTip("Forward")
        reload = QToolButton()
        reload.setText("↻")
        reload.setToolTip("Refresh")
        home = QToolButton()
        home.setText("⌂")
        home.setToolTip("Home")
        row.addWidget(back)
        row.addWidget(forward)
        row.addWidget(reload)
        row.addWidget(home)
        row.addStretch()
        self.add_layout(row)
        try:
            from PySide6.QtWebEngineWidgets import QWebEngineView
            self.view = QWebEngineView()
            self.available = True
            self.add(self.view)
            back.clicked.connect(self.view.back)
            forward.clicked.connect(self.view.forward)
            reload.clicked.connect(self.view.reload)
            home.clicked.connect(lambda: self.view.setUrl(QUrl(self.start_url)))
            self.view.setUrl(QUrl(self.start_url))
        except Exception:
            self.add(QLabel(
                f"{title} needs the browser engine.\n"
                "Install PySide6-WebEngine and restart NexOS."
            ))


class YouTubeApp(WebApp):
    def __init__(self, shell):
        super().__init__(shell, "YouTube", "https://www.youtube.com")


class MailApp(WebApp):
    def __init__(self, shell):
        super().__init__(shell, "Mail", "https://mail.google.com")


class PokiApp(WebApp):
    def __init__(self, shell):
        super().__init__(shell, "Poki Games", "https://poki.com/")


# ───────────────────────── Browser ─────────────────────────
class Browser(AppWindow):
    def __init__(self, shell):
        super().__init__(shell, "Browser")
        self.available = False
        try:
            from PySide6.QtWebEngineWidgets import QWebEngineView
            self.view = QWebEngineView()
            self.available = True
        except Exception:
            self.view = None
        row = QHBoxLayout()
        back = QToolButton()
        back.setText("←")
        forward = QToolButton()
        forward.setText("→")
        reload = QToolButton()
        reload.setText("↻")
        self.url = QLineEdit()
        self.url.setPlaceholderText("Search or enter a website")
        go = QPushButton("Go")
        row.addWidget(back)
        row.addWidget(forward)
        row.addWidget(reload)
        row.addWidget(self.url, 1)
        row.addWidget(go)
        self.add_layout(row)
        if self.available:
            self.add(self.view)
            back.clicked.connect(self.view.back)
            forward.clicked.connect(self.view.forward)
            reload.clicked.connect(self.view.reload)
            go.clicked.connect(self.navigate)
            self.view.urlChanged.connect(lambda u: self.url.setText(u.toString()))
            self.view.setUrl(QUrl("https://www.google.com"))
        else:
            self.add(QLabel("Browser engine unavailable. The included requirements install PySide6-WebEngine."))

    def navigate(self):
        if not self.available:
            return
        text = self.url.text().strip()
        self.view.setUrl(QUrl.fromUserInput(text))

# ───────────────────────── Store ─────────────────────────
class Store(AppWindow):
    def __init__(self, shell):
        super().__init__(shell, "Store")
        hero = QFrame()
        hero.setObjectName("Hero")
        hv = QVBoxLayout(hero)
        h = QLabel("NexOS Store")
        h.setObjectName("storeHero")
        hv.addWidget(h)
        hv.addWidget(QLabel("Installed system apps and the future home for NexOS packages."))
        self.add(hero)
        self.list = QListWidget()
        self.list.setIconSize(QSize(40, 40))
        apps = [
            ("Terminal", "System command line"),
            ("File Explorer", "Files and folders"),
            ("Code Editor", "Edit source code"),
            ("Media Player", "Audio and video"),
            ("Photos", "Image gallery and camera"),
            ("Browser", "Web browser"),
        ]
        for name, desc in apps:
            it = QListWidgetItem(QIcon(str(ASSETS / APP_ICONS.get(name, "nexos.svg"))), f"{name}\n{desc}")
            self.list.addItem(it)
        self.add(self.list)
        b = QPushButton("Open selected app")
        b.clicked.connect(self.open_selected)
        self.add(b)

    def open_selected(self):
        it = self.list.currentItem()
        if it:
            self.shell.open_app(it.text().split("\n")[0])

# ───────────────────────── Tic Tac Toe ─────────────────────────
class TicTacToe(AppWindow):
    def __init__(self, shell):
        super().__init__(shell, "Tic Tac Toe")
        self.board = [""] * 9
        self.buttons = []
        self.vs_bot = True
        top = QHBoxLayout()
        self.status = QLabel("Your turn — X")
        self.status.setObjectName("sectionTitle")
        mode = QComboBox()
        mode.addItems(["Vs Bot", "2 Players"])
        mode.currentTextChanged.connect(lambda x: setattr(self, "vs_bot", x == "Vs Bot"))
        top.addWidget(self.status)
        top.addStretch()
        top.addWidget(mode)
        self.add_layout(top)
        g = QGridLayout()
        g.setSpacing(8)
        for i in range(9):
            b = QPushButton("")
            b.setMinimumSize(110, 90)
            b.setFont(QFont("Segoe UI", 28, QFont.Bold))
            b.setObjectName("gameCell")
            b.clicked.connect(lambda _, x=i: self.move(x))
            self.buttons.append(b)
            g.addWidget(b, i // 3, i % 3)
        self.add_layout(g)
        new = QPushButton("New game")
        new.setMinimumHeight(40)
        new.clicked.connect(self.reset)
        self.add(new)

    def move(self, i):
        if self.board[i] or self.result():
            return
        mark = "X" if self.board.count("X") == self.board.count("O") else "O"
        self.board[i] = mark
        self.paint()
        if self.result():
            return
        if self.vs_bot and mark == "X":
            choices = [j for j, x in enumerate(self.board) if not x]
            if choices:
                self.board[random.choice(choices)] = "O"
                self.paint()
                self.result()

    def result(self):
        for a, b, c in [(0, 1, 2), (3, 4, 5), (6, 7, 8), (0, 3, 6), (1, 4, 7), (2, 5, 8), (0, 4, 8), (2, 4, 6)]:
            if self.board[a] and self.board[a] == self.board[b] == self.board[c]:
                self.status.setText(self.board[a] + " wins!")
                return True
        if all(self.board):
            self.status.setText("Draw")
            return True
        return False

    def paint(self):
        for i, x in enumerate(self.board):
            self.buttons[i].setText(x)
        if not self.result():
            if self.vs_bot:
                self.status.setText("Your turn — X")
            else:
                self.status.setText("Player O" if self.board.count("X") > self.board.count("O") else "Player X")

    def reset(self):
        self.board = [""] * 9
        self.paint()
        self.status.setText("Your turn — X")

# ───────────────────────── Tetris ─────────────────────────
class Tetris(AppWindow):
    def __init__(self, shell):
        super().__init__(shell, "Tetris")
        self.w = 10
        self.h = 20
        self.grid = [[0] * 10 for _ in range(20)]
        self.score = 0
        self.status = QLabel("Score: 0")
        self.status.setObjectName("sectionTitle")
        self.add(self.status)
        self.view = QTableWidget(20, 10)
        self.view.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.view.horizontalHeader().setVisible(False)
        self.view.verticalHeader().setVisible(False)
        self.view.horizontalHeader().setDefaultSectionSize(28)
        self.view.verticalHeader().setDefaultSectionSize(28)
        self.view.setFixedSize(28 * 10 + 4, 28 * 20 + 4)
        self.add(self.view)
        self.add(QLabel("A/D or ←/→ move  •  S/↓ drop  •  W rotate  •  Space hard drop"))
        self.setFocusPolicy(Qt.StrongFocus)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.drop)
        self.timer.start(430)
        self.spawn()
        self.render()

    def showEvent(self, e):
        super().showEvent(e)
        self.setFocus()

    def spawn(self):
        self.piece = random.choice([
            [(0, 0), (1, 0), (0, 1), (1, 1)],
            [(0, 0), (1, 0), (2, 0), (3, 0)],
            [(1, 0), (0, 1), (1, 1), (2, 1)]
        ])
        self.px = 4
        self.py = 0

    def cells(self):
        return [(self.px + x, self.py + y) for x, y in self.piece]

    def valid(self, c):
        return all(0 <= x < self.w and y < self.h and (y < 0 or not self.grid[y][x]) for x, y in c)

    def drop(self):
        if self.valid([(x, y + 1) for x, y in self.cells()]):
            self.py += 1
        else:
            self.lock()
        self.render()

    def lock(self):
        for x, y in self.cells():
            if 0 <= y < self.h:
                self.grid[y][x] = 1
        old = len(self.grid)
        self.grid = [r for r in self.grid if not all(r)]
        cleared = old - len(self.grid)
        self.score += cleared * 100
        while len(self.grid) < self.h:
            self.grid.insert(0, [0] * self.w)
        self.spawn()
        if not self.valid(self.cells()):
            self.grid = [[0] * self.w for _ in range(self.h)]
            self.score = 0

    def keyPressEvent(self, e):
        if e.key() in (Qt.Key_A, Qt.Key_Left) and self.valid([(x - 1, y) for x, y in self.cells()]):
            self.px -= 1
        elif e.key() in (Qt.Key_D, Qt.Key_Right) and self.valid([(x + 1, y) for x, y in self.cells()]):
            self.px += 1
        elif e.key() in (Qt.Key_S, Qt.Key_Down):
            self.drop()
        elif e.key() in (Qt.Key_W, Qt.Key_Up):
            rot = [(-y, x) for x, y in self.piece]
            old = self.piece
            self.piece = rot
            if not self.valid(self.cells()):
                self.piece = old
        elif e.key() == Qt.Key_Space:
            while self.valid([(x, y + 1) for x, y in self.cells()]):
                self.py += 1
            self.drop()
        self.render()

    def render(self):
        self.view.clearContents()
        self.status.setText(f"Score: {self.score}")
        for y in range(self.h):
            for x in range(self.w):
                if self.grid[y][x]:
                    self.view.setItem(y, x, QTableWidgetItem("■"))
        for x, y in self.cells():
            if 0 <= y < self.h:
                self.view.setItem(y, x, QTableWidgetItem("■"))

# ───────────────────────── Pong ─────────────────────────
class Pong(AppWindow):
    def __init__(self, shell):
        super().__init__(shell, "Pong")
        self.score = 0
        self.player = 160
        self.bot = 160
        self.ball = [400, 220]
        self.vel = [5, 3]
        self.canvas = QLabel()
        self.canvas.setMinimumSize(760, 420)
        self.canvas.setAlignment(Qt.AlignCenter)
        self.add(self.canvas)
        self.info = QLabel("W/S or ↑/↓ to move  •  first to 10")
        self.info.setAlignment(Qt.AlignCenter)
        self.add(self.info)
        self.setFocusPolicy(Qt.StrongFocus)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(20)

    def showEvent(self, e):
        super().showEvent(e)
        self.setFocus()

    def keyPressEvent(self, e):
        if e.key() in (Qt.Key_W, Qt.Key_Up):
            self.player = max(0, self.player - 22)
        elif e.key() in (Qt.Key_S, Qt.Key_Down):
            self.player = min(360, self.player + 22)

    def reset_ball(self, direction=1):
        self.ball = [380, 220]
        self.vel = [5 * direction, random.choice([-3, 3])]

    def tick(self):
        self.ball[0] += self.vel[0]
        self.ball[1] += self.vel[1]
        if self.ball[1] <= 0 or self.ball[1] >= 420:
            self.vel[1] *= -1
        if self.ball[0] <= 35 and self.player - 5 <= self.ball[1] <= self.player + 85:
            self.vel[0] = abs(self.vel[0])
        if self.ball[0] >= 735 and self.bot - 5 <= self.ball[1] <= self.bot + 85:
            self.vel[0] = -abs(self.vel[0])
        self.bot = max(0, min(360, self.bot + (7 if self.ball[1] > self.bot + 42 else -7)))
        if self.ball[0] < 0:
            self.score -= 1
            self.reset_ball(1)
        if self.ball[0] > 760:
            self.score += 1
            self.reset_ball(-1)
        pix = QPixmap(self.canvas.size())
        theme = THEMES.get(settings.get("theme"), THEMES["Midnight"])
        pix.fill(QColor(theme[1]))
        p = QPainter(pix)
        p.setRenderHint(QPainter.Antialiasing)
        accent = QColor(settings.get("accent", "#6ea8ff"))
        p.setPen(QPen(accent, 2))
        p.drawLine(pix.width() // 2, 0, pix.width() // 2, pix.height())
        p.setBrush(accent)
        p.drawRoundedRect(22, self.player, 12, 85, 5, 5)
        p.drawRoundedRect(pix.width() - 34, self.bot, 12, 85, 5, 5)
        p.drawEllipse(int(self.ball[0]), int(self.ball[1]), 16, 16)
        p.setPen(QColor(theme[2]))
        p.setFont(QFont("Segoe UI", 20, QFont.Bold))
        p.drawText(0, 10, pix.width(), 40, Qt.AlignHCenter, f"{max(self.score, 0)}")
        p.end()
        self.canvas.setPixmap(pix)

# ───────────────────────── Shell ─────────────────────────
class Shell(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_VERSION)
        self.resize(1280, 800)
        self.setMinimumSize(1050, 680)
        self.apps = {}
        self.bg = Background()
        self.setCentralWidget(self.bg)
        self.root = QVBoxLayout(self.bg)
        self.root.setContentsMargins(0, 0, 0, 0)
        self.root.setSpacing(0)
        self.build_top()
        self.build_desktop()
        self.build_dock()
        self.apply_theme()

    def build_top(self):
        bar = QFrame()
        bar.setObjectName("TopBar")
        l = QHBoxLayout(bar)
        l.setContentsMargins(18, 8, 18, 8)
        l.addWidget(Logo(34))
        brand = QLabel("NexOS")
        brand.setObjectName("Brand")
        l.addWidget(brand)
        l.addStretch()
        self.userlbl = QLabel()
        self.time = QLabel()
        self.status = QLabel()
        l.addWidget(self.userlbl)
        l.addSpacing(12)
        l.addWidget(self.time)
        l.addSpacing(14)
        l.addWidget(self.status)
        self.root.addWidget(bar)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_top)
        self.timer.start(1000)
        self.update_top()

    def update_top(self):
        self.userlbl.setText(settings.get("username", "NexUser"))
        self.time.setText(datetime.now().strftime("%I:%M:%S %p  •  %d %b %Y"))
        self.status.setText("Airplane mode" if settings.get("airplane") else "Online")

    def build_desktop(self):
        area = QWidget()
        v = QVBoxLayout(area)
        v.setContentsMargins(30, 24, 30, 18)
        hero = QFrame()
        hero.setObjectName("Hero")
        hv = QHBoxLayout(hero)
        hv.addWidget(Logo(56))
        vv = QVBoxLayout()
        t = QLabel("Welcome to NexOS")
        t.setObjectName("HeroTitle")
        vv.addWidget(t)
        vv.addWidget(QLabel("A calm desktop for your apps, files and games."))
        hv.addLayout(vv)
        hv.addStretch()
        v.addWidget(hero)
        grid = QGridLayout()
        grid.setSpacing(12)
        apps = [
            ("Terminal", "Commands"),
            ("File Explorer", "Files & folders"),
            ("Calculator", "Basic • Scientific • Programmer"),
            ("Calendar", "Dates & notes"),
            ("Messages", "Local conversations"),
            ("Clock", "Clock • Stopwatch • Alarm"),
            ("Notepad", "Text files"),
            ("Code Editor", "Source code"),
            ("Paint", "Drawing"),
            ("Photos", "Gallery"),
            ("Camera", "Photo • Video"),
            ("Voice Recorder", "Record audio"),
            ("Settings", "Customize NexOS"),
            ("Get Help", "Guides"),
            ("Media Player", "Audio • Video"),
            ("Browser", "Web"),
            ("YouTube", "Watch videos"),
            ("Mail", "Email"),
            ("Poki Games", "Online games"),
            ("Store", "Apps"),
            ("Tetris", "Block game"),
            ("Tic Tac Toe", "2 players • Bot"),
            ("Pong", "Arcade"),
        ]
        for i, (name, desc) in enumerate(apps):
            b = QPushButton()
            b.setObjectName("AppTile")
            h = QHBoxLayout(b)
            h.setContentsMargins(12, 10, 12, 10)
            h.addWidget(Logo(36, name))
            vv = QVBoxLayout()
            lab = QLabel(name)
            lab.setObjectName("TileName")
            d = QLabel(desc)
            d.setObjectName("TileDesc")
            vv.addWidget(lab)
            vv.addWidget(d)
            h.addLayout(vv)
            b.clicked.connect(lambda _, n=name: self.open_app(n))
            grid.addWidget(b, i // 6, i % 6)
        v.addLayout(grid)
        v.addStretch()
        self.root.addWidget(area, 1)

    def build_dock(self):
        dock = QFrame()
        dock.setObjectName("Dock")
        l = QHBoxLayout(dock)
        l.setContentsMargins(18, 9, 18, 9)
        menu = QPushButton("NexOS")
        menu.clicked.connect(self.menu)
        l.addWidget(menu)
        l.addStretch()
        self.storage_label = QLabel()
        l.addWidget(self.storage_label)
        l.addSpacing(18)
        power = QPushButton("Power")
        power.clicked.connect(self.close)
        l.addWidget(power)
        self.root.addWidget(dock)
        self.stimer = QTimer(self)
        self.stimer.timeout.connect(self.update_storage)
        self.stimer.start(1500)
        self.update_storage()

    def update_storage(self):
        self.storage_label.setText(f"Storage  {fmt_size(storage_size())} / 20 MB")

    def refresh_explorer(self):
        if "File Explorer" in self.apps:
            self.apps["File Explorer"].refresh()

    def menu(self):
        m = QMenu(self)
        m.addAction("File Explorer", lambda: self.open_app("File Explorer"))
        m.addAction("Settings", lambda: self.open_app("Settings"))
        m.addSeparator()
        m.addAction("Restart desktop", self.restart)
        m.addAction("Shut down", self.close)
        m.exec(self.sender().mapToGlobal(self.sender().rect().topLeft()))

    def restart(self):
        self.hide()
        self.show()

    def open_app(self, name):
        if name in self.apps:
            w = self.apps[name]
            w.show()
            w.raise_()
            w.activateWindow()
            return
        cls = {
            "Terminal": Terminal,
            "File Explorer": FileExplorer,
            "Calculator": Calculator,
            "Calendar": CalendarApp,
            "Messages": MessagesApp,
            "Clock": ClockApp,
            "Notepad": Notepad,
            "Code Editor": CodeEditor,
            "Paint": Paint,
            "Photos": Photos,
            "Camera": CameraApp,
            "Voice Recorder": VoiceRecorder,
            "Settings": SettingsApp,
            "Get Help": Help,
            "Media Player": MediaPlayer,
            "Browser": Browser,
            "YouTube": YouTubeApp,
            "Mail": MailApp,
            "Poki Games": PokiApp,
            "Store": Store,
            "Tetris": Tetris,
            "Tic Tac Toe": TicTacToe,
            "Pong": Pong,
        }.get(name)
        if not cls:
            return
        w = cls(self)
        self.apps[name] = w
        w.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint)
        w.resize(960, 660)
        w.show()
        w.raise_()
        w.activateWindow()

    def open_file(self, p):
        p = Path(p)
        ext = p.suffix.lower()
        if ext in {".txt", ".md", ".log"}:
            self.open_app("Notepad")
            self.apps["Notepad"].load_path(p)
        elif ext in {".py", ".js", ".html", ".css", ".json", ".xml", ".ts", ".cpp", ".c", ".java"}:
            self.open_app("Code Editor")
            self.apps["Code Editor"].load_path(p)
        elif ext in {".png", ".jpg", ".jpeg", ".bmp", ".webp", ".gif"}:
            self.open_app("Photos")
            self.apps["Photos"].load_path(p)
        elif ext in {".mp3", ".wav", ".m4a", ".ogg", ".flac", ".mp4", ".mkv", ".webm", ".avi", ".mov", ".wmv"}:
            self.open_app("Media Player")
            self.apps["Media Player"].load_media(p)
        else:
            QMessageBox.information(self, "NexOS", "No built-in app is registered for this file type yet.")

    def apply_theme(self):
        bg, panel, text, accent = THEMES.get(settings.get("theme"), THEMES["Midnight"])
        accent = settings.get("accent") or accent
        if settings.get("background"):
            bg = settings["background"]
        self.setStyleSheet(f"""
        * {{ font-family: 'Segoe UI'; font-size: 14px; color: {text}; }}
        QMainWindow {{ background: {bg}; }}
        QWidget {{ background: transparent; }}
        #TopBar, #Dock, #AppBar {{
            background: {panel};
            border: 1px solid rgba(255,255,255,18);
        }}
        #Brand {{ font-size: 21px; font-weight: 700; }}
        #AppTitle {{ font-size: 16px; font-weight: 700; }}
        #Hero {{
            background: {panel};
            border: 1px solid rgba(255,255,255,20);
            border-radius: 22px;
        }}
        #HeroTitle {{ font-size: 28px; font-weight: 750; }}
        #TileName {{ font-weight: 650; }}
        #TileDesc {{ color: #94a7bd; font-size: 12px; }}
        QPushButton, QToolButton, QComboBox, QLineEdit, QTextEdit, QPlainTextEdit,
        QListWidget, QTreeWidget, QTableWidget, QSpinBox, QSlider, QTimeEdit, QProgressBar {{
            background: {panel};
            border: 1px solid rgba(255,255,255,25);
            border-radius: 10px;
            padding: 7px;
        }}
        QPushButton:hover, QToolButton:hover {{
            border: 1px solid {accent};
            background: rgba(255,255,255,10);
        }}
        #AppTile {{
            min-height: 74px;
            text-align: left;
            border-radius: 18px;
            background: rgba(255,255,255,7);
        }}
        #AppTile:hover {{
            background: rgba(255,255,255,13);
            border: 1px solid {accent};
        }}
        #AppWindow {{
            background: {bg};
            border: 1px solid rgba(255,255,255,30);
            border-radius: 14px;
        }}
        #AppBar {{ border-radius: 14px 14px 0 0; }}
        #sectionTitle {{ font-size: 19px; font-weight: 700; }}
        #calcDisplay {{ font-size: 28px; padding: 14px; }}
        #bigClock {{ font-size: 60px; font-weight: 700; }}
        #terminalOut, #codeEditor {{
            font-family: Consolas, monospace;
            background: #05080d;
        }}
        #storeHero {{ font-size: 25px; font-weight: 750; }}
        #location {{ font-weight: 600; padding-left: 8px; }}
        #photoView {{
            background: {panel};
            border: 1px solid rgba(255,255,255,20);
            border-radius: 12px;
        }}
        #gameCell {{
            font-size: 28px;
            font-weight: 700;
            min-height: 90px;
        }}
        #runBtn {{
            background: {accent};
            color: #07101d;
            font-weight: 700;
            border: none;
        }}
        QScrollBar:vertical {{ width: 10px; background: transparent; }}
        QScrollBar::handle:vertical {{ background: {accent}; border-radius: 5px; }}
        QTabBar::tab {{ padding: 10px 18px; }}
        QTabBar::tab:selected {{ border-bottom: 2px solid {accent}; }}
        QProgressBar::chunk {{ background: {accent}; border-radius: 5px; }}
        QCalendarWidget QWidget {{ background: {panel}; }}
        QSplitter::handle {{ background: rgba(255,255,255,15); width: 3px; }}
        """)
        self.bg.update()
        self.update_top()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setApplicationName("NexOS")
    app.setApplicationDisplayName("NexOS")
    app.setWindowIcon(QIcon(str(ASSETS / "nexos.svg")))
    w = Shell()
    w.show()
    sys.exit(app.exec())
