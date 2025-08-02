import datetime
import time
import re
import feedparser

ISO_DATE_REGEX = re.compile(r"(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2})")

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