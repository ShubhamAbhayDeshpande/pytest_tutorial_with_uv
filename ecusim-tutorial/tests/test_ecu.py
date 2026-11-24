# Imports
import pytest
from ecusim.ecu import Ecu, EcuError

def test_fresh_ecu_is_diconnected():
    assert not Ecu("HU").connected

def test_install_upgrades_firmware(ecu):
    ecu.install("1.1.0")
    assert ecu.firmware=="1.1.0"

def test_downgrade_is_rejected(ecu):
    with pytest.raises(EcuError, match="not newer"):
        ecu.install("0.9.0")
    assert ecu.firmware == "1.0.0"

def test_reading_voltage_needs_connection():
    with pytest.raises(EcuError, match="not connected"):
        Ecu("HU").read_voltage()

# Use Factory Fixture to make two ecus and compare their software versions
def test_check_firmwares_on_ecus(make_ecu):
    ecu_1 = make_ecu(name="HU1", firmware="1.2.1")
    ecu_2 = make_ecu(name="HU2", firmware="1.2.2")
    assert (ecu_1.firmware, ecu_2.firmware) == ("1.2.1", "1.2.2")

# Adding testcases to check a fixture with scope="module"
def test_bench_power_on(bench, ecu):
    assert bench["booted"]
    assert ecu.connected

def test_bench_is_shared(bench):
    assert bench["supply"]=="PSU-1"

