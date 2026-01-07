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
from zoneinfo import ZoneInfo

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
    SET_ON_OFF_OP_CODE = 1013
    SET_TEMPERATURE_OP_CODE = 1019
    SET_POWER_OP_CODE = 1004
    SET_OPERATIVE_MODE_OP_CODE = 1081

    def __init__(
            self,
            base_url: str,
            username: str,
            password: str,
            auth_mode: str = "basic"
    ):
        self._stoveInternalState = -1
        self._stoveInternalOperativeMode = -1
        super().__init__(base_url = base_url, username=username, password=password, auth_mode=auth_mode)

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
            return Operative_Mode(mode=mode, description="Potencia")
        elif mode == 1:
            return Operative_Mode(mode=mode, description="Temperatura")
        elif mode == -1:
            return Operative_Mode(mode=mode, description="Error")
        else:
            return Operative_Mode(mode=mode, description="Emergencia")

    def get_hour(self) -> Hora:
        """
        Query the stove internal clock.

        The firmware returns a Unix epoch timestamp (UTC) in the `int_rx` field.
        This method converts it to Madrid timezone before building the model.

        Returns:
            Hora model with hour, minute, formatted HH:MM string and date (Madrid TZ).

        Raises:
            StoveOperationError:
                If `int_rx` is missing in the response payload.
            StoveTransportError / StoveProtocolError:
                Raised by the parent client when request/parse fails.
        """
        resp = self.send_operation(self.GET_HOUR_OP_CODE)

        unix_time = resp.params.get("int_rx")
        if unix_time is None:
            raise StoveOperationError(f"int_rx not present in response: {resp.raw}")

        try:
            dt_utc = datetime.fromtimestamp(int(unix_time), tz=timezone.utc)

            # --- conversión a Madrid ---
            dt_madrid = dt_utc.astimezone(ZoneInfo("Europe/Madrid"))

        except Exception as e:
            raise StoveOperationError(f"invalid unix timestamp: {unix_time}") from e

        return Hora(
            dt_madrid.hour,
            dt_madrid.minute,
            dt_madrid.strftime("%H:%M"),
            dt_madrid.strftime("%d %B %Y")
        )


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
                functionalMode = Operative_Mode(mode=funcMode, description="Temperatura")
            elif funcMode == -1:
                functionalMode = Operative_Mode(mode=funcMode, description="Error")
            else:
                functionalMode = Operative_Mode(mode=funcMode, description="Potencia")
        elif mode == -1:
            functionalMode = Operative_Mode(mode=-1, description="Error")
        else:
            functionalMode = Operative_Mode(mode=0, description="Potencia")
        self._stoveInternalState = int(resp.params.get("estado", "-1"))
        self._stoveInternalOperativeMode = mode
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
    
    def power_on(self) -> None:
        """
        Power on the stove by setting the power mode to ON (1).

        Raises:
            StoveOperationError:
                If the operation fails or the stove does not acknowledge.
            StoveTransportError / StoveProtocolError:
                Raised by the parent client when request/parse fails.
        """
        self.get_data()  # Refresh internal state
        if self._stoveInternalState == 0:
            self.send_operation_params(self.SET_ON_OFF_OP_CODE, {"on_off": 1})
    def power_off(self) -> None:
        """
        Power off the stove by setting the power mode to OFF (0).

        Raises:
            StoveOperationError:
                If the operation fails or the stove does not acknowledge.
            StoveTransportError / StoveProtocolError:
                Raised by the parent client when request/parse fails.
        """
        self.get_data()  # Refresh internal state
        if self._stoveInternalState == 7:
            self.send_operation_params(self.SET_ON_OFF_OP_CODE, {"on_off": 0})
    
    def _set_temperature(self, temperature: float) -> None:
        """
        Set the temperature setpoint.

        Args:
            temperature: The desired temperature in degrees Celsius.

        Raises:
            StoveOperationError:
                If the operation fails or the stove does not acknowledge.
            StoveTransportError / StoveProtocolError:
                Raised by the parent client when request/parse fails.
        """
        self.send_operation_params(self.SET_TEMPERATURE_OP_CODE, {"temperatura": temperature})
    
    def _set_power(self, power: int) -> None:
        """
        Set the power setpoint.

        Args:
            power: The desired power level (firmware-specific scale).

        Raises:
            StoveOperationError:
                If the operation fails or the stove does not acknowledge.
            StoveTransportError / StoveProtocolError:
                Raised by the parent client when request/parse fails.
        """
        self.send_operation_params(self.SET_POWER_OP_CODE, {"potencia": power})
    
    def increase_temperature(self, delta: float = 0.1) -> None:
        """
        Increase the temperature setpoint by a given delta.

        Args:
            delta: The amount to increase the temperature by in degrees Celsius.

        Raises:
            StoveOperationError:
                If the operation fails or the stove does not acknowledge.
            StoveTransportError / StoveProtocolError:
                Raised by the parent client when request/parse fails.
        """
        data = self.get_data()
        new_temp = data.temperatureSetpoint + delta
        if new_temp > 40:
            new_temp = 40
        self._set_temperature(new_temp)
    def decrease_temperature(self, delta: float = 0.1) -> None:
        """
        Decrease the temperature setpoint by a given delta.
        Args:
            delta: The amount to decrease the temperature by in degrees Celsius.
        Raises:
            StoveOperationError:
                If the operation fails or the stove does not acknowledge.
            StoveTransportError / StoveProtocolError:
                Raised by the parent client when request/parse fails.
        """
        data = self.get_data()
        new_temp = data.temperatureSetpoint - delta
        if new_temp < 12:
            new_temp = 12
        self._set_temperature(new_temp)
    
    def increase_power(self) -> None:
        """
        Increase the power setpoint by 1 unit.

        Raises:
            StoveOperationError:
                If the operation fails or the stove does not acknowledge.
            StoveTransportError / StoveProtocolError:
                Raised by the parent client when request/parse fails.
        """
        data = self.get_data()
        new_power = data.powerSetpoint + 1
        if new_power > 9:
            new_power = 9
        self._set_power(new_power)
    def decrease_power(self) -> None:
        """
        Decrease the power setpoint by 1 unit.
        Raises:
            StoveOperationError:
                If the operation fails or the stove does not acknowledge.
            StoveTransportError / StoveProtocolError:
                Raised by the parent client when request/parse fails.
        """
        data = self.get_data()
        new_power = data.powerSetpoint - 1
        if new_power < 1:
            new_power = 1
        self._set_power(new_power)
    def _set_operative_mode(self, mode: int) -> None:
        """
        Set the stove operative mode.

        Args:
            mode: The desired operative mode (0=Power, 1=Temperature, 2=Emergency).

        Raises:
            StoveOperationError:
                If the operation fails or the stove does not acknowledge.
            StoveTransportError / StoveProtocolError:
                Raised by the parent client when request/parse fails.
        """
        if mode not in [0, 1, 2]:
            raise ValueError(f"Invalid operative mode: {mode}")
        if self._stoveInternalOperativeMode != mode and self._stoveInternalOperativeMode != -1:
            self.send_operation_params(self.SET_OPERATIVE_MODE_OP_CODE, {"modo_operacion": mode})
        
    def set_power_mode(self) -> None:
        """
        Set the stove to Power operative mode (0).

        Raises:
            StoveOperationError:
                If the operation fails or the stove does not acknowledge.
            StoveTransportError / StoveProtocolError:
                Raised by the parent client when request/parse fails.
        """
        self.get_data()  # Refresh internal state
        self._set_operative_mode(0)
    def set_temperature_mode(self) -> None:
        """
        Set the stove to Temperature operative mode (1).
        Raises:
            StoveOperationError:
                If the operation fails or the stove does not acknowledge.
            StoveTransportError / StoveProtocolError:
                Raised by the parent client when request/parse fails.
        """
        self.get_data()  # Refresh internal state
        self._set_operative_mode(1)
    def set_emergency_mode(self) -> None:
        """
        Set the stove to Emergency operative mode (2).
        Raises:
            StoveOperationError:
                If the operation fails or the stove does not acknowledge.
            StoveTransportError / StoveProtocolError:
                Raised by the parent client when request/parse fails.
        """
        self.get_data()  # Refresh internal state
        self._set_operative_mode(2)