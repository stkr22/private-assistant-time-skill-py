import jinja2
import pytest
from private_assistant_time_skill.time_skill import (
    Parameters,  # Replace 'parameters_module' with the actual module name
)


# Fixture to set up the Jinja environment
@pytest.fixture(scope="module")
def jinja_env():
    return jinja2.Environment(
        loader=jinja2.PackageLoader(
            "private_assistant_time_skill",
            "templates",
        ),
    )


def get_template_output(parameters, env):
    template = env.get_template("timer_set.j2")
    return template.render(parameters=parameters)


# Define test cases
@pytest.mark.parametrize(
    "parameters,expected_output",
    [
        (
            Parameters(timer_minutes=10, timer_seconds=20),
            "I set a timer for 10 minutes and 20 seconds.",
        ),
        (Parameters(timer_hours=1), "I set a timer for 1 hour."),
        (Parameters(timer_seconds=30), "I set a timer for 30 seconds."),
        (
            Parameters(timer_hours=2, timer_minutes=30),
            "I set a timer for 2 hours and 30 minutes.",
        ),
        (
            Parameters(),
            "I set a timer for .",
        ),  # Depending on how empty values are handled
        (
            Parameters(timer_hours=1, timer_minutes=1, timer_seconds=1),
            "I set a timer for 1 hour and 1 minute and 1 second.",
        ),
    ],
)
def test_timer_template(jinja_env, parameters, expected_output):
    assert get_template_output(parameters, jinja_env) == expected_output


@pytest.mark.parametrize(
    "timers, expected_output",
    [
        ([], "I have no active timers.\n"),
        (
            [{"id": 1, "time_left": "5 minutes and 30 seconds"}],
            "I have 1 active timer.\nTimer 1 will be due in 5 minutes and 30 seconds.\n",
        ),
        (
            [
                {"id": 1, "time_left": "5 minutes and 30 seconds"},
                {"id": 2, "time_left": "1 hour and 2 minutes and 3 seconds"},
            ],
            "I have 2 active timers.\nTimer 1 will be due in 5 minutes and 30 seconds.\nTimer 2 will be due in 1 hour and 2 minutes and 3 seconds.\n",
        ),
    ],
)
def test_list_timers_template(jinja_env, timers, expected_output):
    template = jinja_env.get_template("list_timers.j2")
    parameters = Parameters(timers=timers)
    result = template.render(parameters=parameters)
    assert result == expected_output
