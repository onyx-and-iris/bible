import asyncio
from typing import final

from clypi import Command, Positional, arg
from loguru import logger
from typing_extensions import override

from bible import console
from bible.api import BibleAPI
from bible.render import render_verse
from bible.sqlite import cache_json, load_json


class Verse(Command):
    """Retrieve a single Bible verse."""

    bible_name: str = arg(inherited=True)
    book_name: Positional[str] = arg(help='The name of the Bible book to retrieve')
    chapter_number: Positional[int] = arg(help='The number of the chapter to retrieve')
    verse_number: Positional[int] = arg(help='The number of the verse to retrieve')

    @final
    @classmethod
    def epilog(cls):
        return 'Attribution:\n  Data provided by Bible.API — https://api.bible.com'

    @override
    async def pre_run_hook(self):
        """Ensure chapter list is cached."""
        bibles = load_json('bibles:list')
        for bible in bibles:
            if bible.get('name', '') == self.bible_name:
                break
        else:
            raise ValueError(f"Bible with name '{self.bible_name}' not found.")

        books = load_json(f'books:list:{self.bible_name}')
        for book in books:
            if book.get('name', '') == self.book_name:
                break
        else:
            raise ValueError(f"Book with name '{self.book_name}' not found.")

        key = f'chapters:list:{self.bible_name}:{self.book_name}'
        chapters = load_json(key)
        if chapters:
            logger.debug(
                f"Using cached list of chapters for '{self.bible_name}:{self.book_name}'."
            )
        else:
            async with BibleAPI() as api:
                response = await api.get_chapters(bible['id'], book['id'])
                chapters = response.get('data', [])
                if not chapters:
                    raise ValueError(f"No chapters found for '{self.book_name}'.")
                cache_json(key, chapters)

    @override
    async def run(self):
        bibles = load_json('bibles:list')
        for bible in bibles:
            if bible.get('name', '') == self.bible_name:
                break
        else:
            raise ValueError(f"Bible with name '{self.bible_name}' not found.")

        chapters = load_json(f'chapters:list:{self.bible_name}:{self.book_name}')
        for chapter in chapters:
            if self.chapter_number == int(chapter.get('number', None)):
                break
        else:
            raise ValueError(
                f"Chapter number '{self.chapter_number}' not found in book '{self.book_name}'."
            )

        key = f'verses:list:{self.bible_name}:{self.book_name}:{self.chapter_number}'
        verses = load_json(key)
        if verses:
            logger.debug(
                f"Using cached list of verses for '{self.bible_name}:{self.book_name}:{self.chapter_number}'."
            )
        else:
            async with BibleAPI() as api:
                response = await api.get_verses(bible['id'], chapter['id'])
                verses = response.get('data', [])
                if not verses:
                    raise ValueError(
                        f'No verses found for chapter {self.chapter_number}.'
                    )
                cache_json(key, verses)

        # Match verse by reference string (e.g., "Ruth 1:1")
        target_ref = f'{self.book_name} {self.chapter_number}:{self.verse_number}'
        verse_meta = next((v for v in verses if v.get('reference') == target_ref), None)
        if not verse_meta:
            raise ValueError(f'Verse {target_ref} not found.')

        verse_id = verse_meta['id']
        cache_key = f'verses:content:{self.bible_name}:{self.book_name}:{self.chapter_number}:{self.verse_number}'

        verse_data = load_json(cache_key)
        if verse_data:
            logger.debug(f'Using cached verse {target_ref}.')
        else:
            async with BibleAPI() as api:
                response = await api.get_verse(bible['id'], verse_id)
                verse_data = response.get('data', {})
                if not verse_data:
                    raise ValueError(f'No content found for verse {target_ref}.')
                cache_json(cache_key, verse_data)

        text = render_verse(verse_data.get('content', ''))
        console.out.print(text)


