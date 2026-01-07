# ui.py
from __future__ import annotations

from PySide6.QtCore import Qt, QSize, QRectF, Signal, Property, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QPainter, QFont, QColor
from PySide6.QtWidgets import (
    QWidget, QMainWindow, QLabel, QPushButton, QHBoxLayout, QVBoxLayout,
    QFrame, QSizePolicy, QToolButton, QAbstractButton
)



# Paleta (muy parecida a la imagen)
BG = "#1f232b"
PANEL = "#3a3f48"
TEXT = "#E9EDF2"
MUTED = "#AAB2BE"
ACCENT = "#FF8C2F"       # naranja brillante
ACCENT_DIM = "#A85A1F"   # naranja más oscuro/tenue
BTN_DARK = "#141821"


class CircleButton(QToolButton):
    def __init__(self, text: str = "", diameter: int = 72):
        super().__init__()
        self.setText(text)
        self.setFixedSize(diameter, diameter)
        self.setStyleSheet(f"""
            QToolButton {{
                border-radius: {diameter//2}px;
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
    Toggle tipo 'pill' con knob animado izquierda/derecha.
    - checked=True  => ON (knob a la derecha)
    - checked=False => OFF (knob a la izquierda)
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
        self._knob_d = self._h - 2 * self._margin  # círculo interior
        self._x = float(self._margin)  # posición actual del knob (animada)

        # Fondo "pill" (gris claro)
        self._bg_on = QColor("#E6E8EC")
        self._bg_off = QColor("#E6E8EC")

        # Knob (gris oscuro)
        self._knob_on = QColor("#2B313A")
        self._knob_off = QColor("#2B313A")

        # Color del texto dentro del pill
        self._text_color = QColor("#1f232b")  # similar a BG    
        self._text_on = "On"
        self._text_off = "Off"

        self._anim = QPropertyAnimation(self, b"knobX", self)
        self._anim.setDuration(180)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)

        #self.clicked.connect(self._on_clicked)

        # Sincroniza posición inicial con checked
        self._snap_to_state()
    def mouseReleaseEvent(self, event):
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
        self._x = self._right_x() if self.isChecked() else self._left_x()
        self.update()

    def _animate_to_state(self):
        self._anim.stop()
        start = self._x
        end = self._right_x() if self.isChecked() else self._left_x()
        self._anim.setStartValue(start)
        self._anim.setEndValue(end)
        self._anim.start()

    def _on_clicked(self):
        desired = not self.isChecked()

        # Cambia estado local + anima
        super().setChecked(desired)
        self._animate_to_state()

        # Emite intención para que el backend actúe
        self.toggledAnimated.emit(desired)



    # --- propiedad animable ---
    def getKnobX(self) -> float:
        return float(self._x)

    def setKnobX(self, v: float):
        self._x = float(v)
        self.update()

    knobX = Property(float, getKnobX, setKnobX)

    # --- API para setear desde el estado de la estufa sin emitir "clic" ---
    def setCheckedFromState(self, checked: bool, animate: bool = True):
        checked = bool(checked)
        if self.isChecked() == checked:
            return
        super().setChecked(checked)
        if animate:
            self._animate_to_state()
        else:
            self._snap_to_state()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)

        w, h = self._w, self._h
        m = self._margin
        d = self._knob_d

        # fondo pill
        p.setPen(Qt.NoPen)
        p.setBrush(self._bg_on if self.isChecked() else self._bg_off)
        p.drawRoundedRect(QRectF(0, 0, w, h), h / 2, h / 2)

        # texto On/Off (siempre en el lado OPUESTO al knob)
        p.setPen(self._text_color)
        p.setFont(QFont("Arial", 22, QFont.DemiBold))

        txt = self._text_on if self.isChecked() else self._text_off

        # Áreas: izquierda y derecha (dejando hueco al knob)
        left_rect = QRectF(18, 0, w - d - 18, h)
        right_rect = QRectF(d, 0, w - d - 18, h)

        if self.isChecked():
            # ON: knob a la derecha -> texto a la izquierda
            p.drawText(left_rect, Qt.AlignVCenter | Qt.AlignLeft, txt)
        else:
            # OFF: knob a la izquierda -> texto a la derecha
            p.drawText(right_rect, Qt.AlignVCenter | Qt.AlignRight, txt)

        # knob circular
        p.setBrush(self._knob_on if self.isChecked() else self._knob_off)
        p.drawEllipse(QRectF(self._x, m, d, d))

        # símbolo power dentro del knob
        p.setPen(QColor("#FFFFFF"))
        p.setFont(QFont("Arial", 26, QFont.Black))
        p.drawText(QRectF(self._x, m, d, d), Qt.AlignCenter, "⏻")


class ThermostatDial(QWidget):
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
        if v is None:
            return
        try:
            self._setpoint = float(v)
        except (TypeError, ValueError):
            return
        self.update()

    def setCurrentTemperature(self, v: float | None):
        if v is None:
            return
        try:
            self._current = float(v)
        except (TypeError, ValueError):
            return
        self.update()


    def setValue(self, v: float):
        self.setSetpoint(float(v))

    def setSubtitle(self, t: str):
        self._subtitle = t
        self.update()

    def setConnected(self, ok: bool):
        self._connected = ok
        self.update()


    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)

        # Fondo
        p.fillRect(self.rect(), QColor(BG))

        # Dial geom
        w, h = self.width(), self.height()
        cx, cy = w * 0.5, h * 0.45
        r = min(w, h) * 0.28

        def clamp01(x: float) -> float:
            if x < 0.0:
                return 0.0
            if x > 1.0:
                return 1.0
            return x

        def ratio_from_temp(t: float) -> float:
            denom = (self._max_t - self._min_t)
            if denom <= 0:
                return 0.0
            return clamp01((t - self._min_t) / denom)

        
        # Anillo de puntos (dos coronas como en la imagen)
        def draw_dotted_ring(radius: float, dots: int, size: float, color_on: QColor, color_off: QColor, on_ratio: float):
            import math
            for i in range(dots):
                a = (i / dots) * math.tau
                x = cx + math.cos(a) * radius
                y = cy + math.sin(a) * radius
                is_on = (i / dots) <= on_ratio
                p.setPen(Qt.NoPen)
                p.setBrush(color_on if is_on else color_off)
                p.drawEllipse(QRectF(x - size/2, y - size/2, size, size))

        accent = QColor(ACCENT if self._connected else ACCENT_DIM)
        off = QColor("#2b313a")

        # ratios (10..40)
        sp_ratio = ratio_from_temp(self._setpoint)   # consigna
        ct_ratio = ratio_from_temp(self._current)    # temperatura actual

        pt_size = max(4.0, min(w, h) * 0.012)

        draw_dotted_ring(r * 1.55, dots=110, size=pt_size, color_on=accent, color_off=off, on_ratio=sp_ratio)
        draw_dotted_ring(r * 1.36, dots=60,  size=pt_size * 1.3, color_on=accent, color_off=off, on_ratio=ct_ratio)



        # Texto central
        p.setPen(QColor(TEXT if self._connected else MUTED))

        f_big = QFont("Arial", 64, QFont.Light)
        p.setFont(f_big)
        temp_txt = f"{self._setpoint:.1f}°"
        p.drawText(QRectF(0, cy - 70, w, 90), Qt.AlignHCenter | Qt.AlignVCenter, temp_txt)

        f_sub = QFont("Arial", 12, QFont.Normal)
        p.setFont(f_sub)
        p.drawText(QRectF(0, cy + 15, w, 40), Qt.AlignHCenter | Qt.AlignTop, self._subtitle)


class MainWindow(QMainWindow):
    # Señales para que el main conecte acciones a la lógica de control
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

        # Top container
        top = QWidget()
        top_lay = QVBoxLayout(top)
        top_lay.setContentsMargins(24, 18, 24, 18)
        top_lay.setSpacing(16)

        # Header row (hora/fecha + alarmas + IP)
        header = QHBoxLayout()

        self.lblTopLeft = QLabel("10:10 • 1 AUG 2024")
        self.lblTopLeft.setStyleSheet(f"color:{MUTED}; font-size:16px;")
        header.addWidget(self.lblTopLeft, 0, Qt.AlignLeft)

        self.lblAlarms = QLabel("—")
        self.lblAlarms.setStyleSheet(f"color:{MUTED}; font-size:14px;")
        self.lblAlarms.setAlignment(Qt.AlignCenter)
        header.addWidget(self.lblAlarms, 1)  # ocupa el centro

        self.lblIp = QLabel("Desconectado")
        self.lblIp.setStyleSheet(f"color:{MUTED}; font-size:14px;")
        header.addWidget(self.lblIp, 0, Qt.AlignRight)

        top_lay.addLayout(header)

        # Middle row
        mid = QHBoxLayout()
        mid.setSpacing(28)

        # Left: MODE + down button
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

        # Center: dial
        self.dial = ThermostatDial()
        mid.addWidget(self.dial, 3)

        # Right: up button + potencia actual
        right_col = QVBoxLayout()
        right_col.setSpacing(18)

        self.btnUp = CircleButton("⌃", diameter=86)
        self.btnUp.clicked.connect(lambda: self.incTemp.emit(self._temp_step))
        right_col.addWidget(self.btnUp, 0, Qt.AlignRight)

        right_col.addStretch(1)

        # Icono modo (decorativo)
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
        for i in range(1, 10):  # 1..9
            b = ZoneButton(str(i))
            b.clicked.connect(lambda checked, n=i: self._on_zone(n))
            self.zone_buttons.append(b)
            zone_row.addWidget(b)

        self.zone_buttons[0].setChecked(True)

        right_col.addLayout(zone_row)
        right_col.addStretch(2)

        mid.addLayout(right_col, 1)
        top_lay.addLayout(mid, 1)

        # Bottom bar
        bottom = QFrame()
        bottom.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        bottom.setStyleSheet(f"background:{PANEL}; border-radius:16px;")

        bot_lay = QHBoxLayout(bottom)
        bot_lay.setContentsMargins(18, 14, 18, 14)
        bot_lay.setSpacing(18)

        # Left: home + indoor temp
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

        # Center: botón grande (modo)
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

        # Right: Power toggle animado (sync solo primera vez)
        self.powerToggle = PowerToggle(width=220, height=86)
        bot_lay.addWidget(self.powerToggle, 0, Qt.AlignVCenter)

        # Click -> intención (desired bool) -> backend
        self.powerToggle.toggledAnimated.connect(self.togglePower.emit)

        # Root layout
        root_lay = QVBoxLayout(root)
        root_lay.setContentsMargins(18, 18, 18, 18)
        root_lay.addWidget(top)
        root_lay.addWidget(bottom)

        # Estado interno UI
        self._connected = False
        self._status_on = False
        self._power_synced_once = False

        self._temp_step = 0.1 


    def set_power_setpoint(self, p: int):
        try:
            p = int(p)
        except Exception:
            p = 1

        if p < 1:
            p = 1
        elif p > 9:
            p = 9

        for i, b in enumerate(self.zone_buttons, start=1):
            b.blockSignals(True)
            b.setChecked(i == p)
            b.blockSignals(False)

    def _on_zone(self, n: int):
        for i, b in enumerate(self.zone_buttons, start=1):
            b.setChecked(i == n)
        self.changeZone.emit(n)

    # ---- API de actualización desde el worker ----
    def set_connected(self, ip: str):
        self._connected = True
        self.lblIp.setText(f"IP: {ip}")
        self.dial.setConnected(True)
        self._power_synced_once = False

    def set_disconnected(self, reason: str):
        self._connected = False
        self.lblIp.setText("Desconectado")
        self.dial.setConnected(False)
        self._power_synced_once = False

    def update_snapshot(self, snap):
        # Temperatura en dial
        sp = snap.set_temp if snap.set_temp is not None else snap.current_temp
        self.dial.setSetpoint(sp)
        self.dial.setCurrentTemperature(snap.current_temp)



        # Potencia actual (1..9)
        self.set_power_setpoint(snap.power_setpoint)

        # Indoor
        self.lblIndoorTemp.setText(f"{snap.current_temp:.1f}°")

        # Mode label + subtitle
        self.lblMode.setText(snap.mode_text)
        self.dial.setSubtitle(snap.state_text)

        # Power toggle: sync SOLO primera vez tras conectar
        self._status_on = bool(snap.status_on)
        if self._connected and not self._power_synced_once:
            self.powerToggle.setCheckedFromState(self._status_on, animate=True)
            self._power_synced_once = True

        if getattr(snap, "mode_code", None) == 1:
            self.lblModeSelect.setText("🌡️")
            self.btnChangeMode.setText("🔥")
        else:
            self.lblModeSelect.setText("🔥")
            self.btnChangeMode.setText("🌡️")

        # Fecha y hora
        if getattr(snap, "current_time", None):
            self.lblTopLeft.setText(snap.current_time)

        # Alarmas
        alarm_text = (getattr(snap, "alarms_text", "") or "").strip()
        alarm_code = (getattr(snap, "alarms_code", "") or "").strip()
        if not alarm_text:
            alarm_text = "—"
        self.lblAlarms.setText(f"{alarm_code}: {alarm_text}" if alarm_code else alarm_text)
