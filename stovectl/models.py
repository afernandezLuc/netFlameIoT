# =============================================================================
# StoveClient Library – Response Model
# -----------------------------------------------------------------------------
# Copyright (c) Alejandro Feránandez Rodríguez. All rights reserved.
#
# This source code is released under the GEL 3.0 License.
#
# DISCLAIMER:
# This software is provided "AS IS", without warranty of any kind, express or
# implied, including but not limited to the warranties of merchantability,
# fitness for a particular purpose, and non-infringement. In no event shall the
# authors or copyright holders be liable for any claim, damages, or other
# liability, whether in an action of contract, tort, or otherwise, arising from,
# out of, or in connection with the software or the use or other dealings in
# the software.
#
# LICENSE – GEL 3.0:
# You may use, copy, modify, and distribute this code according to the terms of
# the GEL 3.0 License. A full copy of the license text should accompany any
# redistribution. If the license text is missing, see: https://gel-license.org
#  @author
#    Alejandro Fernández Rodríguez — github.com/afernandezLuc
#  @version 1.0.0
#  @date 2026-01-07
# =============================================================================

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass(frozen=True)
class StoveResponse:
    """
    Immutable representation of a CGI response returned by the stove controller.

    Attributes:
        operation_id:
            Identifier of the operation that generated this response. This is the
            same value that was sent to the device using the `idOperacion` field.

        status_ok:
            Boolean flag indicating whether the operation succeeded. It is
            typically derived from `error_code == 0`, but may remain True when
            the firmware does not provide an explicit error code.

        error_code:
            Optional integer error/result code returned by the device firmware.
            A value of 0 means success; any other value indicates a device-level
            rejection or failure.

        params:
            Dictionary containing all parsed `key=value` lines from the CGI body.
            Values are preserved as strings exactly as received.

        lines:
            List of non-empty, stripped text lines from the raw response. This is
            useful for debugging or for tolerant parsing of legacy firmware.

        raw:
            Original unmodified text body returned by the CGI endpoint.
    """

    operation_id: int
    status_ok: bool
    error_code: Optional[int]
    params: Dict[str, str]
    lines: List[str]
    raw: str
