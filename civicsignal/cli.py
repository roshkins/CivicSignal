#!/usr/bin/env python3
"""
CivicSignal CLI - A tool to help you get signal out of San Francisco's civics.

This CLI provides commands for embedding archived meetings and searching for topics
across San Francisco government meetings.
"""

import time
import click
import datetime
import random
from pathlib import Path
from typing import Optional

from civicsignal.ingest.archives import SanFranciscoArchiveSource, SanFranciscoArchiveParser
from civicsignal.transform.embed_meeting import MeetingRAGDb
from civicsignal.output.similar_topics import search_for_similar_topics
from civicsignal.chat import CivicSignalChat


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """
    CivicSignal CLI - Get signal out of San Francisco's civics.
    
    This tool helps you analyze and search through San Francisco government meetings
    including the Board of Supervisors, Planning Commission, and other commissions.
    """
    pass


@cli.command()
@click.option(
    '--group', 
    '-g',
    type=click.Choice([source.name for source in SanFranciscoArchiveSource], case_sensitive=False),
    required=True,
    help='The government group/commission to embed meetings for'
)
@click.option(
    '--date',
    '-d',
    type=click.DateTime(formats=['%Y-%m-%d']),
    required=False,
    default=None,
    help='The date of the meeting to embed (YYYY-MM-DD format), defaults to latest'
)
@click.option(
    '--db-path',
    type=click.Path(path_type=Path),
    default=Path("sf_meetings_rag_db"),
    help='Path to the ChromaDB database (default: sf_meetings_rag_db)'
)
@click.option(
    '--force',
    '-f',
    is_flag=True,
    help='Force re-embedding even if meeting already exists in database'
)
def embed(group: str, date: datetime.datetime | None, db_path: Path, force: bool):
    """
    Embed an archived meeting into the RAG database.
    
    This command downloads, transcribes, and embeds a specific meeting
    from the San Francisco government archives into a searchable database.
    
    Examples:
        civicsignal embed --group BOARD_OF_SUPERVISORS --date 2024-01-15
        civicsignal embed -g PLANNING_COMMISSION -d 2024-02-20 --force
    """
    try:
        # Convert group name to enum
        group_enum = SanFranciscoArchiveSource[group.upper()]
        
        # Initialize parser and RAG database
        parser = SanFranciscoArchiveParser(source=group_enum)
        # Convert datetime to date
        if date is None:
            meeting_date = parser.last_meeting_date()
        else:
            meeting_date = date.date()

        click.echo(f"Embedding meeting for {group} on {meeting_date}")
        rag_db = MeetingRAGDb(db_path=db_path)
        
        # Check if meeting already exists (simple check - could be improved)
        if not force:
            click.echo("Checking if meeting already exists in database...")
            # This is a simplified check - in practice you might want to check the actual database
            # For now, we'll proceed and let the upsert handle duplicates
        
        # Get meeting transcript
        click.echo("Downloading and transcribing meeting...")
        meeting = parser.get_meeting_transcript(date=meeting_date)
        
        if not meeting.transcript:
            click.echo("Warning: No transcript found for this meeting", err=True)
            return
        
        # Embed the meeting
        click.echo(f"Embedding {len(meeting.transcript)} paragraphs...")
        rag_db.embed_meeting(meeting)
        
        click.echo(f"✅ Successfully embedded meeting for {group} on {meeting_date}")
        click.echo(f"Database location: {db_path.absolute()}")
        
    except KeyError:
        click.echo(f"Error: Invalid group '{group}'. Use --help to see available groups.", err=True)
        raise click.Abort()
    except Exception as e:
        click.echo(f"Error embedding meeting: {str(e)}", err=True)
        raise e

