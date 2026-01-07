# stoveApp/main.py
from __future__ import annotations

import os
import sys

# 1) __file__ = .../netFlameIoT/stoveApp/main.py
# 2) PROJECT_ROOT = .../netFlameIoT
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Inserta al inicio para que tenga prioridad
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)




import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QThread

from ui import MainWindow
from net import StoveWorker


def main():
    app = QApplication(sys.argv)

    w = MainWindow()
    w.showMaximized()

    # Worker en thread aparte
    worker = StoveWorker()
    worker.log.connect(print)
    th = QThread()
    worker.moveToThread(th)

    th.started.connect(worker.start)

    # Señales worker -> UI
    worker.connected.connect(w.set_connected)
    worker.disconnected.connect(w.set_disconnected)
    worker.snapshot.connect(w.update_snapshot)

    w.incTemp.connect(worker.request_increase_temp)
    w.decTemp.connect(worker.request_decrease_temp)
    w.togglePower.connect(worker.request_power)
    w.changeModeRequested.connect(worker.request_mode)

    w.changeZone.connect(lambda n: None)

    th.start()

    code = app.exec()

    # Cleanup
    worker.stop()
    th.quit()
    th.wait(2000)

    sys.exit(code)


if __name__ == "__main__":
    main()
