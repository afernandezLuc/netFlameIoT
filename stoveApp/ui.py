# =============================================================================
# stoveApp – UI module (PySide6)
# -----------------------------------------------------------------------------
# Copyright (c) Alejandro Fernández Rodríguez
#
# This source code is released under the GEL 3.0 License.
#
# DISCLAIMER:
# This software is provided "AS IS", without warranty of any kind, express or
# implied, including but not limited to the warranties of merchantability,
# fitness for a particular purpose and noninfringement. In no event shall the
# authors or copyright holders be liable for any claim, damages or other
# liability, whether in an action of contract, tort or otherwise, arising from,
# out of or in connection with the software or the use or other dealings in the
# software.
#
# LICENSE – GEL 3.0:
# You may use, copy, modify, and distribute this code according to the terms of
# the GEL 3.0 License. A full copy of the license should accompany any
# redistribution. If the license text is missing, see: https://gel-license.org
# @author
#    Alejandro Fernández Rodríguez — github.com/afernandezLuc
#  @version 1.0.0
#  @date 2026-01-07
# ====================
# =============================================================================

from __future__ import annotations

from PySide6.QtCore import (
    Qt, QSize, QRectF, Signal, Property, QPropertyAnimation, QEasingCurve
)
from PySide6.QtGui import QPainter, QFont, QColor
from PySide6.QtWidgets import (
    QWidget, QMainWindow, QLabel, QPushButton, QHBoxLayout, QVBoxLayout,
    QFrame, QSizePolicy, QToolButton, QAbstractButton
)

# -----------------------------------------------------------------------------
# Color palette (designed to match the reference UI style)
# -----------------------------------------------------------------------------
BG = "#1f232b"
PANEL = "#3a3f48"
TEXT = "#E9EDF2"
MUTED = "#AAB2BE"
ACCENT = "#FF8C2F"       # bright orange
ACCENT_DIM = "#A85A1F"   # dim/disabled orange
BTN_DARK = "#141821"


class CircleButton(QToolButton):
    """
    Circular tool button used for the main +/- (up/down) controls.

    Args:
        text: Button label (e.g., "⌃", "⌄").
        diameter: Fixed diameter in pixels.
    """

    def __init__(self, text: str = "", diameter: int = 72):
        super().__init__()
        self.setText(text)
        self.setFixedSize(diameter, diameter)
        self.setStyleSheet(f"""
            QToolButton {{
                border-radius: {diameter // 2}px;
                background: {BTN_DARK};
                color: {TEXT};
                font-size: 24px;
            }}
            QToolButton:hover {{
                background: #0f1218;
            }}
            QToolButton:pressed {{
                background: #0b0d12;
            }}
        """)


class ZoneButton(QPushButton):
    """
    Small selectable button used for "power setpoint" selection (1..9).

    Each button is checkable. The UI uses these as an indicator / selector row.
    """

    def __init__(self, label: str):
        super().__init__(label)
        self.setFixedSize(24, 16)
        self.setCheckable(True)
        self.setStyleSheet(f"""
            QPushButton {{
                border-radius: 6px;
                background: #2d323a;
                color: {TEXT};
                font-size: 12px;
            }}
            QPushButton:checked {{
                background: #59606c;
            }}
        """)


