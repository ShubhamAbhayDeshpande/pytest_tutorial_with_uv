"""
This module contains testcases that are parameterized. 
Each test case is ran once per every line of data in pytest.mark.parameterize()

"""
import pytest
from ecusim.version import is_newer, parse_version