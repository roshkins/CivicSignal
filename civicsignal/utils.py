import datetime
import time
import re
import logging
import os
from dataclasses import dataclass

import feedparser

log_level = os.getenv("CIVICSIGNAL_LOG_LEVEL", "INFO").upper()
logger = logging.getLogger("civicsignal")
logger.setLevel(log_level)

ISO_DATE_REGEX = re.compile(r"(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2})")

@dataclass
class Paragraph:
    start_time: float
    end_time: float
    speaker_id: str
    sentences: list[str]

    @property
    def text(self) -> str:
        return ' '.join(self.sentences)

@dataclass
class Meeting:
    date: datetime.date
    # Board of Supervisors, Planning Commission, etc.
    group: str
    transcript: list[Paragraph]
    topics: list[str]

def get_date_from_feed_entry(entry: feedparser.FeedParserDict) -> datetime.date:
    """Get the date from a feed entry."""
    parsed_date = entry.published_parsed
    if parsed_date is None:
        try:
            if (found:= ISO_DATE_REGEX.search(entry.published)) is not None:
                parsed_date = time.struct_time(
                    (int(found.group("year")), int(found.group("month")), int(found.group("day")), 0, 0, 0, 0, 0, 0)
                )
            else:
                raise ValueError(f"Invalid date format: {entry.published}")
        except AttributeError:
            raise ValueError(f"No published date found for {entry}")
    return datetime.date(parsed_date.tm_year, parsed_date.tm_mon, parsed_date.tm_mday)