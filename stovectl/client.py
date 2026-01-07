# =============================================================================
# StoveClient - HTTP CGI client for stove controller devices
# -----------------------------------------------------------------------------
# Copyright (c) Alejandro Feránandez Rodríguez. All rights reserved.
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
#  @author
#    Alejandro Fernández Rodríguez — github.com/afernandezLuc
#  @version 1.0.0
#  @date 2026-01-07
# =============================================================================

from __future__ import annotations

import time
from typing import Dict, Optional, Literal, Any

import requests
from requests.auth import HTTPBasicAuth, HTTPDigestAuth

from .exceptions import (
    StoveOperationError,
    StoveProtocolError,
    StoveTransportError,
)
from .models import StoveResponse


AuthMode = Literal["none", "basic", "digest"]


class StoveClient:
    """
    Minimal HTTP client to interact with a stove controller that exposes a CGI
    endpoint (commonly `/recepcion_datos_4.cgi`) accepting POST form data.

    This client focuses on:
      - Simple operations by sending `idOperacion=<int>`
      - Optional parameters for operations (e.g., `int_rx=<value>`)
      - Transport reliability (retries + delay)
      - Optional authentication:
          * none (default)
          * HTTP Basic
          * HTTP Digest
        and/or session cookies

    Typical device behavior:
      - The CGI returns a text body with lines like `key=value`
      - Some devices return an error/result code either as `error=<int>` or
        as a single numeric line.

    The parsing logic attempts to be tolerant to variations in key naming.
    """

    def __init__(
        self,
        base_url: str,
        cgi_path: str = "/recepcion_datos_4.cgi",
        timeout_s: float = 5.0,
        retries: int = 3,
        retry_delay_s: float = 2.1,
        auth_mode: AuthMode = "none",
        username: Optional[str] = None,
        password: Optional[str] = None,
        cookies: Optional[Dict[str, str]] = None,
        session: Optional[requests.Session] = None,
    ) -> None:
        """
        Create a StoveClient.

        Args:
            base_url:
                Base URL of the device, e.g. 'http://192.168.1.50' or
                'http://stove.local'. Trailing slashes are removed.
            cgi_path:
                Path to the CGI endpoint. If missing a leading '/', it is added.
            timeout_s:
                HTTP request timeout in seconds.
            retries:
                Number of attempts for transient transport errors (>= 1).
            retry_delay_s:
                Delay in seconds between retry attempts.
            auth_mode:
                Authentication mode: "none", "basic", or "digest".
            username:
                Username for basic/digest authentication.
            password:
                Password for basic/digest authentication.
            cookies:
                Optional cookie dict to be applied to the session
                (useful if the web UI requires a login session cookie).
            session:
                Optional preconfigured requests.Session. If not provided, a new
                session is created.

        Raises:
            ValueError:
                If auth_mode is unknown, or required credentials are missing.
        """
        self.base_url = base_url.rstrip("/")
        self.cgi_path = cgi_path if cgi_path.startswith("/") else "/" + cgi_path
        self.timeout_s = timeout_s
        self.retries = max(1, int(retries))
        self.retry_delay_s = float(retry_delay_s)

        self.session = session or requests.Session()

        # ---- Auth (Basic/Digest) ----
        self.auth_mode = auth_mode
        self.username = username
        self.password = password

        if auth_mode == "basic":
            if not username or password is None:
                raise ValueError("Basic auth requires username and password")
            self.session.auth = HTTPBasicAuth(username, password)

        elif auth_mode == "digest":
            if not username or password is None:
                raise ValueError("Digest auth requires username and password")
            self.session.auth = HTTPDigestAuth(username, password)

        elif auth_mode == "none":
            self.session.auth = None

        else:
            raise ValueError(f"Unknown auth_mode={auth_mode!r}")

        # ---- Cookies (if the web login uses a session cookie) ----
        if cookies:
            self.session.cookies.update(cookies)

    @property
    def endpoint(self) -> str:
        """
        Full endpoint URL to the CGI, derived from `base_url` and `cgi_path`.

        Returns:
            Full URL string, e.g. 'http://192.168.1.50/recepcion_datos_4.cgi'.
        """
        return f"{self.base_url}{self.cgi_path}"

    def send_operation(self, operation_id: int) -> StoveResponse:
        """
        Send an operation using only `idOperacion`.

        Args:
            operation_id: Operation identifier expected by the device firmware.

        Returns:
            Parsed StoveResponse containing:
              - operation_id
              - status_ok (boolean)
              - error_code (int or None)
              - params (parsed key/value lines)
              - lines (non-empty, stripped lines)
              - raw (original body text)

        Raises:
            StoveTransportError:
                On HTTP/transport issues after retries, or explicit 401.
            StoveProtocolError:
                If the response cannot be parsed into a coherent structure.
            StoveOperationError:
                If the device returns a non-zero error_code.
        """
        payload = {"idOperacion": str(int(operation_id))}

        last_exc: Optional[Exception] = None
        for attempt in range(1, self.retries + 1):
            try:
                r = self.session.post(
                    self.endpoint,
                    data=payload,
                    timeout=self.timeout_s,
                    allow_redirects=True,
                )

                # If the device redirects to or enforces auth, treat 401 explicitly.
                if r.status_code == 401:
                    raise StoveTransportError(
                        "401 Unauthorized. The device requires authentication. "
                        "Try auth_mode='basic' or 'digest', or provide session cookies."
                    )

                r.raise_for_status()

                raw = r.text
                resp = self._parse_response(operation_id, raw)

                # If the firmware provides an error code, enforce it.
                if resp.error_code is not None and resp.error_code != 0:
                    raise StoveOperationError(
                        f"Operation {operation_id} failed with error_code={resp.error_code}"
                    )

                return resp

            except StoveTransportError:
                # Already classified as transport; do not retry here unless you
                # explicitly want that behavior.
                raise

            except (requests.RequestException) as exc:
                last_exc = exc
                if attempt < self.retries:
                    time.sleep(self.retry_delay_s)
                    continue
                raise StoveTransportError(
                    f"HTTP error sending idOperacion={operation_id} to {self.endpoint}: {exc}"
                ) from exc

            except ValueError as exc:
                # Parsing or type conversion errors are treated as protocol errors.
                raise StoveProtocolError(f"Protocol error: {exc}") from exc

        # Defensive fallback: should not be reached.
        raise StoveTransportError(f"Unexpected transport error: {last_exc}")

    def send_operation_params(
        self,
        operation_id: int,
        extra: Optional[Dict[str, Any]] = None
    ) -> StoveResponse:
        """
        Send an operation including extra parameters in addition to `idOperacion`.

        This is a convenience method for operations that require additional form
        fields (e.g., setting a clock might require `int_rx=<unix_time>`).

        Args:
            operation_id: Operation identifier expected by the device firmware.
            extra:
                Optional dict of extra parameters. Values are converted to str.

        Returns:
            Parsed StoveResponse.

        Raises:
            StoveTransportError, StoveProtocolError, StoveOperationError:
                Same behavior as send_operation().
        """
        payload: Dict[str, str] = {"idOperacion": str(int(operation_id))}
        if extra:
            payload.update({k: str(v) for k, v in extra.items()})

        last_exc: Optional[Exception] = None
        for attempt in range(1, self.retries + 1):
            try:
                r = self.session.post(
                    self.endpoint,
                    data=payload,
                    timeout=self.timeout_s,
                    allow_redirects=True,
                )

                if r.status_code == 401:
                    raise StoveTransportError(
                        "401 Unauthorized. The device requires authentication. "
                        "Try auth_mode='basic' or 'digest', or provide session cookies."
                    )

                r.raise_for_status()

                raw = r.text
                resp = self._parse_response(operation_id, raw)

                if resp.error_code is not None and resp.error_code != 0:
                    raise StoveOperationError(
                        f"Operation {operation_id} failed with error_code={resp.error_code}"
                    )

                return resp

            except StoveTransportError:
                raise

            except (requests.RequestException) as exc:
                last_exc = exc
                if attempt < self.retries:
                    time.sleep(self.retry_delay_s)
                    continue
                raise StoveTransportError(
                    f"HTTP error sending idOperacion={operation_id} to {self.endpoint}: {exc}"
                ) from exc

            except ValueError as exc:
                raise StoveProtocolError(f"Protocol error: {exc}") from exc

        raise StoveTransportError(f"Unexpected transport error: {last_exc}")

    def _parse_response(self, operation_id: int, raw: str) -> StoveResponse:
        """
        Parse the raw CGI response into a StoveResponse.

        The function:
          1) Splits into non-empty lines
          2) Extracts key/value pairs for lines containing '='
          3) Tries to infer an integer error/result code from common keys
          4) If no key-based error code exists, tries to find a standalone
             integer line.

        Args:
            operation_id: Operation identifier originally sent.
            raw: Raw HTTP body text.

        Returns:
            StoveResponse object.

        Notes:
            - If no error code is found, `status_ok` defaults to True.
            - `params` contains only parsed key/value pairs.
            - `lines` contains all non-empty lines, stripped.

        Raises:
            ValueError:
                Only if integer conversion fails in a way that is not ignored.
                (Callers wrap this into StoveProtocolError.)
        """
        lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]

        # Parse key=value style lines
        params: Dict[str, str] = {}
        for ln in lines:
            if "=" in ln:
                k, v = ln.split("=", 1)
                k, v = k.strip(), v.strip()
                if k:
                    params[k] = v

        # Try to detect a numeric error code in common fields
        error_code = None
        for key in ("error", "err", "codigo", "code", "resultado", "result"):
            if key in params:
                try:
                    error_code = int(params[key])
                    break
                except ValueError:
                    # Ignore non-numeric values and keep searching
                    pass

        # Fallback: detect a standalone integer line
        if error_code is None:
            for ln in lines:
                if ln.isdigit() or (ln.startswith("-") and ln[1:].isdigit()):
                    error_code = int(ln)
                    break

        status_ok = (error_code == 0) if error_code is not None else True

        return StoveResponse(
            operation_id=operation_id,
            status_ok=status_ok,
            error_code=error_code,
            params=params,
            lines=lines,
            raw=raw,
        )
