from pathlib import Path


def parse_reference(text: str):
    """
    Parse references like:
      Genesis 1
      Genesis 1:1
      Genesis 1-3
      Genesis 1:1-5
      Genesis 1-3:1-4
    Returns (book, chapter_numbers, verse_numbers)
    """
    text = text.strip()

    try:
        book, rest = text.split(maxsplit=1)
    except ValueError:
        raise ValueError('Invalid format. Use: Genesis 1 or Genesis 1:1')

    # Chapter and verse part
    if ':' in rest:
        chapter_part, verse_part = rest.split(':', 1)
        chapter_items = chapter_part.split()
        verse_items = verse_part.split()
        chapters = expand_numbers(chapter_items)
        verses = expand_numbers(verse_items)
        return book, chapters, verses

    # Only chapters
    chapter_items = rest.split()
    chapters = expand_numbers(chapter_items)
    return book, chapters, None


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
    env_path = Path('.env')
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
