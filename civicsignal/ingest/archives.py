#!/usr/bin/env python3
import datetime
import os
from enum import Enum

import feedparser
import requests
from feedparser.util import FeedParserDict
from deepgram import DeepgramClient, PrerecordedOptions, PrerecordedResponse

from civicsignal.ingest.utils import get_date_from_feed_entry

DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")

class SanFranciscoArchiveSource(Enum):
    ADDITIONAL_PROGRAMS = "74"
    AGING_AND_ADULT_SERVICES = "174"
    ARTS_COMMISSION = "230"
    ARTS_COMMISSION_COMMITTEE = "233"
    BOARD_OF_APPEALS = "6"
    BOARD_OF_SUPERVISORS = "10"
    BUDGET_AND_APPROPRIATIONS_COMMITTEE = "207"
    BUDGET_AND_FINANCE_COMMITTEE = "7"
    BUDGET_AND_FINANCE_FEDERAL_SELECT_COMMITTEE = "190"
    BUDGET_AND_FINANCE_SUB_COMMITTEE = "189"
    BUILDING_INSPECTION_COMMISSION_ABATEMENT_APPEALS_BOARD = "14"
    BUILDING_SF = "3"
    CITIZENS_GENERAL_OBLIGATION_BOND_OVERSIGHT_COMMITTEE = "191"
    CITY_AND_SCHOOL_DISTRICTS_SELECT_COMMITTEE = "9"
    CITY_EVENTS = "90"
    CITY_EVENTS_INFO_SUMMITS = "74"
    CITY_INFORMATION = "89"
    CITY_OPERATIONS_AND_NEIGHBORHOOD_SERVICES_COMMITTEE = "8"
    CITY_SUMMITS = "88"
    COMMISSIONS_COUNCILS_BOARDS = "20"
    COMMONWEALTH_CLUB = "143"
    COMMUNITY_INVESTMENT_AND_INFRASTRUCTURE_COMMISSION = "169"
    DISABILITY_AND_AGING_SERVICES_COMMISSION = "206"
    DISASTER_COUNCIL = "15"
    EDUCATION_SFUSD_BOARD_OF = "47"
    ELECTION_PROGRAMMING = "42"
    ELECTION_PROGRAMMING_ARCHIVE = "200"
    ENTERTAINMENT_COMMISSION = "99"
    ENVIRONMENT_COMMISSION_ON_THE = "165"
    ETHICS_COMMISSION = "142"
    FIRE_COMMISSION = "180"
    GOVERNMENT_AUDIT_AND_OVERSIGHT_COMMITTEE = "11"
    HEALTH_COMMISSION_DEPARTMENT_OF_PUBLIC_HEALTH = "171"
    HEALTH_SERVICE_BOARD = "168"
    HISTORIC_PRESERVATION_COMMISSION = "166"
    HOMELESSNESS_AND_BEHAVIORAL_HEALTH_SELECT_COMMITTEE = "225"
    HOMELESSNESS_OVERSIGHT_COMMISSION = "227"
    HOUSING_AUTHORITY_BOARD_OF_DIRECTORS = "229"
    HUMAN_RIGHTS_COMMISSION = "156"
    JOINT_CITY_SCHOOL_DISTRICT_AND_CITY_COLLEGE_SELECT_COMMITTEE = "203"
    LAND_USE_AND_ECONOMIC_DEVELOPMENT_COMMITTEE = "12"
    LAND_USE_AND_TRANSPORTATION_COMMITTEE = "177"
    LOCAL_AGENCY_FORMATION_COMMISSION = "16"
    MAIN_STAGE = "57"
    MAYOR_BREED_ARCHIVE = "235"
    MAYOR_FARRELL_ARCHIVE = "198"
    MAYOR_LEE_ARCHIVE = "197"
    MAYOR_NEWSOM_ARCHIVE = "106"
    MAYORS_DISABILITY_COUNCIL = "17"
    MAYORS_PRESS_CONFERENCE = "18"
    MAYORS_PRESS_CONFERENCE_1 = "18"
    MEET_YOUR_DISTRICT_SUPERVISOR = "107"
    MUNICIPAL_TRANSPORTATION_AGENCY_SFMTA = "55"
    NEIGHBORHOOD_SERVICES_AND_SAFETY_COMMITTEE = "164"
    OUR_CITY_OUR_HOME_OVERSIGHT_COMMITTEE = "209"
    PLANNING_COMMISSION = "20"
    POLICE_COMMISSION = "21"
    PORT_COMMISSION = "92"
    PRESS_CONFERENCE = "38"
    PUBLIC_SAFETY_AND_NEIGHBORHOOD_SERVICES_COMMITTEE = "178"
    PUBLIC_SAFETY_COMMITTEE = "44"
    PUBLIC_UTILITIES_COMMISSION = "22"
    PUBLIC_WORKS_COMMISSION = "218"
    RECREATION_AND_PARK_COMMISSION = "91"
    REDISTRICTING_TASK_FORCE = "155"
    REFUSE_RATE_BOARD = "226"
    RETIREMENT_BOARD_SAN_FRANCISCO_EMPLOYEES = "175"
    RULES_COMMITTEE = "13"
    SANITATION_STREETS_COMMISSION = "219"
    SHERIFFS_DEPARTMENT_OVERSIGHT_BOARD = "223"
    SMALL_BUSINESS_COMMISSION = "45"
    TAXICAB_COMMISSION = "28"
    TRANSBAY_JOINT_POWERS_AUTHORITY_BOARD_OF_DIRECTORS = "29"
    TRANSPORTATION_AUTHORITY_FINANCE_COMMITTEE = "23"
    TRANSPORTATION_AUTHORITY_FULL_BOARD = "24"
    TRANSPORTATION_AUTHORITY_PERSONNEL_COMMITTEE = "27"
    TRANSPORTATION_AUTHORITY_PLANS_PROGRAMS_COMMITTEE = "25"
    TRANSPORTATION_AUTHORITY_VISION_ZERO_COMMITTEE = "172"
    TREASURE_ISLAND_DEVELOPMENT_AUTHORITY = "181"
    TREASURE_ISLAND_DEVELOPMENT_AUTHORITY_COMMITTEE = "193"
    TREASURE_ISLAND_MOBILITY_MANAGEMENT_AGENCY = "179"
    VARIOUS_COMMISSIONS = "30"
    YOUTH_YOUNG_ADULT_AND_FAMILIES_COMMITTEE = "211"

    @classmethod
    def get_url(cls, vod_id):
        """Get the SF VOD URL for a given view ID."""
        if isinstance(vod_id, cls):
            return vod_id.url
        return f"https://sanfrancisco.granicus.com/ViewPublisher.php?view_id={vod_id}"

    @property
    def url(self):
        """Get the SF VOD URL for a given view ID."""
        return f"https://sanfrancisco.granicus.com/ViewPublisher.php?view_id={self.value}"

    @property
    def video_rss_url(self):
        """Get the SF VOD RSS URL for a given view ID."""
        return f"https://sanfrancisco.granicus.com/ViewPublisherRSS.php?view_id={self.value}"

    @property
    def agenda_rss_url(self):
        """Get the SF VOD RSS URL for a given view ID."""
        return f"https://sanfrancisco.granicus.com/ViewPublisherRSS.php?view_id={self.value}&mode=agendas"

    @property
    def audio_rss_url(self):
        """Get the SF VOD RSS URL for a given view ID."""
        return f"https://sanfrancisco.granicus.com/Podcast.php?view_id={self.value}"


    @classmethod
    def get_audio_url_from_rss_entry(cls, entry: FeedParserDict):
        """Get the audio URL for a given RSS entry."""
        return [link for link in entry.links if "audio/" in link["type"] ][0]["href"]

    @classmethod
    def from_string(cls, name):
        """Get enum member from string name (case-insensitive)."""
        name = name.upper().replace('-', '_')
        try:
            return cls[name]
        except KeyError:
            return None

