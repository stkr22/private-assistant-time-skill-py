import unittest
import uuid
from datetime import timedelta
from unittest.mock import Mock, patch

import jinja2
from private_assistant_commons.messages import ClientRequest, IntentAnalysisResult, NumberAnalysisResult
from private_assistant_time_skill.time_skill import Parameters, TimeSkill


class TestTimeSkill(unittest.TestCase):
    def setUp(self):
        # Mock the MQTT client, config, and Jinja2 template environment
        self.mock_mqtt_client = Mock()
        self.mock_config = Mock()
        self.mock_template_env = jinja2.Environment(
            loader=jinja2.PackageLoader(
                "private_assistant_time_skill",
                "templates",
            )
        )
        # Instantiate TimeSkill with the mocks
        self.skill = TimeSkill(
            config_obj=self.mock_config,
            mqtt_client=self.mock_mqtt_client,
            template_env=self.mock_template_env,
        )

    def test_register_timer(self):
        # Mock client request and parameters
        mock_client_request = Mock()
        mock_client_request.output_topic = "test_topic"

        parameters = Parameters(hours=1, minutes=30, seconds=0)

        with patch("private_assistant_time_skill.time_skill.threading.Timer") as mock_timer:
            # Call the register_timer method
            self.skill.register_timer(parameters, mock_client_request)

            # Verify that a new timer was created
            mock_timer.assert_called_once_with(
                timedelta(hours=1, minutes=30).total_seconds(),
                function=self.skill.publish_triggered_timer,
                kwargs={"parameters": parameters},
            )
            self.assertTrue(self.skill.active_timers)

    def test_delete_last_timer(self):
        # Mock parameters for creating and deleting a timer
        parameters = Parameters(hours=1, minutes=30, seconds=0)
        mock_client_request = Mock()

        # Register a timer first
        self.skill.register_timer(parameters, mock_client_request)

        # Call delete_last_timer method
        self.skill.delete_last_timer(parameters)

        # Verify the timer has been deleted
        self.assertFalse(self.skill.active_timers)
        self.assertIsNone(self.skill.last_created_timer_name)

    def test_list_timers(self):
        # Mock parameters and client request to register timers
        parameters_1 = Parameters(hours=0, minutes=5, seconds=0)
        parameters_2 = Parameters(hours=0, minutes=10, seconds=0)
        mock_client_request = Mock()

        # Register two timers
        self.skill.register_timer(parameters_1, mock_client_request)
        self.skill.register_timer(parameters_2, mock_client_request)

        # Call list_timers method
        result = self.skill.find_active_timers()
        assert len(result) == 2

    def test_process_request_set(self):
        # Mock the IntentAnalysisResult and ClientRequest
        mock_client_request = ClientRequest(
            id=uuid.uuid4(), text="set timer for 10 minutes", output_topic="test_topic", room="livingroom"
        )

        mock_number_analysis_result = NumberAnalysisResult(number_token=10, next_token="minutes")
        mock_intent_result = IntentAnalysisResult(
            client_request=mock_client_request, numbers=[mock_number_analysis_result], nouns=["timer"], verbs=["set"]
        )

        parameters = Parameters(minutes=10)

        # Mock the Timer creation
        with patch("private_assistant_time_skill.time_skill.threading.Timer") as mock_timer:
            # Call the process_request method with SET action
            self.skill.process_request(mock_intent_result)

            # Verify that the timer was created
            mock_timer.assert_called_once_with(
                timedelta(minutes=10).total_seconds(),
                function=self.skill.publish_triggered_timer,
                kwargs={"parameters": parameters},
            )
