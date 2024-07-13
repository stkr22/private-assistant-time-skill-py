import enum
import logging
import string
import threading
from datetime import datetime, timedelta

import jinja2
import paho.mqtt.client as mqtt
import private_assistant_commons as commons
import spacy
import sqlalchemy
from pydantic import BaseModel
from sqlmodel import Session, select

from private_assistant_time_skill import models, tools_time_units

logger = logging.getLogger(__name__)


class Parameters(BaseModel):
    targets: list[str] = []
    timer_hours: int | None = None
    timer_minutes: int | None = None
    timer_seconds: int | None = None
    alarm_time: datetime | None = None
    timers: list[dict[str, str | int]] = []

    @property
    def timer_name(self) -> str:
        parts = []
        if self.timer_hours is not None and self.timer_hours > 0:
            parts.append(
                f"{self.timer_hours} hour{'s' if self.timer_hours != 1 else ''}"
            )
        if self.timer_minutes is not None and self.timer_minutes > 0:
            parts.append(
                f"{self.timer_minutes} minute{'s' if self.timer_minutes != 1 else ''}"
            )
        if self.timer_seconds is not None and self.timer_seconds > 0:
            parts.append(
                f"{self.timer_seconds} second{'s' if self.timer_seconds != 1 else ''}"
            )

        return " and ".join(parts)


class Action(enum.Enum):
    HELP = ["help"]
    TIMER_SET = ["set", "timer"]
    TIMER_TRIGGERED = ["timer", "triggered"]
    ALARM_SET = ["set", "alarm"]
    LIST_TIMERS = ["list", "timers"]

    @classmethod
    def find_matching_action(cls, text: str):
        # Remove punctuation from the text
        text = text.translate(str.maketrans("", "", string.punctuation))
        text_words = set(
            text.lower().split()
        )  # Convert text to lowercase and split into words

        for action in cls:
            if all(
                word in text_words for word in action.value
            ):  # Check if all words in the list are in text
                return action
        return None


class TimeSkill(commons.BaseSkill):
    def __init__(
        self,
        config_obj: commons.SkillConfig,
        mqtt_client: mqtt.Client,
        nlp_model: spacy.Language,
        db_engine: sqlalchemy.Engine,
        template_env: jinja2.Environment,
    ) -> None:
        super().__init__(config_obj, mqtt_client, nlp_model)
        self.active_timers: dict[str, threading.Timer] = {}
        self.db_engine = db_engine
        self.action_to_answer: dict[Action, jinja2.Template] = {
            Action.HELP: template_env.get_template("help.j2"),
            Action.TIMER_SET: template_env.get_template("timer_set.j2"),
            Action.TIMER_TRIGGERED: template_env.get_template("timer_triggered.j2"),
            Action.ALARM_SET: template_env.get_template("alarm_set.j2"),
            Action.LIST_TIMERS: template_env.get_template("list_timers.j2"),
        }
        self.template_env = template_env
        self.timer_lock: threading.RLock = threading.RLock()

    def calculate_certainty(self, doc: spacy.language.Doc) -> float:
        for token in doc:
            if token.lemma_.lower() in ["timer", "time", "alarm"]:
                return 1.0
        return 0

    def find_parameters(self, action: Action, text: str) -> Parameters:
        parameters = Parameters()
        if action == Action.TIMER_SET:
            found_time_units = tools_time_units.extract_time_units(
                text=text, nlp_model=self.nlp_model
            )
            if found_time_units:
                parameters.timer_hours = found_time_units["hours"]
                parameters.timer_minutes = found_time_units["minutes"]
                parameters.timer_seconds = found_time_units["seconds"]
        if action == Action.ALARM_SET:
            parameters.alarm_time = tools_time_units.extract_alarm_units(
                text=text, nlp_model=self.nlp_model
            )
        if action == Action.LIST_TIMERS:
            parameters.timers = self.find_active_timers()
        return parameters

    def find_active_timers(self) -> list[dict[str, str | int]]:
        now = datetime.now()
        timers_list: list[dict[str, str | int]] = []
        with Session(self.db_engine) as session:
            statement = select(models.ActiveTimer).where(
                models.ActiveTimer.scheduled_time > now
            )
            timers = session.exec(statement).all()

        for i, timer in enumerate(timers, start=1):
            time_left_delta = timer.scheduled_time - now
            time_left = tools_time_units.format_time_difference(time_left_delta)
            timers_list.append(
                {
                    "id": i,
                    "time_left": time_left,
                }
            )
        return timers_list

    def get_answer(self, action: Action, parameters: Parameters) -> str:
        answer = self.action_to_answer[action].render(
            action=action,
            parameters=parameters,
        )
        return answer

    def publish_triggered_timer(
        self, parameters: Parameters, client_request: commons.ClientRequest
    ):
        answer = self.get_answer(action=Action.TIMER_TRIGGERED, parameters=parameters)
        self.add_text_to_output_topic(answer, client_request=client_request)
        with self.timer_lock:
            del self.active_timers[parameters.timer_name]

    def register_timer(
        self, parameters: Parameters, client_request: commons.ClientRequest
    ) -> None:
        total_diff = timedelta(
            hours=parameters.timer_hours or 0,
            minutes=parameters.timer_minutes or 0,
            seconds=parameters.timer_seconds or 0,
        )
        scheduled_time = datetime.now() + total_diff
        active_timer = models.ActiveTimer(
            output_topic=client_request.output_topic,
            name=parameters.timer_name,
            scheduled_time=scheduled_time,
        )
        with Session(self.db_engine) as session:
            session.add(active_timer)
            session.commit()
        with self.timer_lock:
            self.active_timers[parameters.timer_name] = threading.Timer(
                total_diff.total_seconds(),
                function=self.publish_triggered_timer,
                kwargs={"parameters": parameters, "client_request": client_request},
            )
            self.active_timers[parameters.timer_name].daemon = True
            self.active_timers[parameters.timer_name].start()

    def register_alarm(
        self, parameters: Parameters, client_request: commons.ClientRequest
    ) -> None:
        active_timer = models.ActiveAlarm(
            output_topic=client_request.output_topic,
            name=parameters.timer_name,
            scheduled_time=parameters.alarm_time,
        )
        with Session(self.db_engine) as session:
            session.add(active_timer)
            session.commit()

    def process_request(self, client_request: commons.ClientRequest) -> None:
        action = Action.find_matching_action(client_request.text)
        parameters = None
        if action is not None:
            parameters = self.find_parameters(action, text=client_request.text)
        if parameters is not None and action is not None:
            answer = self.get_answer(action, parameters)
            self.add_text_to_output_topic(answer, client_request=client_request)
            if action == Action.TIMER_SET:
                self.register_timer(parameters, client_request=client_request)
            if action == Action.ALARM_SET:
                self.register_alarm(parameters, client_request=client_request)
