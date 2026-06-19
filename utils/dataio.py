"""CSV loading that respects each file's encoding and title-row offset.

`load_table` skips any banner rows above the header, then yields each data row
as an ordered dict keyed by the real header. Centralised here so no other module
hard-codes an encoding or a header offset.
"""
import csv
from typing import Dict, Iterator, List

from constants.config import FileSpec


def load_table(spec: FileSpec) -> List[Dict[str, str]]:
    """Read a source CSV into a list of {header: value} dicts."""
    with open(spec.path, encoding=spec.encoding, newline="") as fh:
        for _ in range(spec.header_row):
            next(fh)  # discard the title banner row(s)
        reader = csv.DictReader(fh)
        return [row for row in reader]


def iter_table(spec: FileSpec) -> Iterator[Dict[str, str]]:
    """Streaming variant for the large sales file."""
    with open(spec.path, encoding=spec.encoding, newline="") as fh:
        for _ in range(spec.header_row):
            next(fh)
        reader = csv.DictReader(fh)
        for row in reader:
            yield row
