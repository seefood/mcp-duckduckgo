#!/bin/bash
set -e

# Run tests with coverage
echo "Running tests with coverage..."
pytest --cov=mcp_duckduckgo tests/ --cov-report=term-missing

# Generate HTML coverage report
echo "Generating HTML coverage report..."
pytest --cov=mcp_duckduckgo tests/ --cov-report=html

echo "Tests completed. HTML coverage report available in htmlcov/" 