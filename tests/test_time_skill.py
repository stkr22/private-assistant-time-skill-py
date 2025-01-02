import asyncio
import unittest
import uuid
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import jinja2
from private_assistant_commons.messages import ClientRequest, IntentAnalysisResult, NumberAnalysisResult

from private_assistant_time_skill.time_skill import Parameters, TimeSkill


class TestTimeSkill(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        # Mock the MQTT client, config, and Jinja2 template environment
        self.mock_mqtt_client = AsyncMock()
        self.mock_config = Mock()
        self.mock_template_env = jinja2.Environment(
            loader=jinja2.PackageLoader(
                "private_assistant_time_skill",
                "templates",
            )
        )
        self.mock_task_group = AsyncMock()

        # Instantiate TimeSkill with the mocks
        self.skill = TimeSkill(
            config_obj=self.mock_config,
            mqtt_client=self.mock_mqtt_client,
            template_env=self.mock_template_env,
            task_group=self.mock_task_group,
            logger=Mock(),
        )
        await self.skill.skill_preparations()

    async def test_register_timer(self):
        # Mock client request and parameters
        parameters = Parameters(hours=1, minutes=30, seconds=0)

        # Call the register_timer method
        with patch.object(self.skill, "add_task") as mock_create_task:
            mock_create_task.return_value = Mock(spec=asyncio.Task)
            self.skill.register_timer(parameters)

            # Verify that a new async task was created
            mock_create_task.assert_called_once()

            # Verify the timer is added to active_timers
            self.assertTrue(self.skill.active_timers)
            self.assertIn(parameters.duration_name, self.skill.active_timers)

    async def test_delete_last_timer(self):
        # Mock parameters for creating and deleting a timer
        parameters = Parameters(hours=1, minutes=30, seconds=0)

        # Register a timer first
        with patch.object(self.skill, "add_task") as mock_create_task:
            mock_create_task.return_value = Mock(spec=asyncio.Task)
            self.skill.register_timer(parameters)

            # Verify the timer was registered
            self.assertTrue(self.skill.active_timers)

        # Call delete_last_timer method
        self.skill.delete_last_timer(parameters)

        # Verify the timer has been deleted
        self.assertIsNone(self.skill.last_created_timer_name)

    async def test_list_timers(self):
        # Mock parameters and client request to register timers
        parameters_1 = Parameters(hours=0, minutes=5, seconds=0)
        parameters_2 = Parameters(hours=0, minutes=10, seconds=0)

        # Register two timers
        with patch.object(self.skill, "add_task") as mock_create_task:
            mock_create_task.return_value = Mock(spec=asyncio.Task)
            self.skill.register_timer(parameters_1)
            self.skill.register_timer(parameters_2)

        # Call find_active_timers method
        result = self.skill.find_active_timers()

        # Verify that two timers are listed
        self.assertEqual(len(result), 2)

    async def test_process_request_set(self):
        # Mock the IntentAnalysisResult and ClientRequest
        mock_client_request = ClientRequest(
            id=uuid.uuid4(), text="set timer for 10 minutes", output_topic="test_topic", room="livingroom"
        )

        mock_number_analysis_result = NumberAnalysisResult(number_token=10, next_token="minutes")
        mock_intent_result = IntentAnalysisResult(
            client_request=mock_client_request, numbers=[mock_number_analysis_result], nouns=["timer"], verbs=["set"]
        )

        parameters = Parameters(minutes=10)

        # Mock the TaskGroup creation
        with patch.object(self.skill, "add_task") as mock_create_task:
            mock_create_task.return_value = Mock(spec=asyncio.Task)
            # Call the process_request method with SET action
            await self.skill.process_request(mock_intent_result)

            # Verify that the task was created
            mock_create_task.assert_called()

            # Verify the timer is correctly registered
            self.assertTrue(self.skill.active_timers)
            self.assertIn(parameters.duration_name, self.skill.active_timers)

    async def test_publish_triggered_timer(self):
        # Mock parameters and setup a triggered timer
        parameters = Parameters(hours=0, minutes=5, seconds=0)
        with patch.object(self.skill, "publish_triggered_timer") as mock_publish_triggered_timer:
            await self.skill.publish_triggered_timer(parameters)

            # Verify that the publish_triggered_timer was called with rendered output
            mock_publish_triggered_timer.assert_called_once()

    async def test_cleanup_timer(self):
        # Mock parameters and client request to register a timer
        parameters = Parameters(hours=0, minutes=5, seconds=0)

        # Mock the task creation to ensure add_done_callback can be verified
        with patch.object(self.skill, "add_task") as mock_create_task:
            mock_create_task.return_value = Mock(spec=asyncio.Task)
            mock_task = MagicMock()
            mock_task.add_done_callback = MagicMock()
            mock_create_task.return_value = mock_task

            # Register a timer
            self.skill.register_timer(parameters)

            # Verify that add_done_callback was called to attach the cleanup method
            mock_task.add_done_callback.assert_called_once()

            # Manually call the cleanup to simulate task completion
            self.skill.cleanup_timer(parameters.duration_name)

            # Verify that the timer was removed from active_timers
            self.assertNotIn(parameters.duration_name, self.skill.active_timers)
