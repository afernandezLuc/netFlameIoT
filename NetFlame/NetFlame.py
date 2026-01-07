# =============================================================================
# NetFlame - High-level Stove API built on top of StoveClient
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
from datetime import datetime, timezone

from stovectl.client import StoveClient
from stovectl.exceptions import StoveOperationError

from .models import *  # noqa: F403
# NOTE:
# This module expects your package to provide, at least:
#   - Alarms
#   - Stove_State
#   - Stove_Public_State (enum)
#   - Operative_Mode
#   - Hora
#   - Stove_Data
#
# They are imported from .models to keep the public API concise.


class NetFlame(StoveClient):
    """
    High-level client specialized for NetFlame-like stove controllers.

    `NetFlame` extends :class:`stovectl.client.StoveClient` by providing typed
    convenience methods for the common operations exposed by the device CGI.

    Operation codes are device-specific numeric IDs (idOperacion) that instruct
    the stove firmware to return or modify internal state.
    """

    # ---- Read operations (idOperacion) ----
    GET_HOUR_OP_CODE = 1094
    GET_LANGUAGE_OP_CODE = 1090
    GET_ALARMS_OP_CODE = 1079
    GET_STOVE_OP_CODE = 1100
    GET_HEATER_OP_CODE = 1102
    GET_OPERATIVE_MODE_OP_CODE = 1071
    GET_DATA_OP_CODE = 1002

    # ---- Write operations (idOperacion) ----
    SET_HOUR_OP_CODE = 1095

    def _return_alarma(self, alarmCode: str) -> Alarms:  # noqa: N802
        """
        Convert a device alarm code into an `Alarms` model with a human-readable
        description.

        Args:
            alarmCode: Alarm code string returned by the stove firmware.

        Returns:
            Alarms instance with the code and description.
        """
        if alarmCode == "N":
            return Alarms(code=alarmCode, description="No hay alarmas")
        elif alarmCode == "A000":
            return Alarms(code=alarmCode, description="Estufa apagada con alarma")
        elif alarmCode == "A001":
            return Alarms(code=alarmCode, description="Depresion entrada de aire baja")
        elif alarmCode == "A002":
            return Alarms(code=alarmCode, description="Depresion entrada de aire alta")
        elif alarmCode == "A003":
            return Alarms(code=alarmCode, description="Temperatura salida de gases baja")
        elif alarmCode == "A004":
            return Alarms(code=alarmCode, description="Temperatura salida de gases alta")
        elif alarmCode == "A005":
            return Alarms(code=alarmCode, description="Temperatura sonda NTC baja")
        elif alarmCode == "A006":
            return Alarms(code=alarmCode, description="Temperatura sonda NTC alta")
        elif alarmCode == "A009":
            return Alarms(code=alarmCode, description="Temperatura ambiente baja")
        elif alarmCode == "A010":
            return Alarms(code=alarmCode, description="Temperatura ambiente alta")
        elif alarmCode == "A011":
            return Alarms(code=alarmCode, description="Temperatura CPU baja")
        elif alarmCode == "A012":
            return Alarms(code=alarmCode, description="Temperatura CPU alta")
        elif alarmCode == "A013":
            return Alarms(code=alarmCode, description="Corriente motores baja")
        elif alarmCode == "A014":
            return Alarms(code=alarmCode, description="Corriente motores alta")
        elif alarmCode == "A015":
            return Alarms(code=alarmCode, description="Depresion entrada de aire baja")
        elif alarmCode == "A016":
            return Alarms(code=alarmCode, description="Temperatura salida de gases muy alta")
        elif alarmCode == "A017":
            return Alarms(code=alarmCode, description="Temperatura sonda NTC muy alta")
        elif alarmCode == "A018":
            return Alarms(code=alarmCode, description="Fallo ventilador de humos")
        elif alarmCode == "A019":
            return Alarms(code=alarmCode, description="Ventilador a capacidad maxima")
        elif alarmCode == "A020":
            return Alarms(code=alarmCode, description="Error en sondas")
        elif alarmCode == "A099":
            return Alarms(code=alarmCode, description="Estufa sin combustible")
        else:
            return Alarms(code=alarmCode, description="Alarma desconocida")

    def _return_state(self, state: int) -> Stove_State:
        """
        Convert the raw firmware state integer into a structured `Stove_State`
        that includes:
          - a human-readable description
          - a normalized public state enum

        Args:
            state: Raw integer reported by the device.

        Returns:
            Stove_State instance.
        """
        if state == -1:
            return Stove_State(state=state, description="Error obteniendo estado", publicState=Stove_Public_State.INVALID_STATE)
        elif state == 0:
            return Stove_State(state=state, description="Apagado", publicState=Stove_Public_State.POWER_OFF)
        elif state == 1 or state == 2 or state == 3 or state == 4 or state == 10:
            return Stove_State(state=state, description="Precalentamiento", publicState=Stove_Public_State.PREHEAT)
        elif state == 5 or state == 6:
            return Stove_State(state=state, description="Inicio de combustión", publicState=Stove_Public_State.HEATING)
        elif state == 7:
            return Stove_State(state=state, description="Estufa en marcha", publicState=Stove_Public_State.POWERED_ON)
        elif state == 8 or state == 11 or state == -3:
            return Stove_State(state=state, description="Apagando estufa", publicState=Stove_Public_State.WAINTING_FOR_POWER_OFF)
        elif state == -20:
            return Stove_State(state=state, description="A la espera de carga de programa", publicState=Stove_Public_State.WAITING_FOR_PROGRAM_LOAD)
        elif state == -4:
            return Stove_State(state=state, description="Estufa en alarma", publicState=Stove_Public_State.ERROR_STATE)
        else:
            return Stove_State(state=state, description="Estado desconocido", publicState=Stove_Public_State.INVALID_STATE)

    def _return_operative_mode(self, mode: int) -> Operative_Mode:
        """
        Map the raw operational mode code to an `Operative_Mode` model.

        Args:
            mode: Raw mode integer returned by the device.

        Returns:
            Operative_Mode instance.
        """
        if mode == 0:
            return Operative_Mode(mode=mode, description="Modo pontencia")
        elif mode == 1:
            return Operative_Mode(mode=mode, description="Modo Temperatura Ambiente")
        elif mode == -1:
            return Operative_Mode(mode=mode, description="Error retriving data")
        else:
            return Operative_Mode(mode=mode, description="Modo Emergencia")

    def get_hour(self) -> Hora:
        """
        Query the stove internal clock.

        The firmware returns a Unix epoch timestamp (UTC) in the `int_rx` field.

        Returns:
            Hora model with hour, minute, and formatted HH:MM string.

        Raises:
            StoveOperationError:
                If `int_rx` is missing in the response payload.
            StoveTransportError / StoveProtocolError:
                Raised by the parent client when request/parse fails.
        """
        resp = self.send_operation(self.GET_HOUR_OP_CODE)

        unix_time = resp.params.get("int_rx")
        if not unix_time:
            raise StoveOperationError(f"int_rx not present in response: {resp.raw}")

        dt = datetime.fromtimestamp(int(unix_time), tz=timezone.utc)
        return Hora(dt.hour, dt.minute, dt.strftime("%H:%M"))

    def get_language(self) -> int:
        """
        Read the configured device language.

        Returns:
            Integer language code (firmware-specific).
        """
        resp = self.send_operation(self.GET_LANGUAGE_OP_CODE)
        return int(resp.params.get("idioma", "0"))

    def get_alarms(self) -> Alarms:
        """
        Query the current stove alarm state.

        Returns:
            Alarms model with code and description.
        """
        resp = self.send_operation(self.GET_ALARMS_OP_CODE)
        return self._return_alarma(resp.params.get("get_alarmas", "N"))

    def get_stove_type(self) -> int:
        """
        Query the stove type identifier.

        Returns:
            Integer stove type (firmware-specific).
        """
        resp = self.send_operation(self.GET_STOVE_OP_CODE)
        return int(resp.params.get("tipoestufa", "0"))

    def get_heater_type(self) -> int:
        """
        Query the heater/water system type identifier.

        Returns:
            Integer heater type (firmware-specific).
        """
        resp = self.send_operation(self.GET_HEATER_OP_CODE)
        return int(resp.params.get("tipo_agua", "0"))

    def get_operation_mode(self) -> Operative_Mode:
        """
        Query the stove configured operation mode (power vs ambient temperature, etc.).

        Returns:
            Operative_Mode model derived from `modo_operacion`.
        """
        resp = self.send_operation(self.GET_OPERATIVE_MODE_OP_CODE)
        return self._return_operative_mode(int(resp.params.get("modo_operacion", "-1")))

    def get_data(self) -> Stove_Data:
        """
        Query the main device telemetry/state snapshot.

        This reads operation 1002 and builds a `Stove_Data` model containing:
          - power on/off
          - operative mode + derived functional mode
          - setpoints (power/temperature)
          - current temperature
          - internal state mapped to public state

        Returns:
            Stove_Data instance.
        """
        resp = self.send_operation(self.GET_DATA_OP_CODE)

        mode = int(resp.params.get("modo_operacion", "-1"))
        if mode == 1:
            funcMode = int(resp.params.get("modo_func", "-1"))
            if funcMode == 1:
                functionalMode = Operative_Mode(mode=funcMode, description="Modo Temperatura Ambiente")
            elif funcMode == -1:
                functionalMode = Operative_Mode(mode=funcMode, description="Error retriving data")
            else:
                functionalMode = Operative_Mode(mode=funcMode, description="Modo Potencia")
        elif mode == -1:
            functionalMode = Operative_Mode(mode=-1, description="Error retriving data")
        else:
            functionalMode = Operative_Mode(mode=0, description="Modo Potencia")

        return Stove_Data(
            statusOn=(resp.params.get("on_off", "0") == "1"),
            operativeMode=self._return_operative_mode(mode),
            functionalMode=functionalMode,
            powerSetpoint=int(resp.params.get("consigna_potencia", "0")),
            temperatureSetpoint=float(resp.params.get("consigna_temperatura", "0")),
            currentTemperature=float(resp.params.get("temperatura", "0")),
            state=self._return_state(int(resp.params.get("estado", "-1"))),
        )

    def set_hour_now(self) -> Hora:
        """
        Set the device clock to the current UTC time and then read it back.

        The device expects an epoch timestamp sent as `int_rx` with operation 1095.
        This method emulates the behavior seen in the web UI JavaScript:
          - Send SET_HOUR operation with epoch seconds
          - Read the hour again and return the parsed value

        Returns:
            Hora reported by the stove after setting the clock.
        """
        epoch_seconds = int(datetime.now(tz=timezone.utc).timestamp())

        # Use parent's param-aware method so we can send int_rx.
        _ = self.send_operation_params(self.SET_HOUR_OP_CODE, {"int_rx": epoch_seconds})

        # Web UI logic: regardless of return value, read back the hour.
        return self.get_hour()
