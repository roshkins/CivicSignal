# CivicSignal

A tool to help you get signal out of San Francisco's civics.

CivicSignal provides tools to access and analyze data from San Francisco's civic institutions, including the Board of Supervisors, Planning Commission, and other commissions.

## Installation

### From PyPI (when published)
```bash
pip install civicsignal
```

### From source
```bash
git clone https://github.com/roshkins/CivicSignal.git
cd civicsignal
pip install -e .
```

## Quick Start

### Using the CLI

The CivicSignal CLI provides easy access to San Francisco government meeting data:

```bash
# List available government groups
civicsignal list-groups

# List recent meeting dates for a specific group
civicsignal list-meetings --group BOARD_OF_SUPERVISORS

# Embed a specific meeting into the searchable database
civicsignal embed --group BOARD_OF_SUPERVISORS --date 2024-01-15

# Search for topics across embedded meetings
civicsignal search --topic "housing development"

# Backfill the database with all meetings
civicsignal backfill --all-sources --all-dates

# Backfill the database with all cached meetings
civicsignal backfill --cached-only

# Backfill the database with all meetings for a specific group
civicsignal backfill --group BOARD_OF_SUPERVISORS

# Get help for any command
civicsignal --help
civicsignal embed --help
```

### Using the Python API

```python
from civicsignal import SanFranciscoArchiveParser, SanFranciscoArchiveSource

# Parser San Francisco archives
source = SanFranciscoArchiveSource.BOARD_OF_SUPERVISORS
parser = SanFranciscoArchiveParser(source)

# Get all meeting dates
dates = parser.get_meeting_dates()

# Get meeting transcript for a specific date
transcript = parser.get_meeting_transcript(dates[0])

# Get meeting topics
topics = parser.get_meeting_topics(dates[0])
```

## Features

- **Archive Browsing**: Access San Francisco government archives
- **Data Ingestion**: Tools for ingesting civic data from various sources
- **Transformation**: Utilities for processing and transforming civic data
- **RAG Integration**: Ready-to-use RAG (Retrieval-Augmented Generation) components
- **Output**: Tools for outputting data in various formats
- **CLI Interface**: Command-line tools for easy data access and analysis
- **Web App Interface**: Chat interface for asking questions about San Francisco government meetings

## CLI Commands

The CivicSignal CLI provides several commands for working with San Francisco government meeting data:

### `civicsignal list-groups`
List all available San Francisco government groups and commissions.

```bash
# List all groups
civicsignal list-groups

# Get details about a specific group
civicsignal list-groups --group BOARD_OF_SUPERVISORS
```

### `civicsignal list-meetings`
List recent meeting dates for a specific government group.

```bash
# List recent meetings for Board of Supervisors
civicsignal list-meetings --group BOARD_OF_SUPERVISORS

# Show more recent meetings
civicsignal list-meetings --group PLANNING_COMMISSION --limit 20
```

### `civicsignal embed`
Embed a specific meeting into the searchable RAG database. This command downloads, transcribes, and embeds the meeting for later searching.

```bash
# Embed a specific meeting
civicsignal embed --group BOARD_OF_SUPERVISORS --date 2024-01-15

# Use custom database path
civicsignal embed --group PLANNING_COMMISSION --date 2024-02-20 --db-path ./my_meetings_db

# Force re-embedding (overwrite existing)
civicsignal embed --group BOARD_OF_SUPERVISORS --date 2024-01-15 --force
```

### `civicsignal search`
Search for topics across all embedded meetings in the database.

```bash
# Search for housing-related discussions
civicsignal search --topic "housing development"

# Get more results
civicsignal search --topic "budget allocation" --num-results 20

# Output in JSON format
civicsignal search --topic "transportation" --output-format json

# Use custom database
civicsignal search --topic "environment" --db-path ./my_meetings_db
```

## Development

### Setup Development Environment

```bash
# Clone the repository
git clone https://github.com/roshkins/CivicSignal.git
cd civicsignal

# Install in development mode with dev dependencies
pip install -e ".[dev]"
```

## Project Structure

```
civicsignal/
├── civicsignal/
│   ├── ingest/              # Data ingestion modules
│   │   ├── archives.py      # Archive parsing functionality
│   │   └── agendas.py       # Agenda parsing functionality
│   └── transform/           # Data transformation modules
│       └── RAGTest.py       # testing RAG utilities
│   └── output/              # Output modules
│       └── similar_topics.py # Similar topics search
├── pyproject.toml           # Project configuration
├── README.md               # This file
└── uv.lock                 # Dependency lock file
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

If you encounter any issues or have questions, please:

1. Check the [Issues](https://github.com/roshkins/CivicSignal/issues) page
2. Create a new issue if your problem isn't already reported
3. Contact the maintainers

## Roadmap

- [ ] Enhanced archive browsing capabilities
- [ ] Add support for parsing through agendas
- [ ] Embed sentence by sentence data to the vector database
- [ ] Add support for updating agendas with timestamps/links to the meeting
- [ ] Add support for parsing live meetings
- [ ] Add support for parsing/linking with civlab.org
- [ ] Advanced RAG implementations
- [ ] Make transcript cache to a remote vector database
- [ ] API endpoints for web integration
- [ ] Support for remote vector databases
- [ ] Support for local LLMs
- [ ] Asynchronous processing of meetings
- [ ] Documentation improvements
- [ ] Make into MCP server