class Verses(Command):
    """Retrieve multiple Bible verses."""

    bible_name: str = arg(inherited=True)
    book_name: Positional[str] = arg(help='The name of the Bible book to retrieve')
    chapter_number: Positional[int] = arg(help='The number of the chapter to retrieve')
    verse_numbers: Positional[list[int | str]] = arg(
        None, help="List of verse numbers or ranges. For example, '1 2 3', '5-9'."
    )

    @override
    async def pre_run_hook(self):
        """Ensure chapter list is cached."""
        bibles = load_json('bibles:list')
        for bible in bibles:
            if bible.get('name', '') == self.bible_name:
                break
        else:
            raise ValueError(f"Bible with name '{self.bible_name}' not found.")

        books = load_json(f'books:list:{self.bible_name}')
        for book in books:
            if book.get('name', '') == self.book_name:
                break
        else:
            raise ValueError(f"Book with name '{self.book_name}' not found.")

        key = f'chapters:list:{self.bible_name}:{self.book_name}'
        chapters = load_json(key)
        if not chapters:
            async with BibleAPI() as api:
                response = await api.get_chapters(bible['id'], book['id'])
                chapters = response.get('data', [])
                if not chapters:
                    raise ValueError(f"No chapters found for '{self.book_name}'.")
                cache_json(key, chapters)

    @override
    async def run(self):
        bibles = load_json('bibles:list')
        bible = next((b for b in bibles if b.get('name') == self.bible_name), None)
        if not bible:
            raise ValueError(f"Bible with name '{self.bible_name}' not found.")

        chapters = load_json(f'chapters:list:{self.bible_name}:{self.book_name}')
        chapter = next(
            (ch for ch in chapters if int(ch.get('number', 0)) == self.chapter_number),
            None,
        )
        if not chapter:
            raise ValueError(
                f"Chapter {self.chapter_number} not found in '{self.book_name}'."
            )

        key = f'verses:list:{self.bible_name}:{self.book_name}:{self.chapter_number}'
        verses = load_json(key)
        if not verses:
            async with BibleAPI() as api:
                response = await api.get_verses(bible['id'], chapter['id'])
                verses = response.get('data', [])
                if not verses:
                    raise ValueError(
                        f'No verses found for chapter {self.chapter_number}.'
                    )
                cache_json(key, verses)

        allowed = expand_verse_numbers(self.verse_numbers)

        async def fetch_verse(index, verse_meta):
            target_ref = f'{self.book_name} {self.chapter_number}:{index}'
            if allowed and index not in allowed:
                return None

            verse_id = verse_meta['id']
            cache_key = f'verses:content:{self.bible_name}:{self.book_name}:{self.chapter_number}:{index}'
            cached = load_json(cache_key)
            if cached:
                logger.debug(f'Using cached verse {target_ref}.')
                return cached

            async with BibleAPI() as api:
                response = await api.get_verse(bible['id'], verse_id)
                data = response.get('data', {})
                if not data:
                    logger.warning(f'No content found for verse {target_ref}.')
                    return None
                cache_json(cache_key, data)
                return data

        # ✅ Run all verse fetches concurrently
        tasks = [fetch_verse(i, v) for i, v in enumerate(verses, start=1)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        results = [r for r in results if isinstance(r, dict)]

        if not results:
            raise ValueError('No verses retrieved.')

        for verse in results:
            text = render_verse(verse.get('content', ''))
            console.out.print(text)


def expand_verse_numbers(verse_numbers):
    if not verse_numbers:
        return None

    allowed = set()

    for item in verse_numbers:
        # numeric int
        if isinstance(item, int):
            allowed.add(item)
            continue

        # numeric string
        if isinstance(item, str) and item.isdigit():
            allowed.add(int(item))
            continue

        # range string "5-9"
        if isinstance(item, str) and '-' in item:
            try:
                start, end = item.split('-', maxsplit=1)
                allowed.update(range(int(start), int(end) + 1))
            except ValueError:
                logger.warning(f"Invalid verse range '{item}'. Skipping.")
            continue

        logger.warning(f"Invalid verse number '{item}'. Skipping.")

    return allowed
