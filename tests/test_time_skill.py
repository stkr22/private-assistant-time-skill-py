import pytest
from private_assistant_time_skill.time_skill import Action


@pytest.mark.parametrize(
    "text, expected",
    [
        ("Please help", Action.HELP),
        ("help me out!", Action.HELP),
        ("I need to set a timer", Action.TIMER_SET),
        ("set timer for 10 minutes", Action.TIMER_SET),
        ("when the timer is triggered", Action.TIMER_TRIGGERED),
        ("notify when timer triggered", Action.TIMER_TRIGGERED),
        ("how to set alarm", Action.ALARM_SET),
        ("set an alarm for 7 am", Action.ALARM_SET),
        ("list all active timers", Action.LIST_TIMERS),
        ("can you list the timers?", Action.LIST_TIMERS),
        ("this should return none", None),
        ("trigger something else", None),
    ],
)
def test_find_matching_action(text, expected):
    assert Action.find_matching_action(text) == expected


@pytest.mark.parametrize(
    "text, expected", [("timer", None), ("set", None), ("alarm trigger", None)]
)
def test_find_matching_action_partial_matches(text, expected):
    assert Action.find_matching_action(text) == expected