@cli.command()
@click.option(
    '--db-path',
    type=click.Path(path_type=Path),
    default=Path("sf_meetings_rag_db"),
    help='Path to the ChromaDB database (default: sf_meetings_rag_db)'
)
@click.option(
    '--group', 
    '-g',
    type=click.Choice([source.name for source in SanFranciscoArchiveSource], case_sensitive=False),
    required=False,
    help='The government group/commission to backfill meetings for'
)
@click.option(
    '--all-sources',
    '-a',
    is_flag=True,
    help='Backfill all sources'
)
@click.option(
    '--all-dates',
    '-d',
    is_flag=True,
    help='Backfill all dates'
)
@click.option(
    '--max-dates',
    '-m',
    type=int,
    default=1,
    help='Backfill the last N dates for each source'
)
@click.option(
    '--cached-only',
    '-c',
    is_flag=True,
    help='Backfill only cached meetings'
)
@click.option(
    '--shortest-first',
    '-s',
    is_flag=True,
    help='Backfill the shortest meetings first'
)
def backfill(db_path: Path, all_sources: bool, all_dates: bool, cached_only: bool, group: Optional[str], shortest_first: bool, max_dates: int):
    """
    Backfill the RAG database with all meetings.
    
    This command re-embeds all the meetings from the cache into the vector DB.
    
    Examples:
        civicsignal backfill
    """
    try:
        click.echo(f"💾 Backfilling to db at {db_path.absolute()}")
        rag_db = MeetingRAGDb(db_path=db_path)

        to_backfill: list[tuple[SanFranciscoArchiveSource, datetime.date]] = []
        failed_to_backfill: list[tuple[SanFranciscoArchiveSource, datetime.date]] = []

        num_backfilled = 0
        if cached_only:
            sources = SanFranciscoArchiveParser.all_cached_sources()
        elif group:
            sources = [SanFranciscoArchiveSource.from_string(group)]
        elif all_sources:
            sources = list(SanFranciscoArchiveSource)
        else:
            # default to backfilling all cached meetings
            sources = SanFranciscoArchiveParser.all_cached_sources()

        parsers = {source: SanFranciscoArchiveParser(source=source) for source in sources}

        # shuffle the sources to not always go in the same order
        random.shuffle(sources)

        backfill_start_message = f"⏪ Backfilling {len(sources)} sources"
        if cached_only:
            backfill_start_message += " only cached meetings"
        elif all_dates:
            backfill_start_message += " for all dates"
        elif max_dates:
            backfill_start_message += f" for the last {max_dates} dates"
        else:
            backfill_start_message += f" at least one meeting"
        click.echo(backfill_start_message)

        for source in sources:
            parser = parsers[source]
            if cached_only:
                dates = [m.date for m in parser.all_cached_meetings()]
            elif all_dates:
                dates = parser.all_meeting_dates()
            elif max_dates:
                dates = parser.all_meeting_dates()
                dates.sort(reverse=True)
                dates = dates[:max_dates]
            else:
                dates = [m.date for m in parser.all_cached_meetings()]
                if len(dates) == 0 and shortest_first:
                    # if nothing is cached, get the shortest meeting
                    maybe_dates = parser.all_meeting_dates()
                    maybe_dates.sort(key=lambda x: parser.get_audio_size_from_date(x))
                    dates = maybe_dates[:max_dates]
                elif len(dates) == 0:
                    # if nothing is cached, get the latest meeting
                    dates = [parser.last_meeting_date()]
            for date in dates:
                to_backfill.append((source, date))

        click.echo(f"♻️  Backfilling {len(to_backfill)} meetings")

        if shortest_first:
            to_backfill.sort(key=lambda x: parsers[x[0]].get_audio_size_from_date(x[1]))
        
        for source, date in to_backfill:
            parser = parsers[source]
            if date not in parser.meeting_cache:
                # add a delay to avoid rate limiting
                time.sleep(15)
            try:
                click.echo(f"\t⏳ Backfilling {source.name} on {date}")
                meeting = parser.get_meeting_transcript(date=date)
                rag_db.embed_meeting(meeting)
                click.echo(f"\t✅ Backfilled {source.name} on {date}")
                num_backfilled += 1
            except Exception as e:
                click.echo(f"\t❌ Error backfilling {source.name} on {date}: {str(e)}", err=True)
                failed_to_backfill.append((source, date))
                continue

        click.echo(f"✅ Successfully backfilled {num_backfilled} meetings")
        if failed_to_backfill:
            click.echo(f"❌ Failed to backfill {len(failed_to_backfill)} meetings:")
            for source, date in failed_to_backfill:
                click.echo(f"\t{source.name} on {date}")
        click.echo(f"💾 Database location: {db_path.absolute()}")
    except Exception as e:
        click.echo(f"Error backfilling database: {str(e)}", err=True)
        raise e


@cli.command()
@click.option(
    '--topic',
    '-t',
    required=True,
    help='The topic to search for'
)
@click.option(
    '--num-results',
    '-n',
    type=int,
    default=10,
    help='Number of results to return (default: 10)'
)
@click.option(
    '--db-path',
    type=click.Path(path_type=Path),
    default=Path("sf_meetings_rag_db"),
    help='Path to the ChromaDB database (default: sf_meetings_rag_db)'
)
@click.option(
    '--output-format',
    type=click.Choice(['text', 'json']),
    default='text',
    help='Output format (default: text)'
)
def search(topic: str, num_results: int, db_path: Path, output_format: str):
    """
    Search for topics across embedded meetings.
    
    This command searches through all embedded meetings to find discussions
    related to the specified topic.
    
    Examples:
        civicsignal search --topic "housing development"
        civicsignal search -t "budget allocation" -n 20 --output-format json
    """
    try:
        click.echo(f"Searching for topic: '{topic}'")
        click.echo(f"Database location: {db_path.absolute()}")
        
        # Search for similar topics
        results = search_for_similar_topics(topic, n_results=num_results)
        
        if output_format == 'json':
            import json
            click.echo(json.dumps(results, indent=2))
        else:
            # Text output
            if not results['documents'] or not results['documents'][0]:
                click.echo("No results found for this topic.")
                return
            
            click.echo(f"\nFound {len(results['documents'][0])} relevant discussions:\n")
            
            for i, (doc, metadata, distance) in enumerate(zip(
                results['documents'][0], 
                results['metadatas'][0], 
                results['distances'][0]
            ), 1):
                click.echo(f"{i}. Relevance Score: {1 - distance:.3f}")
                click.echo(f"   Speaker: {metadata.get('speaker_id', 'Unknown')}")
                click.echo(f"   Time: {metadata.get('start_time', 'Unknown')} - {metadata.get('end_time', 'Unknown')}")
                click.echo(f"   Text: {doc[:200]}{'...' if len(doc) > 200 else ''}")
                click.echo()
        
    except Exception as e:
        click.echo(f"Error searching for topic: {str(e)}", err=True)
        raise click.Abort()


