import asyncio
from typing import final

from clypi import Command, Positional, Spinner, arg
from loguru import logger
from typing_extensions import override

from bible import console
from bible.mixins import BibleLookupMixin, ReferenceParserMixin
from bible.render import RenderMode, generate_summary, get_renderer


class Chapter(BibleLookupMixin, ReferenceParserMixin, Command):
    """Retrieve a Bible chapter."""

    bible_name: str = arg(inherited=True)
    book_name: Positional[str] = arg(inherited=True)
    chapter_number: Positional[int | str] = arg(
        help='The number of the chapter to retrieve'
    )

    @final
    @classmethod
    def epilog(cls):
        return 'Attribution:\n  Data provided by API.Bible — https://api.bible.com'

    @override
    async def pre_run_hook(self):
        self.bible = self.find_bible(self.bible_name)
        self.book = self.find_book(self.bible_name, self.book_name)
        self.chapters = await self.load_or_fetch_chapters(self.bible, self.book)
        self.renderer = get_renderer(self.bible_name, RenderMode.CHAPTER)

    @override
    async def run(self):
        """Main execution method for the Chapter command."""

        chapter = self.find_chapter(self.chapters, self.chapter_number)
        content = await self.load_or_fetch_chapter_content(
            self.bible, self.book, chapter
        )

        text = self.renderer(
            html=content.get('content', ''),
            reference=content.get('reference', ''),
            summary=generate_summary(content.get('content', '')),
            metadata={
                'Book': content.get('reference', '').split()[0],
                'Chapter': content.get('number'),
                'Verses': content.get('verseCount'),
                'Copyright': content.get('copyright', '').replace('©', '(c)'),
            },
        )
        console.out.print(text)


class Chapters(BibleLookupMixin, ReferenceParserMixin, Command):
    """Retrieve multiple chapters of a Bible book."""

    bible_name: str = arg(inherited=True)
    book_name: Positional[str] = arg(inherited=True)
    chapter_numbers: Positional[list[int | str]] = arg(
        None,
        help="The list of chapter numbers or ranges. For example, '1 2 3', '2-4'.",
    )

    @override
    async def pre_run_hook(self):
        """Load bible, book, and chapter list."""
        self.bible = self.find_bible(self.bible_name)
        self.book = self.find_book(self.bible_name, self.book_name)
        self.chapters = await self.load_or_fetch_chapters(self.bible, self.book)
        self.renderer = get_renderer(self.bible_name, RenderMode.CHAPTER)

    @override
    async def run(self):
        """Main execution method for the Chapters command."""

        allowed = self.expand_chapter_numbers(self.chapter_numbers)

        async def fetch_chapter(chapter):
            number = chapter.get('number')

            if number is None:
                logger.warning(
                    f"Missing chapter number for '{self.book_name}'. Skipping."
                )
                return None

            # --- intro handling ---
            if number == 'intro':
                if allowed and 'intro' not in allowed:
                    return None
            else:
                # numeric chapter
                try:
                    num = int(number)
                except ValueError:
                    logger.warning(
                        f"Invalid chapter number '{number}' for '{self.book_name}'. Skipping."
                    )
                    return None

                if allowed and num not in allowed:
                    return None

            # --- fetch content via mixin ---
            return await self.load_or_fetch_chapter_content(
                self.bible, self.book, chapter
            )

        async with Spinner('Fetching chapters...'):
            # Run all fetches concurrently
            tasks = [fetch_chapter(ch) for ch in self.chapters]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            results = [r for r in results if isinstance(r, dict)]

            if not results:
                raise ValueError('No chapters retrieved.')

        # Render each chapter
        for chapter in results:
            text = self.renderer(
                html=chapter.get('content', ''),
                reference=chapter.get('reference', ''),
                summary=generate_summary(chapter.get('content', '')),
                metadata={
                    'Book': chapter.get('reference', '').split()[0],
                    'Chapter': chapter.get('number'),
                    'Verses': chapter.get('verseCount'),
                    'Copyright': chapter.get('copyright', '').replace('©', '(c)'),
                },
            )
            console.out.print(text)
