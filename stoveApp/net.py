# net.py
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Optional

from PySide6.QtCore import QObject, Signal, Slot, QThread, QTimer


from collections import deque
import threading


from lan_scanner import scan_network
from NetFlame import NetFlame
from config import REFERENCE_MAC, USERNAME, PASSWORD, SUBNET_CIDR, DISCOVERY_INTERVAL_S, POLL_INTERVAL_S


@dataclass(frozen=True)
class StoveSnapshot:
    ip: str
    current_time: str
    current_temp: float
    set_temp: float
    power_setpoint: int
    status_on: bool
    state_text: str
    mode_text: str
    mode_code: int
    alarms_text: str
    alarms_code: str


class StoveWorker(QObject):
    connected = Signal(str)            # ip
    disconnected = Signal(str)         # reason
    snapshot = Signal(object)          # StoveSnapshot
    log = Signal(str)

    def __init__(self):
        super().__init__()
        self._stop = False
        self._client: Optional[NetFlame] = None
        self._ip: str = ""
        self._cmd_lock = threading.Lock()
        self._cmd_queue = deque()  # items: ("inc", delta) / ("dec", delta)
        self._discovery_timer = QTimer(self)
        self._discovery_timer.setInterval(int(DISCOVERY_INTERVAL_S * 1000))
        self._discovery_timer.timeout.connect(self._tick_discovery)

        self._poll_timer = QTimer(self)
        self._poll_timer.setInterval(int(POLL_INTERVAL_S * 1000))
        self._poll_timer.timeout.connect(self._tick_poll)



    @Slot()
    def start(self):
        """Arranca timers en el hilo del worker (QThread)."""
        self._stop = False
        self._client = None
        self._ip = ""
        self.log.emit("Worker iniciado. Buscando estufa...")
        self._discovery_timer.start()

    @Slot()
    def _tick_discovery(self):
        if self._stop or self._client:
            return

        try:
            self.log.emit("Buscando estufa en la red...")
            ip = self._discover_ip()
            if not ip:
                return

            self._ip = ip
            self._client = NetFlame(
                base_url="http://" + ip,
                auth_mode="basic",
                username=USERNAME,
                password=PASSWORD,
            )

            # validar
            _ = self._client.get_data()

            self.connected.emit(ip)
            self.log.emit(f"Conectado a estufa en {ip}")

            # ya no hace falta discovery
            self._discovery_timer.stop()
            self._poll_timer.start()

        except Exception as e:
            self.disconnected.emit(str(e))
            self.log.emit(f"Error conectando: {e}")
            self._client = None
            self._ip = ""
            # discovery seguirá intentándolo en el siguiente tick

    @Slot()
    def _tick_poll(self):
        if self._stop or not self._client:
            return

        try:
            self._process_commands()
            data = self._client.get_data()
            alarms = self._client.get_alarms()
            clientTime = self._client.get_hour()

            snap = StoveSnapshot(
                ip=self._ip,
                current_temp=float(getattr(data, "currentTemperature", 0.0)),
                set_temp=float(getattr(data, "temperatureSetpoint", 0.0)),
                power_setpoint=int(getattr(data, "powerSetpoint", 0)),
                status_on=bool(getattr(data, "statusOn", False)),
                state_text=str(getattr(getattr(data, "state", None), "description", "")),
                mode_text=str(getattr(getattr(data, "operativeMode", None), "description", "")),
                mode_code=int(getattr(getattr(data, "operativeMode", None), "mode", -1)),
                alarms_text=str(getattr(alarms, "description", alarms)),
                alarms_code=str(getattr(alarms, "code", alarms)),
                current_time=clientTime.raw + " • " + clientTime.date,
            )
            self.snapshot.emit(snap)

        except Exception as e:
            # caída: parar polling y volver a discovery
            self.disconnected.emit(str(e))
            self.log.emit(f"Desconectado: {e}. Reintentando...")
            self._poll_timer.stop()
            self._client = None
            self._ip = ""
            self._discovery_timer.start()

    def stop(self):
        self._stop = True
        self._discovery_timer.stop()
        self._poll_timer.stop()
        self._client = None
        self._ip = ""


    def _discover_ip(self) -> str:
        """Busca la IP por MAC en el /24."""
        devices = scan_network(SUBNET_CIDR)
        for ip, info in devices.items():
            print("Found device: IP=" + ip + " MAC=" + (devices[ip].get("mac") or "-"))
            mac = (info.get("mac") or "").upper()
            if mac == REFERENCE_MAC.upper():
                return ip
        return ""
    def _process_commands(self):
        if not self._client:
            # si no hay cliente, vaciamos para que no se acumulen clicks
            with self._cmd_lock:
                self._cmd_queue.clear()
            return

        with self._cmd_lock:
            cmds = list(self._cmd_queue)
            self._cmd_queue.clear()

        for cmd, val in cmds:
            try:
                if cmd == "inc":
                    if self._client._stoveInternalOperativeMode == -1:
                        continue
                    elif self._client._stoveInternalOperativeMode == 0:
                        self.log.emit("Incrementando potencia...")
                        self._client.increase_power()
                    else:
                        self.log.emit("Incrementando temperatura...")
                        self._client.increase_temperature(val)
                elif cmd == "dec":
                    if self._client._stoveInternalOperativeMode == -1:
                        continue
                    elif self._client._stoveInternalOperativeMode == 0:
                        self.log.emit("Decrementando potencia...")
                        self._client.decrease_power()
                    else:
                        self.log.emit("Decrementando temperatura...")
                        self._client.decrease_temperature(val)
                elif cmd == "power":
                    if val:
                        self._client.power_on()
                    else:
                        self._client.power_off()
                elif cmd == "mode":
                    if val:
                        if self._client._stoveInternalOperativeMode == 0:
                            self.log.emit("Cambiando a modo temperatura...")
                            self._client.set_temperature_mode()
                        else:
                            self.log.emit("Cambiando a modo potencia...")
                            self._client.set_power_mode()
            except Exception as e:
                self.log.emit(f"Error comando {cmd}({val}): {e}")

    
    @Slot(float)
    def request_increase_temp(self, delta: float = 0.1):
        self.log.emit(f"QUEUE INC {delta}")
        with self._cmd_lock:
            self._cmd_queue.append(("inc", float(delta)))

    @Slot(float)
    def request_decrease_temp(self, delta: float = 0.1):
        self.log.emit(f"QUEUE DEC {delta}")
        with self._cmd_lock:
            self._cmd_queue.append(("dec", float(delta)))
    @Slot(bool)
    def request_power(self, desired: bool):
        # desired=True  => encender
        # desired=False => apagar
        with self._cmd_lock:
            self._cmd_queue.append(("power", bool(desired)))
    @Slot(bool)
    def request_mode(self, desired: bool):
        # desired=True  => encender
        # desired=False => apagar
        with self._cmd_lock:
            self._cmd_queue.append(("mode", bool(desired)))
                



