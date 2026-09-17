import re

from bible.settings import CONFIG_FILES
from bible.util import normalise_user_book_input as _normalise_user_input

CHAPTER_VERSE_PATTERN = re.compile(
    r"""
    ^                      # start of string
    (?P<chapters>[\d\-]+)  # chapter or chapter-range (e.g. 1 or 1-3)
    (?:
        :                  # optional verse separator
        (?P<verses>[\d\-]+)  # verse or verse-range (e.g. 1 or 1-5)
    )?
    $                      # end of string
    """,
    re.VERBOSE,
)


def parse_reference(text: str):
    """
    Parse references like:
      Genesis
      Genesis 1
      Genesis 1:1
      Genesis 1-3
      Genesis 1:1-5
      Genesis 1-3:1-4
      1 Thes. 1:1
      Song of Songs 3-4:1-5

    Returns (book, chapter_numbers, verse_numbers)
    """
    text = text.strip()

    # --- Case 1: No digits at all → whole book ---
    if not re.search(r'\d', text):
        return text, None, None

    # --- Split from the right ---
    # e.g. "1 Thes. 1:1" -> ["1 Thes.", "1:1"]
    # e.g. "Song of Songs 3-4:1-5" -> ["Song of Songs", "3-4:1-5"]
    parts = text.rsplit(' ', 1)

    if len(parts) == 1:
        # Something like "Genesis1:1" (no space)
        book = ''
        rest = parts[0]
    else:
        book, rest = parts

    # --- Identify chapter/verse structure ---
    match = CHAPTER_VERSE_PATTERN.match(rest)
    if not match:
        # If the right-hand part doesn't match chapter/verse syntax,
        # treat the entire string as a book name.
        return text, None, None

    chapter_raw = match.group('chapters')
    verse_raw = match.group('verses')

    # Expand chapter ranges
    chapters = expand_numbers(chapter_raw.split())

    # Expand verse ranges (if any)
    verses = expand_numbers(verse_raw.split()) if verse_raw else None

    return book, chapters, verses


def expand_numbers(items: list[str | int]) -> list[int]:
    """Expand numbers and ranges like ['1', '3-5'] into [1,3,4,5]."""
    result = []

    for item in items:
        if isinstance(item, int):
            result.append(item)
            continue

        item = item.strip()

        if item.isdigit():
            result.append(int(item))
            continue

        if '-' in item:
            start, end = item.split('-', 1)
            if start.isdigit() and end.isdigit():
                result.extend(range(int(start), int(end) + 1))
                continue

        # Ignore invalid items silently
        continue

    return sorted(set(result))


def save_env_value(key: str, value: str):
    for pn in CONFIG_FILES:
        if pn.exists():
            env_path = pn
            break
    else:
        raise FileNotFoundError('No environment file found.')

    lines = env_path.read_text().splitlines()
    new_lines = []
    found = False

    for line in lines:
        if line.startswith(f'{key}='):
            new_lines.append(f'{key}="{value}"')
            found = True
        else:
            new_lines.append(line)

    if not found:
        new_lines.append(f'{key}="{value}"')

    env_path.write_text('\n'.join(new_lines))


normalise_user_book_input = _normalise_user_input
