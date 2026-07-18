import re
from pathlib import Path
from urllib.parse import unquote

PAPER_ID_PATTERN = re.compile(r'^\[(?P<paper_id>[A-Za-z]+\d+)\]')
FIGURE_PATTERN = re.compile(r'(?:figure|fig)[_\s.-]*(?P<figure_no>\d+[A-Za-z]?)', re.IGNORECASE)
DOI_PATTERN = re.compile(r'10\.\d{4,9}[/_][^\s/]+', re.IGNORECASE)


def parse_filename_metadata(filename: str) -> dict[str, str]:
    """Extract conservative paper/figure metadata without inventing values."""
    name = Path(unquote(filename)).name
    result: dict[str, str] = {}

    paper_match = PAPER_ID_PATTERN.search(name)
    if paper_match:
        result['paper_id'] = paper_match.group('paper_id').upper()

    figure_match = FIGURE_PATTERN.search(name)
    if figure_match:
        result['figure_no'] = figure_match.group('figure_no')

    doi_match = DOI_PATTERN.search(name)
    if doi_match:
        result['doi'] = doi_match.group(0).replace('_', '/', 1)

    return result
