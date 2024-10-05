import pytest

from private_assistant_time_skill.time_skill import Action


@pytest.mark.parametrize(
    "text, expected",
    [
        ("Please help", Action.HELP),
        ("help me out!", Action.HELP),
        ("set timer for 10 minutes", Action.SET),
        ("list all active timers", Action.LIST),
        ("can you list the timers?", Action.LIST),
        ("delete the last timer", Action.DELETE_LAST),
        ("this should return none", None),
        ("trigger something else", None),
    ],
)
def test_find_matching_action(text, expected):
    assert Action.find_matching_action(text) == expected
