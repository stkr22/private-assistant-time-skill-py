import logging
import os
import pathlib
import sys
from typing import Annotated

import jinja2
import paho.mqtt.client as mqtt
import spacy
import typer
from sqlmodel import SQLModel, create_engine

from private_assistant_time_skill import config, time_skill

log_level = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=log_level,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout,
)

app = typer.Typer()


@app.command()
def start_skill(
    config_path: Annotated[
        pathlib.Path, typer.Argument(envvar="PRIVATE_ASSISTANT_CONFIG_PATH")
    ],
):
    config_obj = config.load_config(config_path)
    db_engine = create_engine(config_obj.db_connection_string)
    SQLModel.metadata.create_all(db_engine)
    time_skill_obj = time_skill.TimeSkill(
        mqtt_client=mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2,
            client_id=config_obj.client_id,
            protocol=mqtt.MQTTv5,
        ),
        config_obj=config_obj,
        nlp_model=spacy.load(config_obj.spacy_model),
        template_env=jinja2.Environment(
            loader=jinja2.PackageLoader(
                "private_assistant_time_skill",
                "templates",
            ),
        ),
        db_engine=db_engine,
    )
    time_skill_obj.run()


if __name__ == "__main__":
    start_skill(config_path=pathlib.Path("./local_config.yaml"))
