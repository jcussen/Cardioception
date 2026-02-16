import unittest

from cardioception.input import digit_key_list, parse_digit_key


class TestInputKeys(unittest.TestCase):
    def test_digit_key_list_contains_top_row_and_numpad_variants(self):
        keys = digit_key_list(1, 2)
        assert "1" in keys
        assert "2" in keys
        assert "num_1" in keys
        assert "numpad_1" in keys
        assert "kp_1" in keys

    def test_parse_digit_key_variants(self):
        assert parse_digit_key("1") == "1"
        assert parse_digit_key("num_2") == "2"
        assert parse_digit_key("numpad_3") == "3"
        assert parse_digit_key("kp_4") == "4"
        assert parse_digit_key("NUM5") == "5"
        assert parse_digit_key("escape") is None


if __name__ == "__main__":
    unittest.main(argv=["first-arg-is-ignored"], exit=False)
