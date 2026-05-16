# Docs Buddy CLI

A command line interface for Docs Buddy that allows one to query docs
from the terminal.

## Usage

```bash
usage: python -m docs_buddy.entrypoints.cli [-h] [--repo-id REPO_IDS] [--update-sources | query]

Docs Buddy CLI

positional arguments:
  query               Query string to search the documentation

options:
  -h, --help          show this help message and exit
  --repo-id REPO_IDS  Repository ID(s). Can be used multiple times, each time for a different ID
  --update-sources    Update document sources from repository and recreate index
```
