#!/usr/bin/env python3

import datetime
import re
import time
from enum import Enum

import feedparser
import requests
from bs4 import BeautifulSoup

from civicsignal.utils import get_date_from_feed_entry

class SanFranciscoAgendaSource(Enum):
    """Agenda feeds for San Francisco's various commissions."""
    BOARD_OF_SUPERVISORS = ("https://sfbos.org/events/feed", "rss")
    PLANNING_COMMISSION = ("https://sfplanning.org/hearings-cpc-list", "html")
    ETHICS_COMMISSION = ("https://sfethics.org/ethics/category/agendas/feed", "rss")
    MUNICIPAL_TRANSPORTATION_AGENCY_SFMTA = ("https://www.sfmta.com/meetings-events", "html")
    # TODO: add more sources, see archives.py for more

    @property
    def url(self):
        return self.value[0]
    
    @property
    def format(self):
        return self.value[1]
    

class SanFranciscoAgendaParser:
    def __init__(self, source: SanFranciscoAgendaSource):
        self.source = source
        if self.source.format == "rss":
            self.feed = feedparser.parse(self.source.url)
        elif self.source.format == "html":
            # TODO: parse html, maybe use LLMs to parse them
            # All the commissions have different html structures, so we need to parse them differently
            # perhaps get LLMs + beautifulsoup to parse them
            raise NotImplementedError("HTML parsing not implemented yet")
        else:
            raise ValueError(f"Invalid format: {self.source.format}")

    def last_meeting_date(self) -> datetime.date:
        """Get the last meeting date for the current feed."""
        latest_entry = self.feed.entries[0]
        return get_date_from_feed_entry(latest_entry)

    def get_agenda_entry(self, date: datetime.date | None = None):
        """Get the agenda entry for the current feed."""
        if date is None:
            date = self.last_meeting_date()
        
        agenda_entry = None
        for entry in self.feed.entries:
            entry_date = get_date_from_feed_entry(entry)
            if entry_date == date:
                agenda_entry = entry
                break
        
        if agenda_entry is None:
            raise ValueError(f"No agenda items found for {date}")
        
        return agenda_entry
    
    def get_agenda_items(self, date: datetime.date | None = None):
        """Get the agenda items for the current feed."""
        agenda_entry = self.get_agenda_entry(date)
        request_url = agenda_entry.link
        response = requests.get(request_url)
        soup = BeautifulSoup(response.text, "html.parser")
        # check if the page is an agenda itself, or contains link to an agenda
        agenda_items = []
        for div in soup.find_all("div"):
            if div.id and "agenda" in div.id.lower():
                agenda_items.append(div.text)

        for link in soup.find_all("a"):
            if link.text and "agenda" in link.text.lower():
                agenda_items.append(link.text)
        return agenda_items

    
    # def get_agenda_iltem_topics(self, date: datetime.date | None = None):


def main():
    """Example usage."""
    # test_source = SanFranciscoAgendaSource.BOARD_OF_SUPERVISORS
    test_source = SanFranciscoAgendaSource.ETHICS_COMMISSION
    parser = SanFranciscoAgendaParser(test_source)
    # agenda_items = parser.get_agenda_items()
    # print(agenda_items)


if __name__ == "__main__":
    main()