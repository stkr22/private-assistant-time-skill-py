import re
from datetime import datetime, timedelta

import spacy
from word2number import w2n  # type: ignore


def extract_time_units(text: str, nlp_model: spacy.Language) -> dict[str, int | None]:
    doc = nlp_model(text)
    time_units: dict[str, int | None] = {
        "hours": None,
        "minutes": None,
        "seconds": None,
    }

    for token in doc:
        if token.pos_ == "NUM":
            try:
                number = w2n.word_to_num(token.text)
            except ValueError:
                try:
                    number = int(token.text)
                except ValueError:
                    continue  # Skip if the number conversion fails

            next_token = doc[token.i + 1] if token.i + 1 < len(doc) else None
            if next_token and next_token.text.lower() in ["hour", "hours"]:
                time_units["hours"] = number
            elif next_token and next_token.text.lower() in ["minute", "minutes"]:
                time_units["minutes"] = number
            elif next_token and next_token.text.lower() in ["second", "seconds"]:
                time_units["seconds"] = number

    return time_units


def extract_alarm_units(text: str, nlp_model: spacy.Language) -> datetime | None:
    doc = nlp_model(text)
    time = None

    # First, use regex to find patterns like '730' which spaCy might miss
    match = re.search(r"\b(\d{1,2})([0-5][0-9])\b", text)
    if match:
        # Converts '730' to hour=7, minute=30
        hour, minute = int(match.group(1)), int(match.group(2))
        time = datetime.now().replace(hour=hour, minute=minute, second=0, microsecond=0)

    # Next, use spaCy's built-in entity recognition to find times
    if not time:  # Proceed if no time found by regex
        for ent in doc.ents:
            if ent.label_ == "TIME":
                # Process the time entity to set an alarm
                # Here we need to parse typical expressions like '8 o'clock'
                time_str = ent.text.replace("o'clock", "").strip()
                if time_str.isdigit():
                    hour = int(time_str)
                    time = datetime.now().replace(
                        hour=hour, minute=0, second=0, microsecond=0
                    )
                else:
                    # Handle other formats as necessary
                    pass

    return time


def format_time_difference(time_diff: timedelta) -> str:
    total_seconds = int(time_diff.total_seconds())
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    parts = []
    if hours > 0:
        parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
    if minutes > 0:
        parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
    if seconds > 0:
        parts.append(f"{seconds} second{'s' if seconds != 1 else ''}")
    return " and ".join(parts)
