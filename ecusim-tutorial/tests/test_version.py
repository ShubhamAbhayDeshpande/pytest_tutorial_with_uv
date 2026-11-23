import pytest
from ecusim.version import is_newer, parse_version

def test_simple_parse_version():
    assert parse_version("1.2.3") == (1,2,3)

def test_parse_version_whitespace():
    assert parse_version("2.0.1\n") == (2,0,1)

def test_simple_is_newer():
    assert is_newer("1.2.3", "1.1.1") is True

def test_parse_version_deliberate_failure():
    assert parse_version("2.0.1") == (2,1,2)

# The following tests raise an error with 'pytest.raises. pytest.raises() will catch the specified error and test will pass gracefully without stoping the program run.
def test_raise_error_two_part_version():
    with pytest.raises(ValueError) as error_obj:
        parse_version("1.4")

# Match the error to a given string
def test_non_numeric_software_version():
    with pytest.raises(ValueError, match=r"non-numeric") as error_obj:
        parse_version("1.x.2")

# Print the Exception Info object created by pytest.asserts
def test_negative_value_softwaere_version():
    with pytest.raises(ValueError) as negative_value:
        parse_version("1.-5.6")

# Check if the error message contains specific string using assert
def test_check_string_in_error_message():
    with pytest.raises(ValueError) as error_obj:
        parse_version("1.-5.6")
    assert r"negative" in str(error_obj.value)


"""
Exercise 2: 
1. Test for showing that the parse_version() will raise a ValueError with message: MAJOR.MINOR.PATCH
2. Change test_voltage_is_close_enough so the second assert fails, and read how approx reports the tolerance.
3. Stretch: read about pytest.warns and pytest.RaisesGroup in the assertion how-to.
"""

# Test to check if the parse_version() raises MAJOR.MINOR.PATCH error
def test_check_major_minor_patch_in_error():
    with pytest.raises(ValueError, match="MAJOR.MINOR.PATCH"):
        parse_version("1.4")

# Change the test so that, second assertion in the testcase fails
def test_voltage_is_close_enough():
    assert 0.1+0.2 == pytest.approx(0.3)
    assert 12.58 == pytest.approx(12.6, abs=0.01) # Reduced the 'abs' so that the values are not close enough to pass the test

def test_check_dictionary():
    some_dict={"name":"HU", "fw":"1.0.0", "ok": True}
    assert some_dict == {"name":"HU", "fw":"1.0.1", "ok": True}
