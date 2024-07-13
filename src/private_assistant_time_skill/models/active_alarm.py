from datetime import datetime

from sqlmodel import Field, SQLModel


class ActiveAlarm(SQLModel, table=True):  # type: ignore
    id: int | None = Field(default=None, primary_key=True)
    output_topic: str
    name: str
    scheduled_time: datetime
