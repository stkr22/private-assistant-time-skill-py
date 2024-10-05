import jinja2
import pytest

from private_assistant_time_skill.time_skill import Parameters


# Fixture to set up the Jinja environment
@pytest.fixture(scope="module")
def jinja_env():
    return jinja2.Environment(
        loader=jinja2.PackageLoader(
            "private_assistant_time_skill",
            "templates",
        ),
    )


def get_template_output(template_name, parameters, env):
    template = env.get_template(template_name)
    return template.render(parameters=parameters)


# Test for set.j2 template
@pytest.mark.parametrize(
    "parameters,expected_output",
    [
        (
            Parameters(minutes=10, seconds=20),
            "Timer set for 10 minutes and 20 seconds.",
        ),
        (Parameters(hours=1), "Timer set for 1 hour."),
        (Parameters(seconds=30), "Timer set for 30 seconds."),
        (
            Parameters(hours=2, minutes=30),
            "Timer set for 2 hours and 30 minutes.",
        ),
        (
            Parameters(hours=1, minutes=1, seconds=1),
            "Timer set for 1 hour and 1 minute and 1 second.",
        ),
    ],
)
def test_set_template(jinja_env, parameters, expected_output):
    assert get_template_output("set.j2", parameters, jinja_env) == expected_output


# Test for list.j2 template
@pytest.mark.parametrize(
    "parameters, expected_output",
    [
        (Parameters(timers=[]), "There are no active timers.\n"),
        (
            Parameters(timers=[{"id": "5 minutes", "time_left": "3 minutes"}]),
            "There are 1 active timer.\nTimer 5 minutes will be due in 3 minutes.\n",
        ),
        (
            Parameters(
                timers=[
                    {"id": "5 minutes", "time_left": "3 minutes"},
                    {"id": "10 minutes", "time_left": "8 minutes"},
                ]
            ),
            "There are 2 active timers.\n"
            "Timer 5 minutes will be due in 3 minutes.\n"
            "Timer 10 minutes will be due in 8 minutes.\n",
        ),
    ],
)
def test_list_template(jinja_env, parameters, expected_output):
    assert get_template_output("list.j2", parameters, jinja_env) == expected_output


# Test for delete_last.j2 template
@pytest.mark.parametrize(
    "parameters,expected_output",
    [
        (
            Parameters(minutes=10, is_deleted=True),
            "The last created timer for 10 minutes has been deleted.",
        ),
        (
            Parameters(is_deleted=False),
            "No active timer to delete.",
        ),
    ],
)
def test_delete_last_template(jinja_env, parameters, expected_output):
    assert get_template_output("delete_last.j2", parameters, jinja_env) == expected_output


# Test for triggered.j2 template
@pytest.mark.parametrize(
    "parameters,expected_output",
    [
        (
            Parameters(hours=0, minutes=10, seconds=0),
            "Alert, Alert! The timer 10 minutes is due. Alert, Alert!",
        ),
        (
            Parameters(hours=1),
            "Alert, Alert! The timer 1 hour is due. Alert, Alert!",
        ),
    ],
)
def test_triggered_template(jinja_env, parameters, expected_output):
    assert get_template_output("triggered.j2", parameters, jinja_env) == expected_output
