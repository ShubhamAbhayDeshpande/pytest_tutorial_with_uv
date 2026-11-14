from ecusim.version import is_newer, parse_version

def test_simple_parse_version():
    assert parse_version("1.2.3") == (1,2,3)

def test_parse_version_whitespace():
    assert parse_version("2.0.1\n") == (2,0,1)

def test_simple_is_newer():
    assert is_newer("1.2.3", "1.1.1") is True

def test_parse_version_deliberate_failure():
    assert parse_version("2.0.1") == (2,1,2)

