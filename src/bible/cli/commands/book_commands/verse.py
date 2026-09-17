import asyncio
from typing import final

from clypi import Command, Positional, arg
from loguru import logger
from typing_extensions import override

from bible import console
from bible.mixins import BibleLookupMixin, ReferenceParserMixin
from bible.render import RenderMode, get_renderer


class Verse(BibleLookupMixin, ReferenceParserMixin, Command):
    """Retrieve a single Bible verse."""

    bible_name: str = arg(inherited=True)
    book_name: Positional[str] = arg(inherited=True)
    chapter_number: Positional[int] = arg(help='The number of the chapter to retrieve')
    verse_number: Positional[int] = arg(help='The number of the verse to retrieve')

    @final
    @classmethod
    def epilog(cls):
        return 'Attribution:\n  Data provided by API.Bible — https://api.bible.com'

    @override
    async def pre_run_hook(self):
        self.bible = self.find_bible(self.bible_name)
        self.book = self.find_book(self.bible_name, self.book_name)
        self.chapters = await self.load_or_fetch_chapters(self.bible, self.book)
        self.renderer = get_renderer(self.bible_name, RenderMode.VERSE)

    @override
    async def run(self):
        """Main execution method for the Verse command."""

        # Find chapter
        chapter = self.find_chapter(self.chapters, self.chapter_number)

        # Load or fetch verse list
        verses = await self.load_or_fetch_verses(self.bible, chapter, self.book_name)

        # Find verse metadata
        verse_meta = self.find_verse(
            verses,
            self.book_name,
            self.chapter_number,
            self.verse_number,
        )

        # Load or fetch verse content
        content = await self.load_or_fetch_verse_content(
            self.bible, self.book, chapter, verse_meta
        )

        # Render
        text = self.renderer(content.get('content', ''))
        console.out.print(text)


class Verses(BibleLookupMixin, ReferenceParserMixin, Command):
    """Retrieve multiple Bible verses."""

    bible_name: str = arg(inherited=True)
    book_name: Positional[str] = arg(inherited=True)
    chapter_number: Positional[int] = arg(help='The number of the chapter to retrieve')
    verse_numbers: Positional[list[int | str]] = arg(
        None,
        help="List of verse numbers or ranges. For example, '1 2 3', '5-9'.",
    )

    @override
    async def pre_run_hook(self):
        self.bible = self.find_bible(self.bible_name)
        self.book = self.find_book(self.bible_name, self.book_name)
        self.chapters = await self.load_or_fetch_chapters(self.bible, self.book)
        self.renderer = get_renderer(self.bible_name, RenderMode.VERSE)

    @override
    async def run(self):
        """Main execution method for the Verses command."""

        # Find chapter
        chapter = self.find_chapter(self.chapters, self.chapter_number)

        # Load or fetch verse list
        verses = await self.load_or_fetch_verses(self.bible, chapter, self.book_name)

        allowed = self.expand_verse_numbers(self.verse_numbers)

        async def fetch_verse(index, verse_meta):
            # Skip verses not in allowed list
            if allowed and index not in allowed:
                return None

            # Load or fetch verse content
            return await self.load_or_fetch_verse_content(
                self.bible, self.book, chapter, verse_meta
            )

        # Run all verse fetches concurrently
        tasks = [fetch_verse(i, v) for i, v in enumerate(verses, start=1)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        results = [r for r in results if isinstance(r, dict)]

        if not results:
            raise ValueError('No verses retrieved.')

        # Render
        for verse in results:
            text = self.renderer(verse.get('content', ''))
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
