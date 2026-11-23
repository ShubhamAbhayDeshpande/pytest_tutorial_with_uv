import pytest
from ecusim.ecu import Ecu

@pytest.fixture
def ecu():
    """A connected head unit, disconnected again after the test."""
    unit=Ecu("HU", firmware="1.0.0")
    unit.connect()
    yield unit
    unit.disconnect()

# Fixtures can call other fixtures.
@pytest.fixture(autouse=True)
def fash_flash(monkeypatch): # monkeypatch is an in built fixture
    """Every test flashes instantly instead of waiting for 2 sec."""
    monkeypatch.setenv("ECUSIM_FLASH_DELAY", "0")

# Factory Fixture: For test which needs several objects or needs to choose an argument, return a fucntion.
@pytest.fixture
def make_ecu():
    """Factory Fixture: Build as many ecus as the test needs."""
    ecu_lst = []

    def _make(name="HU", firmware="1.0.0", voltage=12.6):
        unit=Ecu(name)
        unit.battery_voltage=voltage
        unit.connect()
        if unit.firmware != firmware:
            unit.install(firmware)
        ecu_lst.append(unit)
        return unit
    
    yield _make
    for units in ecu_lst:
        units.disconnect()

