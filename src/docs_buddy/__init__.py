"""Akash Docs Buddy

An AI agent helping you navigate Akash's documentation with ease.

Major functionality

- Updating retrieved documentation from the Github Repository
- Indexing the documentation
- Answer queries from the documentation
"""

from dataclasses import dataclass, asdict
import subprocess
from pathlib import Path
from urllib.parse import urlparse
import json
import shutil
import os
from typing import Union, Protocol, Iterator


