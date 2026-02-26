'''
https://github.com/kryvexx/CrosshairZ
This project dates back to mid-2024
Many features have been stripped down, such as the crosshair component selector
    - it's still working if you edit config.json, I just removed the GUI side because it was extremely unreliable
Also, this is a complete rewrite of the original code just for the sake of keeping you sane
Trust me when I say this: it was an abomination.
'''

import os, math, json, keyboard, sys
from pathlib import Path
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QPainter, QBrush, QColor, QPen, QTransform
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QSlider,
    QCheckBox, QColorDialog, QLabel, QPushButton, QMessageBox
)

CONFIG_PATH = Path(__file__).resolve().parent / "config.json"
VERSION = "v2"


class Config:
    def __init__(self):
        self.crosshair_enabled = True
        self.dot_enabled = True

        self.dot_size = 2
        self.thickness = 2
        self.length = 8
        self.gap = 3
        self.rotation = 0

        self.crosshair_top = True
        self.crosshair_bottom = True
        self.crosshair_left = True
        self.crosshair_right = True

        self.crosshair_color = QColor(0, 255, 0)
        self.dot_color = QColor(255, 255, 255)

        self.rainbow_shift = 0.0


cfg = Config()


def save_configuration():
    data = {
        "crosshair": {
            "enabled": cfg.crosshair_enabled,
            "color": cfg.crosshair_color.name(),
            "thickness": cfg.thickness,
            "length": cfg.length,
            "gap": cfg.gap,
            "rotation": cfg.rotation,
            "shown_bits": {
                "top": cfg.crosshair_top,
                "bottom": cfg.crosshair_bottom,
                "left": cfg.crosshair_left,
                "right": cfg.crosshair_right,
            },
        },
        "dot": {
            "enabled": cfg.dot_enabled,
            "color": cfg.dot_color.name(),
            "size": cfg.dot_size,
        },
    }
    try:
        with open(CONFIG_PATH, "w") as f:
            json.dump(data, f, indent=4)
        QMessageBox.information(None, "CrosshairZ", f"Saved: {CONFIG_PATH}")
    except Exception as e:
        QMessageBox.critical(None, "CrosshairZ", f"Unable to save: {e}")


def load_configuration():
    if not os.path.exists(CONFIG_PATH):
        return
    try:
        with open(CONFIG_PATH, "r") as f:
            data = json.load(f)

        cfg.crosshair_enabled = data["crosshair"]["enabled"]
        cfg.crosshair_color = QColor(data["crosshair"]["color"])
        cfg.thickness = data["crosshair"]["thickness"]
        cfg.length = data["crosshair"]["length"]
        cfg.gap = data["crosshair"]["gap"]
        cfg.rotation = data["crosshair"]["rotation"]
        cfg.crosshair_top = data["crosshair"]["shown_bits"]["top"]
        cfg.crosshair_bottom = data["crosshair"]["shown_bits"]["bottom"]
        cfg.crosshair_left = data["crosshair"]["shown_bits"]["left"]
        cfg.crosshair_right = data["crosshair"]["shown_bits"]["right"]

        cfg.dot_enabled = data["dot"]["enabled"]
        cfg.dot_color = QColor(data["dot"]["color"])
        cfg.dot_size = data["dot"]["size"]

    except Exception as e:
        QMessageBox.critical(None, "CrosshairZ", f"Unable to load config file: {e}")


