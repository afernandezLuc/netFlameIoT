# NetFlame Stove Controller

Python application to **discover and control a NetFlame IoT stove** from
a local area network.\
The program locates the device by its reference MAC address, establishes
an authenticated HTTP connection, and starts real‑time polling to
display the device state in a Qt interface built with PySide6.

## Important

This repository requires a `config.py` file with the connection
parameters (inside the stoveApp folder). Example:

``` python
# config.py
REFERENCE_MAC = "00:00:00:00:00:00" # Replace by your device MAC address to discover it
USERNAME = "YOUR USERNAME"
PASSWORD = "YOUR PASSWORD"

SUBNET_CIDR = "192.168.68.0/24" # Replace by your local network ip
DISCOVERY_INTERVAL_S = 5
POLL_INTERVAL_S = 1
```

Without this file the discovery and authentication modules will not
work.

## Features

-   Automatic IP discovery by MAC address\
-   Connection retry every 5 seconds until link is achieved\
-   Polling of stove data each 1 second\
-   UI ↔ Worker communication using signals\
-   Controls:
    -   Power ON / OFF
    -   Increase and decrease temperature (12--40 °C)
    -   Select power level **maximum = 9** with current level
        highlighted
    -   Display device alarms

## Screenshots

You may add images by creating an `assets/` folder and referencing them
in Markdown:

``` markdown
![Main interface](assets/interface.png)
```

``` markdown
![Temperature dial](assets/dial.png)
```

## Requirements

-   Python 3.11+\
-   requests\
-   PySide6\
-   lan_scanner (local library)\
-   NetFlame (local library)

## Installation on Debian / Ubuntu

``` bash
pip install PySide6 requests
```

## Usage

Run:

``` bash
python3 main.py
```

Flow:

1.  Network scan of configured subnet\
2.  Stove IP resolution via MAC\
3.  Authenticated HTTP client creation\
4.  Continuous snapshot update in UI

## Structure

    project/
    ├── lan_scanner/
    │   ├── __init__.py
    │   ├── Readme.md
    │   └── scanner.py
    ├── NetFlame/
    │   ├── __init__.py
    │   ├── models.py
    │   └── NetFlame.py
    ├── stoveApp/
    │   ├── config.py # REQUIRED
    │   ├── main.py
    │   ├── net.py
    │   └── ui.py
    ├── stovectl/
    │   ├── __init__.py
    │   ├── models.py
    │   ├── exceptios.py
    │   ├── Readme.md
    │   └── client.py
    ├── LICENSE
    └── Readme.md

## License

Distributed under **LICENSE -- GEL 3.0** © Alejandro Fernández
Rodríguez.