class PowerToggle(QAbstractButton):
    """
    Animated 'pill' toggle with a sliding knob.

    Semantics:
        - checked=True  => ON  (knob moves to the right)
        - checked=False => OFF (knob moves to the left)

    Signal:
        toggledAnimated(desired: bool)
            Emitted on mouse release when the user toggles the control. This is
            used instead of relying on the default clicked/toggled signals to
            ensure animation + "desired state" delivery in a single step.
    """

    toggledAnimated = Signal(bool)

    def __init__(self, width: int = 220, height: int = 86, parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setChecked(False)

        self._w = width
        self._h = height
        self.setFixedSize(self._w, self._h)

        self._margin = 10
        self._knob_d = self._h - 2 * self._margin  # inner circular knob size
        self._x = float(self._margin)  # animated knob position (x coordinate)

        # Pill background colors (same on/off here, but kept separate for extensibility)
        self._bg_on = QColor("#E6E8EC")
        self._bg_off = QColor("#E6E8EC")

        # Knob colors (same on/off here, but kept separate for extensibility)
        self._knob_on = QColor("#2B313A")
        self._knob_off = QColor("#2B313A")

        # Text styling inside the pill
        self._text_color = QColor("#1f232b")
        self._text_on = "On"
        self._text_off = "Off"

        # Smooth knob animation
        self._anim = QPropertyAnimation(self, b"knobX", self)
        self._anim.setDuration(180)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)

        # Initialize knob position based on current checked state
        self._snap_to_state()

    def mouseReleaseEvent(self, event):
        """
        Custom mouse release handler:
          - toggles internal checked state
          - animates knob
          - emits toggledAnimated(desired_state)
        """
        if event.button() == Qt.LeftButton and self.rect().contains(event.position().toPoint()):
            desired = not self.isChecked()
            super().setChecked(desired)
            self._animate_to_state()
            self.toggledAnimated.emit(desired)
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def sizeHint(self):
        return QSize(self._w, self._h)

    def _left_x(self) -> float:
        return float(self._margin)

    def _right_x(self) -> float:
        return float(self._w - self._margin - self._knob_d)

    def _snap_to_state(self):
        """Instantly position the knob to match the current checked state."""
        self._x = self._right_x() if self.isChecked() else self._left_x()
        self.update()

    def _animate_to_state(self):
        """Animate the knob to the position corresponding to the checked state."""
        self._anim.stop()
        start = self._x
        end = self._right_x() if self.isChecked() else self._left_x()
        self._anim.setStartValue(start)
        self._anim.setEndValue(end)
        self._anim.start()

    # --- animatable property used by QPropertyAnimation ---
    def getKnobX(self) -> float:
        return float(self._x)

    def setKnobX(self, v: float):
        self._x = float(v)
        self.update()

    knobX = Property(float, getKnobX, setKnobX)

    def setCheckedFromState(self, checked: bool, animate: bool = True):
        """
        Update the toggle from an external device state without emitting UI intent.

        This is used to "sync" the UI to the stove status after connecting.

        Args:
            checked: Desired checked state to display.
            animate: Whether to animate the knob transition.
        """
        checked = bool(checked)
        if self.isChecked() == checked:
            return
        super().setChecked(checked)
        if animate:
            self._animate_to_state()
        else:
            self._snap_to_state()

    def paintEvent(self, _):
        """
        Paint the pill background, the 'On/Off' label, and the knob with a
        power symbol.
        """
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)

        w, h = self._w, self._h
        m = self._margin
        d = self._knob_d

        # Background pill
        p.setPen(Qt.NoPen)
        p.setBrush(self._bg_on if self.isChecked() else self._bg_off)
        p.drawRoundedRect(QRectF(0, 0, w, h), h / 2, h / 2)

        # On/Off text (draw on the opposite side of the knob)
        p.setPen(self._text_color)
        p.setFont(QFont("Arial", 22, QFont.DemiBold))
        txt = self._text_on if self.isChecked() else self._text_off

        left_rect = QRectF(18, 0, w - d - 18, h)
        right_rect = QRectF(d, 0, w - d - 18, h)

        if self.isChecked():
            p.drawText(left_rect, Qt.AlignVCenter | Qt.AlignLeft, txt)
        else:
            p.drawText(right_rect, Qt.AlignVCenter | Qt.AlignRight, txt)

        # Knob circle
        p.setBrush(self._knob_on if self.isChecked() else self._knob_off)
        p.drawEllipse(QRectF(self._x, m, d, d))

        # Power icon inside knob
        p.setPen(QColor("#FFFFFF"))
        p.setFont(QFont("Arial", 26, QFont.Black))
        p.drawText(QRectF(self._x, m, d, d), Qt.AlignCenter, "⏻")