class CrosshairOverlay(QMainWindow):
    def __init__(self):
        super().__init__()
        screen = QApplication.primaryScreen().geometry()
        self.setGeometry(screen)
        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool |
            Qt.X11BypassWindowManagerHint
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update)
        self.timer.start(50)

    def rotate_point(self, x, y, angle):
        rad = math.radians(angle)
        return (
            x * math.cos(rad) - y * math.sin(rad),
            x * math.sin(rad) + y * math.cos(rad),
        )

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        
        ch_color = cfg.crosshair_color
        dot_color = cfg.dot_color

        cx = self.width() // 2
        cy = self.height() // 2
        t = cfg.thickness
        g = cfg.gap
        ln = cfg.length

        rects = [
            (cx - t // 2, cy - g - ln, t,  ln),
            (cx - t // 2, cy + g,      t,  ln),
            (cx - g - ln, cy - t // 2, ln, t),
            (cx + g,      cy - t // 2, ln, t),
        ]

        indices = []
        if cfg.crosshair_top:    indices.append(0)
        if cfg.crosshair_bottom: indices.append(1)
        if cfg.crosshair_left:   indices.append(2)
        if cfg.crosshair_right:  indices.append(3)

        if cfg.crosshair_enabled:
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(ch_color))

            for i in indices:
                x, y, w, h = rects[i]
                transform = QTransform()
                transform.translate(cx, cy)
                transform.rotate(cfg.rotation)
                transform.translate(-cx, -cy)
                painter.setTransform(transform)
                painter.drawRect(x, y, w, h)
                painter.setTransform(QTransform())

        if cfg.dot_enabled:
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(dot_color))
            s = cfg.dot_size
            painter.drawEllipse(cx - s // 2, cy - s // 2, s, s)

    def closeEvent(self, event):
        event.ignore()


class SettingsWindow(QWidget):
    def __init__(self, overlay: CrosshairOverlay):
        super().__init__()
        self.overlay = overlay
        self.setWindowTitle(f"CrosshairZ {VERSION} | Settings")
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.WindowTitleHint)
        self.setFixedSize(300, 720)

        layout = QVBoxLayout()

        self.crosshair_cb  = self._checkbox("Show crosshair",       cfg.crosshair_enabled, lambda s: setattr(cfg, "crosshair_enabled",  s == Qt.Checked))
        self.dot_cb        = self._checkbox("Show dot",             cfg.dot_enabled,       lambda s: setattr(cfg, "dot_enabled",        s == Qt.Checked))

        for cb in (self.crosshair_cb, self.dot_cb):
            layout.addWidget(cb)

        for label, attr in (
            ("Change crosshair color", "crosshair_color"),
            ("Change dot color",       "dot_color"),
        ):
            btn = QPushButton(label)
            btn.clicked.connect(lambda _, a=attr: self.pick_color(a))
            layout.addWidget(btn)

        self.dot_size_lbl,  self.dot_size_sl  = self._slider("Dot Size",            2,  20, cfg.dot_size,  lambda v: setattr(cfg, "dot_size",  v))
        self.thickness_lbl, self.thickness_sl = self._slider("Crosshair Thickness", 2,  20, cfg.thickness, lambda v: setattr(cfg, "thickness", v))
        self.length_lbl,    self.length_sl    = self._slider("Crosshair Length",    1,  50, cfg.length,    lambda v: setattr(cfg, "length",    v))
        self.gap_lbl,       self.gap_sl       = self._slider("Crosshair Gap",       1,  20, cfg.gap,       lambda v: setattr(cfg, "gap",       v))
        self.rotation_lbl,  self.rotation_sl  = self._slider("Crosshair Rotation",  0,  90, cfg.rotation,  lambda v: setattr(cfg, "rotation",  v))

        for lbl, sl in (
            (self.dot_size_lbl,  self.dot_size_sl),
            (self.thickness_lbl, self.thickness_sl),
            (self.length_lbl,    self.length_sl),
            (self.gap_lbl,       self.gap_sl),
            (self.rotation_lbl,  self.rotation_sl),
        ):
            layout.addWidget(lbl)
            layout.addWidget(sl)

        credits = QLabel(f"CrosshairZ {VERSION} - https://github.com/kryvexx")
        credits.setStyleSheet("color: gray;")
        layout.addWidget(credits)

        hotkey_lbl = QLabel("Hide keybind: \\ (backslash)")
        hotkey_lbl.setStyleSheet("font-weight: bold;")
        layout.addWidget(hotkey_lbl)

        for label, slot in (
            ("Save Config",     self.save_config),
            ("Load Config",     self.load_config),
            ("Reset",           self.reset_config),
            ("Restart Overlay", self.restart_overlay),
            ("Exit",            self.kill_overlay),
        ):
            btn = QPushButton(label)
            btn.clicked.connect(slot)
            layout.addWidget(btn)

        self.setLayout(layout)

    def _checkbox(self, text, checked, callback):
        cb = QCheckBox(text)
        cb.setChecked(checked)
        cb.stateChanged.connect(callback)
        return cb

    def _slider(self, text, min_val, max_val, value, callback):
        lbl = QLabel(f"{text}: {value}")
        sl = QSlider(Qt.Horizontal)
        sl.setRange(min_val, max_val)
        sl.setValue(value)

        def on_change():
            v = sl.value()
            if text in ("Dot Size", "Crosshair Thickness") and v % 2 != 0:
                v += 1
            lbl.setText(f"{text}: {v}")
            callback(v)

        sl.valueChanged.connect(on_change)
        return lbl, sl

    def pick_color(self, attr):
        color = QColorDialog.getColor(getattr(cfg, attr))
        if color.isValid():
            setattr(cfg, attr, color)

    def sync_ui(self):
        self.crosshair_cb.setChecked(cfg.crosshair_enabled)
        self.dot_cb.setChecked(cfg.dot_enabled)
        self.dot_size_sl.setValue(cfg.dot_size)
        self.thickness_sl.setValue(cfg.thickness)
        self.length_sl.setValue(cfg.length)
        self.gap_sl.setValue(cfg.gap)
        self.rotation_sl.setValue(cfg.rotation)

    def save_config(self):
        if os.path.exists(CONFIG_PATH):
            reply = QMessageBox.question(
                self, f"CrosshairZ {VERSION}",
                "Overwrite config.json with the current values?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
            )
            if reply != QMessageBox.Yes:
                return
        save_configuration()

    def load_config(self):
        load_configuration()
        self.sync_ui()

    def reset_config(self):
        cfg.__init__()
        self.sync_ui()

    def restart_overlay(self):
        self.overlay.timer.stop()
        self.overlay.hide()
        self.overlay = CrosshairOverlay()
        self.overlay.show()

    def kill_overlay(self):
        QApplication.quit()
        sys.exit()


if __name__ == "__main__":
    app = QApplication(sys.argv)

    overlay = CrosshairOverlay()
    settings = SettingsWindow(overlay)

    load_configuration()
    settings.sync_ui()

    overlay.show()
    settings.show()

    keyboard.add_hotkey("\\", lambda: settings.hide() if settings.isVisible() else settings.show())

    sys.exit(app.exec_())