# StoveClient Library

StoveClient is a lightweight Python library designed to communicate with
stove controller devices that expose an HTTP-CGI protocol. It provides a
reliable transport layer with retries, optional authentication (HTTP
Basic/Digest), and tolerant parsing of firmware responses.

## Features

-   Send simple operations using `idOperacion=<int>`
-   Support for additional parameters in POST requests
-   Automatic retries with configurable delay
-   Optional reverse DNS resolution
-   Cookie-based sessions for devices requiring web login
-   Clear classification of errors:
    -   **Transport** -- network, HTTP, timeouts, authentication
    -   **Protocol** -- unexpected or unparseable responses
    -   **Operation** -- device returned non-zero error code

## Installation

pip install stoveclient

## Quick Example

from stoveclient import StoveClient, StoveError

client = StoveClient("http://192.168.1.50", retries=3, timeout_s=5)

try: response = client.send_operation(1094) print(response.params)
except StoveError as exc: print(f"Stove error: {exc}")

## API Overview

### StoveClient

Main client class responsible for HTTP communication with the CGI
endpoint.

**Methods**

-   `send_operation(operation_id: int) -> StoveResponse`
-   `send_operation_params(operation_id: int, extra: Dict[str, Any]) -> StoveResponse`

### Models

#### StoveResponse

Container object holding all parsed information returned by the stove
firmware:

-   operation_id
-   status_ok
-   error_code
-   params
-   lines
-   raw

### Exceptions

-   StoveTransportError
-   StoveProtocolError
-   StoveOperationError

## Requirements

-   Python 3.9+
-   requests

The library assumes that nmap or a compatible stove firmware CGI is
reachable from the host running this code.

## GEL 3.0 License

### Disclaimer

This software is provided "AS IS", without warranty of any kind, express
or implied, including but not limited to the warranties of
merchantability, fitness for a particular purpose, and non-infringement.
In no event shall the authors be liable for any claim, damages, or other
liability arising from the use of this software.

A full copy of the GEL 3.0 License must accompany any redistribution. If
the license text is missing, see: https://gel-license.org
