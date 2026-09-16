import asyncio
from typing import final

from clypi import Command, Positional, arg
from loguru import logger
from typing_extensions import override

from bible import console
from bible.api import BibleAPI
from bible.render import generate_summary, render_chapter
from bible.sqlite import cache_json, load_json


class Chapter(Command):
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
        bibles = load_json('bibles:list')
        bible = next((b for b in bibles if b.get('name') == self.bible_name), None)
        if not bible:
            raise ValueError(f"Bible with name '{self.bible_name}' not found.")

        books = load_json(f'books:list:{self.bible_name}')
        book = next((bk for bk in books if bk.get('name') == self.book_name), None)
        if not book:
            raise ValueError(f"Book with name '{self.book_name}' not found.")

        key = f'chapters:list:{self.bible_name}:{self.book_name}'
        chapters = load_json(key)

        if chapters:
            logger.debug(
                f"Using cached list of chapters for '{self.bible_name}:{self.book_name}'."
            )
            return

        async with BibleAPI() as api:
            response = await api.get_chapters(bible['id'], book['id'])
            chapters = response.get('data', [])
            if not chapters:
                raise ValueError(f"No chapters found for '{self.book_name}'.")
            cache_json(key, chapters)

    @override
    async def run(self):
        """Main execution method for the Chapter command."""

        bibles = load_json('bibles:list')
        bible = next((b for b in bibles if b.get('name') == self.bible_name), None)
        if not bible:
            raise ValueError(f"Bible with name '{self.bible_name}' not found.")

        chapters = load_json(f'chapters:list:{self.bible_name}:{self.book_name}')
        chapter = next(
            (
                ch
                for ch in chapters
                if (
                    (ch.get('number') == 'intro' and self.chapter_number == 'intro')
                    or (
                        ch.get('number') not in ('intro', None)
                        and str(self.chapter_number) == str(ch.get('number'))
                    )
                )
            ),
            None,
        )

        if not chapter:
            raise ValueError(
                f"Chapter number '{self.chapter_number}' not found in book '{self.book_name}'."
            )

        key = (
            f'chapters:content:{self.bible_name}:{self.book_name}:{self.chapter_number}'
        )
        chapter_cache = load_json(key)

        if not chapter_cache:
            async with BibleAPI() as api:
                response = await api.get_chapter(bible['id'], chapter['id'])
                chapter_cache = response.get('data', {})
                if not chapter_cache:
                    raise ValueError(
                        f"No content found for chapter '{self.bible_name}:{self.book_name}:{self.chapter_number}'."
                    )
                cache_json(key, chapter_cache)

        text = render_chapter(
            html=chapter_cache.get('content', ''),
            reference=chapter_cache.get('reference', ''),
            summary=generate_summary(chapter_cache.get('content', '')),
            metadata={
                'Book': chapter_cache.get('reference', '').split()[0],
                'Chapter': chapter_cache.get('number'),
                'Verses': chapter_cache.get('verseCount'),
                'Copyright': chapter_cache.get('copyright', '').replace('©', '(c)'),
            },
        )
        console.out.print(text)


class Chapters(Command):
    """Retrieve multiple chapters of a Bible book."""

    bible_name: str = arg(inherited=True)
    book_name: Positional[str] = arg(inherited=True)
    chapter_numbers: Positional[list[int | str]] = arg(
        None,
        help="The list of chapter numbers or ranges. For example, '1 2 3', '2-4'.",
    )

    @final
    @classmethod
    def epilog(cls):
        return 'Attribution:\n  Data provided by API.Bible — https://api.bible.com'

    @override
    async def pre_run_hook(self):
        bibles = load_json('bibles:list')
        bible = next((b for b in bibles if b.get('name') == self.bible_name), None)
        if not bible:
            raise ValueError(f"Bible with name '{self.bible_name}' not found.")

        books = load_json(f'books:list:{self.bible_name}')
        book = next((bk for bk in books if bk.get('name') == self.book_name), None)
        if not book:
            raise ValueError(f"Book with name '{self.book_name}' not found.")

        key = f'chapters:list:{self.bible_name}:{self.book_name}'
        chapters = load_json(key)

        if chapters:
            logger.debug(
                f"Using cached list of chapters for '{self.bible_name}:{self.book_name}'."
            )
            return

        async with BibleAPI() as api:
            response = await api.get_chapters(bible['id'], book['id'])
            chapters = response.get('data', [])
            if not chapters:
                raise ValueError(f"No chapters found for '{self.book_name}'.")
            cache_json(key, chapters)

    @override
    async def run(self):
        """Main execution method for the Chapters command."""

        # --- Bible lookup ---
        bibles = load_json('bibles:list')
        bible = next((b for b in bibles if b.get('name') == self.bible_name), None)
        if not bible:
            raise ValueError(f"Bible with name '{self.bible_name}' not found.")

        # --- Chapter list ---
        chapters = load_json(f'chapters:list:{self.bible_name}:{self.book_name}')
        allowed = expand_chapter_numbers(self.chapter_numbers)

        async def fetch_chapter(ch):
            number = ch.get('number')

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

            # --- cache lookup ---
            key = f'chapters:content:{self.bible_name}:{self.book_name}:{number}'
            cached = load_json(key)
            if cached:
                logger.debug(
                    f"Using cached content for chapter '{self.book_name} {number}'."
                )
                return cached

            # --- API fetch ---
            async with BibleAPI() as api:
                response = await api.get_chapter(bible['id'], ch['id'])
                data = response.get('data', {})
                if not data:
                    logger.warning(
                        f"No content found for chapter '{self.book_name} {number}'."
                    )
                    return None
                cache_json(key, data)
                return data

        # --- concurrent fetch ---
        tasks = [fetch_chapter(ch) for ch in chapters]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        results = [r for r in results if isinstance(r, dict)]

        if not results:
            raise ValueError('No chapters retrieved.')

        # --- render ---
        for chapter in results:
            text = render_chapter(
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


def expand_chapter_numbers(chapter_numbers):
    if not chapter_numbers:
        return None

    allowed = set()

    for item in chapter_numbers:
        # intro
        if item == 'intro':
            allowed.add('intro')
            continue

        # numeric int
        if isinstance(item, int):
            allowed.add(item)
            continue

        # numeric string
        if isinstance(item, str) and item.isdigit():
            allowed.add(int(item))
            continue

        # range string "2-4"
        if isinstance(item, str) and '-' in item:
            try:
                start, end = item.split('-', maxsplit=1)
                allowed.update(range(int(start), int(end) + 1))
            except ValueError:
                logger.warning(f"Invalid chapter range '{item}'. Skipping.")
            continue

        # anything else is invalid
        logger.warning(f"Invalid chapter number '{item}'. Skipping.")

    return allowed
