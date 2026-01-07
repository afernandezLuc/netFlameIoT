# =============================================================================
# stoveApp – Main application entry point
# -----------------------------------------------------------------------------
# Copyright (c) Alejandro Fernández Rodríguez
#
# This source code is released under the GEL 3.0 License.
#
# DISCLAIMER:
# This program is provided "AS IS", without warranty of any kind, express or
# implied, including but not limited to the warranties of merchantability,
# fitness for a particular purpose, and non-infringement. In no event shall the
# authors be liable for any claim, damages, or other liability arising from,
# out of, or in connection with the use of this software.
#
# LICENSE – GEL 3.0:
# You may use, copy, modify, and distribute this code according to the terms of
# the GEL 3.0 License. A full copy of the license text must accompany any
# redistribution. If the license text is missing, see: https://gel-license.org
# @author
#    Alejandro Fernández Rodríguez — github.com/afernandezLuc
#  @version 1.0.0
#  @date 2026-01-07
# =============================================================================

from __future__ import annotations

import os
import sys

# ---------------------------------------------------------------------------
# Project root discovery
# ---------------------------------------------------------------------------
# 1) __file__ points to: .../netFlameIoT/stoveApp/main.py
# 2) The real project root is two levels above: .../netFlameIoT
#
# The root is inserted at the beginning of sys.path so that local packages
# (stovectl, ui, net, etc.) have priority over any globally installed modules.
# ---------------------------------------------------------------------------

PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QThread

# Local application modules
from ui import MainWindow
from net import StoveWorker


def main():
    """
    Application bootstrap function.

    Responsibilities:
        - Create the Qt application instance.
        - Instantiate and show the main window.
        - Launch the StoveWorker in a separate QThread.
        - Wire all signals between the UI and the worker.
        - Perform deterministic cleanup on exit.

    The worker thread model follows the standard Qt pattern:
        QObject (StoveWorker)  --moved-->  QThread
    """

    app = QApplication(sys.argv)

    # -------------------------------------------------------------------
    # UI initialization
    # -------------------------------------------------------------------
    w = MainWindow()
    w.showMaximized()

    # -------------------------------------------------------------------
    # Worker in background thread
    # -------------------------------------------------------------------
    worker = StoveWorker()

    # Simple logging to stdout via print
    worker.log.connect(print)

    th = QThread()
    worker.moveToThread(th)

    # Start operation when thread begins
    th.started.connect(worker.start)

    # -------------------------------------------------------------------
    # Worker -> UI signals
    # -------------------------------------------------------------------
    worker.connected.connect(w.set_connected)
    worker.disconnected.connect(w.set_disconnected)
    worker.snapshot.connect(w.update_snapshot)

    # -------------------------------------------------------------------
    # UI -> Worker requests
    # -------------------------------------------------------------------
    w.incTemp.connect(worker.request_increase_temp)
    w.decTemp.connect(worker.request_decrease_temp)
    w.togglePower.connect(worker.request_power)
    w.changeModeRequested.connect(worker.request_mode)

    # Placeholder for zone change – not implemented yet
    w.changeZone.connect(lambda n: None)

    # Another placeholder that emulates legacy interface
    w.changeZone.connect(lambda n: None)

    # -------------------------------------------------------------------
    # Thread start
    # -------------------------------------------------------------------
    th.start()

    code = app.exec()

    # -------------------------------------------------------------------
    # Cleanup sequence
    # -------------------------------------------------------------------
    worker.stop()
    th.quit()
    th.wait(2000)

    sys.exit(code)


if __name__ == "__main__":
    main()
