# =============================================================================
# Network LAN Scanner Library
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

import re
import socket
import subprocess
from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any, List


@dataclass
class Device:
    """
    Representation of a device discovered on the LAN.

    Attributes:
        ip: IPv4 address of the device.
        nmap_name: Optional host name as reported by nmap.
        mac: Optional MAC address.
        vendor: Optional vendor string from MAC OUI (as shown by nmap).
        rdns: Optional reverse DNS name if resolution is enabled.
    """
    ip: str
    nmap_name: Optional[str] = None
    mac: Optional[str] = None
    vendor: Optional[str] = None
    rdns: Optional[str] = None


class LanScanError(RuntimeError):
    """
    Custom error type used to signal failures during network scanning.
    """
    pass


def _run(cmd: List[str]) -> str:
    """
    Execute an external command and return its output as text.

    Args:
        cmd: Command and arguments to execute.

    Returns:
        The stdout produced by the command.

    Raises:
        subprocess.CalledProcessError if execution fails.
    """
    return subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL)


def _reverse_dns(ip: str) -> Optional[str]:
    """
    Attempt to resolve an IP address using reverse DNS.

    Args:
        ip: IPv4 address to resolve.

    Returns:
        Host name if available, otherwise None.
    """
    try:
        name, _, _ = socket.gethostbyaddr(ip)
        return name
    except Exception:
        return None


def _parse_nmap_sn(output: str) -> List[Device]:
    """
    Parse the output of 'nmap -sn' in order to build a list of Device objects.

    The parser walks through the text line by line, detecting:
      - start of a new device block (Nmap scan report for ...)
      - MAC address lines (MAC Address: ...)

    Args:
        output: Raw text returned by nmap.

    Returns:
        Sorted list of discovered devices with available metadata.
    """
    devices: List[Device] = []
    current: Optional[Device] = None

    for line in output.splitlines():
        line = line.strip()

        # Detect the beginning of a new scan report block
        m = re.match(r"^Nmap scan report for (.+)$", line)
        if m:
            if current:
                devices.append(current)

            target = m.group(1)

            # Format: "name (ip)"
            m2 = re.match(r"^(.*)\s+\((\d+\.\d+\.\d+\.\d+)\)$", target)
            if m2:
                current = Device(ip=m2.group(2), nmap_name=m2.group(1))

            # Format: just an IP
            else:
                m3 = re.match(r"^(\d+\.\d+\.\d+\.\d+)$", target)
                if m3:
                    current = Device(ip=m3.group(1))

                # Format: hostname that needs to be resolved to IP
                else:
                    try:
                        ip = socket.gethostbyname(target)
                        current = Device(ip=ip, nmap_name=target)
                    except Exception:
                        current = Device(ip="")

            continue

        # Detect MAC address metadata
        m = re.match(
            r"^MAC Address:\s+([0-9A-Fa-f:]{17})\s+\((.*)\)$",
            line
        )
        if m and current:
            current.mac = m.group(1).upper()
            current.vendor = m.group(2)

    # Append last device if present
    if current:
        devices.append(current)

    # Remove entries without valid IP
    devices = [d for d in devices if d.ip]

    # Helper used to sort IPs numerically
    def ip_key(ip: str):
        return [int(x) for x in ip.split(".")]

    devices.sort(key=lambda d: ip_key(d.ip))
    return devices


def scan_network(
    cidr: str,
    *,
    use_sudo: bool = True,
    resolve_rdns: bool = False,
    nmap_path: str = "nmap",
    timeout_seconds: Optional[int] = None,
) -> Dict[str, Dict[str, Any]]:
    """
    Scan a network range using 'nmap -sn' and return a dictionary indexed by IP.

    Args:
        cidr: CIDR range to scan, e.g. '192.168.68.0/24'.
        use_sudo: If True, try 'sudo -n' to run without password prompt.
        resolve_rdns: If True, perform reverse DNS resolution for each device.
        nmap_path: Path or command name of nmap.
        timeout_seconds: Optional timeout for nmap execution.

    Returns:
        Dictionary with structure:
        {
          "192.168.68.1": { ... device fields ... },
          ...
        }

    Raises:
        LanScanError if nmap cannot be executed or no devices are found.
    """
    cmd = [nmap_path, "-sn", cidr]

    output = None
    last_err = None

    # Try execution with sudo first if requested
    if use_sudo:
        try:
            output = subprocess.check_output(
                ["sudo", "-n", *cmd],
                text=True,
                stderr=subprocess.DEVNULL,
                timeout=timeout_seconds,
            )
        except Exception as e:
            last_err = e

    # Fallback: run without sudo
    if output is None:
        try:
            output = subprocess.check_output(
                cmd,
                text=True,
                stderr=subprocess.DEVNULL,
                timeout=timeout_seconds,
            )
        except Exception as e:
            raise LanScanError(
                f"Unable to execute nmap. Error: {e}"
            ) from e

    devices = _parse_nmap_sn(output)

    # Optional reverse DNS enrichment
    if resolve_rdns:
        for d in devices:
            d.rdns = _reverse_dns(d.ip)

    # Build final dictionary
    result: Dict[str, Dict[str, Any]] = {}
    for d in devices:
        result[d.ip] = asdict(d)

    # Validate that we have at least one device
    if not result:
        msg = "nmap did not return any devices."
        if last_err:
            msg += f" (sudo attempt failed: {last_err})"
        raise LanScanError(msg)

    return result
