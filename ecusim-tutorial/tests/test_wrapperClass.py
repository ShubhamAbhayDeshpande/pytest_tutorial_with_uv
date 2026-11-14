"""
Module contains wrapper class 'TestParse' which wraps tests
test_simple_parse_version() and test_parse_version_whitespace()

"""

import test_version

class TestParse:

    # Execute test for simple parse
    def test_simple(self):
        test_version.test_simple_parse_version()

    # Execute the test with whitespace. 
    def test_whitespace(self):
        test_version.test_parse_version_whitespace()

    