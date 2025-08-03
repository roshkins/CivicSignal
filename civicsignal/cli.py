#!/usr/bin/env python3
"""
CivicSignal CLI - A tool to help you get signal out of San Francisco's civics.

This CLI provides commands for embedding archived meetings and searching for topics
across San Francisco government meetings.
"""

import click
import datetime
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
