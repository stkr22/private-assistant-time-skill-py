import asyncio
import pathlib
from typing import Annotated

import jinja2
import typer
from private_assistant_commons import async_typer, mqtt_connection_handler, skill_config, skill_logger

from private_assistant_time_skill import time_skill

app = async_typer.AsyncTyper()


@app.async_command()
async def start_skill(
    config_path: Annotated[pathlib.Path, typer.Argument(envvar="PRIVATE_ASSISTANT_CONFIG_PATH")],
):
    # Load configuration
    config_obj = skill_config.load_config(config_path, skill_config.SkillConfig)

    # Set up logger
    logger = skill_logger.SkillLogger.get_logger("Private Assistant TimeSkill")

    # Set up Jinja2 template environment
    template_env = jinja2.Environment(
        loader=jinja2.PackageLoader(
            "private_assistant_time_skill",
            "templates",
        )
    )

    # Start the skill using the async MQTT connection handler
    await mqtt_connection_handler.mqtt_connection_handler(
        time_skill.TimeSkill,
        config_obj,
        retry_interval=5,
        logger=logger,
        template_env=template_env,
    )


if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(start_skill(config_path=pathlib.Path("./local_config.yaml")))