class SanFranciscoArchiveParser:
    def __init__(self, source: SanFranciscoArchiveSource = SanFranciscoArchiveSource.BOARD_OF_SUPERVISORS):
        self.source = source
        self.audio_rss_feed = feedparser.parse(source.audio_rss_url)
        if not self.audio_rss_feed.status == 200:
            raise Exception(f"Failed to fetch audio RSS feed for {source.name}")
        self.agenda_rss_feed = feedparser.parse(source.agenda_rss_url)
        if not self.agenda_rss_feed.status == 200:
            raise Exception(f"Failed to fetch agenda RSS feed for {source.name}")
        
        if DEEPGRAM_API_KEY is None:
            raise Exception("DEEPGRAM_API_KEY is not set")
        self.deepgram = DeepgramClient(DEEPGRAM_API_KEY)

        self.meeting_transcript_cache: dict[datetime.date, PrerecordedResponse] = {}

    def get_audio_url_from_date(self, date: datetime.date) -> str:
        """Get the audio URL for a given clip ID."""
        for entry in self.audio_rss_feed.entries:
            entry_date = get_date_from_feed_entry(entry)
            if entry_date == date:
                return self.group.get_audio_url_from_rss_entry(entry)
        raise Exception(f"No audio URL found for {date}")
    
    def last_meeting_date(self) -> datetime.date:
        """Get the last meeting date for the current feed."""
        return get_date_from_feed_entry(self.audio_rss_feed.entries[0])

    def download_audio(self, date: datetime.date) -> bytes:
        """Download the audio for a given date."""
        audio_url = self.get_audio_url_from_date(date)
        response = requests.get(audio_url)
        return response.content

    def transcribe_audio(self, date: datetime.date | None = None) -> PrerecordedResponse:
        if date in self.meeting_transcript_cache:
            return self.meeting_transcript_cache[date]
        
        try:
            if date is None:
                date = self.last_meeting_date()

            options = PrerecordedOptions(
                model="nova-3",
                language="en",
                smart_format=True,
                diarize=True,
                topics=True,
                detect_entities=True,
                paragraphs=True,
                # utterances=True, # add this if we need smaller chunks
            )

            audio_bytes = self.download_audio(date)
            source = {"buffer": audio_bytes}
            # or we can do source = {"stream": requests.get(audio_url).iter_content(chunk_size=8192)}

            response = self.deepgram.listen.rest.v("1").transcribe_file(
                source=source,
                options=options,
            )

            self.meeting_transcript_cache[date] = response

            return response

        except Exception as e:
            print(f"Unknown Exception: {e}")
            raise e

    def _get_meeting_transcript(self, date: datetime.date | None = None) -> PrerecordedResponse:
        if date in self.meeting_transcript_cache:
            return self.meeting_transcript_cache[date]
        
        if date is None:
            date = self.last_meeting_date()
        return self.transcribe_audio(date)
    
    def get_meeting_topics(self, date: datetime.date | None = None) -> list[str]:
        """Get the topics for a given meeting."""
        response = self._get_meeting_transcript(date)
        unique_topics = { topic.topic for segment in response.results.topics.segments for topic in segment.topics }
        return unique_topics
    

def main():
    test_source = SanFranciscoArchiveSource.PUBLIC_UTILITIES_COMMISSION
    test_date = datetime.date(2025, 7, 22)
    parser = SanFranciscoArchiveParser(test_source)
    topics = parser.get_meeting_topics(test_date)
    print(topics)

if __name__ == "__main__":
    main()
