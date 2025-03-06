# MCP DuckDuckGo Search Plugin

A DuckDuckGo search plugin for Model Context Protocol (MCP), compatible with Claude Code.

[![PyPI version](https://badge.fury.io/py/mcp-duckduckgo.svg)](https://badge.fury.io/py/mcp-duckduckgo)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Description

This project implements a Model Context Protocol (MCP) server that provides web search functionality using DuckDuckGo. The plugin can be used with Claude Code or any other client that supports MCP.

## Features

- **Web Search Tool**: Perform web searches using DuckDuckGo
- **Search Documentation**: Access comprehensive documentation about the search functionality
- **Search Assistant**: Get help formulating effective search queries
- **Parameterized Resource**: Retrieve formatted search results for specific queries

## Requirements

- Python 3.9 or higher
- pip (Python package manager)
- Python packages listed in `pyproject.toml`

## Installation

### From PyPI

```bash
pip install mcp-duckduckgo
```

### From Source

1. Clone this repository:

   ```bash
   git clone https://github.com/gianlucamazza/mcp_duckduckgo.git
   cd mcp_duckduckgo
   ```

2. Install the package in development mode:

   ```bash
   pip install -e .
   ```

   Or use the provided script:

   ```bash
   ./scripts/install_dev.sh
   ```

   Or use Make:

   ```bash
   make install
   ```

## Usage

### Starting the Server Manually

To start the MCP server:

```bash
mcp-duckduckgo
```

Or with custom parameters:

```bash
mcp-duckduckgo --host 127.0.0.1 --port 8000
```

Or use the provided script for development:

```bash
./scripts/run.sh
```

Or use Make:

```bash
make run
```

### Using with Claude Code

1. Install the package:

   ```bash
   pip install mcp-duckduckgo
   ```

2. Configure Claude Code to use the plugin:

   ```bash
   claude mcp add duckduckgo-search -- mcp-duckduckgo
   ```

3. For global configuration (available in all projects):

   ```bash
   claude mcp add duckduckgo-search --scope global -- mcp-duckduckgo
   ```

4. Start Claude Code:

   ```bash
   claude
   ```

5. Now you can use the DuckDuckGo search functionality within Claude Code.

## Available Endpoints

The plugin provides the following endpoints:

### Tool: `duckduckgo_web_search`

Performs a web search using DuckDuckGo with the following parameters:

- `query` (required): The search query (max 400 characters, 50 words)
- `count` (optional, default: 10): Number of results (1-20)
- `offset` (optional, default: 0): Pagination offset

Example usage in Claude Code:

```text
Search for "artificial intelligence latest developments"
```

### Resource: `docs://search`

Provides comprehensive documentation about the search functionality.

Example usage in Claude Code:

```text
Show me the documentation for the DuckDuckGo search
```

### Prompt: `search_assistant`

Helps formulate effective search queries.

Example usage in Claude Code:

```text
Help me formulate a search query about climate change solutions
```

### Resource: `search://{query}`

Retrieves formatted search results for a specific query.

Example usage in Claude Code:

```text
Get search results for "quantum computing breakthroughs"
```

## Implementation Notes

This implementation uses DuckDuckGo's public web interface and parses the HTML response to extract results. This approach is used for demonstration purposes, as DuckDuckGo does not offer an official search API. In a production environment, it's recommended to use a search service with an official API.

## Development

The project includes several utility scripts in the `scripts` directory to help with development:

- `install_dev.sh`: Sets up the development environment
- `run.sh`: Runs the MCP server with development settings
- `test.sh`: Runs tests with coverage reporting
- `lint.sh`: Runs linting and code formatting
- `publish.sh`: Builds and publishes the package to PyPI

For convenience, a Makefile is also provided with the following targets:

```bash
make install  # Install the package in development mode
make test     # Run tests with coverage
make lint     # Run linting and code formatting
make run      # Run the MCP server
make publish  # Build and publish the package to PyPI
make clean    # Clean build artifacts
make all      # Run install, lint, and test (default)
make help     # Show help message
```

### Running Tests

```bash
pytest
```

Or use the provided script:

```bash
./scripts/test.sh
```

Or use Make:

```bash
make test
```

### Code Formatting and Linting

```bash
black mcp_duckduckgo
isort mcp_duckduckgo
mypy mcp_duckduckgo
```

Or use the provided script:

```bash
./scripts/lint.sh
```

Or use Make:

```bash
make lint
```

### Publishing to PyPI

To build and publish the package to PyPI:

```bash
./scripts/publish.sh
```

Or use Make:

```bash
make publish
```

## License

[MIT](LICENSE)
