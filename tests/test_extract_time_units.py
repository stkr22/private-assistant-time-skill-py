from datetime import timedelta

import pytest
import spacy
from private_assistant_time_skill.tools_time_units import (
    extract_alarm_units,
    extract_time_units,
    format_time_difference,
)


@pytest.fixture(scope="module")  # Use 'module' scope to initialize once per module
def nlp_model():
    return spacy.load("en_core_web_md")


@pytest.mark.parametrize(
    "input_text,expected",
    [
        (
            "Set an alarm for 3 hours and 20 minutes",
            {"hours": 3, "minutes": 20, "seconds": None},
        ),
        ("Reminder in 15 minutes", {"hours": None, "minutes": 15, "seconds": None}),
        ("Timer for 2 hours 30 minutes", {"hours": 2, "minutes": 30, "seconds": None}),
        (
            "Add 5 minutes and 2 seconds to the timer",
            {"hours": None, "minutes": 5, "seconds": 2},
        ),
        # Tests that are expected to return None because they require additional context or parsing logic
        (
            "I need a nap for half an hour",
            {"hours": None, "minutes": None, "seconds": None},
        ),
        ("Let's meet in 25", {"hours": None, "minutes": None, "seconds": None}),
        ("No numbers here", {"hours": None, "minutes": None, "seconds": None}),
    ],
)
def test_extract_time_units(input_text, expected, nlp_model):
    assert extract_time_units(input_text, nlp_model) == expected


@pytest.mark.parametrize(
    "input_text,expected_hour,expected_minute",
    [
        ("Set an alarm for 8 o'clock.", 8, 0),  # 08:00 in 24-hour format
        ("Set an alarm for 730.", 7, 30),  # 07:30 in 24-hour format
        ("Wake me up at 1945.", 19, 45),  # 19:45 in 24-hour format
        ("Alarm set for 1245.", 12, 45),  # 12:45 in 24-hour format
        ("Reminder at 0030.", 0, 30),  # 00:30 in 24-hour format
        ("Alarm at noon", None, None),  # 12:00 in 24-hour format for noon
        ("Set alarm at midnight", None, None),  # 00:00 in 24-hour format for midnight
    ],
)
def test_set_alarm(input_text, expected_hour, expected_minute, nlp_model):
    result = extract_alarm_units(input_text, nlp_model)
    if expected_hour is None or expected_minute is None:
        assert result is None
    else:
        assert result.hour == expected_hour and result.minute == expected_minute


@pytest.mark.parametrize(
    "time_diff, expected_output",
    [
        (timedelta(seconds=45), "45 seconds"),
        (timedelta(minutes=5, seconds=30), "5 minutes and 30 seconds"),
        (
            timedelta(hours=1, minutes=2, seconds=3),
            "1 hour and 2 minutes and 3 seconds",
        ),
        (timedelta(hours=2), "2 hours"),
    ],
)
def test_format_time_difference(time_diff, expected_output):
    result = format_time_difference(time_diff)
    assert result == expected_output
