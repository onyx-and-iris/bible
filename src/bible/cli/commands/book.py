from typing import final

from clypi import Command, arg
from loguru import logger
from typing_extensions import override

from bible.api import BibleAPI
from bible.sqlite import cache_json, load_json

from .book_commands import Chapter, Chapters, List, Verse, Verses


class Book(Command):
    """Manage Bible books, including listing and retrieving chapters."""

    subcommand: List | Chapter | Chapters | Verse | Verses
    bible_name: str = arg(inherited=True)

    @final
    @classmethod
    def epilog(cls):
        return 'Attribution:\n  Data provided by Bible.API — https://api.bible.com'

    @override
    async def pre_run_hook(self):
        """Hook to run before the main command execution."""
        if not self.bible_name:
            raise ValueError("The 'bible_name' flag is required.")

        bibles = load_json('bibles:list')
        bible = next((b for b in bibles if b.get('name') == self.bible_name), None)
        if not bible:
            raise ValueError(f"Bible with name '{self.bible_name}' not found.")

        key = f'books:list:{self.bible_name}'
        books = load_json(key)
        if books:
            logger.debug(f"Using cached list of Bible books for '{self.bible_name}'.")
            return

        logger.debug(f"Fetching list of Bible books for '{self.bible_name}'.")
        async with BibleAPI() as api:
            response = await api.get_books(bible.get('id', ''))
            data = response.get('data', [])
            if not data:
                raise ValueError('Unable to fetch list of Bible books from the API.')
            cache_json(key, data)
