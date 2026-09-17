import re

from loguru import logger

from . import util
from .api import BibleAPI
from .sqlite import cache_json, load_json


class BibleLookupMixin:
    """Shared lookup + caching + API fetch helpers for CLI and TUI."""

    # -----------------------
    # Lookup helpers
    # -----------------------

    def find_bible(self, name: str):
        bibles = load_json('bibles:list')
        bible = next((b for b in bibles if b.get('name') == name), None)
        if not bible:
            raise ValueError(f"Bible with name '{name}' not found.")
        return bible

    def find_book(self, bible_name: str, user_book_name: str):
        books = load_json(f'books:list:{bible_name}')
        if not books:
            raise ValueError(f"No books found for Bible '{bible_name}'.")

        target = util.normalise_user_book_input(user_book_name)

        # 1. Exact normalized match
        for b in books:
            if util.normalise_user_book_input(b.get('name', '')) == target:
                return b

        # 2. Abbreviation match (API-provided)
        for b in books:
            abbr = util.normalise_user_book_input(b.get('abbreviation', ''))
            if abbr == target:
                return b

        # 3. Startswith match (e.g., "gen" → "Gen.")
        for b in books:
            if util.normalise_user_book_input(b.get('name', '')).startswith(target):
                return b

        raise ValueError(f"Book with name '{user_book_name}' not found.")

    def find_chapter(self, chapters: list[dict], chapter_number: str | int):
        """Handles numeric chapters and 'intro' chapters."""
        chapter = next(
            (
                ch
                for ch in chapters
                if (ch.get('number') == 'intro' and chapter_number == 'intro')
                or (
                    ch.get('number') not in ('intro', None)
                    and str(chapter_number) == str(ch.get('number'))
                )
            ),
            None,
        )
        if not chapter:
            raise ValueError(f"Chapter '{chapter_number}' not found.")
        return chapter

    def find_verse(
        self,
        verses: list[dict],
        book_name: str,
        chapter_number: str | int,
        verse_number: str | int,
    ):
        target_ref = f'{book_name} {chapter_number}:{verse_number}'
        verse = next((v for v in verses if v.get('reference') == target_ref), None)
        if not verse:
            raise ValueError(f"Verse '{target_ref}' not found.")
        return verse

    # -----------------------
    # Cached list loaders
    # -----------------------

    async def load_or_fetch_bibles(self):
        key = 'bibles:list'
        cached = load_json(key)
        if cached:
            logger.debug('Using cached list of Bibles.')
            return cached

        async with BibleAPI() as api:
            response = await api.get_bibles()
            data = response.get('data', [])
            if not data:
                raise ValueError('Unable to fetch list of Bibles.')
            cache_json(key, data)
            return data

    async def load_or_fetch_books(self, bible: dict):
        key = f'books:list:{bible["name"]}'
        cached = load_json(key)
        if cached:
            logger.debug(f'Using cached list of books for Bible: {bible["name"]}')
            return cached

        async with BibleAPI() as api:
            response = await api.get_books(bible['id'])
            data = response.get('data', [])
            if not data:
                raise ValueError(f"Unable to fetch books for Bible '{bible['name']}'.")
            cache_json(key, data)
            return data

    async def load_or_fetch_chapters(self, bible: dict, book: dict):
        key = f'chapters:list:{bible["name"]}:{book["name"]}'
        cached = load_json(key)
        if cached:
            logger.debug(f'Using cached list of chapters for book: {book["name"]}')
            return cached

        async with BibleAPI() as api:
            response = await api.get_chapters(bible['id'], book['id'])
            data = response.get('data', [])
            if not data:
                raise ValueError(f"No chapters found for '{book['name']}'.")
            cache_json(key, data)
            return data

    async def load_or_fetch_verses(self, bible: dict, chapter: dict, book_name: str):
        key = f'verses:list:{bible["name"]}:{book_name}:{chapter["number"]}'
        cached = load_json(key)
        if cached:
            logger.debug(
                f'Using cached list of verses for chapter: {chapter["number"]}'
            )
            return cached

        async with BibleAPI() as api:
            response = await api.get_verses(bible['id'], chapter['id'])
            data = response.get('data', [])
            if not data:
                raise ValueError(f'No verses found for chapter {chapter["number"]}.')
            cache_json(key, data)
            return data

    # -----------------------
    # Cached content loaders
    # -----------------------

    async def load_or_fetch_chapter_content(
        self, bible: dict, book: dict, chapter: dict
    ):
        key = f'chapters:content:{bible["name"]}:{book["name"]}:{chapter["number"]}'
        cached = load_json(key)
        if cached:
            logger.debug(
                f"Using cached chapter '{bible['name']}:{book['name']}:{chapter['number']}'"
            )
            return cached

        async with BibleAPI() as api:
            response = await api.get_chapter(bible['id'], chapter['id'])
            data = response.get('data', {})
            if not data:
                raise ValueError(f'No content found for chapter {chapter["number"]}.')
            cache_json(key, data)
            return data

    async def load_or_fetch_verse_content(
        self, bible: dict, book: dict, chapter: dict, verse: dict
    ):
        number = verse['reference'].split(':')[1]
        key = f'verses:content:{bible["name"]}:{book["name"]}:{chapter["number"]}:{number}'

        cached = load_json(key)
        if cached:
            logger.debug(
                f"Using cached verse '{bible['name']}:{book['name']}:{chapter['number']}:{number}'"
            )
            return cached

        async with BibleAPI() as api:
            response = await api.get_verse(bible['id'], verse['id'])
            data = response.get('data', {})
            if not data:
                raise ValueError(f'No content found for verse {verse["reference"]}.')
            cache_json(key, data)
            return data


class ReferenceParserMixin:
    """Shared reference parsing helpers."""

    CHAPTER_VERSE_PATTERN = re.compile(
        r"""
        ^(?P<chapters>[\d\-]+)
        (?::(?P<verses>[\d\-]+))?
        $""",
        re.VERBOSE,
    )

    def parse_reference(self, text: str):
        text = text.strip()

        # Whole-book reference (no digits)
        if not re.search(r'\d', text):
            return text, None, None

        # Split from the right
        parts = text.rsplit(' ', 1)
        if len(parts) == 1:
            book = ''
            rest = parts[0]
        else:
            book, rest = parts

        match = self.CHAPTER_VERSE_PATTERN.match(rest)
        if not match:
            return text, None, None

        chapter_raw = match.group('chapters')
        verse_raw = match.group('verses')

        chapters = self.expand_numbers(chapter_raw.split())
        verses = self.expand_numbers(verse_raw.split()) if verse_raw else None

        return book, chapters, verses

    def expand_numbers(self, items):
        """Expand ranges like ['1', '3-5'] into [1, 3, 4, 5]."""
        if items is None:
            return None

        result = []
        for item in items:
            if '-' in item:
                start, end = item.split('-', 1)
                result.extend(range(int(start), int(end) + 1))
            else:
                result.append(int(item))
        return result

    def expand_chapter_numbers(self, items):
        return self.expand_numbers(items)

    def expand_verse_numbers(self, items):
        return self.expand_numbers(items)