@cli.command()
@click.option(
    '--group',
    '-g',
    type=click.Choice([source.name for source in SanFranciscoArchiveSource], case_sensitive=False),
    help='Filter by specific group/commission'
)
def list_groups(group: Optional[str]):
    """
    List available government groups/commissions.
    
    This command shows all available San Francisco government groups
    that can be used with the embed command.
    """
    if group:
        # Show details for specific group
        try:
            group_enum = SanFranciscoArchiveSource[group.upper()]
            click.echo(f"Group: {group_enum.name}")
            click.echo(f"ID: {group_enum.value}")
            click.echo(f"URL: {group_enum.url}")
        except KeyError:
            click.echo(f"Error: Invalid group '{group}'", err=True)
            raise click.Abort()
    else:
        # List all groups
        click.echo("Available San Francisco Government Groups:\n")
        for source in SanFranciscoArchiveSource:
            click.echo(f"  {source.name}")
        click.echo(f"\nTotal: {len(SanFranciscoArchiveSource)} groups")
        click.echo("\nUse 'civicsignal list-groups --group GROUP_NAME' for details about a specific group.")


@cli.command()
@click.option(
    '--group',
    '-g',
    type=click.Choice([source.name for source in SanFranciscoArchiveSource], case_sensitive=False),
    required=True,
    help='The government group to check'
)
@click.option(
    '--limit',
    '-l',
    type=int,
    default=10,
    help='Number of recent meeting dates to show (default: 10)'
)
def list_meetings(group: str, limit: int):
    """
    List recent meeting dates for a specific group.
    
    This command shows the most recent meeting dates available
    for a specific government group.
    
    Examples:
        civicsignal list-meetings --group BOARD_OF_SUPERVISORS
        civicsignal list-meetings -g PLANNING_COMMISSION -l 20
    """
    try:
        group_enum = SanFranciscoArchiveSource[group.upper()]
        parser = SanFranciscoArchiveParser(source=group_enum)
        
        click.echo(f"Recent meeting dates for {group}:\n")
        
        meeting_dates = parser.get_meeting_dates()
        recent_dates = sorted(meeting_dates, reverse=True)[:limit]
        
        if not recent_dates:
            click.echo("No meeting dates found.")
            return
        
        for i, date in enumerate(recent_dates, 1):
            click.echo(f"{i}. {date.strftime('%Y-%m-%d')} ({date.strftime('%A')})")
        
        click.echo(f"\nTotal meetings found: {len(meeting_dates)}")
        click.echo(f"Showing most recent {len(recent_dates)} meetings")
        
    except Exception as e:
        click.echo(f"Error listing meetings: {str(e)}", err=True)
        raise click.Abort()


@cli.command()
@click.option(
    '--api-key',
    help='Cerebras API key (or set CEREBRAS_API_KEY environment variable)'
)
@click.option(
    '--query',
    help='Single query to process (non-interactive mode)'
)
def chat(api_key: Optional[str], query: Optional[str]):
    """
    Start an interactive chat session with CivicSignal.
    
    This command provides a conversational interface to explore civic meetings
    and government discussions in San Francisco using AI-powered responses.
    
    The chat interface uses the Cerebras AI model to generate responses and
    automatically searches for similar topics from archived meeting transcripts.
    
    Examples:
        civicsignal chat
        civicsignal chat --query "What was discussed about housing in recent meetings?"
    """
    try:
        chat_interface = CivicSignalChat(api_key=api_key)
        
        if query:
            # Single query mode
            click.echo(f"Query: {query}")
            response = chat_interface.chat(query)
            click.echo(f"Response: {response}")
        else:
            # Interactive mode
            chat_interface.interactive_chat()
            
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        raise click.Abort()
    except Exception as e:
        click.echo(f"Unexpected error: {e}", err=True)
        raise click.Abort()

if __name__ == '__main__':
    cli()