class ThermostatDial(QWidget):
    """
    Central thermostat dial widget.

    It renders:
      - a background
      - two dotted rings:
          * setpoint ring (outer)
          * current temperature ring (inner)
      - a large numeric setpoint in the center
      - a subtitle below (typically stove state text)

    The widget does not manage user interaction here; it is display-focused.
    """

    setpointChanged = Signal(float)

    def __init__(self):
        super().__init__()
        self._setpoint = 24.0
        self._current = 20.0
        self._subtitle = "Conectando..."
        self._connected = False

        self._min_t = 12.0
        self._max_t = 40.0

        self.setMinimumSize(420, 300)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def setSetpoint(self, v: float | None):
        """Set the displayed setpoint temperature (°C)."""
        if v is None:
            return
        try:
            self._setpoint = float(v)
        except (TypeError, ValueError):
            return
        self.update()

    def setCurrentTemperature(self, v: float | None):
        """Set the displayed current temperature (°C)."""
        if v is None:
            return
        try:
            self._current = float(v)
        except (TypeError, ValueError):
            return
        self.update()

    def setValue(self, v: float):
        """Alias for setSetpoint(), useful for Qt-style APIs."""
        self.setSetpoint(float(v))

    def setSubtitle(self, t: str):
        """Set the subtitle text displayed under the main temperature."""
        self._subtitle = t
        self.update()

    def setConnected(self, ok: bool):
        """
        Set connection status affecting color intensity (accent vs dim accent).
        """
        self._connected = ok
        self.update()

    def paintEvent(self, _):
        """Render the dial UI."""
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)

        # Background fill
        p.fillRect(self.rect(), QColor(BG))

        # Dial geometry
        w, h = self.width(), self.height()
        cx, cy = w * 0.5, h * 0.45
        r = min(w, h) * 0.28

        def clamp01(x: float) -> float:
            return 0.0 if x < 0.0 else 1.0 if x > 1.0 else x

        def ratio_from_temp(t: float) -> float:
            denom = (self._max_t - self._min_t)
            if denom <= 0:
                return 0.0
            return clamp01((t - self._min_t) / denom)

        def draw_dotted_ring(radius: float, dots: int, size: float, color_on: QColor, color_off: QColor, on_ratio: float):
            """
            Draw a dotted ring. Dots up to on_ratio are "on", the rest "off".
            """
            import math
            for i in range(dots):
                a = (i / dots) * math.tau
                x = cx + math.cos(a) * radius
                y = cy + math.sin(a) * radius
                is_on = (i / dots) <= on_ratio
                p.setPen(Qt.NoPen)
                p.setBrush(color_on if is_on else color_off)
                p.drawEllipse(QRectF(x - size / 2, y - size / 2, size, size))

        accent = QColor(ACCENT if self._connected else ACCENT_DIM)
        off = QColor("#2b313a")

        sp_ratio = ratio_from_temp(self._setpoint)
        ct_ratio = ratio_from_temp(self._current)

        pt_size = max(4.0, min(w, h) * 0.012)

        # Outer ring for setpoint, inner ring for current temperature
        draw_dotted_ring(r * 1.55, dots=110, size=pt_size,       color_on=accent, color_off=off, on_ratio=sp_ratio)
        draw_dotted_ring(r * 1.36, dots=60,  size=pt_size * 1.3, color_on=accent, color_off=off, on_ratio=ct_ratio)

        # Central text
        p.setPen(QColor(TEXT if self._connected else MUTED))

        p.setFont(QFont("Arial", 64, QFont.Light))
        p.drawText(QRectF(0, cy - 70, w, 90), Qt.AlignHCenter | Qt.AlignVCenter, f"{self._setpoint:.1f}°")

        p.setFont(QFont("Arial", 12, QFont.Normal))
        p.drawText(QRectF(0, cy + 15, w, 40), Qt.AlignHCenter | Qt.AlignTop, self._subtitle)


