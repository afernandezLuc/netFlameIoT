# LAN Scanner Library

The **LAN Scanner** is a small Python utility library that performs host
discovery on local IPv4 networks using the external tool **nmap -sn**.

It provides a clean Python API that returns structured information about
the devices found on the network, including:

-   Host name reported by nmap\
-   MAC address (if available)\
-   Vendor string from OUI database\
-   Optional reverse DNS resolution

## Main Goals

-   Offer a reusable and scriptable interface for LAN discovery\
-   Hide subprocess invocation details\
-   Provide deterministic IP sorting\
-   Classify failures with clear English exceptions

## Installation

The package does not require special dependencies other than:

-   Python 3.9+\
-   nmap installed on the host\
-   Optional sudo privileges for enhanced ARP discovery

## Quick Example

``` python
from lanscanner import scan_network, LanScanError

try:
    devices = scan_network("192.168.68.0/24")
    for ip, info in devices.items():
        print(ip, info.get("mac"), info.get("vendor"))
except LanScanError as exc:
    print("Scan failed:", exc)
```

## Architecture Overview

### Device Model

Each discovered host is represented internally by the `Device` dataclass
which holds:

-   `ip: str`\
-   `nmap_name: Optional[str]`\
-   `mac: Optional[str]`\
-   `vendor: Optional[str]`\
-   `rdns: Optional[str]`

### Error Classification

The library defines:

-   **LanScanError** -- base error for scanning\
-   **Transport errors** -- nmap not executable, HTTP/network issues\
-   **Protocol errors** -- unexpected output format\
-   **Operation errors** -- no devices returned

## Limitations

-   This library is only a wrapper around nmap; it does not implement
    raw ARP or ICMP itself.\
-   Accuracy depends on the nmap binary and system network
    configuration.

## GEL 3.0 License

### Disclaimer

This software is provided **"AS IS"**, without warranty of any kind,
express or implied, including but not limited to the warranties of
merchantability, fitness for a particular purpose, and non‑infringement.
In no event shall the authors be liable for any claim, damages, or other
liability arising from the use of this software.

A full copy of the **GEL 3.0 License** must accompany any
redistribution.\
If the license text is missing, see: https://gel-license.org
