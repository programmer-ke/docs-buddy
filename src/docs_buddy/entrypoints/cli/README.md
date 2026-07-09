# Docs Buddy CLI

A command line interface for Docs Buddy that allows one to query docs
from the terminal.

## Usage

```bash
usage: __main__.py [-h] [--log-level {DEBUG,INFO,WARNING,ERROR,CRITICAL}] [--update-sources] [--init]
                   [--current-config]
                   [query]

Docs Buddy CLI

positional arguments:
  query                 Query string to search the documentation

options:
  -h, --help            show this help message and exit
  --log-level {DEBUG,INFO,WARNING,ERROR,CRITICAL}
                        The log level to use (default WARNING)
  --update-sources      Update document sources from repository and recreate index
  --init                Create a .docs_buddy.yaml config file from template in the current directory
  --current-config      Show location of the current config file in use
```
