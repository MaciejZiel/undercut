import pytest
from django.core.exceptions import ValidationError

from apps.accounts.validators import validate_display_name, validate_timezone


@pytest.mark.parametrize("name", ["abc", "x" * 20, "Max V.", "kimi-räikkönen", "a_b c", "ŁukaszŻ"])
def test_valid_display_names(name):
    assert validate_display_name(name) == name


@pytest.mark.parametrize(
    "name",
    ["ab", "x" * 21, "a<b>c", "a@b.c", " ", "a\nb\tc"[:2], "Admin", "UNDERCUT", "emoji🙂abc"],
)
def test_invalid_display_names(name):
    with pytest.raises(ValidationError):
        validate_display_name(name)


def test_whitespace_is_normalised_before_the_length_check():
    assert validate_display_name("  a   b  ") == "a b"
    with pytest.raises(ValidationError):
        validate_display_name("  ab  ")


@pytest.mark.parametrize("tz", ["UTC", "Europe/Warsaw", "America/Argentina/Buenos_Aires"])
def test_valid_timezones(tz):
    assert validate_timezone(tz) == tz


@pytest.mark.parametrize("tz", ["", "Warsaw", "Europe/Nowhere", "..", "utc "])
def test_invalid_timezones(tz):
    with pytest.raises(ValidationError):
        validate_timezone(tz)