class MainWindow(QMainWindow):
    """
    Main application window.

    This window:
      - renders the thermostat UI layout
      - emits high-level user intents via Qt Signals
      - exposes an API to update the UI from StoveSnapshot objects

    Signals:
        incTemp(delta): user requested temperature increase
        decTemp(delta): user requested temperature decrease
        togglePower(desired): user toggled power on/off
        changeZone(n): user selected a power setpoint (1..9)
        changeModeRequested(desired): user requested a mode change (toggle intent)
    """

    incTemp = Signal(float)
    decTemp = Signal(float)
    togglePower = Signal(bool)
    changeZone = Signal(int)
    changeModeRequested = Signal(bool)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("NetFlame IoT Stove Controller")
        self.setMinimumSize(900, 400)

        root = QWidget()
        self.setCentralWidget(root)
        root.setStyleSheet(f"background:{BG}; color:{TEXT};")

        # --- Layout containers ---
        top = QWidget()
        top_lay = QVBoxLayout(top)
        top_lay.setContentsMargins(24, 18, 24, 18)
        top_lay.setSpacing(16)

        # Header row: date/time + alarms + IP
        header = QHBoxLayout()

        self.lblTopLeft = QLabel("10:10 • 1 AUG 2024")
        self.lblTopLeft.setStyleSheet(f"color:{MUTED}; font-size:16px;")
        header.addWidget(self.lblTopLeft, 0, Qt.AlignLeft)

        self.lblAlarms = QLabel("—")
        self.lblAlarms.setStyleSheet(f"color:{MUTED}; font-size:14px;")
        self.lblAlarms.setAlignment(Qt.AlignCenter)
        header.addWidget(self.lblAlarms, 1)

        self.lblIp = QLabel("Desconectado")
        self.lblIp.setStyleSheet(f"color:{MUTED}; font-size:14px;")
        header.addWidget(self.lblIp, 0, Qt.AlignRight)

        top_lay.addLayout(header)

        # Middle row: left controls + dial + right controls
        mid = QHBoxLayout()
        mid.setSpacing(28)

        # Left column: down button + mode text
        left_col = QVBoxLayout()
        left_col.setSpacing(18)

        self.btnDown = CircleButton("⌄", diameter=86)
        self.btnDown.clicked.connect(lambda: self.decTemp.emit(self._temp_step))
        left_col.addWidget(self.btnDown, 0, Qt.AlignLeft)

        self.lblModeTitle = QLabel("Modo")
        self.lblModeTitle.setStyleSheet(f"color:{MUTED}; font-size:13px; letter-spacing:1px;")

        self.lblMode = QLabel("Conectando...")
        self.lblMode.setStyleSheet(f"color:{TEXT}; font-size:28px; font-weight:600;")

        left_col.addStretch(1)
        left_col.addWidget(self.lblModeTitle)
        left_col.addWidget(self.lblMode)
        left_col.addStretch(2)

        mid.addLayout(left_col, 1)

        # Center dial widget
        self.dial = ThermostatDial()
        mid.addWidget(self.dial, 3)

        # Right column: up button + power indicators
        right_col = QVBoxLayout()
        right_col.setSpacing(18)

        self.btnUp = CircleButton("⌃", diameter=86)
        self.btnUp.clicked.connect(lambda: self.incTemp.emit(self._temp_step))
        right_col.addWidget(self.btnUp, 0, Qt.AlignRight)

        right_col.addStretch(1)

        # Decorative mode icon (thermometer/fire)
        self.lblModeSelect = QLabel("-")
        self.lblModeSelect.setStyleSheet(f"color:{ACCENT}; font-size:34px;")
        right_col.addWidget(self.lblModeSelect, 0, Qt.AlignRight)

        right_col.addSpacing(10)

        self.lblZoneTitle = QLabel("POTENCIA ACTUAL")
        self.lblZoneTitle.setStyleSheet(f"color:{MUTED}; font-size:13px; letter-spacing:1px;")
        right_col.addWidget(self.lblZoneTitle, 0, Qt.AlignRight)

        zone_row = QHBoxLayout()
        zone_row.setSpacing(6)

        self.zone_buttons = []
        for i in range(1, 10):
            b = ZoneButton(str(i))
            b.clicked.connect(lambda checked, n=i: self._on_zone(n))
            self.zone_buttons.append(b)
            zone_row.addWidget(b)

        self.zone_buttons[0].setChecked(True)

        right_col.addLayout(zone_row)
        right_col.addStretch(2)

        mid.addLayout(right_col, 1)
        top_lay.addLayout(mid, 1)

        # Bottom bar panel
        bottom = QFrame()
        bottom.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        bottom.setStyleSheet(f"background:{PANEL}; border-radius:16px;")

        bot_lay = QHBoxLayout(bottom)
        bot_lay.setContentsMargins(18, 14, 18, 14)
        bot_lay.setSpacing(18)

        # Left: home icon + indoor temperature
        self.lblHome = QLabel("⌂")
        self.lblHome.setStyleSheet(f"color:{TEXT}; font-size:50px;")
        bot_lay.addWidget(self.lblHome, 0, Qt.AlignVCenter)

        indoor_col = QVBoxLayout()
        self.lblIndoorTitle = QLabel("Temperatura interior (C)")
        self.lblIndoorTitle.setStyleSheet(f"color:{MUTED}; font-size:14px;")

        self.lblIndoorTemp = QLabel("24°")
        self.lblIndoorTemp.setStyleSheet(f"color:{TEXT}; font-size:36px; font-weight:700;")

        indoor_col.addWidget(self.lblIndoorTitle)
        indoor_col.addWidget(self.lblIndoorTemp)
        bot_lay.addLayout(indoor_col)

        bot_lay.addStretch(1)

        # Center: large mode change button
        self.btnChangeMode = QPushButton("-")
        self.btnChangeMode.setFixedSize(86, 86)
        self.btnChangeMode.setStyleSheet(f"""
            QPushButton {{
                border-radius: 43px;
                background: {ACCENT};
                color: {BG};
                font-size: 34px;
                font-weight: 800;
            }}
            QPushButton:hover {{ background: #FF9E52; }}
            QPushButton:pressed {{ background: #E8741B; }}
        """)
        self.btnChangeMode.clicked.connect(lambda: self.changeModeRequested.emit(True))
        bot_lay.addWidget(self.btnChangeMode, 0, Qt.AlignVCenter)

        # Right: animated power toggle
        self.powerToggle = PowerToggle(width=220, height=86)
        bot_lay.addWidget(self.powerToggle, 0, Qt.AlignVCenter)

        # User intent: power on/off
        self.powerToggle.toggledAnimated.connect(self.togglePower.emit)

        # Root layout
        root_lay = QVBoxLayout(root)
        root_lay.setContentsMargins(18, 18, 18, 18)
        root_lay.addWidget(top)
        root_lay.addWidget(bottom)

        # UI internal state
        self._connected = False
        self._status_on = False
        self._power_synced_once = False

        # Temperature step used for inc/dec actions
        self._temp_step = 0.1

    def set_power_setpoint(self, p: int):
        """
        Update the UI row of 1..9 buttons to reflect the current power setpoint.

        Args:
            p: power setpoint expected in range [1..9]. Out-of-range values are clamped.
        """
        try:
            p = int(p)
        except Exception:
            p = 1

        p = 1 if p < 1 else 9 if p > 9 else p

        for i, b in enumerate(self.zone_buttons, start=1):
            b.blockSignals(True)
            b.setChecked(i == p)
            b.blockSignals(False)

    def _on_zone(self, n: int):
        """
        Handler for when a zone/power button is clicked by the user.

        Args:
            n: Selected zone index in [1..9].
        """
        for i, b in enumerate(self.zone_buttons, start=1):
            b.setChecked(i == n)
        self.changeZone.emit(n)

    # ---- API called by the worker to update connection state ----
    def set_connected(self, ip: str):
        """Mark UI as connected and display the stove IP."""
        self._connected = True
        self.lblIp.setText(f"IP: {ip}")
        self.dial.setConnected(True)
        self._power_synced_once = False

    def set_disconnected(self, reason: str):
        """Mark UI as disconnected and reset certain UI elements."""
        self._connected = False
        self.lblIp.setText("Desconectado")
        self.dial.setConnected(False)
        self._power_synced_once = False

    def update_snapshot(self, snap):
        """
        Update UI from a StoveSnapshot-like object.

        Expected fields (by convention):
            - set_temp, current_temp, power_setpoint, status_on, state_text, mode_text, mode_code
            - current_time, alarms_text, alarms_code
        """
        sp = snap.set_temp if snap.set_temp is not None else snap.current_temp
        self.dial.setSetpoint(sp)
        self.dial.setCurrentTemperature(snap.current_temp)

        self.set_power_setpoint(snap.power_setpoint)

        self.lblIndoorTemp.setText(f"{snap.current_temp:.1f}°")

        self.lblMode.setText(snap.mode_text)
        self.dial.setSubtitle(snap.state_text)

        # Sync power toggle only once after connecting (avoid fighting with user interaction)
        self._status_on = bool(snap.status_on)
        if self._connected and not self._power_synced_once:
            self.powerToggle.setCheckedFromState(self._status_on, animate=True)
            self._power_synced_once = True

        # Mode indicators: update icon and "change mode" button label
        if getattr(snap, "mode_code", None) == 1:
            self.lblModeSelect.setText("🌡️")
            self.btnChangeMode.setText("🔥")
        else:
            self.lblModeSelect.setText("🔥")
            self.btnChangeMode.setText("🌡️")

        # Date/time header
        if getattr(snap, "current_time", None):
            self.lblTopLeft.setText(snap.current_time)

        # Alarms header
        alarm_text = (getattr(snap, "alarms_text", "") or "").strip()
        alarm_code = (getattr(snap, "alarms_code", "") or "").strip()
        if not alarm_text:
            alarm_text = "—"
        self.lblAlarms.setText(f"{alarm_code}: {alarm_text}" if alarm_code else alarm_text)
