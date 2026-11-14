"""A tiny simulated ECU that can receive OTA updates."""

import json
import logging
import os
import time
from pathlib import Path

from ecusim.version import is_newer

log = logging.getLogger("ecusim")


class EcuError(Exception):
    pass


class Ecu:
    def __init__(self, name: str, firmware: str = "1.0.0") -> None:
        self.name = name
        self.firmware = firmware
        self.connected = False
        self.battery_voltage = 12.6

    def connect(self) -> None:
        log.info("connecting to %s", self.name)
        self.connected = True

    def disconnect(self) -> None:
        log.info("disconnecting from %s", self.name)
        self.connected = False

    def read_voltage(self) -> float:
        self._require_connection()
        return self.battery_voltage

    def install(self, version: str) -> None:
        """Install an OTA update. Only upgrades are allowed."""
        self._require_connection()
        if self.battery_voltage < 11.5:
            raise EcuError("battery too low for update")
        if not is_newer(version, self.firmware):
            log.warning("rejected %s: not newer than %s", version, self.firmware)
            raise EcuError(f"{version} is not newer than {self.firmware}")
        time.sleep(flash_delay())
        self.firmware = version
        log.info("%s now runs %s", self.name, version)

    def _require_connection(self) -> None:
        if not self.connected:
            raise EcuError(f"{self.name} is not connected")


def flash_delay() -> float:
    """Seconds a flash takes. Override with ECUSIM_FLASH_DELAY."""
    return float(os.environ.get("ECUSIM_FLASH_DELAY", "2"))


def load_fleet(path: Path) -> list[Ecu]:
    """Read a JSON file like [{"name": "HU", "firmware": "1.2.0"}]."""
    data = json.loads(Path(path).read_text())
    return [Ecu(item["name"], item.get("firmware", "1.0.0")) for item in data]


def report(ecus: list[Ecu]) -> None:
    for ecu in ecus:
        print(f"{ecu.name}: {ecu.firmware}")
