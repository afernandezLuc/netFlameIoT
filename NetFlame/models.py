# =============================================================================
# StoveClient / NetFlame – Models
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

from enum import Enum
from dataclasses import dataclass


class Stove_Public_State(Enum):
    """
    Normalized/public stove states.

    This enum maps the vendor-specific internal state codes into a stable set
    of "public" states that are easier to use in UIs, automations, or APIs.

    Values are intentionally numeric for easy serialization.
    """

    POWER_OFF = 0
    PREHEAT = 1
    HEATING = 2
    POWERED_ON = 3
    WAINTING_FOR_POWER_OFF = 4  # NOTE: kept as-is for backward compatibility
    WAITING_FOR_PROGRAM_LOAD = 5
    ERROR_STATE = 6
    INVALID_STATE = 7


@dataclass(frozen=True)
class Hora:
    """
    Stove clock representation.

    Attributes:
        hh: Hour component (0-23).
        mm: Minute component (0-59).
        raw: Human-friendly representation (e.g., "14:07") or any original
             string representation kept for display/logging.
    """

    hh: int
    mm: int
    raw: str


@dataclass(frozen=True)
class Alarms:
    """
    Current alarm status.

    Attributes:
        code: Alarm code returned by the stove firmware (e.g., "A001", "N").
        description: Human-readable alarm explanation.
    """

    code: str
    description: str


@dataclass(frozen=True)
class Operative_Mode:
    """
    Operational mode configuration.

    The meaning of `mode` is firmware-specific, but commonly:
      - 0: Power mode
      - 1: Ambient temperature mode

    Attributes:
        mode: Raw integer mode code.
        description: Human-readable description of the mode.
    """

    mode: int
    description: str


@dataclass(frozen=True)
class Stove_State:
    """
    Detailed state returned by the stove controller.

    Attributes:
        state: Raw firmware state integer.
        description: Human-readable state label (may be localized).
        publicState: Normalized public state derived from `state`.
    """

    state: int
    description: str
    publicState: Stove_Public_State


@dataclass(frozen=True)
class Stove_Data:
    """
    Snapshot of stove telemetry/state returned by the device.

    This model is typically built from the response of an operation like
    `GET_DATA_OP_CODE` and includes the most relevant information for an app/UI.

    Attributes:
        statusOn: True if the stove reports it is ON (e.g., on_off == "1").
        operativeMode: Primary mode reported by the device (power/temperature).
        functionalMode: Secondary/derived mode (may depend on other fields).
        state: Current stove state (raw + normalized public state).
        powerSetpoint: Requested power setpoint (unit/scale firmware-specific).
        temperatureSetpoint: Requested temperature setpoint (°C).
        currentTemperature: Current measured temperature (°C).
    """

    statusOn: bool
    operativeMode: Operative_Mode
    functionalMode: Operative_Mode
    state: Stove_State
    powerSetpoint: int
    temperatureSetpoint: float
    currentTemperature: float
