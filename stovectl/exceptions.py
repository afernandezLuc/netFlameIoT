# =============================================================================
# StoveClient Library – Exceptions Module
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


class StoveError(Exception):
    """
    Base exception for the library.

    All custom exceptions of the StoveClient library inherit from this class so
    that callers can catch `StoveError` to handle any library-specific failure
    in a generic way.
    """
    pass


class StoveTransportError(StoveError):
    """
    Errors related to the transport layer.

    This includes problems such as:
      - Network unreachable
      - HTTP errors
      - Request timeouts
      - Authentication failures (e.g., HTTP 401)
    """
    pass


class StoveProtocolError(StoveError):
    """
    The response returned by the stove controller cannot be parsed or does not
    follow the expected CGI format.

    Raised when:
      - The body text contains an unexpected structure
      - Key/value pairs are missing or malformed
      - The firmware returns data that the client does not understand
    """
    pass


class StoveOperationError(StoveError):
    """
    The stove controller explicitly responded with a non-zero error code for
    the requested operation.

    This indicates that the command was delivered correctly but the device
    rejected it or was unable to execute it at the application level.
    """
    pass
