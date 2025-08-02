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
git clone https://github.com/your-username/civicsignal.git
cd civicsignal
pip install -e .
```

## Quick Start

```python
from civicsignal import SanFranciscoArchiveBrowser, SF_ARCHIVE_GROUP

# Browse San Francisco archives
browser = SanFranciscoArchiveBrowser()
archives = browser.get_archives()

# Access specific archive groups
sf_archives = SF_ARCHIVE_GROUP
```

## Features

- **Archive Browsing**: Access San Francisco government archives
- **Data Ingestion**: Tools for ingesting civic data from various sources
- **Transformation**: Utilities for processing and transforming civic data
- **RAG Integration**: Ready-to-use RAG (Retrieval-Augmented Generation) components

## Development

### Setup Development Environment

```bash
# Clone the repository
git clone https://github.com/your-username/civicsignal.git
cd civicsignal

# Install in development mode with dev dependencies
pip install -e ".[dev]"
```

### Running Tests

```bash
# Run tests (when implemented)
pytest

# Run with coverage
pytest --cov=civicsignal
```

## Project Structure

```
civicsignal/
├── civicsignal/
│   ├── __init__.py          # Main package exports
│   ├── ingest/              # Data ingestion modules
│   │   ├── archives.py      # Archive browsing functionality
│   │   └── deepgram_test.py # Deepgram integration tests
│   └── Transform/           # Data transformation modules
│       └── RAGTest.py       # RAG testing utilities
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

1. Check the [Issues](https://github.com/your-username/civicsignal/issues) page
2. Create a new issue if your problem isn't already reported
3. Contact the maintainers

## Roadmap

- [ ] Enhanced archive browsing capabilities
- [ ] More comprehensive data ingestion tools
- [ ] Advanced RAG implementations
- [ ] API endpoints for web integration
- [ ] Documentation improvements
