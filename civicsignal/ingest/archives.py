#!/usr/bin/env python3
import datetime
import json
import os
import logging
from enum import Enum
from pathlib import Path
import random

import feedparser
import requests
from feedparser.util import FeedParserDict
from deepgram import DeepgramClient, PrerecordedOptions, PrerecordedResponse

from civicsignal.utils import get_date_from_feed_entry, Meeting, Paragraph

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
    def get_video_url_from_rss_entry(cls, entry: FeedParserDict):
        """Get the video URL for a given RSS entry."""
        return [link for link in entry.links if "video/" in link["type"] ][0]["href"]

    @classmethod
    def from_string(cls, name):
        """Get enum member from string name (case-insensitive)."""
        name = name.upper().replace('-', '_')
        try:
            return cls[name]
        except KeyError:
            return None

class SanFranciscoArchiveParser:
    DEFAULT_CACHE_DIR = Path("cache")
    def __init__(self, source: SanFranciscoArchiveSource = SanFranciscoArchiveSource.BOARD_OF_SUPERVISORS, cache_dir: Path = Path("cache")):
        self.source = source
        self.audio_rss_feed = feedparser.parse(source.audio_rss_url)
        if not self.audio_rss_feed.status == 200:
            raise Exception(f"Failed to fetch audio RSS feed for {source.name}")
        self.agenda_rss_feed = feedparser.parse(source.agenda_rss_url)
        if not self.agenda_rss_feed.status == 200:
            raise Exception(f"Failed to fetch agenda RSS feed for {source.name}")
        self.video_rss_feed = feedparser.parse(source.video_rss_url)
        if not self.video_rss_feed.status == 200:
            raise Exception(f"Failed to fetch video RSS feed for {source.name}")
        
        if DEEPGRAM_API_KEY is None:
            raise Exception("DEEPGRAM_API_KEY is not set")
        self.deepgram = DeepgramClient(DEEPGRAM_API_KEY)

        self.transcript_response_cache: dict[datetime.date, PrerecordedResponse] = {}
        self.transcript_response_disk_cache: dict[datetime.date, Path] = {}
        self.meeting_cache: dict[datetime.date, Meeting] = {}
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        for file in self.cache_dir.glob(f"transcript_*_{self.source.name}.json"):
            date = datetime.date.fromisoformat(file.stem.split("_")[1])
            self.transcript_response_disk_cache[date] = file
            self._get_transcript_from_disk(date)

    @classmethod
    def all_cached_sources(cls) -> list[SanFranciscoArchiveSource]:
        return [source for source in SanFranciscoArchiveSource if len(list(cls.DEFAULT_CACHE_DIR.glob(f"transcript_*_{source.name}.json"))) > 0]

    def all_cached_meetings(self) -> list[Meeting]:
        return [self.get_meeting_transcript(date) for date in self.transcript_response_disk_cache.keys()]

    def _transcript_path(self, date: datetime.date) -> Path:
        return self.cache_dir / f"transcript_{date}_{self.source.name}.json"

    def _get_transcript_from_disk(self, date: datetime.date) -> PrerecordedResponse:
        transcript_path = self._transcript_path(date)
        if date in self.transcript_response_disk_cache and transcript_path.is_file():
            with open(transcript_path, "r") as f:
                transcript = PrerecordedResponse.from_dict(json.load(f))
                self.transcript_response_cache[date] = transcript
                return transcript
        raise Exception(f"No transcript found for source {self.source.name} and date {date}")

    def _save_transcript_to_disk(self, date: datetime.date, transcript: PrerecordedResponse):
        if date not in self.transcript_response_disk_cache:
            self.transcript_response_disk_cache[date] = self._transcript_path(date)
        with open(self.transcript_response_disk_cache[date], "w") as f:
            json.dump(transcript.to_dict(), f, indent=4)


    def _get_rss_entry_from_date(self, date: datetime.date, rss_feed: feedparser.FeedParserDict, date_tolerance: datetime.timedelta = datetime.timedelta(days=1)) -> FeedParserDict:
        """Get the RSS entry for a given date.
        
        Args:
            date: The date to get the RSS entry for.
            rss_feed: The RSS feed to search in.
            date_tolerance: The tolerance for the date of the RSS entry.
                This is used to account for the fact that the date of the RSS entry
                may be slightly different from the date of the meeting.
                For example, the date of the RSS entry may be the day after the meeting.
                This is useful because the RSS feed is updated after the meeting.
        """
        for entry in rss_feed.entries:
            entry_date = get_date_from_feed_entry(entry)
            if entry_date == date or (entry_date - date) <= date_tolerance:
                return entry
        raise Exception(f"No RSS entry found for {self.source.name} on {date}")

    def get_audio_url_from_date(self, date: datetime.date) -> str:
        """Get the audio URL for a given clip ID."""
        entry = self._get_rss_entry_from_date(date, self.audio_rss_feed)
        return self.source.get_audio_url_from_rss_entry(entry)
    
    def get_video_url_from_date(self, date: datetime.date) -> str:
        """Get the video URL for a given clip ID."""
        entry = self._get_rss_entry_from_date(date, self.video_rss_feed)
        return self.source.get_video_url_from_rss_entry(entry)
    
    def last_meeting_date(self) -> datetime.date:
        """Get the last meeting date for the current feed."""
        return get_date_from_feed_entry(self.audio_rss_feed.entries[0])

    def all_meeting_dates(self) -> list[datetime.date]:
        """Get all meeting dates for the current feed."""
        return [get_date_from_feed_entry(entry) for entry in self.audio_rss_feed.entries]

    def download_audio(self, date: datetime.date) -> bytes:
        """Download the audio for a given date."""
        audio_url = self.get_audio_url_from_date(date)
        response = requests.get(audio_url)
        if response.status_code != 200:
            raise Exception(f"Failed to download audio for {date}")
        return response

    def _transcribe_audio(self, date: datetime.date | None = None) -> PrerecordedResponse:
        if date in self.transcript_response_cache:
            return self.transcript_response_cache[date]
        
        if date in self.transcript_response_disk_cache:
            return self._get_transcript_from_disk(date)
        
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

            audio_data = self.download_audio(date)
            # source = {"buffer": audio_data.content}
            source = {"stream": audio_data.iter_content(chunk_size=8192)}

            response = self.deepgram.listen.rest.v("1").transcribe_file(
                source=source,
                options=options,
            )

            self.transcript_response_cache[date] = response
            self._save_transcript_to_disk(date, response)

            return response

        except Exception as e:
            logging.error(f"Exception while transcribing audio: {e}")
            raise e

    def _get_raw_transcribed_meeting(self, date: datetime.date | None = None) -> PrerecordedResponse:
        if date is None:
            date = self.last_meeting_date()

        if date in self.transcript_response_cache:
            logging.debug(f"Using cached transcript for {date}")
            return self.transcript_response_cache[date]
        
        if date in self.transcript_response_disk_cache:
            logging.debug(f"Using cached transcript from disk for {date}")
            return self._get_transcript_from_disk(date)        
        
        logging.debug(f"Transcribing audio for {date}")
        return self._transcribe_audio(date)
        

    def get_meeting_transcript(self, date: datetime.date | None = None) -> Meeting:
        if date in self.meeting_cache:
            return self.meeting_cache[date]
        
        if date is None:
            date = self.last_meeting_date()
        
        response = self._get_raw_transcribed_meeting(date)
        paragraphs = response.results.channels[0].alternatives[0].paragraphs.paragraphs
        paragraphs = [
            Paragraph(
                start_time=paragraph.start,
                end_time=paragraph.end,
                speaker_id=paragraph.speaker,
                sentences=[sentence.text for sentence in paragraph.sentences]
            ) for paragraph in paragraphs]
        unique_topics = { topic.topic for segment in response.results.topics.segments for topic in segment.topics }
        meeting = Meeting(
            date=date,
            group=self.source.name,
            transcript=paragraphs,
            topics=list(unique_topics),
            video_url=self.get_video_url_from_date(date),
        )
        self.meeting_cache[date] = meeting
        return meeting
    
    def get_meeting_topics(self, date: datetime.date | None = None) -> list[str]:
        """Get the topics for a given meeting."""
        return self.get_meeting_transcript(date).topics
    

def main():
    test_source = SanFranciscoArchiveSource.PUBLIC_UTILITIES_COMMISSION
    test_date = datetime.date(2025, 7, 22)
    parser = SanFranciscoArchiveParser(test_source)
    transcript = parser.get_meeting_transcript(test_date)

    print(transcript)

if __name__ == "__main__":
    main()
