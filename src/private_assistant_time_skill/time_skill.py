import enum
import string
import threading
from datetime import datetime, timedelta

import jinja2
import paho.mqtt.client as mqtt
import private_assistant_commons as commons
from private_assistant_commons import messages
from private_assistant_commons.skill_logger import SkillLogger
from pydantic import BaseModel

from private_assistant_time_skill.tools_time_units import format_time_difference

# Configure logging
logger = SkillLogger.get_logger(__name__)


class Parameters(BaseModel):
    hours: int | None = None
    minutes: int | None = None
    seconds: int | None = None
    is_deleted: bool | None = None
    timers: list[dict[str, str | int]] = []

    @property
    def duration_name(self) -> str:
        parts = []
        if self.hours is not None and self.hours > 0:
            parts.append(f"{self.hours} hour{'s' if self.hours != 1 else ''}")
        if self.minutes is not None and self.minutes > 0:
            parts.append(f"{self.minutes} minute{'s' if self.minutes != 1 else ''}")
        if self.seconds is not None and self.seconds > 0:
            parts.append(f"{self.seconds} second{'s' if self.seconds != 1 else ''}")

        return " and ".join(parts)


class Action(enum.Enum):
    HELP = ["help"]
    SET = ["set"]
    LIST = ["list"]
    DELETE_LAST = ["delete", "last"]

    @classmethod
    def find_matching_action(cls, text: str):
        text = text.translate(str.maketrans("", "", string.punctuation))
        text_words = set(text.lower().split())

        for action in cls:
            if all(word in text_words for word in action.value):
                return action
        return None


class TimeSkill(commons.BaseSkill):
    def __init__(
        self,
        config_obj: commons.SkillConfig,
        mqtt_client: mqtt.Client,
        template_env: jinja2.Environment,
    ) -> None:
        super().__init__(config_obj, mqtt_client)
        self.active_timers: dict[str, dict] = {}
        self.last_created_timer_name: str | None = None
        self.action_to_answer: dict[Action, jinja2.Template] = {
            Action.HELP: template_env.get_template("help.j2"),
            Action.SET: template_env.get_template("set.j2"),
            Action.LIST: template_env.get_template("list.j2"),
            Action.DELETE_LAST: template_env.get_template("delete_last.j2"),
        }
        # Adding a separate template dictionary for non-action-related operations
        self.non_action_templates: dict[str, jinja2.Template] = {
            "triggered": template_env.get_template("triggered.j2"),
        }
        self.template_env = template_env
        self.timer_lock: threading.RLock = threading.RLock()

    def calculate_certainty(self, intent_analysis_result: messages.IntentAnalysisResult) -> float:
        if "timer" in intent_analysis_result.nouns:
            return 1.0
        return 0.0

    def find_parameters(self, action: Action, intent_analysis_result: messages.IntentAnalysisResult) -> Parameters:
        parameters = Parameters()
        if action == Action.SET:
            for result in intent_analysis_result.numbers:
                if result.next_token == "hours":
                    parameters.hours = result.number_token
                elif result.next_token == "minutes":
                    parameters.minutes = result.number_token
                elif result.next_token == "seconds":
                    parameters.seconds = result.number_token
        elif action == Action.LIST:
            parameters.timers = self.find_active_timers()
        return parameters

    def get_answer(self, action: Action, parameters: Parameters) -> str:
        template = self.action_to_answer[action]
        return template.render(parameters=parameters)

    def register_timer(self, parameters: Parameters, client_request: commons.ClientRequest) -> None:
        total_diff = timedelta(
            hours=parameters.hours or 0,
            minutes=parameters.minutes or 0,
            seconds=parameters.seconds or 0,
        )
        duration_name = parameters.duration_name
        if not duration_name:
            logger.error("No valid timer duration provided.")
            return

        with self.timer_lock:
            if duration_name in self.active_timers:
                self.active_timers[duration_name]["timer"].cancel()
                logger.debug("Existing timer '%s' canceled before registering a new one.", duration_name)

            new_timer = threading.Timer(
                total_diff.total_seconds(),
                function=self.publish_triggered_timer,
                kwargs={"parameters": parameters},
            )
            new_timer.daemon = True
            new_timer.start()
            self.active_timers[duration_name] = {
                "timer": new_timer,
                "start_time": datetime.now(),
                "total_duration": total_diff,
            }
            self.last_created_timer_name = duration_name
            logger.debug("Timer '%s' registered and started.", duration_name)

    def publish_triggered_timer(self, parameters: Parameters):
        # Use the triggered template from the non-action templates
        template = self.non_action_templates["triggered"]
        answer = template.render(parameters=parameters)
        self.broadcast_text(answer)
        with self.timer_lock:
            if parameters.duration_name in self.active_timers:
                del self.active_timers[parameters.duration_name]
                logger.debug("Timer '%s' removed from active timers.", parameters.duration_name)

    def find_active_timers(self) -> list[dict]:
        """Find all currently active timers with remaining time."""
        with self.timer_lock:
            active_timers_info = []
            for timer_name, timer_data in self.active_timers.items():
                total_duration = timer_data["total_duration"]
                start_time = timer_data["start_time"]
                time_passed = datetime.now() - start_time
                time_left = total_duration - time_passed

                if time_left.total_seconds() > 0:
                    active_timers_info.append({"id": timer_name, "time_left": format_time_difference(time_left)})

            return active_timers_info

    def delete_last_timer(self, parameters: Parameters) -> None:
        with self.timer_lock:
            if self.last_created_timer_name and self.last_created_timer_name in self.active_timers:
                self.active_timers[self.last_created_timer_name]["timer"].cancel()
                del self.active_timers[self.last_created_timer_name]
                logger.debug("Last created timer '%s' deleted.", self.last_created_timer_name)
                self.last_created_timer_name = None
                parameters.is_deleted = True
            else:
                logger.debug("No active timer to delete.")
                parameters.is_deleted = False

    def process_request(self, intent_analysis_result: messages.IntentAnalysisResult) -> None:
        action = Action.find_matching_action(intent_analysis_result.client_request.text)
        if action is None:
            logger.error("Unrecognized action in text: %s", intent_analysis_result.client_request.text)
            return

        parameters = self.find_parameters(action, intent_analysis_result=intent_analysis_result)

        if action == Action.SET:
            self.register_timer(parameters, client_request=intent_analysis_result.client_request)
        elif action == Action.HELP:
            pass
        elif action == Action.LIST:
            pass
        elif action == Action.DELETE_LAST:
            self.delete_last_timer(parameters)
        else:
            logger.debug("No specific action implemented for action: %s", action)
            return
        answer = self.get_answer(action, parameters)
        self.add_text_to_output_topic(answer, client_request=intent_analysis_result.client_request)
