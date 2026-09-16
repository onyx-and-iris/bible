from typing import final

from clypi import Command, arg
from loguru import logger
from typing_extensions import override

from bible import console
from bible.sqlite import load_json


class List(Command):
    """List all available Bible books."""

    bible_name: str = arg(inherited=True)
    contains: str = arg(
        None,
        help='Filter Bible books by name containing this string',
        group='Filter',
    )
    sort: bool = arg(
        False,
        help='Sort the Bible books alphabetically',
        group='Filter',
    )

    @final
    @classmethod
    def epilog(cls):
        return 'Attribution:\n  Data provided by Bible.API — https://api.bible.com'

    @override
    async def run(self):
        """List all Bible books, optionally filtered by the 'contains' argument."""
        books = load_json(f'books:list:{self.bible_name}')
        if self.sort:
            books = sorted(books, key=lambda x: x.get('name', '').lower())
        seen = set()
        for book in books:
            if (
                self.contains
                and self.contains.lower() not in book.get('name', '').lower()
            ):
                continue

            if book.get('name', '') in seen:
                logger.debug(f'Skipping duplicate Bible book: {book.get("name", "")}')
                continue

            console.out.print(f'{book.get("name", "")}')
            seen.add(book.get('name', ''))
