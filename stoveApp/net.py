# =============================================================================
# stoveApp – Network/Device worker (Qt thread + discovery + polling)
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
# =============================================================================

from __future__ import annotations

import threading
from collections import deque
from dataclasses import dataclass
from typing import Optional

from PySide6.QtCore import QObject, Signal, Slot, QTimer

from lan_scanner import scan_network
from NetFlame import NetFlame
from config import (
    REFERENCE_MAC,
    USERNAME,
    PASSWORD,
    SUBNET_CIDR,
    DISCOVERY_INTERVAL_S,
    POLL_INTERVAL_S,
)


@dataclass(frozen=True)
class StoveSnapshot:
    """
    Immutable data snapshot emitted from the worker thread to the UI.

    This object is intended to be UI-friendly and serializable.

    Attributes:
        ip: Discovered stove IP address.
        current_time: Stove-reported time string (as presented to the UI).
        current_temp: Current measured temperature (°C).
        set_temp: Current temperature setpoint (°C).
        power_setpoint: Power setpoint (firmware-specific scale).
        status_on: True if the stove reports it is ON.
        state_text: Human-readable internal state description.
        mode_text: Human-readable operative mode description.
        mode_code: Raw operative mode code.
        alarms_text: Human-readable alarm description.
        alarms_code: Raw alarm code string.
    """

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
    """
    Background worker that owns all device I/O.

    Design:
      - Runs in a dedicated QThread (moved using QObject.moveToThread).
      - Uses QTimer for:
          * discovery ticks (find stove IP by matching MAC)
          * polling ticks (read stove data periodically)
      - Uses a thread-safe command queue to avoid blocking the UI thread.

    Signals:
      - connected(ip): emitted when the stove is found and validated.
      - disconnected(reason): emitted on connection/poll failures.
      - snapshot(obj): emitted periodically with StoveSnapshot.
      - log(msg): emitted for logging/debug.
    """

    connected = Signal(str)            # ip
    disconnected = Signal(str)         # reason
    snapshot = Signal(object)          # StoveSnapshot
    log = Signal(str)

    def __init__(self):
        super().__init__()
        self._stop = False
        self._client: Optional[NetFlame] = None
        self._ip: str = ""

        # Command queue protected with a lock because UI signals may enqueue
        # commands while the worker processes them on poll ticks.
        self._cmd_lock = threading.Lock()
        self._cmd_queue = deque()  # items: ("inc", delta) / ("dec", delta) / ("power", bool) / ("mode", bool)

        # Discovery timer: periodically scans the LAN to find the stove by MAC.
        self._discovery_timer = QTimer(self)
        self._discovery_timer.setInterval(int(DISCOVERY_INTERVAL_S * 1000))
        self._discovery_timer.timeout.connect(self._tick_discovery)

        # Poll timer: once connected, periodically reads stove state and emits snapshots.
        self._poll_timer = QTimer(self)
        self._poll_timer.setInterval(int(POLL_INTERVAL_S * 1000))
        self._poll_timer.timeout.connect(self._tick_poll)

    @Slot()
    def start(self):
        """
        Start the worker lifecycle.

        This method is intended to be connected to QThread.started and will run
        in the worker thread context.

        Behavior:
          - resets internal state
          - starts discovery timer (polling only begins after discovery succeeds)
        """
        self._stop = False
        self._client = None
        self._ip = ""
        self.log.emit("Worker started. Looking for stove...")
        self._discovery_timer.start()

    @Slot()
    def _tick_discovery(self):
        """
        Discovery tick handler.

        Attempts to discover the stove IP address by scanning `SUBNET_CIDR` and
        matching `REFERENCE_MAC`. On success:
          - instantiates NetFlame client
          - validates connectivity by calling get_data()
          - emits connected(ip)
          - stops discovery and starts polling
        """
        if self._stop or self._client:
            return

        try:
            self.log.emit("Searching stove on the LAN...")
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

            # Validate connectivity (forces an HTTP request and parsing).
            _ = self._client.get_data()

            self.connected.emit(ip)
            self.log.emit(f"Connected to stove at {ip}")

            # Switch from discovery to polling.
            self._discovery_timer.stop()
            self._poll_timer.start()

        except Exception as e:
            # Connection failed: report and keep discovery running for next ticks.
            self.disconnected.emit(str(e))
            self.log.emit(f"Connection error: {e}")
            self._client = None
            self._ip = ""

    @Slot()
    def _tick_poll(self):
        """
        Poll tick handler.

        When connected:
          - processes queued commands (increase/decrease temperature or power, etc.)
          - reads device telemetry and alarms
          - emits a StoveSnapshot for UI rendering

        On any exception:
          - emits disconnected(reason)
          - stops polling
          - clears client and restarts discovery
        """
        if self._stop or not self._client:
            return

        try:
            self._process_commands()

            data = self._client.get_data()
            alarms = self._client.get_alarms()
            clientTime = self._client.get_hour()

            # NOTE:
            # Your Hora dataclass (as provided) has fields: hh, mm, raw
            # but here you also reference clientTime.date. If Hora doesn't
            # provide .date in your runtime, this will raise AttributeError.
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
            # Poll failed: stop polling and return to discovery mode.
            self.disconnected.emit(str(e))
            self.log.emit(f"Disconnected: {e}. Retrying...")
            self._poll_timer.stop()
            self._client = None
            self._ip = ""
            self._discovery_timer.start()

    def stop(self):
        """
        Stop the worker.

        This should be called from the main thread during application shutdown.
        It stops timers and releases the client reference.
        """
        self._stop = True
        self._discovery_timer.stop()
        self._poll_timer.stop()
        self._client = None
        self._ip = ""

    def _discover_ip(self) -> str:
        """
        Discover the stove IP address by matching a known MAC address.

        Returns:
            The discovered IP address as a string, or "" if not found.

        Notes:
            - `scan_network()` is expected to return a dict indexed by IP,
              where each value is a dict that may contain "mac".
        """
        devices = scan_network(SUBNET_CIDR)
        for ip, info in devices.items():
            print("Found device: IP=" + ip + " MAC=" + (devices[ip].get("mac") or "-"))
            mac = (info.get("mac") or "").upper()
            if mac == REFERENCE_MAC.upper():
                return ip
        return ""

    def _process_commands(self):
        """
        Drain the command queue and apply commands to the stove.

        Commands are queued by UI signals and executed on poll ticks to keep UI
        responsive and avoid concurrent HTTP requests from multiple threads.

        Supported commands:
            - ("inc", delta)
            - ("dec", delta)
            - ("power", bool)
            - ("mode", bool)

        Notes:
            - This code expects internal attributes and methods on NetFlame:
              `_stoveInternalOperativeMode`, `increase_power()`, `increase_temperature()`,
              `decrease_power()`, `decrease_temperature()`, `power_on()`, `power_off()`,
              `set_temperature_mode()`, `set_power_mode()`.
              If those are not implemented, you will get AttributeError.
        """
        if not self._client:
            # If no client exists, clear queue so UI clicks do not accumulate.
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
                        self.log.emit("Increasing power...")
                        self._client.increase_power()
                    else:
                        self.log.emit("Increasing temperature...")
                        self._client.increase_temperature(val)

                elif cmd == "dec":
                    if self._client._stoveInternalOperativeMode == -1:
                        continue
                    elif self._client._stoveInternalOperativeMode == 0:
                        self.log.emit("Decreasing power...")
                        self._client.decrease_power()
                    else:
                        self.log.emit("Decreasing temperature...")
                        self._client.decrease_temperature(val)

                elif cmd == "power":
                    if val:
                        self._client.power_on()
                    else:
                        self._client.power_off()

                elif cmd == "mode":
                    if val:
                        if self._client._stoveInternalOperativeMode == 0:
                            self.log.emit("Switching to temperature mode...")
                            self._client.set_temperature_mode()
                        else:
                            self.log.emit("Switching to power mode...")
                            self._client.set_power_mode()

            except Exception as e:
                self.log.emit(f"Command error {cmd}({val}): {e}")

    @Slot(float)
    def request_increase_temp(self, delta: float = 0.1):
        """
        Enqueue a request to increase temperature (or power, depending on mode).

        Args:
            delta: Temperature increment (°C). If in power mode, delta may be ignored.
        """
        self.log.emit(f"QUEUE INC {delta}")
        with self._cmd_lock:
            self._cmd_queue.append(("inc", float(delta)))

    @Slot(float)
    def request_decrease_temp(self, delta: float = 0.1):
        """
        Enqueue a request to decrease temperature (or power, depending on mode).

        Args:
            delta: Temperature decrement (°C). If in power mode, delta may be ignored.
        """
        self.log.emit(f"QUEUE DEC {delta}")
        with self._cmd_lock:
            self._cmd_queue.append(("dec", float(delta)))

    @Slot(bool)
    def request_power(self, desired: bool):
        """
        Enqueue a power request.

        Args:
            desired: True to power on, False to power off.
        """
        with self._cmd_lock:
            self._cmd_queue.append(("power", bool(desired)))

    @Slot(bool)
    def request_mode(self, desired: bool):
        """
        Enqueue a mode toggle request.

        Args:
            desired: UI-provided boolean. In this code it acts as a "toggle intent"
                     rather than a strict target mode; the worker checks current
                     internal mode and flips accordingly.
        """
        with self._cmd_lock:
            self._cmd_queue.append(("mode", bool(desired)))
